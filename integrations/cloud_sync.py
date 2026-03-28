"""
HappyFarmer - Lacasa Sync
integrations/cloud_sync.py

Synkar dashboard-filer fran Pi 4 till lacasa via SCP.
"""

import json
import logging
import datetime
import subprocess
import tempfile
from pathlib import Path

from config.paths import (
    DATA_DIR, TIMELAPSE_DIR, LOG_FILE, SYNC_LOG_FILE, BASE_DIR,
)
from integrations.db import build_sample_data_from_db, test_connection

logging.basicConfig(
    filename=str(SYNC_LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("cloud_sync")

MAX_LOG_BYTES  = 5 * 1024 * 1024
DELETE_AFTER_UPLOAD = True

# Lacasa
LACASA_USER    = "pi"
LACASA_HOST    = "192.168.1.129"
LACASA_WEB     = "/var/www/happyfarmer"
LACASA_DASH    = f"{LACASA_WEB}/dashboard"
LACASA_SAMPLE  = f"{LACASA_DASH}/sample_data.json"
LACASA_IMAGE   = f"{LACASA_DASH}/latest_image.jpg"


def _scp(local: str, remote: str) -> bool:
    """Kopiera en fil till lacasa via SCP. Returnerar True vid lyckat."""
    try:
        result = subprocess.run(
            ["scp", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
             local, f"{LACASA_USER}@{LACASA_HOST}:{remote}"],
            timeout=15, capture_output=True
        )
        if result.returncode == 0:
            return True
        log.error(f"SCP misslyckades: {result.stderr.decode().strip()}")
        return False
    except Exception as e:
        log.error(f"SCP fel: {e}")
        return False


def lacasa_is_reachable() -> bool:
    """Kolla om lacasa svarar pa SSH."""
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=3", "-o", "StrictHostKeyChecking=no",
             f"{LACASA_USER}@{LACASA_HOST}", "echo OK"],
            timeout=5, capture_output=True
        )
        return result.returncode == 0
    except Exception:
        return False


def ensure_lacasa_dirs():
    subprocess.run(
        ["ssh", "-o", "ConnectTimeout=3",
         f"{LACASA_USER}@{LACASA_HOST}",
         f"mkdir -p {LACASA_DASH}"],
        timeout=5, capture_output=True
    )


def sync_image():
    """SCP latest_image.jpg till lacasa."""
    img = BASE_DIR / "dashboard" / "latest_image.jpg"
    if not img.exists():
        return
    if _scp(str(img), LACASA_IMAGE):
        log.info("latest_image.jpg synkad till lacasa")


def write_sample_data():
    """Bygg sample_data.json och SCP till lacasa."""
    try:
        state_file = DATA_DIR / "state.json"
        state = {}
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
            except Exception:
                pass

        uptime_hours = 0.0
        if "start_time" in state:
            start = datetime.datetime.fromisoformat(state["start_time"])
            uptime_hours = round((datetime.datetime.now() - start).total_seconds() / 3600, 1)

        system_info = {
            "loop_count":        state.get("loop_count", 0),
            "sleep_minutes":     5,
            "drive_sync_status": "synced",
            "drive_sync_last":   datetime.datetime.now().isoformat(),
            "uptime_hours":      uptime_hours,
            "simulation_mode":   state.get("simulation_mode", False),
        }
        actuator_states = state.get("actuator_states")

        if test_connection():
            data = build_sample_data_from_db(
                actuator_states=actuator_states,
                system_info=system_info,
            )
            log.info("sample_data.json byggd fran MariaDB")
        else:
            data = _build_from_csv()
            log.warning("DB ej tillganglig - anvander CSV-fallback")

        json_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)

        # Skriv till tempfil och SCP
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_str)
            tmp_path = f.name

        if _scp(tmp_path, LACASA_SAMPLE):
            log.info(f"sample_data.json synkad till lacasa:{LACASA_SAMPLE}")
        Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        log.error(f"write_sample_data: {e}")


def _build_from_csv():
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
                    try:
                        return cast(v)
                    except Exception:
                        return None
                current.update({
                    "timestamp": last[0],
                    "air_temperature_c": safe(last[1]),
                    "humidity_pct": safe(last[2]),
                    "water_temperature_c": safe(last[3]),
                    "ph": safe(last[4]),
                    "lux": safe(last[5], int),
                })
                r8 = rows[-8:]
                history["air_temperature_c"] = [safe(r[1]) for r in r8]
                history["humidity_pct"]       = [safe(r[2]) for r in r8]
                history["water_temperature_c"]= [safe(r[3]) for r in r8]
                history["ph"]                 = [safe(r[4]) for r in r8]
                history["lux"]                = [safe(r[5], int) for r in r8]
        except Exception as e:
            log.error(f"CSV parse: {e}")
    return {
        "_comment": "CSV fallback",
        "_generated": now.isoformat(),
        "latest_image": {"filename": "latest_image.jpg", "captured_at": now.isoformat(), "resolution": "640x480"},
        "current_readings": current,
        "actuator_states": {"pump": "unknown", "grow_lights": "unknown", "fan": "unknown", "heater": "unknown"},
        "system": {"loop_count": 0, "sleep_minutes": 5, "drive_sync_status": "synced",
                   "drive_sync_last": now.isoformat(), "uptime_hours": 0.0, "simulation_mode": False},
        "pump_schedule": {"on_seconds": 1800, "off_seconds": 900, "next_cycle_in_minutes": 0, "cycles_today": 0},
        "light_schedule": {"on_hour": 6, "off_hour": 23, "light_hours": 5, "today": [
            {"start": "06:00", "end": "11:00", "status": "done",   "label": "Morgon"},
            {"start": "11:30", "end": "12:00", "status": "active", "label": "Middag"},
            {"start": "12:15", "end": "12:45", "status": "next",   "label": "Eftermiddag"},
            {"start": "18:00", "end": "23:00", "status": "next",   "label": "Kvaell"},
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


def main():
    if not lacasa_is_reachable():
        log.error(f"Lacasa ej nåbar på {LACASA_HOST}")
        return
    log.info("=== cloud_sync start ===")
    try:
        ensure_lacasa_dirs()
        write_sample_data()
        sync_image()
    except Exception as e:
        log.exception(f"cloud_sync fel: {e}")
    log.info("=== cloud_sync klar ===")


if __name__ == "__main__":
    main()
