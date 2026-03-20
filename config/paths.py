"""
HappyFarmer - Central path configuration
config/paths.py
Revised by Claude - 2026-03-20

All file system paths are defined here.
To move the entire installation, change only BASE_DIR.

Usage everywhere in the codebase:
    from config.paths import BASE_DIR, DATA_DIR, TIMELAPSE_DIR, LOG_FILE, SA_FILE
"""

from pathlib import Path

# ── Root ───────────────────────────────────────────────────────────────────────
# Change this ONE variable to relocate the entire HappyFarmer installation
BASE_DIR = Path("/home/pi/happyfarmer")

# ── Runtime data (never committed to GitHub - covered by .gitignore) ──────────
DATA_DIR      = BASE_DIR / "data"
TIMELAPSE_DIR = BASE_DIR / "timelapse"
LOG_FILE      = BASE_DIR / "happyfarmer.log"
SYNC_LOG_FILE = BASE_DIR / "sync.log"

# ── Credentials (never committed to GitHub) ───────────────────────────────────
SA_FILE = BASE_DIR / "service_account.json"

# ── Code roots (for imports) ──────────────────────────────────────────────────
CODE_DIR        = BASE_DIR  # root of Python package
CORE_DIR        = CODE_DIR / "core"
INTEGRATIONS_DIR= CODE_DIR / "integrations"
CONFIG_DIR      = CODE_DIR / "config"
DASHBOARD_DIR   = CODE_DIR / "dashboard"
DOCS_DIR        = CODE_DIR / "docs"

# ── Convenience dict (optional - pass around or unpack as needed) ─────────────
PATHS = {
    "base":         BASE_DIR,
    "data":         DATA_DIR,
    "timelapse":    TIMELAPSE_DIR,
    "log":          LOG_FILE,
    "sync_log":     SYNC_LOG_FILE,
    "sa_file":      SA_FILE,
    "core":         CORE_DIR,
    "integrations": INTEGRATIONS_DIR,
    "config":       CONFIG_DIR,
    "dashboard":    DASHBOARD_DIR,
    "docs":         DOCS_DIR,
}

# ── Ensure runtime directories exist on import ────────────────────────────────
DATA_DIR.mkdir(parents=True, exist_ok=True)
TIMELAPSE_DIR.mkdir(parents=True, exist_ok=True)
