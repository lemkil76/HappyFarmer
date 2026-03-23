"""
HappyFarmer - Central path configuration
config/paths.py
Revised by Claude - 2026-03-20

Change BASE_DIR here to relocate the entire installation.
Change NAS_* variables to match your Synology network path.

Import everywhere instead of hardcoding paths:
    from config.paths import BASE_DIR, DATA_DIR, TIMELAPSE_DIR, LOG_FILE
    from config.paths import NAS_DASHBOARD_DIR
"""

from pathlib import Path

# ── Pi installation root ───────────────────────────────────────────────────────
# Change this ONE variable to relocate the entire HappyFarmer installation
BASE_DIR = Path("/home/pi/happyfarmer")

# ── Pi runtime data (never committed to GitHub) ───────────────────────────────
DATA_DIR      = BASE_DIR / "data"
TIMELAPSE_DIR = BASE_DIR / "timelapse"
LOG_FILE      = BASE_DIR / "happyfarmer.log"
SYNC_LOG_FILE = BASE_DIR / "sync.log"

# ── Pi credentials ─────────────────────────────────────────────────────────────
SA_FILE = BASE_DIR / "service_account.json"

# ── NAS mount point (SMB/CIFS mounted on Pi) ──────────────────────────────────
# Mount NAS share on Pi first - see docs/SETUP.md step 6:
#   sudo mount -t cifs //NAS_IP/HappyFarmer /mnt/nas/happyfarmer -o username=happyfarmer,...
#
# The NAS serves the dashboard on http://server:8080/
# Files written here are immediately accessible via the web server.
NAS_MOUNT        = Path("/mnt/nas/happyfarmer")     # where NAS is mounted on Pi
NAS_SENSORS_DIR  = NAS_MOUNT / "sensors"            # -> http://server:8080/sensors/
NAS_TIMELAPSE_DIR= NAS_MOUNT / "timelapse"          # -> http://server:8080/timelapse/
NAS_LOGS_DIR     = NAS_MOUNT / "logs"               # -> http://server:8080/logs/
NAS_DASHBOARD_DIR= NAS_MOUNT / "dashboard"          # -> http://server:8080/dashboard/

# sample_data.json is written here so the dashboard can fetch() it:
#   http://server:8080/dashboard/sample_data.json
NAS_SAMPLE_DATA  = NAS_DASHBOARD_DIR / "sample_data.json"

# ── Code directories (for reference) ──────────────────────────────────────────
CODE_DIR         = BASE_DIR
CORE_DIR         = CODE_DIR / "core"
INTEGRATIONS_DIR = CODE_DIR / "integrations"
CONFIG_DIR       = CODE_DIR / "config"
DASHBOARD_DIR    = CODE_DIR / "dashboard"
DOCS_DIR         = CODE_DIR / "docs"

# ── Convenience dict ──────────────────────────────────────────────────────────
PATHS = {
    "base":          BASE_DIR,
    "data":          DATA_DIR,
    "timelapse":     TIMELAPSE_DIR,
    "log":           LOG_FILE,
    "sync_log":      SYNC_LOG_FILE,
    "sa_file":       SA_FILE,
    "nas_mount":     NAS_MOUNT,
    "nas_sensors":   NAS_SENSORS_DIR,
    "nas_timelapse": NAS_TIMELAPSE_DIR,
    "nas_logs":      NAS_LOGS_DIR,
    "nas_dashboard": NAS_DASHBOARD_DIR,
    "nas_sample":    NAS_SAMPLE_DATA,
}

# ── Ensure local runtime directories exist on import ──────────────────────────
DATA_DIR.mkdir(parents=True, exist_ok=True)
TIMELAPSE_DIR.mkdir(parents=True, exist_ok=True)
