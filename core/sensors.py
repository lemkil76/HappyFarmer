"""
HappyFarmer - Sensor & Actuator Module
core/sensors.py
Revised by Claude - 2026-03-20

All hardware operations live here. core/main.py imports and calls these
functions — keeping the main loop clean and this module independently testable.

Sensors:
  - DHT22     Air temperature + humidity          GPIO 4  (1-Wire)
  - DS18B20   Water temperature                   GPIO 17 (1-Wire sysfs)
  - Atlas EZO-pH  pH via I2C                      I2C bus
  - MCP3008   Photoresistor (lux) via SPI ADC     SPI

Actuators (relay board, active-low):
  - GPIO 22  Water pump
  - GPIO 23  Grow lights
  - GPIO 24  Cooling fan
  - GPIO 25  Water heater

All pin numbers and thresholds are imported from config/paths.py and
config/secrets.py so a single change there propagates everywhere.
"""

import time
import logging
from pathlib import Path

log = logging.getLogger("happyfarmer.sensors")

# ── Try importing hardware libs ────────────────────────────────────────────────
try:
    import RPi.GPIO as GPIO
    import Adafruit_DHT
    HW_AVAILABLE = True
except ImportError:
    log.warning("RPi hardware libs not found - sensors running in simulation mode")
    HW_AVAILABLE = False

# ── Pin map (BCM numbering) ────────────────────────────────────────────────────
PIN_DHT22        = 4   # Air temp + humidity (DHT22)
PIN_WATER_TEMP   = 17  # DS18B20 data (1-Wire kernel driver)
PIN_PUMP_RELAY   = 22  # Water pump    (active-low relay)
PIN_LIGHT_RELAY  = 23  # Grow lights   (active-low relay)
PIN_FAN_RELAY    = 24  # Cooling fan   (active-low relay)
PIN_HEATER_RELAY = 25  # Water heater  (active-low relay)

ALL_RELAY_PINS = [PIN_PUMP_RELAY, PIN_LIGHT_RELAY, PIN_FAN_RELAY, PIN_HEATER_RELAY]

# ── I2C address for Atlas EZO-pH ──────────────────────────────────────────────
PH_I2C_ADDRESS = 0x63  # Default Atlas EZO-pH address

# ── MCP3008 channel for photoresistor ─────────────────────────────────────────
LUX_CHANNEL = 0        # SPI channel 0 on MCP3008


# ==============================================================================
# GPIO setup / teardown
# ==============================================================================

def setup():
    """Initialise all GPIO pins. Call once at program start."""
    if not HW_AVAILABLE:
        log.info("Simulation mode - skipping GPIO setup")
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in ALL_RELAY_PINS:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)  # HIGH = relay OFF
    log.info("GPIO initialised")


def teardown():
    """Turn off all actuators and release GPIO. Call at program exit."""
    if not HW_AVAILABLE:
        return
    for pin in ALL_RELAY_PINS:
        GPIO.output(pin, GPIO.HIGH)  # ensure everything is off
    GPIO.cleanup()
    log.info("GPIO cleaned up")


# ==============================================================================
# Relay helpers
# ==============================================================================

def _relay_on(pin: int):
    if HW_AVAILABLE:
        GPIO.output(pin, GPIO.LOW)


def _relay_off(pin: int):
    if HW_AVAILABLE:
        GPIO.output(pin, GPIO.HIGH)


def _relay_state(pin: int) -> bool:
    """Return True if relay is currently ON (active-low: LOW = ON)."""
    if not HW_AVAILABLE:
        return False
    return GPIO.input(pin) == GPIO.LOW


# ==============================================================================
# Sensor: Air temperature + humidity (DHT22)
# ==============================================================================

def read_air_temperature() -> float | None:
    """
    Read air temperature from DHT22.
    Returns temperature in Celsius, or None on failure.
    """
    if not HW_AVAILABLE:
        return 22.5  # simulation

    _, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, PIN_DHT22)
    if temperature is None:
        log.error("DHT22: temperature read failed")
        return None
    return round(temperature, 1)


