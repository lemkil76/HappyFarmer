"""
HappyFarmer – Admin REST API
core/api.py
Revised by Claude - 2026-03-26

Startas som en daemon-tråd inuti core/main.py.
Tillhandahåller HTTP-endpoints som används av dashboard/admin.html.

Endpoints:
  GET  /admin            → Serverar admin.html
  POST /api/login        → { "password": "..." } → { "token": "..." }
  POST /api/logout       → Tar bort token
  GET  /api/status       → Relälägen, manuella overrides, schema
  POST /api/relay/<name> → { "state": "on"|"off"|"auto" }
  POST /api/auto         → Återgå till automatisk styrning för alla reläer
  POST /api/camera       → Utlös kamerabild
  POST /api/schedule     → Uppdatera schemainställningar
"""

import threading
import logging
import secrets
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

log = logging.getLogger("happyfarmer.api")

# ── Delad tillstånd (skyddad av _lock) ────────────────────────────────────────
_lock = threading.Lock()

_state: dict = {
    "manual": {          # None = auto  "on" = tvingad på  "off" = tvingad av
        "pump":   None,
        "lights": None,
        "fan":    None,
        "heater": None,
    },
    "schedule": {
        "pump_on_seconds":  1800,   # 30 min
        "pump_off_seconds": 900,    # 15 min (luftning)
        "light_on_hour":    6,
        "light_off_hour":   23,
        "light_hours":      5,
    },
}

_tokens: set = set()
_camera_fn = None
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "happyfarmer")


# ── Publika accessorer (anropas från main.py) ─────────────────────────────────

def get_override(name: str):
    """Returnerar 'on', 'off' eller None (auto-läge)."""
    with _lock:
        return _state["manual"].get(name)

def any_manual_active() -> bool:
    """True om minst ett relä är i manuellt läge."""
    with _lock:
        return any(v is not None for v in _state["manual"].values())

def get_schedule() -> dict:
    """Returnerar en kopia av aktuella schemainställningar."""
    with _lock:
        return dict(_state["schedule"])

def set_camera_callback(fn):
    """Injiceras av main.py för att ge API tillgång till kamerafunktionen."""
    global _camera_fn
    _camera_fn = fn


# ── Flask-applikation ──────────────────────────────────────────────────────────

