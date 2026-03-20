"""
HappyFarmer - Google Drive Sync
Revised by Claude - 2026-03-20

Batchar sensordata (CSV) och timelapse-bilder till Google Drive.
Kors lokala filer efter lyckad uppladdning for att spara minne pa Pi:n.

Korsstruktur i Google Drive:
  HappyFarmer/
    sensor_data/
      sensors_2026-03-20.csv
      sensors_2026-03-21.csv
      ...
    timelapse/
      lowres/
        20260320_120000_lowres.jpg
        ...
      videos/
        timelapse_2026-03-20.mp4
        ...

Installera beroenden:
    pip install google-api-python-client google-auth

Kom igang - Google Drive API:
  1. Ga till https://console.cloud.google.com
  2. Skapa ett nytt projekt (t.ex. "HappyFarmer")
  3. Aktivera "Google Drive API"
  4. Skapa credentials: "OAuth 2.0 Client ID" -> typ "Desktop app"
  5. Ladda ner credentials.json och lagg den pa Pi:n i /home/pi/happyfarmer/
  6. Forsta gangen: kor skriptet manuellt pa Pi:n for att autentisera
     -> oppnar en webbsida dar du loggar in med ditt Google-konto
     -> token.json sparas automatiskt for framtida kok utan inloggning

Miljovariabel:
    HAPPYFARMER_GDRIVE_CREDENTIALS  (stig till credentials.json)
"""

import os
import json
import logging
from pathlib import Path
from datetime import date, timedelta

log = logging.getLogger("happyfarmer.gdrive")

# ── Beroenden (graceful import) ────────────────────────────────────────────────
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    GDRIVE_AVAILABLE = True
except ImportError:
    log.warning("Google Drive libs ej installerade - kor: pip install google-api-python-client google-auth google-auth-oauthlib")
    GDRIVE_AVAILABLE = False

# ── Konfiguration ──────────────────────────────────────────────────────────────
CREDENTIALS_FILE = os.environ.get(
    "HAPPYFARMER_GDRIVE_CREDENTIALS",
    "/home/pi/happyfarmer/credentials.json"
)
TOKEN_FILE       = "/home/pi/happyfarmer/token.json"
SCOPES           = ["https://www.googleapis.com/auth/drive.file"]

DATA_DIR      = Path("/home/pi/happyfarmer/data")
TIMELAPSE_DIR = Path("/home/pi/happyfarmer/timelapse")

# Behall lokala CSV-filer i N dagar innan de tas bort efter uppladdning
KEEP_CSV_DAYS = 2

# Behall lokala bilder i N dagar efter uppladdning
KEEP_IMAGE_DAYS = 1


# ── Google Drive autentisering ─────────────────────────────────────────────────

def get_drive_service():
    """
    Returnerar en autentiserad Drive-tjänst.
    Forsta gangen: oppnar OAuth-flow i webblasaren.
    Darefter: anvander sparad token.json utan interaktion.
    """
    if not GDRIVE_AVAILABLE:
        return None

    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        Path(TOKEN_FILE).write_text(creds.to_json())

    return build("drive", "v3", credentials=creds)


# ── Mapphantering ──────────────────────────────────────────────────────────────

def get_or_create_folder(service, name: str, parent_id: str = None) -> str:
    """Returnerar ID for en mapp i Drive, skapar den om den inte finns."""
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    log.info(f"Skapade Drive-mapp: {name}")
    return folder["id"]


def ensure_folder_structure(service) -> dict:
    """
    Skapar mappstrukturen i Drive om den inte finns:
      HappyFarmer/sensor_data/
      HappyFarmer/timelapse/lowres/
      HappyFarmer/timelapse/videos/
    Returnerar dict med mapp-ID:n.
    """
    root    = get_or_create_folder(service, "HappyFarmer")
    sensors = get_or_create_folder(service, "sensor_data", root)
    tl      = get_or_create_folder(service, "timelapse", root)
    lowres  = get_or_create_folder(service, "lowres", tl)
    videos  = get_or_create_folder(service, "videos", tl)
    return {
        "root":         root,
        "sensor_data":  sensors,
        "lowres":       lowres,
        "videos":       videos,
    }


# ── Filuppladdning ─────────────────────────────────────────────────────────────

