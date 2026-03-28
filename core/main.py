"""
HappyFarmer - Main Control Loop
core/main.py
Revised by Claude - 2026-03-26
"""

import time
import datetime
import logging
import subprocess
import shutil
import json

from config.paths import DATA_DIR, TIMELAPSE_DIR, LOG_FILE, DASHBOARD_DIR
from core import sensors, api
from integrations import homekit
from integrations import db
from integrations.social_media import post_sensor_update, post_timelapse_update, verify_credentials

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("happyfarmer")

TIMELAPSE_ENABLED = True
SOCIAL_ENABLED    = True
SLEEP_MINUTES     = 5
LOOP_COUNT        = 0
LIGHT_ON_HOUR     = 6
LIGHT_OFF_HOUR    = 23
LIGHT_HOURS       = 5
TEMP_MIN          = 18.0
TEMP_MAX          = 28.0
PUMP_ON_SECONDS   = 30 * 60
PUMP_OFF_SECONDS  = 15 * 60
TIMELAPSE_LOWRES_MINS     = 60
TIMELAPSE_HIRES_HOUR      = 11
TIMELAPSE_BUILD_DAYS      = 30
SOCIAL_POST_EVERY_N_LOOPS = 1152
CAMERA_DEVICE = "/dev/video0"


def capture_image(hires: bool = False):
    ts    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    res   = "1920x1080" if hires else "640x480"
    itype = "hires" if hires else "lowres"
    path  = TIMELAPSE_DIR / f"{ts}_{itype}.jpg"
    local_latest = DASHBOARD_DIR / "latest_image.jpg"
    try:
        subprocess.run(
                        ["fswebcam",
                        "-d", CAMERA_DEVICE,
                        "-r", res,
                        "--no-banner",
                        "--skip", "1",
                        str(path)],
                        check=True, capture_output=True,
                        )
        shutil.copy2(str(path), str(local_latest))
        db.log_timelapse_image(filename=path.name, image_type=itype, resolution=res)
        log.info(f"Image: {path}")
        return str(path)
    except Exception as e:
        log.error(f"Camera failed: {e}")
        return None


def build_timelapse():
    out = TIMELAPSE_DIR / f"timelapse_{datetime.date.today()}.mp4"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-framerate", "24",
            "-pattern_type", "glob",
            "-i", str(TIMELAPSE_DIR / "*_lowres.jpg"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out),
        ], check=True, capture_output=True)
        db.log_timelapse_video(filename=out.name)
        log.info(f"Timelapse: {out}")
        return str(out)
    except Exception as e:
        log.error(f"Timelapse failed: {e}")
        return None


def store_sensor_data(data: dict):
    ts  = datetime.datetime.now().isoformat()
    csv = DATA_DIR / f"sensors_{datetime.date.today()}.csv"
    if not csv.exists():
        with csv.open("w") as f:
            f.write("timestamp,air_temp,humidity,water_temp,ph,lux,lux_desc\n")
    with csv.open("a") as f:
        row = (f"{ts},{data['air_temp']},{data['humidity']},"
               f"{data['water_temp']},{data['ph']},"
               f"{data['lux']},{data['lux_desc']}\n")
        f.write(row)
    db.insert_sensor_reading(
        air_temp_c=data["air_temp"],
        humidity_pct=data["humidity"],
        water_temp_c=data["water_temp"],
        ph=data["ph"],
        lux=data["lux"],
        lux_description=data["lux_desc"],
        loop_count=LOOP_COUNT,
    )


def run_grow_lights(now: datetime.datetime, schedule: dict):
    """Styr odlingslampan. Hoppar över om manuell override är aktiv."""
    if api.get_override("lights") is not None:
        log.info("Grow lights: manuell override aktiv – hoppar över automatik")
        return
    on_h  = schedule.get("light_on_hour",  LIGHT_ON_HOUR)
    off_h = schedule.get("light_off_hour", LIGHT_OFF_HOUR)
    hrs   = schedule.get("light_hours",    LIGHT_HOURS)
    if on_h <= now.hour < off_h:
        sensors.lights_on()
        db.log_actuator_event("grow_lights", "on", "schedule")
        api.write_relay_states()
        time.sleep(hrs * 3600)
        sensors.lights_off()
        db.log_actuator_event("grow_lights", "off", "schedule",
                              duration_sec=hrs * 3600)
        api.write_relay_states()
    else:
        sensors.lights_off()
        api.write_relay_states()


