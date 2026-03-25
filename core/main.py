"""
HappyFarmer - Main Control Loop
core/main.py
Revised by Claude - 2026-03-24

Sensordata skrivs till bade CSV (fallback) och MariaDB.
All sensor/aktuator-logik delegeras till core/sensors.py.
All DB-logik delegeras till integrations/db.py.

Kor:
    python3 -m core.main
    """

import time
import datetime
import logging
import subprocess

from config.paths import DATA_DIR, TIMELAPSE_DIR, LOG_FILE
from core import sensors
from integrations import db
from integrations.social_media import (
    post_sensor_update, post_timelapse_update, verify_credentials
)

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

LIGHT_ON_HOUR  = 6
LIGHT_OFF_HOUR = 23
LIGHT_HOURS    = 5

TEMP_MIN = 18.0
TEMP_MAX = 28.0

PUMP_ON_SECONDS  = 30 * 60
PUMP_OFF_SECONDS = 15 * 60

TIMELAPSE_LOWRES_MINS     = 60
TIMELAPSE_HIRES_HOUR      = 11
TIMELAPSE_BUILD_DAYS      = 30
SOCIAL_POST_EVERY_N_LOOPS = 1152


def run_grow_lights(now: datetime.datetime):
        if LIGHT_ON_HOUR <= now.hour < LIGHT_OFF_HOUR:
                    sensors.lights_on()
                    db.log_actuator_event("grow_lights", "on", "schedule")
                    time.sleep(LIGHT_HOURS * 3600)
                    sensors.lights_off()
                    db.log_actuator_event("grow_lights", "off", "schedule",
                                          duration_sec=LIGHT_HOURS * 3600)
else:
        sensors.lights_off()


def control_climate(air_temp):
        if air_temp is None:
                    return
                if air_temp < TEMP_MIN:
                            log.info(f"Heater ON ({air_temp}C < {TEMP_MIN}C)")
                            sensors.heater_on()
                            sensors.fan_off()
                            db.log_actuator_event("heater", "on", "climate")
                            time.sleep(30 * 60)
                            sensors.heater_off()
                            db.log_actuator_event("heater", "off", "climate", duration_sec=1800)
elif air_temp > TEMP_MAX:
        log.info(f"Fan ON ({air_temp}C > {TEMP_MAX}C)")
        sensors.fan_on()
        sensors.heater_off()
        db.log_actuator_event("fan", "on", "climate")
        time.sleep(30 * 60)
        sensors.fan_off()
        db.log_actuator_event("fan", "off", "climate", duration_sec=1800)
else:
        sensors.fan_off()
        sensors.heater_off()


def store_sensor_data(data: dict):
        """Skriv till bade CSV (fallback) och MariaDB."""
    ts  = datetime.datetime.now().isoformat()
    csv = DATA_DIR / f"sensors_{datetime.date.today()}.csv"
    if not csv.exists():
                csv.write_text("timestamp,air_temp,humidity,water_temp,ph,lux,lux_desc\n")
            with csv.open("a") as f:
                        f.write(
                                        f"{ts},{data['air_temp']},{data['humidity']},"
                                        f"{data['water_temp']},{data['ph']},"
                                        f"{data['lux']},{data['lux_desc']}\n"
                        )
                    db.insert_sensor_reading(
                                air_temp_c      = data["air_temp"],
                                humidity_pct    = data["humidity"],
                                water_temp_c    = data["water_temp"],
                                ph              = data["ph"],
                                lux             = data["lux"],
                                lux_description = data["lux_desc"],
                                loop_count      = LOOP_COUNT,
                    )


def capture_image(hires: bool = False):
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = TIMELAPSE_DIR / f"{ts}_{'hires' if hires else 'lowres'}.jpg"
    try:
                subprocess.run(
                                ["fswebcam", "-r", "1920x1080" if hires else "640x480",
                                              "--no-banner", str(path)],
                                check=True, capture_output=True,
                )
                db.log_timelapse_image(
                    filename   = path.name,
                    image_type = "hires" if hires else "lowres",
                    resolution = "1920x1080" if hires else "640x480",
                )
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


def main():
        global LOOP_COUNT

    log.info("=== HappyFarmer starting ===")
    db.log_system_event("HappyFarmer starting", "info", "main")
    sensors.setup()

    if not db.test_connection():
                log.warning("DB ej tillganglig - fortsatter med CSV-lagring")

    if SOCIAL_ENABLED:
                verify_credentials()

    last_hires = None
    last_tl    = None

    try:
                while True:
                                LOOP_COUNT += 1
                                now = datetime.datetime.now()
                                log.info(f"--- Loop {LOOP_COUNT} ---")

                    data = sensors.read_all()
            log.info(
                                f"air={data['air_temp']}C hum={data['humidity']}% "
                                f"water={data['water_temp']}C ph={data['ph']} lux={data['lux']}"
            )

            store_sensor_data(data)

            sensors.pump_on()
            db.log_actuator_event("pump", "on", "schedule")
            time.sleep(PUMP_ON_SECONDS)
            sensors.pump_off()
            db.log_actuator_event("pump", "off", "schedule", duration_sec=PUMP_ON_SECONDS)
            time.sleep(PUMP_OFF_SECONDS)

            run_grow_lights(now)

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

            if SOCIAL_ENABLED and data["air_temp"] is not None:
                                if LOOP_COUNT % SOCIAL_POST_EVERY_N_LOOPS == 0:
                    msg = (f"Lufttemp: {data['air_temp']}C | "
                                                      f"Vatten: {data['water_temp']}C | "
                                                      f"Fukt: {data['humidity']}% | "
                                                      f"Ljus: {data['lux_desc']}")
                    post_sensor_update(
                                                data["air_temp"],
                                                data["water_temp"] or 0.0,
                                                data["humidity"]   or 0.0,
                                                data["lux_desc"],
                    )
                    db.log_social_post("sensor_update", msg)

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