def upload_file(service, local_path: Path, folder_id: str, mime_type: str) -> bool:
    """
    Laddar upp en fil till angiven Drive-mapp.
    Om en fil med samma namn redan finns uppdateras den (ingen dubblett).
    Returnerar True vid lyckat resultat.
    """
    name = local_path.name

    # Kolla om filen redan finns (for att undvika dubletter vid omstart)
    existing = service.files().list(
        q=f"name='{name}' and '{folder_id}' in parents and trashed=false",
        fields="files(id)"
    ).execute().get("files", [])

    media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)

    try:
        if existing:
            service.files().update(
                fileId=existing[0]["id"],
                media_body=media
            ).execute()
            log.info(f"Uppdaterade i Drive: {name}")
        else:
            service.files().create(
                body={"name": name, "parents": [folder_id]},
                media_body=media,
                fields="id"
            ).execute()
            log.info(f"Laddade upp till Drive: {name}")
        return True
    except Exception as e:
        log.error(f"Uppladdning misslyckades for {name}: {e}")
        return False


# ── Synk-funktioner ────────────────────────────────────────────────────────────

def sync_sensor_data(service, folders: dict):
    """
    Laddar upp alla CSV-filer aldre an KEEP_CSV_DAYS och tar bort dem lokalt
    efter lyckad uppladdning.
    Dagens fil laddas upp men raderas INTE (den skrivs fortfarande till).
    """
    cutoff = date.today() - timedelta(days=KEEP_CSV_DAYS)
    uploaded = 0
    deleted = 0

    for csv_file in sorted(DATA_DIR.glob("sensors_*.csv")):
        # Parsa datum fran filnamn: sensors_2026-03-20.csv
        try:
            file_date = date.fromisoformat(csv_file.stem.replace("sensors_", ""))
        except ValueError:
            continue

        ok = upload_file(service, csv_file, folders["sensor_data"], "text/csv")
        if ok:
            uploaded += 1
            # Radera gamla filer lokalt efter uppladdning
            if file_date < cutoff:
                csv_file.unlink()
                deleted += 1
                log.info(f"Raderade lokal CSV: {csv_file.name}")

    log.info(f"CSV-synk klar: {uploaded} uppladdade, {deleted} raderade lokalt")


def sync_timelapse_images(service, folders: dict):
    """
    Laddar upp lowres-bilder till Drive och raderar dem lokalt efter
    KEEP_IMAGE_DAYS dagar for att spara utrymme pa Pi:n.
    """
    cutoff = date.today() - timedelta(days=KEEP_IMAGE_DAYS)
    uploaded = 0
    deleted = 0

    for img in sorted(TIMELAPSE_DIR.glob("*_lowres.jpg")):
        # Filnamn: 20260320_120000_lowres.jpg
        try:
            file_date = date(int(img.name[:4]), int(img.name[4:6]), int(img.name[6:8]))
        except (ValueError, IndexError):
            continue

        ok = upload_file(service, img, folders["lowres"], "image/jpeg")
        if ok:
            uploaded += 1
            if file_date < cutoff:
                img.unlink()
                deleted += 1
                log.info(f"Raderade lokal bild: {img.name}")

    log.info(f"Bild-synk klar: {uploaded} uppladdade, {deleted} raderade lokalt")


def sync_timelapse_video(service, folders: dict, video_path: str) -> bool:
    """
    Laddar upp en fardig timelapse-video till Drive och raderar den lokalt.
    Anropas fran main.py efter build_timelapse().
    """
    path = Path(video_path)
    if not path.exists():
        log.error(f"Video ej hittad: {video_path}")
        return False

    ok = upload_file(service, path, folders["videos"], "video/mp4")
    if ok:
        path.unlink()
        log.info(f"Raderade lokal video: {path.name}")
    return ok


# ── Huvudfunktion (kors som cron-jobb) ────────────────────────────────────────

def run_sync():
    """
    Synkar all data till Drive.
    Korsatt var 15:e minut via cron:
      */15 * * * * python3 /home/pi/happyfarmer/gdrive_sync.py >> /home/pi/happyfarmer/gdrive_sync.log 2>&1
    """
    if not GDRIVE_AVAILABLE:
        log.error("Google Drive libs saknas - avbryter synk")
        return

    log.info("=== Drive-synk startar ===")
    service = get_drive_service()
    if not service:
        log.error("Kunde inte autentisera mot Drive")
        return

    folders = ensure_folder_structure(service)
    sync_sensor_data(service, folders)
    sync_timelapse_images(service, folders)
    log.info("=== Drive-synk klar ===")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    run_sync()