try:
    from flask import Flask, request, jsonify, send_file, Response
    from functools import wraps

    _app = Flask(__name__)
    _app.secret_key = secrets.token_hex(32)

    _ADMIN_HTML = Path(__file__).parent.parent / "dashboard" / "admin.html"

    # ── Autentisering ──────────────────────────────────────────────────────────

    def _auth_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = request.headers.get("X-Auth-Token", "")
            if token not in _tokens:
                return jsonify({"error": "Ej autentiserad"}), 401
            return f(*args, **kwargs)
        return wrapper

    @_app.route("/api/login", methods=["POST"])
    def _login():
        data = request.get_json(force=True, silent=True) or {}
        if data.get("password") == ADMIN_PASSWORD:
            token = secrets.token_hex(24)
            _tokens.add(token)
            log.info("Admin: inloggning lyckad")
            return jsonify({"token": token})
        log.warning("Admin: felaktigt lösenord")
        return jsonify({"error": "Fel lösenord"}), 401

    @_app.route("/api/logout", methods=["POST"])
    def _logout():
        token = request.headers.get("X-Auth-Token", "")
        _tokens.discard(token)
        return jsonify({"ok": True})

    # ── Status ─────────────────────────────────────────────────────────────────

    @_app.route("/api/status")
    @_auth_required
    def _status():
        from core import sensors
        with _lock:
            return jsonify({
                "manual":   dict(_state["manual"]),
                "schedule": dict(_state["schedule"]),
                "relays": {
                    "pump":   sensors.pump_is_on(),
                    "lights": sensors.lights_is_on(),
                    "fan":    sensors.fan_is_on(),
                    "heater": sensors.heater_is_on(),
                },
            })

    # ── Reläkontroll ───────────────────────────────────────────────────────────

    _RELAY_FNS = {
        "pump":   ("pump_on",   "pump_off"),
        "lights": ("lights_on", "lights_off"),
        "fan":    ("fan_on",    "fan_off"),
        "heater": ("heater_on", "heater_off"),
    }

    @_app.route("/api/relay/<name>", methods=["POST"])
    @_auth_required
    def _set_relay(name):
        if name not in _RELAY_FNS:
            return jsonify({"error": f"Okänd relä: {name}"}), 400
        data = request.get_json(force=True, silent=True) or {}
        state = data.get("state")
        if state not in ("on", "off", "auto"):
            return jsonify({"error": "state måste vara on, off eller auto"}), 400

        from core import sensors
        on_fn, off_fn = _RELAY_FNS[name]
        with _lock:
            if state == "auto":
                _state["manual"][name] = None
            else:
                _state["manual"][name] = state
                getattr(sensors, on_fn if state == "on" else off_fn)()

        log.info(f"Admin: relä '{name}' → '{state}'")
        return jsonify({"ok": True, "relay": name, "state": state})

    @_app.route("/api/auto", methods=["POST"])
    @_auth_required
    def _resume_auto():
        with _lock:
            for key in _state["manual"]:
                _state["manual"][key] = None
        log.info("Admin: återgått till automatisk styrning")
        return jsonify({"ok": True})

    # ── Kamera ─────────────────────────────────────────────────────────────────

    @_app.route("/api/camera", methods=["POST"])
    @_auth_required
    def _camera():
        if _camera_fn is None:
            return jsonify({"error": "Kamerafunktion ej registrerad"}), 503
        result = _camera_fn(hires=False)
        if result:
            return jsonify({"ok": True, "file": str(result)})
        return jsonify({"error": "Kameran misslyckades – kontrollera anslutningen"}), 500

    # ── Schema ─────────────────────────────────────────────────────────────────

    _SCHEDULE_BOUNDS = {
        "pump_on_seconds":  (60,   7200),   # 1–120 min
        "pump_off_seconds": (60,   3600),   # 1–60 min
        "light_on_hour":    (0,    22),
        "light_off_hour":   (1,    24),
        "light_hours":      (1,    18),
    }

    @_app.route("/api/schedule", methods=["POST"])
    @_auth_required
    def _update_schedule():
        data = request.get_json(force=True, silent=True) or {}
        updated = {}
        with _lock:
            for field, (lo, hi) in _SCHEDULE_BOUNDS.items():
                if field not in data:
                    continue
                try:
                    val = int(data[field])
                except (ValueError, TypeError):
                    return jsonify({"error": f"Ogiltigt värde för {field}"}), 400
                if not (lo <= val <= hi):
                    return jsonify({"error": f"{field} måste vara {lo}–{hi}"}), 400
                _state["schedule"][field] = val
                updated[field] = val
        log.info(f"Admin: schema uppdaterat → {updated}")
        return jsonify({"ok": True, "updated": updated,
                        "schedule": dict(_state["schedule"])})

    # ── Serverar admin-sidan ────────────────────────────────────────────────────

    @_app.route("/admin")
    def _admin_page():
        return send_file(str(_ADMIN_HTML))

    @_app.route("/")
    def _root():
        return Response('<meta http-equiv="refresh" content="0;url=/admin">',
                        content_type="text/html")

    FLASK_OK = True

except ImportError:
    FLASK_OK = False
    log.warning("Flask ej installerat – admin-API inaktivt. "
                "Kör: pip3 install --break-system-packages flask")


def start(host: str = "0.0.0.0", port: int = 5000):
    """Startar Flask i en daemon-tråd. Anropas från main()."""
    if not FLASK_OK:
        log.warning("Flask saknas – admin-API startar ej")
        return
    thread = threading.Thread(
        target=lambda: _app.run(
            host=host, port=port,
            debug=False, use_reloader=False, threaded=True,
        ),
        daemon=True,
        name="HappyFarmer-API",
    )
    thread.start()
    log.info(f"Admin-API startad → http://{host}:{port}/admin")
