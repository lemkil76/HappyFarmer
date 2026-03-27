"""
HappyFarmer - MariaDB Integration
integrations/db.py
Revised by Claude - 2026-03-26

All databaskommunikation mot MariaDB pa NAS:en.
Importeras av core/main.py och integrations/cloud_sync.py.

Install:
    pip install mysql-connector-python

Lagg till i config/secrets.py:
    DB_HOST = "192.168.1.100"
    DB_PORT = 3307
    DB_NAME = "happyfarmer"
    DB_USER = "happyfarmer"
    DB_PASS = "ditt_losenord"
"""

import logging
import datetime
from typing import Optional

log = logging.getLogger("happyfarmer.db")

try:
    import mysql.connector
    DB_AVAILABLE = True
except ImportError:
    log.warning("Installera: pip install mysql-connector-python")
    DB_AVAILABLE = False

try:
    from config.secrets import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
except ImportError:
    DB_HOST, DB_PORT, DB_NAME = "nas", 3306, "happyfarmer"
    DB_USER, DB_PASS = "happyfarmer", ""


def get_connection():
    if not DB_AVAILABLE:
        return None
    try:
        return mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            connection_timeout=5,
            charset="utf8",
        )
    except Exception as e:
        log.error(f"DB-anslutning misslyckades: {e}")
        return None


def test_connection() -> bool:
    conn = get_connection()
    if conn:
        conn.close()
        log.info(f"DB OK ({DB_HOST}/{DB_NAME})")
        return True
    return False


def insert_sensor_reading(
    air_temp_c, humidity_pct, water_temp_c, ph,
    lux, lux_description, loop_count=None,
) -> bool:
    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sensor_readings "
            "(air_temp_c, humidity_pct, water_temp_c, ph, lux, lux_description, loop_count) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (air_temp_c, humidity_pct, water_temp_c, ph, lux, lux_description, loop_count),
        )
        conn.commit()
        return True
    except Exception as e:
        log.error(f"DB sensor insert: {e}")
        return False
    finally:
        conn.close()


def get_latest_reading() -> Optional[dict]:
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM senaste_avlasning")
        return cur.fetchone()
    except Exception as e:
        log.error(f"DB get_latest: {e}")
        return None
    finally:
        conn.close()


def get_hourly_readings(hours: int = 24, interval_hours: int = 2) -> list:
    """
    Hamta ett medelvarde per intervall under de senaste timmarna.
    Returnerar 12 datapunkter med 2h intervall som standard.
    Anvands for sparkline-diagram i dashboarden.
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT
                FLOOR(HOUR(recorded_at) / %s) * %s AS hour_group,
                ROUND(AVG(air_temp_c), 1)    AS air_temp_c,
                ROUND(AVG(humidity_pct), 1)  AS humidity_pct,
                ROUND(AVG(water_temp_c), 1)  AS water_temp_c,
                ROUND(AVG(ph), 2)            AS ph,
                ROUND(AVG(lux), 0)           AS lux
            FROM sensor_readings
            WHERE recorded_at >= NOW() - INTERVAL %s HOUR
            GROUP BY hour_group
            ORDER BY hour_group ASC
            LIMIT %s
        """, (interval_hours, interval_hours, hours, hours // interval_hours))
        return cur.fetchall()
    except Exception as e:
        log.error(f"DB get_hourly: {e}")
        return []
    finally:
        conn.close()


def get_daily_summary(date: datetime.date = None) -> Optional[dict]:
    if date is None:
        date = datetime.date.today()
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM dagssammanfattning WHERE datum = %s", (date,))
        return cur.fetchone()
    except Exception as e:
        log.error(f"DB get_summary: {e}")
        return None
    finally:
        conn.close()


def log_actuator_event(
    actuator, state, trigger_src=None, duration_sec=None
) -> bool:
    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO actuator_events (actuator, state, trigger_src, duration_sec) "
            "VALUES (%s, %s, %s, %s)",
            (actuator, state, trigger_src, duration_sec),
        )
        conn.commit()
        return True
    except Exception as e:
        log.error(f"DB actuator: {e}")
        return False
    finally:
        conn.close()


def log_timelapse_image(
    filename, image_type="lowres", resolution="640x480",
    nas_path=None, synced=False,
) -> bool:
    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO timelapse_images (filename, type, resolution, nas_path, synced) "
            "VALUES (%s, %s, %s, %s, %s)",
            (filename, image_type, resolution, nas_path, 1 if synced else 0),
        )
        conn.commit()
        return True
    except Exception as e:
        log.error(f"DB timelapse_image: {e}")
        return False
    finally:
        conn.close()