def control_climate(air_temp):
    """Styr fläkt/värmare. Hoppar över enheter med manuell override."""
    if air_temp is None:
        return
    fan_ov    = api.get_override("fan")
    heater_ov = api.get_override("heater")

    if air_temp < TEMP_MIN:
        if heater_ov is None:
            sensors.heater_on()
            db.log_actuator_event("heater", "on", "climate")
        if fan_ov is None:
            sensors.fan_off()
        api.write_relay_states()
        if heater_ov is None:
            time.sleep(30 * 60)
            sensors.heater_off()
            db.log_actuator_event("heater", "off", "climate", duration_sec=1800)
            api.write_relay_states()
    elif air_temp > TEMP_MAX:
        if fan_ov is None:
            sensors.fan_on()
            db.log_actuator_event("fan", "on", "climate")
        if heater_ov is None:
            sensors.heater_off()
        api.write_relay_states()
        if fan_ov is None:
            time.sleep(30 * 60)
            sensors.fan_off()
            db.log_actuator_event("fan", "off", "climate", duration_sec=1800)
            api.write_relay_states()
    else:
        if fan_ov    is None: sensors.fan_off()
        if heater_ov is None: sensors.heater_off()
        api.write_relay_states()


def main():
    global LOOP_COUNT
    START_TIME = datetime.datetime.now()
    log.info("=== HappyFarmer starting ===")
    db.log_system_event("HappyFarmer starting", "info", "main")
    sensors.setup()
    api.set_camera_callback(lambda: capture_image(hires=True))
    api.start()
    homekit.start()
    if not db.test_connection():
        log.warning("DB ej tillganglig - fortsatter med CSV")
    last_hires = None
    last_tl    = None
    try:
        while True:
            LOOP_COUNT += 1
            now = datetime.datetime.now()
            log.info(f"--- Loop {LOOP_COUNT} ---")
            data = sensors.read_all()
            store_sensor_data(data)
            # Skriv state.json för cloud_sync
            try:
                state = {
                    "loop_count":      LOOP_COUNT,
                    "start_time":      START_TIME.isoformat(),
                    "simulation_mode": not sensors.HW_AVAILABLE,
                    "actuator_states": {
                        "pump":        "on" if sensors.pump_is_on()    else "off",
                        "grow_lights": "on" if sensors.lights_is_on()  else "off",
                        "fan":         "on" if sensors.fan_is_on()     else "off",
                        "heater":      "on" if sensors.heater_is_on()  else "off",
                    },
                }
                (DATA_DIR / "state.json").write_text(json.dumps(state))
            except Exception as e:
                log.warning(f"state.json write failed: {e}")
            if SOCIAL_ENABLED and LOOP_COUNT % SOCIAL_POST_EVERY_N_LOOPS == 0:
                post_sensor_update(
                    air_temp=data["air_temp"],
                    water_temp=data["water_temp"],
                    humidity=data["humidity"],
                    light_level=data["lux_desc"],
                )
                db.log_social_post("sensor_update", f"Loop {LOOP_COUNT}")
            schedule = api.get_schedule()
            pump_ov = api.get_override("pump")
            if pump_ov is None:
                on_s  = schedule.get("pump_on_seconds",  PUMP_ON_SECONDS)
                off_s = schedule.get("pump_off_seconds", PUMP_OFF_SECONDS)
                sensors.pump_on()
                db.log_actuator_event("pump", "on", "schedule")
                api.write_relay_states()
                time.sleep(on_s)
                sensors.pump_off()
                db.log_actuator_event("pump", "off", "schedule", duration_sec=on_s)
                api.write_relay_states()
                time.sleep(off_s)
            else:
                log.info(f"Pump: manuell override aktiv ({pump_ov}) – hoppar över automatik")
            run_grow_lights(now, schedule)
            if TIMELAPSE_ENABLED:
                if LOOP_COUNT % (TIMELAPSE_LOWRES_MINS // SLEEP_MINUTES) == 0:
                    capture_image(hires=False)
                if now.hour == TIMELAPSE_HIRES_HOUR and last_hires != now.date():
                    capture_image(hires=True)
                    last_hires = now.date()
                if last_tl is None:
                    last_tl = now.date()
                elif (now.date() - last_tl).days >= TIMELAPSE_BUILD_DAYS:
                    video = build_timelapse()
                    if video and SOCIAL_ENABLED:
                        post_timelapse_update(video)
                        db.log_social_post("timelapse", "Timelapse posted")
                    last_tl = now.date()
            control_climate(data["air_temp"])
            log.info(f"Loop {LOOP_COUNT} done - sleeping {SLEEP_MINUTES} min")
            time.sleep(SLEEP_MINUTES * 60)
    except KeyboardInterrupt:
        log.info("Stopped by user")
        db.log_system_event("Stopped by user", "info", "main")
    except Exception as e:
        log.exception(f"Unhandled error: {e}")
        db.log_system_event(str(e), "error", "main")
    finally:
        sensors.teardown()
        log.info("=== HappyFarmer shutdown ===")


if __name__ == "__main__":
    main()