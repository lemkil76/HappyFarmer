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
import json
import datetime
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

def load_schedule_from_db():
    """Laddar sparad schema från DB vid uppstart. Faller tillbaka på defaults."""
    try:
        saved = db.get_schedule()
        if saved:
            with _lock:
                _state["schedule"].update(saved)
            log.info(f"Schema laddat från DB: {saved}")
    except Exception as e:
        log.warning(f"Kunde inte ladda schema från DB: {e}")

def set_camera_callback(fn):
    """Injiceras av main.py för att ge API tillgång till kamerafunktionen."""
    global _camera_fn
    _camera_fn = fn


# API-relänamn → DB/JSON-namn (grow_lights heter "lights" i URL-routen)
_RELAY_DB_NAME = {
    "pump":   "pump",
    "lights": "grow_lights",
    "fan":    "fan",
    "heater": "heater",
}


_relay_sync_running = False  # Debounce – max en SCP åt gången

def write_relay_states():
    """Synkar relälägen till lacasa via SCP i bakgrundstråd.

    Anropas från _set_relay(), _resume_auto() och core/main.py varje loop.
    PHP data.php läser relay_states.json för realtidsvisning.
    """
    global _relay_sync_running
    try:
        from core import sensors
        states = {
            "pump":        "on" if sensors.pump_is_on()   else "off",
            "grow_lights": "on" if sensors.lights_is_on() else "off",
            "fan":         "on" if sensors.fan_is_on()    else "off",
            "heater":      "on" if sensors.heater_is_on() else "off",
            "_updated":    datetime.datetime.now().isoformat(),
        }
        if _relay_sync_running:
            return  # Pågående SCP – hoppa över, nästa loop hämtar aktuellt värde
        def _sync():
            global _relay_sync_running
            _relay_sync_running = True
            try:
                from integrations.cloud_sync import sync_relay_states
                sync_relay_states(states)
            finally:
                _relay_sync_running = False
        threading.Thread(target=_sync, daemon=True, name="RelaySync").start()
    except Exception as e:
        log.debug(f"write_relay_states fel: {e}")


# ── Flask-applikation ──────────────────────────────────────────────────────────

try:
    from flask import Flask, request, jsonify, send_file, Response
    from functools import wraps
    from integrations import db

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
        db_name = _RELAY_DB_NAME.get(name, name)

        # GPIO-kontroll i lock (~1ms) – svara direkt utan att vänta på DB/SCP
        with _lock:
            if state == "auto":
                _state["manual"][name] = None
            else:
                _state["manual"][name] = state
                getattr(sensors, on_fn if state == "on" else off_fn)()

        # DB-loggning och relay-sync i bakgrunden – blockerar inte svaret
        def _post_relay():
            try:
                if state != "auto":
                    db.log_actuator_event(db_name, state, trigger_src="manual")
            except Exception as e:
                log.warning(f"DB-loggning relä misslyckades: {e}")
            write_relay_states()
        threading.Thread(target=_post_relay, daemon=True, name=f"Relay-{name}").start()

        log.info(f"Admin: relä '{name}' → '{state}'")
        return jsonify({"ok": True, "relay": name, "state": state})

    @_app.route("/api/auto", methods=["POST"])
    @_auth_required
    def _resume_auto():
        from core import sensors
        _is_on = {
            "pump":   sensors.pump_is_on,
            "lights": sensors.lights_is_on,
            "fan":    sensors.fan_is_on,
            "heater": sensors.heater_is_on,
        }
        events = []
        with _lock:
            for key in _state["manual"]:
                if _state["manual"][key] is not None:
                    actual  = "on" if _is_on[key]() else "off"
                    events.append((_RELAY_DB_NAME.get(key, key), actual))
                _state["manual"][key] = None

        # DB-loggning i bakgrunden – blockerar inte svaret
        def _post_auto():
            for db_name, actual in events:
                try:
                    db.log_actuator_event(db_name, actual, trigger_src="auto")
                except Exception as e:
                    log.warning(f"DB-loggning auto misslyckades: {e}")
            write_relay_states()
        threading.Thread(target=_post_auto, daemon=True, name="AutoResume").start()

        log.info("Admin: återgått till automatisk styrning")
        return jsonify({"ok": True})

    # ── Kamera ─────────────────────────────────────────────────────────────────

    @_app.route("/api/camera", methods=["POST"])
    @_auth_required
    def _camera():
        if _camera_fn is None:
            return jsonify({"error": "Kamerafunktion ej registrerad"}), 503
        result = _camera_fn()
        if result:
            # Synka bilden till lacasa i bakgrunden (för dashboard.html + cron)
            def _sync():
                try:
                    from integrations.cloud_sync import sync_image
                    sync_image()
                except Exception as e:
                    log.warning(f"Bildsynk efter kamera misslyckades: {e}")
            threading.Thread(target=_sync, daemon=True, name="CameraSync").start()
            return jsonify({"ok": True, "file": str(result)})
        return jsonify({"error": "Kameran misslyckades – kontrollera anslutningen"}), 500

    @_app.route("/api/latest-image")
    @_auth_required
    def _latest_image():
        """Serverar latest_image.jpg direkt från RASP – ingen SCP-fördröjning."""
        img_path = Path(__file__).parent.parent / "dashboard" / "latest_image.jpg"
        if not img_path.exists():
            return jsonify({"error": "Ingen bild tillgänglig"}), 404
        return send_file(str(img_path), mimetype="image/jpeg",
                         max_age=0, conditional=False)

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
        threading.Thread(
            target=db.save_schedule,
            args=(dict(_state["schedule"]),),
            daemon=True, name="SaveSchedule"
        ).start()
        return jsonify({"ok": True, "updated": updated,
                        "schedule": dict(_state["schedule"])})

    # ── Systemuppdatering ──────────────────────────────────────────────────────

    @_app.route("/api/sysupdate/status")
    @_auth_required
    def _sysupdate_status():
        last = db.get_last_system_update()
        if last:
            last = {k: str(v) if hasattr(v, 'isoformat') else v
                    for k, v in last.items()}
        return jsonify({"last_update": last})

    @_app.route("/api/sysupdate/check")
    @_auth_required
    def _sysupdate_check():
        from integrations.system_updater import check_available_updates
        packages = check_available_updates()
        return jsonify({"available": len(packages), "packages": packages})

    @_app.route("/api/sysupdate/run", methods=["POST"])
    @_auth_required
    def _sysupdate_run():
        from integrations.system_updater import run_updates
        import threading
        # Kör i bakgrundstråd – kan ta flera minuter
        def _do_update():
            log.info("Admin: systemuppdatering startad")
            run_updates(dry_run=False)
            log.info("Admin: systemuppdatering klar")
        threading.Thread(target=_do_update, daemon=True,
                         name="SysUpdater").start()
        return jsonify({"ok": True,
                        "message": "Uppdatering startad i bakgrunden – klar om 1–5 min"})

    # admin.html serveras av Nginx – Flask hanterar bara JSON-API

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
