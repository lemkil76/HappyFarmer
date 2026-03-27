"""
HappyFarmer - Central path configuration
config/paths.py
Revised by Claude - 2026-03-20

Change BASE_DIR here to relocate the Pi installation.
Change NAS_MOUNT to match where the NAS share is mounted on the Pi.

The Synology virtual host "happyfarmer" points to /web/happyfarmer
in the NAS filesystem and serves on http://server:8080/

Import everywhere instead of hardcoding paths:
    from config.paths import BASE_DIR, DATA_DIR, TIMELAPSE_DIR, LOG_FILE
    from config.paths import NAS_DASHBOARD_DIR, NAS_SAMPLE_DATA
"""

from pathlib import Path

# ── Pi installation root ───────────────────────────────────────────────────────
# Change this ONE variable to relocate the entire HappyFarmer installation on Pi
BASE_DIR = Path("/home/pi/happyfarmer")

# ── Pi runtime data (never committed to GitHub) ───────────────────────────────
DATA_DIR      = BASE_DIR / "data"
TIMELAPSE_DIR = BASE_DIR / "timelapse"
LOG_FILE      = BASE_DIR / "happyfarmer.log"
SYNC_LOG_FILE = BASE_DIR / "sync.log"

# ── Pi credentials ─────────────────────────────────────────────────────────────
SA_FILE = BASE_DIR / "service_account.json"

# ── NAS mount point on Pi ──────────────────────────────────────────────────────
# The Pi mounts the NAS share via SMB/CIFS (see docs/SETUP.md step 6):
#
#   sudo mount -t cifs //NAS_IP/web /mnt/nas/web \
#     -o username=happyfarmer,password=LÖSENORD,uid=pi,gid=pi
#
# On the NAS, the Synology virtual host "happyfarmer" is configured to:
#   - Document root: /web/happyfarmer
#   - Port: 8080
#   - URL: http://server:8080/
#
# NAS_MOUNT points to the virtual host root as seen from the Pi.
NAS_MOUNT = Path("/mnt/nas/web/happyfarmer")   # = NAS:/web/happyfarmer

# ── NAS subdirectories (auto-created by cloud_sync.py) ────────────────────────
# These map directly to URLs on the web server:
#   NAS_SENSORS_DIR   -> http://server:8080/sensors/
#   NAS_TIMELAPSE_DIR -> http://server:8080/timelapse/
#   NAS_LOGS_DIR      -> http://server:8080/logs/
#   NAS_DASHBOARD_DIR -> http://server:8080/dashboard/
NAS_SENSORS_DIR   = NAS_MOUNT / "sensors"
NAS_TIMELAPSE_DIR = NAS_MOUNT / "timelapse"
NAS_LOGS_DIR      = NAS_MOUNT / "logs"
NAS_DASHBOARD_DIR = NAS_MOUNT / "dashboard"

# dashboard/sample_data.json is fetched by the browser dashboard:
#   http://server:8080/dashboard/sample_data.json
NAS_SAMPLE_DATA = NAS_DASHBOARD_DIR / "sample_data.json"

# api/relay_states.json – skrivs av core/api.py och core/main.py vid varje reläändring.
# Läses av dashboard/api/data.php för realtidsvisning utan fördröjning.
NAS_RELAY_STATES = NAS_MOUNT / "api" / "relay_states.json"

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
