"""
HappyFarmer - Central path configuration
config/paths.py

Change BASE_DIR here to relocate the Pi installation.

Import everywhere instead of hardcoding paths:
    from config.paths import BASE_DIR, DATA_DIR, TIMELAPSE_DIR, LOG_FILE
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

# ── Code directories (for reference) ──────────────────────────────────────────
CODE_DIR         = BASE_DIR
CORE_DIR         = CODE_DIR / "core"
INTEGRATIONS_DIR = CODE_DIR / "integrations"
CONFIG_DIR       = CODE_DIR / "config"
DASHBOARD_DIR    = CODE_DIR / "dashboard"
DOCS_DIR         = CODE_DIR / "docs"

# ── Convenience dict ──────────────────────────────────────────────────────────
PATHS = {
    "base":      BASE_DIR,
    "data":      DATA_DIR,
    "timelapse": TIMELAPSE_DIR,
    "log":       LOG_FILE,
    "sync_log":  SYNC_LOG_FILE,
    "sa_file":   SA_FILE,
    "dashboard": DASHBOARD_DIR,
}

# ── Ensure local runtime directories exist on import ──────────────────────────
DATA_DIR.mkdir(parents=True, exist_ok=True)
TIMELAPSE_DIR.mkdir(parents=True, exist_ok=True)