def read_humidity() -> float | None:
    """
    Read relative humidity from DHT22.
    Returns humidity as percentage (0-100), or None on failure.
    """
    if not HW_AVAILABLE:
        return 64.0  # simulation

    humidity, _ = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, PIN_DHT22)
    if humidity is None:
        log.error("DHT22: humidity read failed")
        return None
    return round(humidity, 1)


def read_air_climate() -> tuple[float | None, float | None]:
    """
    Read both air temperature and humidity from DHT22 in one call
    (avoids two separate sensor reads).
    Returns (temperature_C, humidity_pct).
    """
    if not HW_AVAILABLE:
        return 22.5, 64.0  # simulation

    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, PIN_DHT22)
    if temperature is None or humidity is None:
        log.error("DHT22: combined read failed")
        return None, None
    return round(temperature, 1), round(humidity, 1)


# ==============================================================================
# Sensor: Water temperature (DS18B20 via 1-Wire sysfs)
# ==============================================================================

def read_water_temperature() -> float | None:
    """
    Read water temperature from DS18B20 via Linux 1-Wire sysfs interface.
    Returns temperature in Celsius, or None on failure.

    Prerequisite: add to /boot/config.txt:
        dtoverlay=w1-gpio,gpiopin=17
    """
    if not HW_AVAILABLE:
        return 20.1  # simulation

    try:
        w1_base = Path("/sys/bus/w1/devices")
        sensor_dirs = list(w1_base.glob("28-*"))
        if not sensor_dirs:
            log.error("DS18B20: no 1-Wire device found under /sys/bus/w1/devices")
            return None
        slave_file = sensor_dirs[0] / "w1_slave"
        lines = slave_file.read_text().splitlines()
        if "YES" not in lines[0]:
            log.error("DS18B20: CRC check failed")
            return None
        temp_str = lines[1].split("t=")[1]
        return round(int(temp_str) / 1000.0, 1)
    except Exception as e:
        log.error(f"DS18B20 read failed: {e}")
        return None


# ==============================================================================
# Sensor: pH (Atlas Scientific EZO-pH via I2C)
# ==============================================================================

def read_ph() -> float | None:
    """
    Read pH value from Atlas Scientific EZO-pH sensor via I2C.
    Returns pH value (0-14), or None on failure.

    Prerequisite: enable I2C in raspi-config and set sensor to I2C mode.
    Install: pip install smbus2
    """
    if not HW_AVAILABLE:
        return 6.5  # simulation

    try:
        import smbus2
        bus = smbus2.SMBus(1)
        # Send 'R' (read) command
        bus.write_i2c_block_data(PH_I2C_ADDRESS, 0, [ord('R')])
        time.sleep(0.9)  # EZO-pH needs ~900 ms to process
        data = bus.read_i2c_block_data(PH_I2C_ADDRESS, 0, 7)
        bus.close()
        # First byte is status code, rest is ASCII pH value
        if data[0] != 1:
            log.error(f"EZO-pH: bad status code {data[0]}")
            return None
        ph_str = "".join(chr(b) for b in data[1:] if b != 0)
        return round(float(ph_str), 2)
    except ImportError:
        log.error("smbus2 not installed - run: pip install smbus2")
        return None
    except Exception as e:
        log.error(f"EZO-pH read failed: {e}")
        return None


# ==============================================================================
# Sensor: Light level / lux (Photoresistor via MCP3008 ADC, SPI)
# ==============================================================================

