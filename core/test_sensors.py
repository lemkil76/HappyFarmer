"""
HappyFarmer - Interactive Sensor Test Menu
core/test_sensors.py
Revised by Claude - 2026-03-20

Terminal-based test tool for verifying all sensors and actuators.
Works in both simulation mode (no RPi) and real hardware mode.

Run from the repo root:
    python3 -m core.test_sensors

Menu:
  1. Hamta luftfuktighet
  2. Hamta vattentemperatur
  3. Hamta lufttemperatur
  4. Hamta pH-varde
  5. Hamta luxvarde
  6. Starta / sla av flakt
  7. Starta / sla av belysning
  8. Starta / sla av vattenvarmaren
  9. Las alla sensorer pa en gang
  0. Avsluta
"""

import sys
import time
import logging
from datetime import datetime

# ── Setup basic logging to stdout for test tool ───────────────────────────────
logging.basicConfig(
    level=logging.WARNING,          # suppress info/debug during interactive use
    format="%(levelname)s: %(message)s",
    stream=sys.stdout,
)

# ── Import sensor module ───────────────────────────────────────────────────────
try:
    from core import sensors
except ModuleNotFoundError:
    import sensors  # fallback if run directly from core/

# ── ANSI color codes ───────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
DIM    = "\033[2m"


def clr(text: str, code: str) -> str:
    """Wrap text in ANSI color code."""
    return f"{code}{text}{RESET}"


def hr(char: str = "─", width: int = 50) -> str:
    return clr(char * width, DIM)


def header(title: str):
    print()
    print(hr())
    print(clr(f"  {title}", BOLD + CYAN))
    print(hr())


def ok(label: str, value, unit: str = ""):
    if value is None:
        print(f"  {label:<25} {clr('FAILED - kontrollera kablar', RED)}")
    else:
        print(f"  {label:<25} {clr(str(value), GREEN)} {unit}")


def toggle_result(name: str, is_on: bool):
    state = clr("ON  ●", GREEN) if is_on else clr("OFF ○", YELLOW)
    print(f"  {name:<20} {state}")


# ==============================================================================
# Test functions
# ==============================================================================

def test_humidity():
    header("Luftfuktighet (DHT22)")
    print(clr("  Laser sensor...", DIM))
    val = sensors.read_humidity()
    ok("Luftfuktighet:", val, "%")
    print()


def test_water_temp():
    header("Vattentemperatur (DS18B20)")
    print(clr("  Laser sensor...", DIM))
    val = sensors.read_water_temperature()
    ok("Vattentemperatur:", val, "°C")
    if val is not None:
        if val < 18:
            print(clr("  ⚠ For kalt - overvaeg att slaa pa varmaren", YELLOW))
        elif val > 28:
            print(clr("  ⚠ For varmt - kontrollera systemet", RED))
        else:
            print(clr("  ✓ Inom normalintervall (18-28°C)", GREEN))
    print()


def test_air_temp():
    header("Lufttemperatur (DHT22)")
    print(clr("  Laser sensor...", DIM))
    val = sensors.read_air_temperature()
    ok("Lufttemperatur:", val, "°C")
    if val is not None:
        if val < 18:
            print(clr("  ⚠ For kalt", YELLOW))
        elif val > 28:
            print(clr("  ⚠ For varmt", RED))
        else:
            print(clr("  ✓ Inom normalintervall (18-28°C)", GREEN))
    print()


def test_ph():
    header("pH-varde (Atlas EZO-pH via I2C)")
    print(clr("  Laser sensor (~1s)...", DIM))
    val = sensors.read_ph()
    ok("pH:", val, "")
    if val is not None:
        if val < 5.5:
            print(clr("  ⚠ For surt - justera naring", YELLOW))
        elif val > 7.5:
            print(clr("  ⚠ For basiskt - justera naring", YELLOW))
        else:
            print(clr("  ✓ Inom optimalt intervall (5.5-7.5)", GREEN))
    print()


def test_lux():
    header("Luxvarde (Fotoresistor via MCP3008 ADC)")
    print(clr("  Laser sensor...", DIM))
    val  = sensors.read_lux()
    desc = sensors.lux_to_description(val)
    ok("Lux:", val, "lx")
    ok("Beskrivning:", desc)
    if val is not None:
        bar_len = min(40, int((val / 12000.0) * 40))
        bar = clr("█" * bar_len, YELLOW) + clr("░" * (40 - bar_len), DIM)
        print(f"  [0 lx] {bar} [12000 lx]")
    print()


def test_fan():
    header("Flakt (GPIO 24)")
    currently_on = sensors.fan_is_on()
    print(f"  Nuvarande status: ", end="")
    toggle_result("Flakt", currently_on)
    print()

    if currently_on:
        action = input(clr("  Sla AV flakten? (j/n): ", BOLD)).strip().lower()
        if action == "j":
            sensors.fan_off()
            print(clr("  ✓ Flakt AV", YELLOW))
        else:
            print(clr("  Ingen andring.", DIM))
    else:
        action = input(clr("  Sla PA flakten? (j/n): ", BOLD)).strip().lower()
        if action == "j":
            sensors.fan_on()
            print(clr("  ✓ Flakt PA", GREEN))
            duration = input(clr("  Hur lange? (sekunder, Enter = manuell): ", BOLD)).strip()
            if duration.isdigit():
                print(clr(f"  Vantar {duration}s...", DIM))
                time.sleep(int(duration))
                sensors.fan_off()
                print(clr("  ✓ Flakt AV (timer)", YELLOW))
        else:
            print(clr("  Ingen andring.", DIM))
    print()


