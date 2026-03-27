"""
HappyFarmer – Apple HomeKit Integration
integrations/homekit.py
Revised by Claude - 2026-03-27

Exponerar HappyFarmer-sensorer och reläer i Apple Home-appen
via HomeKit Accessory Protocol (HAP-python).

Startas som en daemon-tråd av core/main.py.

Install:
    pip3 install --break-system-packages HAP-python

Parning:
    1. Starta main.py
    2. Öppna Apple Home → Lägg till tillbehör → Sök i närheten
    3. Välj "HappyFarmer" och ange PIN: 111-22-333

Enheter som exponeras:
    Sensorer : Luftklimat (temp+fukt), Vattentemperatur, Ljusnivå, pH-larm
    Switchar : Vattenpump, Odlingslampa, Fläkt, Vattenvärmare
"""

import threading
import logging
from pathlib import Path

log = logging.getLogger("happyfarmer.homekit")

HAP_PINCODE = b"111-22-333"   # Ändra till valfri kod (format: XXX-XX-XXX)
HAP_PORT    = 51826
HAP_STATE   = Path("/home/pi/happyfarmer/data/homekit.state")


try:
    from pyhap.accessory import Accessory, Bridge
    from pyhap.accessory_driver import AccessoryDriver
    from pyhap.const import CATEGORY_SENSOR, CATEGORY_SWITCH
    HAP_OK = True
except ImportError:
    HAP_OK = False
    log.warning("HAP-python saknas – HomeKit inaktivt. "
                "Kör: pip3 install --break-system-packages HAP-python")