def mark_image_synced(filename: str) -> bool:
    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE timelapse_images SET synced=1 WHERE filename=%s", (filename,))
        conn.commit()
        return True
    except Exception as e:
        log.error(f"DB mark_synced: {e}")
        return False
    finally:
        conn.close()


def log_timelapse_video(
    filename, nas_path=None, period_from=None, period_to=None, frame_count=None
) -> bool:
    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO timelapse_videos (filename, nas_path, period_from, period_to, frame_count) "
            "VALUES (%s, %s, %s, %s, %s)",
            (filename, nas_path, period_from, period_to, frame_count),
        )
        conn.commit()
        return True
    except Exception as e:
        log.error(f"DB timelapse_video: {e}")
        return False
    finally:
        conn.close()


def log_social_post(post_type, message, platform="twitter", post_id=None) -> bool:
    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO social_posts (platform, post_id, type, message) "
            "VALUES (%s, %s, %s, %s)",
            (platform, post_id, post_type, message),
        )
        conn.commit()
        return True
    except Exception as e:
        log.error(f"DB social_post: {e}")
        return False
    finally:
        conn.close()


def get_recent_posts(n: int = 2) -> list:
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM social_posts ORDER BY posted_at DESC LIMIT %s", (n,)
        )
        return cur.fetchall()
    except Exception as e:
        log.error(f"DB get_posts: {e}")
        return []
    finally:
        conn.close()


def log_feature(
    title: str,
    description: str = None,
    category: str = "core",
    version: str = None,
    released_at: datetime.date = None,
) -> bool:
    """Loggar en ny feature i feature_log-tabellen (kronologisk changelog)."""
    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO feature_log (released_at, version, category, title, description) "
            "VALUES (%s, %s, %s, %s, %s)",
            (released_at or datetime.date.today(), version, category, title, description),
        )
        conn.commit()
        return True
    except Exception as e:
        log.error(f"DB feature_log: {e}")
        return False
    finally:
        conn.close()


def log_system_event(message: str, level: str = "info", source: str = "main") -> bool:
    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO system_events (level, source, message) VALUES (%s, %s, %s)",
            (level, source, message),
        )
        conn.commit()
        return True
    except Exception as e:
        log.error(f"DB system_event: {e}")
        return False
    finally:
        conn.close()