def read_lux() -> int | None:
    """
    Read light level from photoresistor via MCP3008 ADC (SPI).
    Returns raw ADC value 0-1023, mapped to approximate lux.
    Returns None on failure.

    Wiring: photoresistor + 10kOhm voltage divider into MCP3008 CH0.
    Install: pip install spidev
    """
    if not HW_AVAILABLE:
        return 8240  # simulation (lux)

    try:
        import spidev
        spi = spidev.SpiDev()
        spi.open(0, 0)  # bus 0, device 0
        spi.max_speed_hz = 1_000_000
        # MCP3008 read: start bit + single-ended mode + channel
        cmd = [1, (8 + LUX_CHANNEL) << 4, 0]
        reply = spi.xfer2(cmd)
        spi.close()
        raw = ((reply[1] & 3) << 8) | reply[2]  # 0-1023
        # Approximate lux mapping: 0 ADC = dark, 1023 = ~12000 lux
        lux = int((raw / 1023.0) * 12000)
        return lux
    except ImportError:
        log.error("spidev not installed - run: pip install spidev")
        return None
    except Exception as e:
        log.error(f"MCP3008 lux read failed: {e}")
        return None


def lux_to_description(lux: int | None) -> str:
    """Convert lux value to human-readable description."""
    if lux is None:
        return "okand"
    if lux < 100:
        return "morker"
    if lux < 1000:
        return "inomhusljus"
    if lux < 5000:
        return "molnigt"
    return "dag"


# ==============================================================================
# Actuator: Water pump
# ==============================================================================

def pump_on():
    """Turn water pump ON."""
    _relay_on(PIN_PUMP_RELAY)
    log.info("Pump ON")


def pump_off():
    """Turn water pump OFF."""
    _relay_off(PIN_PUMP_RELAY)
    log.info("Pump OFF")


def pump_is_on() -> bool:
    return _relay_state(PIN_PUMP_RELAY)


def run_pump_cycle(on_seconds: int = 1800, off_seconds: int = 900):
    """
    Run one full pump cycle: ON for on_seconds, then OFF for off_seconds.
    Default: 30 min ON, 15 min OFF (as per flowchart).
    """
    pump_on()
    time.sleep(on_seconds)
    pump_off()
    log.info(f"Pump aeration pause ({off_seconds}s)")
    time.sleep(off_seconds)


# ==============================================================================
# Actuator: Grow lights
# ==============================================================================

def lights_on():
    """Turn grow lights ON."""
    _relay_on(PIN_LIGHT_RELAY)
    log.info("Lights ON")


def lights_off():
    """Turn grow lights OFF."""
    _relay_off(PIN_LIGHT_RELAY)
    log.info("Lights OFF")


def lights_is_on() -> bool:
    return _relay_state(PIN_LIGHT_RELAY)


# ==============================================================================
# Actuator: Cooling fan
# ==============================================================================

def fan_on():
    """Turn cooling fan ON."""
    _relay_on(PIN_FAN_RELAY)
    log.info("Fan ON")


def fan_off():
    """Turn cooling fan OFF."""
    _relay_off(PIN_FAN_RELAY)
    log.info("Fan OFF")


def fan_is_on() -> bool:
    return _relay_state(PIN_FAN_RELAY)


# ==============================================================================
# Actuator: Water heater
# ==============================================================================

def heater_on():
    """Turn water heater ON."""
    _relay_on(PIN_HEATER_RELAY)
    log.info("Heater ON")


def heater_off():
    """Turn water heater OFF."""
    _relay_off(PIN_HEATER_RELAY)
    log.info("Heater OFF")


def heater_is_on() -> bool:
    return _relay_state(PIN_HEATER_RELAY)


# ==============================================================================
# Convenience: read all sensors at once
# ==============================================================================

def read_all() -> dict:
    """
    Read all sensors and return results as a dict.
    Called once per main loop iteration.
    """
    air_temp, humidity = read_air_climate()
    lux = read_lux()
    return {
        "air_temp":   air_temp,
        "humidity":   humidity,
        "water_temp": read_water_temperature(),
        "ph":         read_ph(),
        "lux":        lux,
        "lux_desc":   lux_to_description(lux),
    }
