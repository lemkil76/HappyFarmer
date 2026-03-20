"""
HappyFarmer - Main Control Loop
core/main.py
Revised by Claude - 2026-03-20

All paths imported from config/paths.py.
To relocate the installation, change BASE_DIR in config/paths.py only.

Run:
    cd /home/pi/happyfarmer && python3 -m core.main
"""

import time, datetime, logging, subprocess
from config.paths import DATA_DIR, TIMELAPSE_DIR, LOG_FILE

logging.basicConfig(filename=str(LOG_FILE), level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("happyfarmer")

try:
    import RPi.GPIO as GPIO, Adafruit_DHT
    HW_AVAILABLE = True
except ImportError:
    log.warning("RPi libs not found - simulation mode")
    HW_AVAILABLE = False

from integrations.social_media import (
    post_sensor_update, post_timelapse_update, verify_credentials
)

# ── GPIO pin map ───────────────────────────────────────────────────────────────
PIN_DHT22        = 4
PIN_WATER_TEMP   = 17
PIN_PUMP_RELAY   = 22
PIN_LIGHT_RELAY  = 23
PIN_FAN_RELAY    = 24
PIN_HEATER_RELAY = 25

# ── Global variables (V in flowchart) ─────────────────────────────────────────
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

TIMELAPSE_LOWRES_MINS    = 60
TIMELAPSE_HIRES_HOUR     = 11
TIMELAPSE_BUILD_DAYS     = 30
SOCIAL_POST_EVERY_N_LOOPS = 1152  # ~4 days at 5-min intervals


# ── GPIO helpers ───────────────────────────────────────────────────────────────

def setup_gpio():
    if not HW_AVAILABLE: return
    GPIO.setmode(GPIO.BCM)
    for pin in [PIN_PUMP_RELAY, PIN_LIGHT_RELAY, PIN_FAN_RELAY, PIN_HEATER_RELAY]:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
    log.info("GPIO initialised")

def relay_on(pin):
    if HW_AVAILABLE: GPIO.output(pin, GPIO.LOW)

def relay_off(pin):
    if HW_AVAILABLE: GPIO.output(pin, GPIO.HIGH)


# ── Sensor reads ───────────────────────────────────────────────────────────────

def read_air_climate():
    """Return (air_temp_C, humidity_pct). Simulation fallback if no hardware."""
    if not HW_AVAILABLE: return 22.0, 60.0
    h, t = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, PIN_DHT22)
    if t is None: log.error("DHT22 read failed"); return None, None
    return round(t, 1), round(h, 1)

def read_water_climate():
    """Return (water_temp_C, ph)."""
    if not HW_AVAILABLE: return 20.0, 6.5
    from pathlib import Path
    try:
        f = list(Path("/sys/bus/w1/devices").glob("28-*"))[0] / "w1_slave"
        temp_c = int(f.read_text().splitlines()[1].split("t=")[1]) / 1000.0
    except Exception as e:
        log.error(f"DS18B20 failed: {e}"); temp_c = None
    return temp_c, None  # pH: implement Atlas I2C protocol as needed

def read_light_level():
    """Return light level string via fotoresistor ADC."""
    if not HW_AVAILABLE: return "dag"
    return "okand"  # TODO: implement MCP3008 SPI read


# ── Operations ─────────────────────────────────────────────────────────────────

def run_pump_cycle():
    """30 min ON / 15 min OFF as per flowchart."""
    log.info("Pump ON (30 min)")
    relay_on(PIN_PUMP_RELAY)
    time.sleep(PUMP_ON_SECONDS)
    relay_off(PIN_PUMP_RELAY)
    log.info("Pump OFF (15 min aeration)")
    time.sleep(PUMP_OFF_SECONDS)

def run_grow_lights(now: datetime.datetime):
    """Control lights by schedule."""
    if LIGHT_ON_HOUR <= now.hour < LIGHT_OFF_HOUR:
        log.info("Grow lights ON")
        relay_on(PIN_LIGHT_RELAY)
        time.sleep(LIGHT_HOURS * 3600)
        relay_off(PIN_LIGHT_RELAY)
        log.info("Grow lights OFF")
    else:
        relay_off(PIN_LIGHT_RELAY)