if HAP_OK:

    # ── Luftklimat – DHT22 (temp + fuktighet) ─────────────────────────────────

    class AirClimateSensor(Accessory):
        """Lufttemperatur och relativ fuktighet från DHT22."""
        category = CATEGORY_SENSOR

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            t = self.add_preload_service("TemperatureSensor")
            self.temp = t.configure_char("CurrentTemperature")
            h = self.add_preload_service("HumiditySensor")
            self.hum  = h.configure_char("CurrentRelativeHumidity")

        @Accessory.run_at_interval(30)
        async def run(self):
            from core import sensors
            temp, hum = sensors.read_air_climate()
            if temp is not None:
                self.temp.set_value(round(float(temp), 1))
            if hum is not None:
                self.hum.set_value(round(float(min(100, max(0, hum))), 1))


    # ── Vattentemperatur – DS18B20 ────────────────────────────────────────────

    class WaterTempSensor(Accessory):
        """Vattentemperatur från DS18B20 via 1-Wire."""
        category = CATEGORY_SENSOR

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            serv = self.add_preload_service("TemperatureSensor")
            self.temp = serv.configure_char("CurrentTemperature")

        @Accessory.run_at_interval(30)
        async def run(self):
            from core import sensors
            temp = sensors.read_water_temperature()
            if temp is not None:
                self.temp.set_value(round(float(temp), 1))


    # ── Ljusnivå – MCP3008 ────────────────────────────────────────────────────

    class LuxSensor(Accessory):
        """Ljusnivå i lux från fotomotstånd via MCP3008 ADC."""
        category = CATEGORY_SENSOR

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            serv = self.add_preload_service("LightSensor")
            self.lux = serv.configure_char("CurrentAmbientLightLevel")

        @Accessory.run_at_interval(30)
        async def run(self):
            from core import sensors
            lux = sensors.read_lux()
            if lux is not None:
                self.lux.set_value(max(0.0001, float(lux)))


    # ── pH-larm – Atlas EZO-pH ────────────────────────────────────────────────

    class PhAlarmSensor(Accessory):
        """pH-sensor representerad som larm i HomeKit.

        ContactSensor = öppen (larm) när pH är utanför 5.5–7.5.
        AirQuality visar exakt nivå:
            Excellent  pH 5.5 – 7.5  (optimalt)
            Good       pH 5.0 – 8.0
            Fair       pH 4.5 – 8.5
            Inferior   pH 4.0 – 9.0
            Poor       utanför ovan
        """
        category = CATEGORY_SENSOR

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            aq   = self.add_preload_service("AirQualitySensor")
            self.quality = aq.configure_char("AirQuality")
            cs   = self.add_preload_service("ContactSensor")
            self.alert   = cs.configure_char("ContactSensorState")

        @staticmethod
        def _ph_quality(ph: float) -> int:
            if 5.5 <= ph <= 7.5: return 1  # Excellent
            if 5.0 <= ph <= 8.0: return 2  # Good
            if 4.5 <= ph <= 8.5: return 3  # Fair
            if 4.0 <= ph <= 9.0: return 4  # Inferior
            return 5                        # Poor

        @Accessory.run_at_interval(60)
        async def run(self):
            from core import sensors
            ph = sensors.read_ph()
            if ph is not None:
                self.quality.set_value(self._ph_quality(ph))
                # 0 = kontakt sluten (OK), 1 = öppen (larm)
                self.alert.set_value(0 if 5.5 <= ph <= 7.5 else 1)


    # ── Reläbrytare ───────────────────────────────────────────────────────────

    class RelaySwitch(Accessory):
        """Styr ett relä som en HomeKit-switch.

        Aktivering sätter manuell override i api.py.
        Stängs av via AUTO-knappen i adminpanelen eller Apple Home.
        """
        category = CATEGORY_SWITCH

        _RELAY_FNS = {
            "pump":   ("pump_on",   "pump_off"),
            "lights": ("lights_on", "lights_off"),
            "fan":    ("fan_on",    "fan_off"),
            "heater": ("heater_on", "heater_off"),
        }

        _STATE_FNS = {
            "pump":   "pump_is_on",
            "lights": "lights_is_on",
            "fan":    "fan_is_on",
            "heater": "heater_is_on",
        }

        def __init__(self, *args, relay_name: str, **kwargs):
            super().__init__(*args, **kwargs)
            self.relay_name = relay_name
            serv = self.add_preload_service("Switch")
            self.on_char = serv.configure_char(
                "On", setter_callback=self._set_relay
            )

        def _set_relay(self, value: bool):
            from core import api, sensors
            state    = "on" if value else "off"
            on_fn, off_fn = self._RELAY_FNS[self.relay_name]
            with api._lock:
                api._state["manual"][self.relay_name] = state
                getattr(sensors, on_fn if value else off_fn)()
            log.info(f"HomeKit: '{self.relay_name}' → {state}")

        @Accessory.run_at_interval(10)
        async def run(self):
            """Synkar switch-läge med faktisk GPIO-status."""
            from core import sensors
            is_on = getattr(sensors, self._STATE_FNS[self.relay_name])()
            self.on_char.set_value(is_on)


    # ── Bygg bridge ───────────────────────────────────────────────────────────

    def _build_bridge(driver) -> Bridge:
        bridge = Bridge(driver, display_name="HappyFarmer")
        bridge.add_accessory(AirClimateSensor(driver, "Luftklimat"))
        bridge.add_accessory(WaterTempSensor(driver,  "Vattentemperatur"))
        bridge.add_accessory(LuxSensor(driver,         "Ljusnivå"))
        bridge.add_accessory(PhAlarmSensor(driver,     "pH-larm"))
        bridge.add_accessory(RelaySwitch(driver, "Vattenpump",    relay_name="pump"))
        bridge.add_accessory(RelaySwitch(driver, "Odlingslampa",  relay_name="lights"))
        bridge.add_accessory(RelaySwitch(driver, "Fläkt",         relay_name="fan"))
        bridge.add_accessory(RelaySwitch(driver, "Vattenvärmare", relay_name="heater"))
        return bridge


# ── Publik startfunktion ───────────────────────────────────────────────────────

def _get_local_ip() -> str:
    """Hämtar Pi:ns lokala IP utan att nå internet."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.168.1.1", 80))   # router – ingen data skickas
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())


def start():
    """Startar HomeKit-bridge i en daemon-tråd. Anropas från main()."""
    if not HAP_OK:
        log.warning("HAP-python saknas – HomeKit startar ej")
        return

    HAP_STATE.parent.mkdir(parents=True, exist_ok=True)

    try:
        local_ip = _get_local_ip()
        driver = AccessoryDriver(
            port         = HAP_PORT,
            persist_file = str(HAP_STATE),
            pincode      = HAP_PINCODE,
            address      = local_ip,
        )
        driver.add_accessory(_build_bridge(driver))

        t = threading.Thread(
            target=driver.start,
            daemon=True,
            name="HappyFarmer-HomeKit",
        )
        t.start()
        log.info(
            f"HomeKit-bridge startad på port {HAP_PORT} "
            f"– parningskod: {HAP_PINCODE.decode()}"
        )
    except Exception as e:
        log.error(f"HomeKit kunde inte startas: {e} – fortsätter utan HomeKit")
