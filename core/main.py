"""
HappyFarmer - Main Control Loop
core/main.py
Revised by Claude - 2026-03-20

All sensor/actuator operations are delegated to core/sensors.py.
This file contains only the business logic (loop, scheduling, decisions).

Run:
    python3 -m core.main

All paths from config/paths.py - change BASE_DIR there to relocate.
"""

import time
import datetime
import logging
import subprocess

from config.paths import DATA_DIR, TIMELAPSE_DIR, LOG_FILE
from core import sensors
from integrations.social_media import (
    post_sensor_update, post_timelapse_update, verify_credentials
)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("happyfarmer")

# ── Global variables (V in flowchart) ─────────────────────────────────────────
TIMELAPSE_ENABLED = True
SOCIAL_ENABLED    = True
SLEEP_MINUTES     = 5
LOOP_COUNT        = 0

# Grow light schedule
LIGHT_ON_HOUR  = 6
LIGHT_OFF_HOUR = 23
LIGHT_HOURS    = 5

# Temperature thresholds (Celsius)
TEMP_MIN = 18.0
TEMP_MAX = 28.0

# Pump cycle
PUMP_ON_SECONDS  = 30 * 60
PUMP_OFF_SECONDS = 15 * 60

# Timelapse schedule
TIMELAPSE_LOWRES_MINS     = 60
TIMELAPSE_HIRES_HOUR      = 11
TIMELAPSE_BUILD_DAYS      = 30
SOCIAL_POST_EVERY_N_LOOPS = 1152   # ~4 days at 5-min intervals


# ==============================================================================
# Scheduling helpers
# ==============================================================================

def should_lights_be_on(now: datetime.datetime) -> bool:
    return LIGHT_ON_HOUR <= now.hour < LIGHT_OFF_HOUR


def run_grow_lights(now: datetime.datetime):
    if should_lights_be_on(now):
        sensors.lights_on()
        time.sleep(LIGHT_HOURS * 3600)
        sensors.lights_off()
    else:
        sensors.lights_off()


def control_climate(air_temp: float | None):
    """Fan/heater based on air temperature thresholds."""
    if air_temp is None:
        log.warning("No air temp reading - skipping climate control")
        return
    if air_temp < TEMP_MIN:
        log.info(f"Temp {air_temp}C < {TEMP_MIN}C - heater ON (30 min)")
        sensors.heater_on()
        sensors.fan_off()
        time.sleep(30 * 60)
        sensors.heater_off()
    elif air_temp > TEMP_MAX:
        log.info(f"Temp {air_temp}C > {TEMP_MAX}C - fan ON (30 min)")
        sensors.fan_on()
        sensors.heater_off()
        time.sleep(30 * 60)
        sensors.fan_off()
    else:
        sensors.fan_off()
        sensors.heater_off()


# ==============================================================================
# Data storage
# ==============================================================================

def store_sensor_data(data: dict):
    """Append sensor reading to daily CSV in DATA_DIR."""
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


# ==============================================================================
# Camera / timelapse
# ==============================================================================

def capture_image(hires: bool = False) -> str | None:
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = TIMELAPSE_DIR / f"{ts}_{'hires' if hires else 'lowres'}.jpg"
    try:
        subprocess.run(
            ["fswebcam", "-r", "1920x1080" if hires else "640x480",
             "--no-banner", str(path)],
            check=True, capture_output=True,
        )
        log.info(f"Image captured: {path}")
        return str(path)
    except Exception as e:
        log.error(f"Camera failed: {e}")
        return None


def build_timelapse() -> str | None:
    out = TIMELAPSE_DIR / f"timelapse_{datetime.date.today()}.mp4"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-framerate", "24",
            "-pattern_type", "glob",
            "-i", str(TIMELAPSE_DIR / "*_lowres.jpg"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out),
        ], check=True, capture_output=True)
        log.info(f"Timelapse built: {out}")
        return str(out)
    except Exception as e:
        log.error(f"Timelapse failed: {e}")
        return None


# ==============================================================================
# Main loop
# ==============================================================================

def main():
    global LOOP_COUNT

    log.info("=== HappyFarmer starting ===")
    sensors.setup()

    if SOCIAL_ENABLED:
        verify_credentials()

    last_hires = None
    last_tl    = None

    try:
        while True:
            LOOP_COUNT += 1
            now = datetime.datetime.now()
            log.info(f"--- Loop {LOOP_COUNT} ---")

            # Forced start (physical button - TODO: read GPIO pin)
            # if gpio_button_pressed(): sensors.pump_on(); sensors.lights_on()

            # 1. Read all sensors via core/sensors.py
            data = sensors.read_all()
            log.info(
                f"air={data['air_temp']}C hum={data['humidity']}% "
                f"water={data['water_temp']}C ph={data['ph']} lux={data['lux']}"
            )

            # 2. Store to filesystem
            store_sensor_data(data)

            # 3. Pump cycle (30 min ON / 15 min OFF)
            sensors.run_pump_cycle(PUMP_ON_SECONDS, PUMP_OFF_SECONDS)

            # 4. Grow lights (schedule-based)
            run_grow_lights(now)

            # 5. Timelapse capture + build
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
                    last_tl = now.date()

            # 6. Social media post (every ~4 days)
            if SOCIAL_ENABLED and data["air_temp"] is not None:
                if LOOP_COUNT % SOCIAL_POST_EVERY_N_LOOPS == 0:
                    post_sensor_update(
                        data["air_temp"],
                        data["water_temp"] or 0.0,
                        data["humidity"]   or 0.0,
                        data["lux_desc"],
                    )

            # 7. Climate control (fan / heater)
            control_climate(data["air_temp"])

            log.info(f"Loop {LOOP_COUNT} done - sleeping {SLEEP_MINUTES} min")
            time.sleep(SLEEP_MINUTES * 60)

    except KeyboardInterrupt:
        log.info("Stopped by user")
    except Exception as e:
        log.exception(f"Unhandled error: {e}")
    finally:
        sensors.teardown()
        log.info("=== HappyFarmer shutdown ===")


if __name__ == "__main__":
    main()