def control_climate(air_temp):
    """Fan/heater based on temperature thresholds."""
    if air_temp is None: return
    if air_temp < TEMP_MIN:
        log.info(f"Heater ON ({air_temp}C < {TEMP_MIN}C)")
        relay_on(PIN_HEATER_RELAY); relay_off(PIN_FAN_RELAY)
        time.sleep(30 * 60); relay_off(PIN_HEATER_RELAY)
    elif air_temp > TEMP_MAX:
        log.info(f"Fan ON ({air_temp}C > {TEMP_MAX}C)")
        relay_on(PIN_FAN_RELAY); relay_off(PIN_HEATER_RELAY)
        time.sleep(30 * 60); relay_off(PIN_FAN_RELAY)
    else:
        relay_off(PIN_FAN_RELAY); relay_off(PIN_HEATER_RELAY)

def store_sensor_data(air_temp, humidity, water_temp, ph, light):
    """Append reading to daily CSV in DATA_DIR."""
    ts = datetime.datetime.now().isoformat()
    csv = DATA_DIR / f"sensors_{datetime.date.today()}.csv"
    if not csv.exists():
        csv.write_text("timestamp,air_temp,humidity,water_temp,ph,light\n")
    with csv.open("a") as f:
        f.write(f"{ts},{air_temp},{humidity},{water_temp},{ph},{light}\n")
    log.info(f"Sensor stored: air={air_temp} water={water_temp} hum={humidity}")

def capture_image(hires: bool = False):
    """Capture from USB camera via fswebcam."""
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = TIMELAPSE_DIR / f"{ts}_{'hires' if hires else 'lowres'}.jpg"
    try:
        subprocess.run(
            ["fswebcam", "-r", "1920x1080" if hires else "640x480", "--no-banner", str(path)],
            check=True, capture_output=True)
        log.info(f"Image: {path}"); return str(path)
    except Exception as e:
        log.error(f"Camera failed: {e}"); return None

def build_timelapse():
    """Assemble low-res frames into MP4 via ffmpeg."""
    out = TIMELAPSE_DIR / f"timelapse_{datetime.date.today()}.mp4"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-framerate", "24", "-pattern_type", "glob",
            "-i", str(TIMELAPSE_DIR / "*_lowres.jpg"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)
        ], check=True, capture_output=True)
        log.info(f"Timelapse: {out}"); return str(out)
    except Exception as e:
        log.error(f"Timelapse failed: {e}"); return None


# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    global LOOP_COUNT
    log.info("=== HappyFarmer starting ===")
    setup_gpio()
    if SOCIAL_ENABLED: verify_credentials()

    last_hires = None
    last_tl    = None

    try:
        while True:
            LOOP_COUNT += 1
            now = datetime.datetime.now()
            log.info(f"--- Loop {LOOP_COUNT} ---")

            forced_start = False  # TODO: read GPIO button
            if forced_start:
                relay_on(PIN_PUMP_RELAY); relay_on(PIN_LIGHT_RELAY)

            air_temp, humidity = read_air_climate()
            water_temp, ph     = read_water_climate()
            light              = read_light_level()

            store_sensor_data(air_temp, humidity, water_temp, ph, light)
            run_pump_cycle()
            run_grow_lights(now)

            if TIMELAPSE_ENABLED:
                if LOOP_COUNT % (TIMELAPSE_LOWRES_MINS // SLEEP_MINUTES) == 0:
                    capture_image(hires=False)
                if now.hour == TIMELAPSE_HIRES_HOUR and last_hires != now.date():
                    capture_image(hires=True); last_hires = now.date()
                if last_tl is None:
                    last_tl = now.date()
                elif (now.date() - last_tl).days >= TIMELAPSE_BUILD_DAYS:
                    v = build_timelapse()
                    if v and SOCIAL_ENABLED: post_timelapse_update(v)
                    last_tl = now.date()

            if SOCIAL_ENABLED and air_temp and LOOP_COUNT % SOCIAL_POST_EVERY_N_LOOPS == 0:
                post_sensor_update(air_temp, water_temp or 0.0, humidity or 0.0, light)

            control_climate(air_temp)
            log.info(f"Loop {LOOP_COUNT} done - sleeping {SLEEP_MINUTES} min")
            time.sleep(SLEEP_MINUTES * 60)

    except KeyboardInterrupt:
        log.info("Stopped by user")
    except Exception as e:
        log.exception(f"Unhandled error: {e}")
    finally:
        if HW_AVAILABLE:
            for p in [PIN_PUMP_RELAY, PIN_LIGHT_RELAY, PIN_FAN_RELAY, PIN_HEATER_RELAY]:
                relay_off(p)
            GPIO.cleanup()
        log.info("=== HappyFarmer shutdown ===")


if __name__ == "__main__":
    main()
