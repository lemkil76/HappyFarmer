"""
HappyFarmer - NAS Sync
integrations/cloud_sync.py
Revised by Claude - 2026-03-24

Synkar filer till NAS och skriver sample_data.json fran MariaDB.
Kors var 15:e minut via cron.

Cron:
    */15 * * * * cd /home/pi/happyfarmer && python3 -m integrations.cloud_sync
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
from integrations.db import build_sample_data_from_db, test_connection, log_system_event

logging.basicConfig(
       filename=str(SYNC_LOG_FILE),
       level=logging.INFO,
       format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("cloud_sync")

MAX_LOG_BYTES      = 5 * 1024 * 1024
DELETE_AFTER_UPLOAD = True


def nas_is_mounted() -> bool:
       return NAS_MOUNT.exists() and NAS_MOUNT.is_dir()


def ensure_nas_dirs():
       for d in [NAS_SENSORS_DIR, NAS_TIMELAPSE_DIR, NAS_LOGS_DIR, NAS_DASHBOARD_DIR]:
                  d.mkdir(parents=True, exist_ok=True)


def sync_sensor_data():
       today     = datetime.date.today()
       yesterday = today - datetime.timedelta(days=1)
       for date in [yesterday, today]:
                  src = DATA_DIR / f"sensors_{date}.csv"
                  if src.exists() and src.stat().st_size > 0:
                                 shutil.copy2(src, NAS_SENSORS_DIR / src.name)
                                 log.info(f"CSV synkad: {src.name}")


   def sync_timelapse_images():
          images = sorted(TIMELAPSE_DIR.glob("*.jpg"))
          if not images:
                     return
                 nas_img = NAS_TIMELAPSE_DIR / "images"
    nas_img.mkdir(parents=True, exist_ok=True)
    for img in images:
               shutil.copy2(img, nas_img / img.name)
               log.info(f"Bild synkad: {img.name}")
               if DELETE_AFTER_UPLOAD:
                              img.unlink()


def sync_timelapse_videos():
       nas_vid = NAS_TIMELAPSE_DIR / "videos"
    nas_vid.mkdir(parents=True, exist_ok=True)
    for video in TIMELAPSE_DIR.glob("*.mp4"):
               shutil.copy2(video, nas_vid / video.name)
               log.info(f"Video synkad: {video.name}")
               if DELETE_AFTER_UPLOAD:
                              video.unlink()


def sync_log():
       if not LOG_FILE.exists():
                  return
              shutil.copy2(LOG_FILE, NAS_LOGS_DIR / LOG_FILE.name)
    if LOG_FILE.stat().st_size > MAX_LOG_BYTES:
               lines = LOG_FILE.read_text(errors="replace").splitlines()
               LOG_FILE.write_text("\n".join(lines[-500:]) + "\n")
               log.info("Logg roterad")


def write_sample_data():
       """
           Bygg sample_data.json fran MariaDB och skriv till NAS-dashboard-mappen.
               Faller tillbaka pa CSV om DB ej tillganglig.
                   """
    try:
               if test_connection():
                              data = build_sample_data_from_db()
                              log.info("sample_data.json byggd fran MariaDB")
    else:
            data = _build_from_csv()
                   log.warning("DB ej tillganglig - anvander CSV-fallback")

        NAS_DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
        NAS_SAMPLE_DATA.write_text(
                       json.dumps(data, ensure_ascii=False, indent=2, default=str)
        )
        log.info(f"sample_data.json skriven till {NAS_SAMPLE_DATA}")
except Exception as e:
        log.error(f"write_sample_data: {e}")


def _build_from_csv() -> dict:
       """CSV-fallback om DB ej ar tillganglig."""
    now   = datetime.datetime.now()
    today = datetime.date.today()
    csv   = DATA_DIR / f"sensors_{today}.csv"

    current = {
               "timestamp": now.isoformat(),
               "air_temperature_c": None, "humidity_pct": None,
               "water_temperature_c": None, "ph": None,
               "lux": None, "lux_description": "okand",
    }
    history = {
               "description": "Last 8 readings (CSV fallback)",
               "interval_minutes": 5,
               "air_temperature_c": [], "humidity_pct": [],
               "water_temperature_c": [], "ph": [], "lux": [],
    }

    if csv.exists():
               try:
                              rows = [l.split(",") for l in csv.read_text().splitlines()[1:] if l.strip()]
                              if rows:
                                                 last = rows[-1]
                                                 def safe(v, cast=float):
                                                                        try: return cast(v)
                                                                                               except: return None
                                                                                                                  current.update({
                                                                        "timestamp": last[0],
                                                                        "air_temperature_c":   safe(last[1]),
                                                                        "humidity_pct":        safe(last[2]),
                                                                        "water_temperature_c": safe(last[3]),
                                                                        "ph":                  safe(last[4]),
                                                                        "lux":                 safe(last[5], int),
                                                                        })
                                                                    r8 = rows[-8:]
                                                 history["air_temperature_c"]   = [safe(r[1]) for r in r8]
                                                 history["humidity_pct"]        = [safe(r[2]) for r in r8]
                                                 history["water_temperature_c"] = [safe(r[3]) for r in r8]
                                                 history["ph"]                  = [safe(r[4]) for r in r8]
                                                 history["lux"]                 = [safe(r[5], int) for r in r8]
               except Exception as e:
                              log.error(f"CSV parse: {e}")

           return {
                      "_comment": "CSV fallback - DB unavailable",
                      "_generated": now.isoformat(),
                      "latest_image": {"filename": "latest_image.jpg", "captured_at": now.isoformat(), "resolution": "640x480"},
                      "current_readings": current,
                      "actuator_states": {"pump": "unknown", "grow_lights": "unknown", "fan": "unknown", "heater": "unknown"},
                      "system": {"loop_count": 0, "sleep_minutes": 5, "drive_sync_status": "synced",
                                                    "drive_sync_last": now.isoformat(), "uptime_hours": 0.0, "simulation_mode": False},
                      "pump_schedule": {"on_seconds": 1800, "off_seconds": 900, "next_cycle_in_minutes": 0, "cycles_today": 0},
                      "light_schedule": {"on_hour": 6, "off_hour": 23, "light_hours": 5, "today": [
                                     {"start":"06:00","end":"11:00","status":"done",   "label":"Morgon"},
                                     {"start":"11:30","end":"12:00","status":"active", "label":"Middag"},
                                     {"start":"12:15","end":"12:45","status":"next",   "label":"Eftermiddag"},
                                     {"start":"18:00","end":"23:00","status":"next",   "label":"Kvaell"},
                      ]},
                      "social_media": {"enabled": False, "platform": "X / Twitter", "handle": "@lemkil76",
                                                                "recent_posts": [], "next_post_in_loops": 0},
                      "sensor_history": history,
                      "thresholds": {"temp_min_c": 18.0, "temp_max_c": 28.0, "ph_min": 5.5, "ph_max": 7.5,
                                                            "humidity_min_pct": 50.0, "humidity_max_pct": 80.0, "lux_max": 12000},
                      "daily_summary": {"date": str(today), "air_temp_avg_c": None, "air_temp_min_c": None,
                                                                  "air_temp_max_c": None, "water_temp_avg_c": None, "humidity_avg_pct": None,
                                                                  "ph_avg": None, "lux_avg": None, "pump_cycles": 0,
                                                                  "images_captured_lowres": 0, "images_captured_hires": 0, "social_posts": 0},
           }


def purge_old_sensor_files(keep_days: int = 90):
       cutoff = datetime.date.today() - datetime.timedelta(days=keep_days)
    for f in NAS_SENSORS_DIR.glob("sensors_*.csv"):
               try:
                              if datetime.date.fromisoformat(f.stem.replace("sensors_", "")) < cutoff:
                                                 f.unlink()
                                                 log.info(f"Gallrad: {f.name}")
               except Exception:
                              pass


def main():
       if not nas_is_mounted():
                  log.error(f"NAS ej tillganglig pa {NAS_MOUNT}")
                  return
              log.info("=== cloud_sync start ===")
    try:
               ensure_nas_dirs()
               sync_sensor_data()
               sync_timelapse_images()
               sync_timelapse_videos()
               sync_log()
               write_sample_data()
               if datetime.datetime.now().hour == 3:
                              purge_old_sensor_files(90)
    except Exception as e:
        log.exception(f"cloud_sync fel: {e}")
    log.info("=== cloud_sync klar ===")


if __name__ == "__main__":
       main()
