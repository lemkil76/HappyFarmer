"""
HappyFarmer - Google Drive Cloud Sync
integrations/cloud_sync.py  (moved from cloud_sync.py)
Revised by Claude - 2026-03-20

All paths from config/paths.py - change BASE_DIR there to relocate.

Cron (every 15 min):
    */15 * * * * /usr/bin/python3 /home/pi/happyfarmer/integrations/cloud_sync.py

Install: pip install google-api-python-client google-auth
See docs/SETUP.md step 3 for Google service account setup.
"""

import logging
import datetime
from pathlib import Path

from config.paths import DATA_DIR, TIMELAPSE_DIR, LOG_FILE, SA_FILE, SYNC_LOG_FILE

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# ── Configuration ──────────────────────────────────────────────────────────────
DRIVE_ROOT_NAME          = "HappyFarmer"
DELETE_IMAGES_AFTER_UPLOAD = True
MAX_LOG_BYTES            = 5 * 1024 * 1024  # 5 MB before rotation

logging.basicConfig(
    filename=str(SYNC_LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("cloud_sync")

SCOPES = ["https://www.googleapis.com/auth/drive"]


# ── Drive client ───────────────────────────────────────────────────────────────

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        str(SA_FILE), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# ── Folder management ──────────────────────────────────────────────────────────

def get_or_create_folder(service, name: str, parent_id: str = None) -> str:
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = service.files().list(q=query, fields="files(id)").execute()
    files   = results.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    folder = service.files().create(body=meta, fields="id").execute()
    log.info(f"Created Drive folder: {name}")
    return folder["id"]


def ensure_folder_structure(service) -> dict:
    root = get_or_create_folder(service, DRIVE_ROOT_NAME)
    sens = get_or_create_folder(service, "sensors",   root)
    tl   = get_or_create_folder(service, "timelapse", root)
    img  = get_or_create_folder(service, "images",    tl)
    vid  = get_or_create_folder(service, "videos",    tl)
    logs = get_or_create_folder(service, "logs",      root)
    return {"sensors": sens, "images": img, "videos": vid, "logs": logs}


# ── Upload helpers ─────────────────────────────────────────────────────────────

def file_exists_in_drive(service, name: str, folder_id: str):
    query   = f"name='{name}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    files   = results.get("files", [])
    return files[0]["id"] if files else None


def upload_or_update(service, local_path: Path, folder_id: str, mime: str) -> bool:
    """Upload or update a file in Drive. Returns True on success."""
    try:
        media       = MediaFileUpload(str(local_path), mimetype=mime, resumable=True)
        existing_id = file_exists_in_drive(service, local_path.name, folder_id)
        if existing_id:
            service.files().update(fileId=existing_id, media_body=media).execute()
            log.info(f"Updated in Drive: {local_path.name}")
        else:
            meta = {"name": local_path.name, "parents": [folder_id]}
            service.files().create(body=meta, media_body=media, fields="id").execute()
            log.info(f"Uploaded to Drive: {local_path.name}")
        return True
    except HttpError as e:
        log.error(f"Drive error {local_path.name}: {e}")
        return False
    except Exception as e:
        log.error(f"Upload error {local_path.name}: {e}")
        return False


# ── Sync routines ──────────────────────────────────────────────────────────────

def sync_sensor_data(service, folders: dict):
    """Upload today's and yesterday's CSV to Drive/sensors/."""
    today     = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    for date in [yesterday, today]:
        csv = DATA_DIR / f"sensors_{date}.csv"
        if csv.exists() and csv.stat().st_size > 0:
            upload_or_update(service, csv, folders["sensors"], "text/csv")


def sync_timelapse_images(service, folders: dict):
    """Upload all JPEG images and delete locally after successful upload."""
    images = sorted(TIMELAPSE_DIR.glob("*.jpg"))
    if not images:
        return
    log.info(f"Syncing {len(images)} timelapse images...")
    for img in images:
        ok = upload_or_update(service, img, folders["images"], "image/jpeg")
        if ok and DELETE_IMAGES_AFTER_UPLOAD:
            img.unlink()
            log.info(f"Deleted locally: {img.name}")


def sync_timelapse_videos(service, folders: dict):
    """Upload MP4 videos and delete locally after successful upload."""
    for video in TIMELAPSE_DIR.glob("*.mp4"):
        ok = upload_or_update(service, video, folders["videos"], "video/mp4")
        if ok and DELETE_IMAGES_AFTER_UPLOAD:
            video.unlink()
            log.info(f"Deleted locally: {video.name}")


def sync_log(service, folders: dict):
    """Upload log file and rotate locally if over MAX_LOG_BYTES."""
    if not LOG_FILE.exists():
        return
    upload_or_update(service, LOG_FILE, folders["logs"], "text/plain")
    if LOG_FILE.stat().st_size > MAX_LOG_BYTES:
        lines = LOG_FILE.read_text(errors="replace").splitlines()
        LOG_FILE.write_text("\n".join(lines[-500:]) + "\n")
        log.info("Log rotated locally (kept last 500 lines)")


def purge_old_sensor_files(service, folders: dict, keep_days: int = 90):
    """Delete Drive sensor CSV files older than keep_days."""
    cutoff  = datetime.date.today() - datetime.timedelta(days=keep_days)
    query   = f"'{folders['sensors']}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    for f in results.get("files", []):
        try:
            date_str  = f["name"].replace("sensors_", "").replace(".csv", "")
            file_date = datetime.date.fromisoformat(date_str)
            if file_date < cutoff:
                service.files().delete(fileId=f["id"]).execute()
                log.info(f"Purged from Drive: {f['name']}")
        except Exception:
            pass


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if not SA_FILE.exists():
        log.error(f"service_account.json not found at {SA_FILE}. See docs/SETUP.md.")
        return
    log.info("=== cloud_sync start ===")
    try:
        service = get_drive_service()
        folders = ensure_folder_structure(service)
        sync_sensor_data(service, folders)
        sync_timelapse_images(service, folders)
        sync_timelapse_videos(service, folders)
        sync_log(service, folders)
        if datetime.datetime.now().hour == 3:
            purge_old_sensor_files(service, folders, keep_days=90)
    except Exception as e:
        log.exception(f"Unhandled error in cloud_sync: {e}")
    log.info("=== cloud_sync done ===")


if __name__ == "__main__":
    main()