def test_lights():
    header("Belysning - odlingsljus (GPIO 23)")
    currently_on = sensors.lights_is_on()
    print(f"  Nuvarande status: ", end="")
    toggle_result("Belysning", currently_on)
    print()

    if currently_on:
        action = input(clr("  Sla AV belysningen? (j/n): ", BOLD)).strip().lower()
        if action == "j":
            sensors.lights_off()
            print(clr("  ✓ Belysning AV", YELLOW))
        else:
            print(clr("  Ingen andring.", DIM))
    else:
        action = input(clr("  Sla PA belysningen? (j/n): ", BOLD)).strip().lower()
        if action == "j":
            sensors.lights_on()
            print(clr("  ✓ Belysning PA", GREEN))
            duration = input(clr("  Hur lange? (sekunder, Enter = manuell): ", BOLD)).strip()
            if duration.isdigit():
                print(clr(f"  Vantar {duration}s...", DIM))
                time.sleep(int(duration))
                sensors.lights_off()
                print(clr("  ✓ Belysning AV (timer)", YELLOW))
        else:
            print(clr("  Ingen andring.", DIM))
    print()


def test_heater():
    header("Vattenvarmaren (GPIO 25)")
    currently_on = sensors.heater_is_on()
    print(f"  Nuvarande status: ", end="")
    toggle_result("Varmare", currently_on)
    print()

    if currently_on:
        action = input(clr("  Sla AV varmaren? (j/n): ", BOLD)).strip().lower()
        if action == "j":
            sensors.heater_off()
            print(clr("  ✓ Varmare AV", YELLOW))
        else:
            print(clr("  Ingen andring.", DIM))
    else:
        action = input(clr("  Sla PA varmaren? (j/n): ", BOLD)).strip().lower()
        if action == "j":
            sensors.heater_on()
            print(clr("  ✓ Varmare PA", GREEN))
            duration = input(clr("  Hur lange? (sekunder, Enter = manuell): ", BOLD)).strip()
            if duration.isdigit():
                print(clr(f"  Vantar {duration}s...", DIM))
                time.sleep(int(duration))
                sensors.heater_off()
                print(clr("  ✓ Varmare AV (timer)", YELLOW))
        else:
            print(clr("  Ingen andring.", DIM))
    print()


def test_all():
    header("Alla sensorer - snabbgenomgang")
    print(clr("  Laser alla sensorer...", DIM))
    data = sensors.read_all()
    print()
    ok("Lufttemperatur:",  data["air_temp"],   "°C")
    ok("Luftfuktighet:",   data["humidity"],   "%")
    ok("Vattentemperatur:", data["water_temp"], "°C")
    ok("pH:",              data["ph"],          "")
    ok("Lux:",             data["lux"],         "lx")
    ok("Ljusbeskrivning:", data["lux_desc"],    "")
    print()
    print(clr(f"  Tidpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", DIM))
    print()


# ==============================================================================
# Main menu
# ==============================================================================

MENU = [
    ("1", "Hamta luftfuktighet",            test_humidity),
    ("2", "Hamta vattentemperatur",          test_water_temp),
    ("3", "Hamta lufttemperatur",            test_air_temp),
    ("4", "Hamta pH-varde",                  test_ph),
    ("5", "Hamta luxvarde",                  test_lux),
    ("6", "Starta / sla av flakt",           test_fan),
    ("7", "Starta / sla av belysning",       test_lights),
    ("8", "Starta / sla av vattenvarmaren",  test_heater),
    ("9", "Las alla sensorer pa en gang",    test_all),
    ("0", "Avsluta",                         None),
]


def print_menu():
    sim = clr(" [SIMULATION]", YELLOW) if not sensors.HW_AVAILABLE else clr(" [HARDWARE]", GREEN)
    print()
    print(clr("  ╔══════════════════════════════════╗", CYAN))
    print(clr("  ║   HappyFarmer - Sensortest       ║", CYAN + BOLD))
    print(clr("  ╚══════════════════════════════════╝", CYAN))
    print(f"  Lage:{sim}")
    print()
    for key, label, _ in MENU:
        bullet = clr(f"  [{key}]", BOLD + CYAN)
        print(f"{bullet} {label}")
    print()


def main():
    sensors.setup()
    try:
        while True:
            print_menu()
            choice = input(clr("  Val: ", BOLD + CYAN)).strip()
            matched = False
            for key, _, fn in MENU:
                if choice == key:
                    matched = True
                    if fn is None:
                        print(clr("\n  Avslutar. Alla aktuatorer stangda av.\n", DIM))
                        sensors.teardown()
                        sys.exit(0)
                    fn()
                    input(clr("  Tryck Enter for att fortsatta...", DIM))
                    break
            if not matched:
                print(clr("  ⚠ Ogiltigt val - prova igen.", YELLOW))
    except KeyboardInterrupt:
        print(clr("\n\n  Avbryts av anvandaren. Slangar av aktuatorer.", YELLOW))
        sensors.teardown()
        sys.exit(0)


if __name__ == "__main__":
    main()
