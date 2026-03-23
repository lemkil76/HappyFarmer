"""
HappyFarmer - NAS Sync
integrations/cloud_sync.py
Revised by Claude - 2026-03-20

Syncs sensor data, timelapse images/videos and logs to a Synology NAS
mounted on the Pi via SMB/CIFS. Also writes sample_data.json so the
dashboard at http://server:8080/ gets fresh data on every sync.

All paths from config/paths.py - change NAS_MOUNT there if needed.

Cron (every 15 min):
    */15 * * * * cd /home/pi/happyfarmer && /usr/bin/python3 -m integrations.cloud_sync

Mount the NAS first (see docs/SETUP.md step 6):
    sudo mount -t cifs //NAS_IP/HappyFarmer /mnt/nas/happyfarmer \
      -o username=happyfarmer,password=LÖSENORD,uid=pi,gid=pi
"""

import json
import logging
import datetime
import shutil
from pathlib import Path

from config.paths import (
    DATA_DIR, TIMELAPSE_DIR, LOG_FILE, SYNC_LOG_FILE,
    NAS_MOUNT, NAS_SENSORS_DIR, NAS_TIMELAPSE_DIR,
    NAS_LOGS_DIR, NAS_DASHBOARD_DIR, NAS_SAMPLE_DATA,
)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=str(SYNC_LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("cloud_sync")

# Max loggstorlek innan lokal rotation (5 MB)
MAX_LOG_BYTES = 5 * 1024 * 1024

# Radera lokala bilder/videor efter lyckad uppladdning
DELETE_AFTER_UPLOAD = True


# ==============================================================================
# NAS-tillgänglighet
# ==============================================================================

def nas_is_mounted() -> bool:
    """Kontrollera att NAS-mounten är tillgänglig."""
    return NAS_MOUNT.exists() and NAS_MOUNT.is_dir()


def ensure_nas_dirs():
    """Skapa NAS-mappar om de saknas."""
    for d in [NAS_SENSORS_DIR, NAS_TIMELAPSE_DIR, NAS_LOGS_DIR, NAS_DASHBOARD_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# Filsynk: sensorer
# ==============================================================================

def sync_sensor_data():
    """
    Kopiera dagens och gårdagens sensor-CSV till NAS.
    Befintlig fil på NAS skrivs över (ny data tillkommer löpande).
    """
    today     = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    for date in [yesterday, today]:
        src = DATA_DIR / f"sensors_{date}.csv"
        if src.exists() and src.stat().st_size > 0:
            dst = NAS_SENSORS_DIR / src.name
            shutil.copy2(src, dst)
            log.info(f"Sensor-CSV synkad: {src.name}")


# ==============================================================================
# Filsynk: timelapse
# ==============================================================================

def sync_timelapse_images():
    """
    Kopiera alla JPEG-bilder till NAS och radera lokalt.
    Frigör utrymme på Pi:ns minneskort.
    """
    images = sorted(TIMELAPSE_DIR.glob("*.jpg"))
    if not images:
        return
    nas_img = NAS_TIMELAPSE_DIR / "images"
    nas_img.mkdir(parents=True, exist_ok=True)
    log.info(f"Synkroniserar {len(images)} timelapse-bilder...")
    for img in images:
        dst = nas_img / img.name
        shutil.copy2(img, dst)
        log.info(f"Bild synkad: {img.name}")
        if DELETE_AFTER_UPLOAD:
            img.unlink()
            log.info(f"Raderad lokalt: {img.name}")


def sync_timelapse_videos():
    """Kopiera MP4-videor till NAS och radera lokalt."""
    nas_vid = NAS_TIMELAPSE_DIR / "videos"
    nas_vid.mkdir(parents=True, exist_ok=True)
    for video in TIMELAPSE_DIR.glob("*.mp4"):
        dst = nas_vid / video.name
        shutil.copy2(video, dst)
        log.info(f"Video synkad: {video.name}")
        if DELETE_AFTER_UPLOAD:
            video.unlink()


# ==============================================================================
# Filsynk: logg
# ==============================================================================

def sync_log():
    """
    Kopiera loggfilen till NAS.
    Rotera lokalt om den överstiger MAX_LOG_BYTES.
    """
    if not LOG_FILE.exists():
        return
    dst = NAS_LOGS_DIR / LOG_FILE.name
    shutil.copy2(LOG_FILE, dst)
    log.info("Logg synkad till NAS")
    if LOG_FILE.stat().st_size > MAX_LOG_BYTES:
        lines = LOG_FILE.read_text(errors="replace").splitlines()
        LOG_FILE.write_text("\n".join(lines[-500:]) + "\n")
        log.info("Loggfil roterad lokalt (behöll 500 rader)")


# ==============================================================================
# sample_data.json - dashboard-feed
# ==============================================================================

def build_sample_data() -> dict:
    """
    Bygg en färsk sample_data.json från senaste sensor-CSV och systemstatus.
    Returnerar en dict som skrivs till NAS_SAMPLE_DATA.
    """
    now   = datetime.datetime.now()
    today = datetime.date.today()
    csv   = DATA_DIR / f"sensors_{today}.csv"

    # ── Läs senaste sensoravläsning från dagens CSV ───────────────────────────
    current = {
        "timestamp":          now.isoformat(),
        "air_temperature_c":  None,
        "humidity_pct":       None,
        "water_temperature_c":None,
        "ph":                 None,
        "lux":                None,
        "lux_description":    "okänd",
    }
    history = {
        "description":         "Last 8 readings (newest last)",
        "interval_minutes":    5,
        "air_temperature_c":   [],
        "humidity_pct":        [],
        "water_temperature_c": [],
        "ph":                  [],
        "lux":                 [],
    }
    daily = {
        "date":              str(today),
        "air_temp_avg_c":    None,
        "air_temp_min_c":    None,
        "air_temp_max_c":    None,
        "water_temp_avg_c":  None,
        "humidity_avg_pct":  None,
        "ph_avg":            None,
        "lux_avg":           None,
        "pump_cycles":       0,
        "images_captured_lowres": len(list(TIMELAPSE_DIR.glob("*_lowres.jpg"))),
        "images_captured_hires":  len(list(TIMELAPSE_DIR.glob("*_hires.jpg"))),
        "social_posts":      0,
    }

    if csv.exists():
        try:
            lines = csv.read_text().splitlines()
            # Hoppa över header, ta senaste 8 rader
            rows = [l.split(",") for l in lines[1:] if l.strip()]
            if rows:
                # Senaste avläsning
                last = rows[-1]
                def safe(val, cast=float):
                    try: return cast(val)
                    except: return None

                current["timestamp"]           = last[0] if last[0] else now.isoformat()
                current["air_temperature_c"]   = safe(last[1])
                current["humidity_pct"]        = safe(last[2])
                current["water_temperature_c"] = safe(last[3])
                current["ph"]                  = safe(last[4])
                current["lux"]                 = safe(last[5], int)

                lux = current["lux"]
                if lux is None:           current["lux_description"] = "okänd"
                elif lux < 100:           current["lux_description"] = "mörker"
                elif lux < 1000:          current["lux_description"] = "inomhusljus"
                elif lux < 5000:          current["lux_description"] = "molnigt"
                else:                     current["lux_description"] = "dag"

                # Sparkline-historik: senaste 8 avläsningar
                recent = rows[-8:]
                history["air_temperature_c"]   = [safe(r[1]) for r in recent]
                history["humidity_pct"]        = [safe(r[2]) for r in recent]
                history["water_temperature_c"] = [safe(r[3]) for r in recent]
                history["ph"]                  = [safe(r[4]) for r in recent]
                history["lux"]                 = [safe(r[5], int) for r in recent]

                # Dagssammanfattning
                def avg(vals):
                    v = [x for x in vals if x is not None]
                    return round(sum(v) / len(v), 1) if v else None

                airs   = [safe(r[1]) for r in rows]
                waters = [safe(r[3]) for r in rows]
                hums   = [safe(r[2]) for r in rows]
                phs    = [safe(r[4]) for r in rows]
                luxes  = [safe(r[5], int) for r in rows]

                daily["air_temp_avg_c"]   = avg(airs)
                daily["air_temp_min_c"]   = round(min(v for v in airs if v), 1) if any(v for v in airs if v) else None
                daily["air_temp_max_c"]   = round(max(v for v in airs if v), 1) if any(v for v in airs if v) else None
                daily["water_temp_avg_c"] = avg(waters)
                daily["humidity_avg_pct"] = avg(hums)
                daily["ph_avg"]           = avg(phs)
                daily["lux_avg"]          = int(avg([v for v in luxes if v]) or 0)

        except Exception as e:
            log.error(f"CSV parse failed: {e}")

    # ── Räkna timelapse-bilder ────────────────────────────────────────────────
    nas_img = NAS_TIMELAPSE_DIR / "images"
    if nas_img.exists():
        daily["images_captured_lowres"] = len(list(nas_img.glob("*_lowres.jpg")))
        daily["images_captured_hires"]  = len(list(nas_img.glob("*_hires.jpg")))

    # ── Senaste timelapse-bild ────────────────────────────────────────────────
    nas_img_dir = NAS_TIMELAPSE_DIR / "images"
    latest_imgs = sorted(nas_img_dir.glob("*.jpg")) if nas_img_dir.exists() else []
    latest_img  = latest_imgs[-1] if latest_imgs else None

    return {
        "_comment":       "Auto-generated by integrations/cloud_sync.py",
        "_format_version": "1.0",
        "_generated":     now.isoformat(),

        "latest_image": {
            "filename":    latest_img.name if latest_img else "ingen bild ännu",
            "captured_at": now.isoformat(),
            "resolution":  "640x480",
            "path_on_nas": str(NAS_TIMELAPSE_DIR / "images" / latest_img.name) if latest_img else "",
        },

        "current_readings": current,

        "actuator_states": {
            "pump":        "unknown",
            "grow_lights": "unknown",
            "fan":         "unknown",
            "heater":      "unknown",
        },

        "system": {
            "loop_count":        0,
            "sleep_minutes":     5,
            "drive_sync_status": "synced",
            "drive_sync_last":   now.isoformat(),
            "uptime_hours":      0.0,
            "simulation_mode":   False,
        },

        "pump_schedule": {
            "on_seconds":            1800,
            "off_seconds":           900,
            "next_cycle_in_minutes": 0,
            "cycles_today":          daily.get("pump_cycles", 0),
        },

        "light_schedule": {
            "on_hour":  6,
            "off_hour": 23,
            "light_hours": 5,
            "today": [
                {"start":"06:00","end":"11:00","status":"done",   "label":"Morgon"},
                {"start":"11:30","end":"12:00","status":"active", "label":"Middag"},
                {"start":"12:15","end":"12:45","status":"next",   "label":"Eftermiddag"},
                {"start":"18:00","end":"23:00","status":"next",   "label":"Kväll"},
            ],
        },

        "social_media": {
            "enabled":     False,
            "platform":    "X / Twitter",
            "handle":      "@lemkil76",
            "recent_posts": [],
            "next_post_in_loops": 0,
        },

        "sensor_history": history,

        "thresholds": {
            "temp_min_c":      18.0,
            "temp_max_c":      28.0,
            "ph_min":           5.5,
            "ph_max":           7.5,
            "humidity_min_pct": 50.0,
            "humidity_max_pct": 80.0,
            "lux_max":         12000,
        },

        "daily_summary": daily,
    }


def write_sample_data():
    """Skriv färsk sample_data.json till NAS så dashboarden kan hämta den."""
    try:
        data = build_sample_data()
        NAS_DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
        NAS_SAMPLE_DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        log.info(f"sample_data.json skriven till {NAS_SAMPLE_DATA}")
    except Exception as e:
        log.error(f"Kunde inte skriva sample_data.json: {e}")


# ==============================================================================
# Gallring av gamla sensor-CSV på NAS
# ==============================================================================

def purge_old_sensor_files(keep_days: int = 90):
    """Ta bort sensor-CSV-filer på NAS som är äldre än keep_days dagar."""
    cutoff = datetime.date.today() - datetime.timedelta(days=keep_days)
    for f in NAS_SENSORS_DIR.glob("sensors_*.csv"):
        try:
            date_str  = f.stem.replace("sensors_", "")
            file_date = datetime.date.fromisoformat(date_str)
            if file_date < cutoff:
                f.unlink()
                log.info(f"Gallrad från NAS: {f.name}")
        except Exception:
            pass


# ==============================================================================
# Huvudfunktion
# ==============================================================================

def main():
    if not nas_is_mounted():
        log.error(
            f"NAS ej tillgänglig på {NAS_MOUNT}. "
            "Montera NAS-sharetjänsten enligt docs/SETUP.md steg 6."
        )
        return

    log.info("=== cloud_sync start ===")
    try:
        ensure_nas_dirs()
        sync_sensor_data()
        sync_timelapse_images()
        sync_timelapse_videos()
        sync_log()

        # Skriv dashboard-data sist (när allt annat är synkat)
        write_sample_data()

        # Gallra en gång per dag vid 03:00
        if datetime.datetime.now().hour == 3:
            purge_old_sensor_files(keep_days=90)

    except Exception as e:
        log.exception(f"Oväntat fel i cloud_sync: {e}")

    log.info("=== cloud_sync klar ===")


if __name__ == "__main__":
    main()