def build_sample_data_from_db(actuator_states=None, system_info=None) -> dict:
    now     = datetime.datetime.now()
    latest  = get_latest_reading() or {}
    recent  = get_hourly_readings(24, 2)
    summary = get_daily_summary() or {}
    posts   = get_recent_posts(2)

    def col(rows, key):
        return [float(r[key]) if r.get(key) is not None else None for r in rows]

    return {
        "_comment":        "Auto-generated from MariaDB by integrations/db.py",
        "_format_version": "1.0",
        "_generated":      now.isoformat(),
        "latest_image": {
            "filename":    "latest_image.jpg",
            "captured_at": now.isoformat(),
            "resolution":  "640x480",
        },
        "current_readings": {
            "timestamp":           str(latest.get("recorded_at", now)),
            "air_temperature_c":   float(latest["air_temp_c"])   if latest.get("air_temp_c")   else None,
            "humidity_pct":        float(latest["humidity_pct"]) if latest.get("humidity_pct") else None,
            "water_temperature_c": float(latest["water_temp_c"]) if latest.get("water_temp_c") else None,
            "ph":                  float(latest["ph"])            if latest.get("ph")            else None,
            "lux":                 int(latest["lux"])             if latest.get("lux")           else None,
            "lux_description":     latest.get("lux_description", "okand"),
        },
        "actuator_states": actuator_states or {
            "pump": "unknown", "grow_lights": "unknown",
            "fan":  "unknown", "heater":      "unknown",
        },
        "system": {
            "loop_count":        int(latest.get("loop_count") or 0),
            "sleep_minutes":     5,
            "drive_sync_status": "synced",
            "drive_sync_last":   now.isoformat(),
            "uptime_hours":      0.0,
            "simulation_mode":   False,
            **(system_info or {}),
        },
        "pump_schedule": {
            "on_seconds": 1800, "off_seconds": 900,
            "next_cycle_in_minutes": 0,
            "cycles_today": int(summary.get("antal_avlasningar", 0)),
        },
        "light_schedule": {
            "on_hour": 6, "off_hour": 23, "light_hours": 5,
            "today": [
                {"start": "06:00", "end": "11:00", "status": "done",   "label": "Morgon"},
                {"start": "11:30", "end": "12:00", "status": "active", "label": "Middag"},
                {"start": "12:15", "end": "12:45", "status": "next",   "label": "Eftermiddag"},
                {"start": "18:00", "end": "23:00", "status": "next",   "label": "Kvaell"},
            ],
        },
        "social_media": {
            "enabled": False, "platform": "X / Twitter", "handle": "@lemkil76",
            "recent_posts": [
                {
                    "id":        str(p.get("post_id", "")),
                    "posted_at": str(p.get("posted_at", "")),
                    "text":      p.get("message", ""),
                    "likes":     int(p.get("likes", 0)),
                    "retweets":  int(p.get("retweets", 0)),
                    "type":      p.get("type", "sensor_update"),
                }
                for p in posts
            ],
            "next_post_in_loops": 0,
        },
        "sensor_history": {
            "description":         "Medelvarde per 2h senaste 24h",
            "interval_minutes":    120,
            "air_temperature_c":   col(recent, "air_temp_c"),
            "humidity_pct":        col(recent, "humidity_pct"),
            "water_temperature_c": col(recent, "water_temp_c"),
            "ph":                  col(recent, "ph"),
            "lux": [int(r["lux"]) if r.get("lux") else None for r in recent],
        },
        "thresholds": {
            "temp_min_c": 18.0, "temp_max_c": 28.0,
            "ph_min": 5.5, "ph_max": 7.5,
            "humidity_min_pct": 50.0, "humidity_max_pct": 80.0,
            "lux_max": 12000,
        },
        "daily_summary": {
            "date":             str(summary.get("datum", datetime.date.today())),
            "air_temp_avg_c":   float(summary["lufttemp_medel"])   if summary.get("lufttemp_medel")   else None,
            "air_temp_min_c":   float(summary["lufttemp_min"])     if summary.get("lufttemp_min")     else None,
            "air_temp_max_c":   float(summary["lufttemp_max"])     if summary.get("lufttemp_max")     else None,
            "water_temp_avg_c": float(summary["vattentemp_medel"]) if summary.get("vattentemp_medel") else None,
            "humidity_avg_pct": float(summary["fuktighet_medel"])  if summary.get("fuktighet_medel")  else None,
            "ph_avg":           float(summary["ph_medel"])         if summary.get("ph_medel")         else None,
            "lux_avg":          int(summary["lux_medel"])          if summary.get("lux_medel")        else None,
            "pump_cycles":      int(summary.get("antal_avlasningar", 0)),
            "images_captured_lowres": 0,
            "images_captured_hires":  0,
            "social_posts":           len(posts),
        },
    }


def log_system_update(
    status: str,
    packages_updated: int = 0,
    packages_list: str = None,
    os_version: str = None,
    kernel_version: str = None,
    python_version: str = None,
    duration_sec: int = None,
    notes: str = None,
) -> bool:
    """Loggar ett apt-uppdateringsresultat till system_updates-tabellen."""
    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO system_updates "
            "(status, packages_updated, packages_list, os_version, "
            " kernel_version, python_version, duration_sec, notes) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (status, packages_updated, packages_list, os_version,
             kernel_version, python_version, duration_sec, notes),
        )
        conn.commit()
        return True
    except Exception as e:
        log.error(f"DB system_update insert: {e}")
        return False
    finally:
        conn.close()


def get_last_system_update() -> Optional[dict]:
    """Returnerar den senaste system_updates-raden."""
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM system_updates ORDER BY updated_at DESC LIMIT 1"
        )
        return cur.fetchone()
    except Exception as e:
        log.error(f"DB get_last_update: {e}")
        return None
    finally:
        conn.close()


def get_system_updates(n: int = 10) -> list:
    """Returnerar de n senaste system_updates-raderna."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM system_updates ORDER BY updated_at DESC LIMIT %s", (n,)
        )
        return cur.fetchall()
    except Exception as e:
        log.error(f"DB get_system_updates: {e}")
        return []
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if test_connection():
        print("DB OK! Senaste:", get_latest_reading())
    else:
        print("Misslyckades - kontrollera config/secrets.py")