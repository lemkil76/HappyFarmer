-- ============================================================
-- HappyFarmer – System Events 2026-03-27
-- Loggar dagens arbete i kronologisk ordning
-- ============================================================

USE happyfarmer;

INSERT INTO system_events (occurred_at, level, source, message) VALUES
('2026-03-27 09:00:00', 'info', 'homekit',      'HAP-python 5.0.0 installerat på Pi – HomeKit Accessory Protocol implementerat i Python'),
('2026-03-27 09:15:00', 'info', 'homekit',      'integrations/homekit.py skapad – Bridge med 4 reläswitchar och 3 sensortillbehör'),
('2026-03-27 09:30:00', 'info', 'homekit',      'HomeKit-bridge startad på port 51826 – annonseras via avahi/Bonjour på nätverket'),
('2026-03-27 09:45:00', 'info', 'homekit',      'HappyFarmer parat med Apple Home – pump, lampa, fläkt, värmare, klimat och pH synliga'),
('2026-03-27 10:00:00', 'info', 'homekit',      'Apple TV konfigurerad som HomeKit-hub – fjärrstyrning möjlig utanför hemmanätverket'),
('2026-03-27 10:15:00', 'info', 'main',         'happyfarmer.service skapad som systemd-service – startar automatiskt vid omstart'),
('2026-03-27 10:30:00', 'info', 'main',         'Crontab städad – @reboot och dubbletter för sensor/kamera borttagna, cloud_sync behållen'),
('2026-03-27 10:45:00', 'info', 'sensors',      'VMA311 (DHT11) kopplad till GPIO 17 – lufttemperatur och luftfuktighet verifierade'),
('2026-03-27 11:00:00', 'info', 'sensors',      'Luftfuktighet 21% och temperatur 24.3°C bekräftade i MariaDB och dashboarden'),
('2026-03-27 11:15:00', 'info', 'dashboard',    'Kamera (Logitech HD 1080p) konfigurerad – fswebcam tar 1920x1080-bild var 5:e minut'),
('2026-03-27 11:30:00', 'info', 'sensors',      'Keyes 4-kanals relämodul (ver 4R18) kopplad – VCC pin4, GND pin20, IN1-4 på GPIO 22-25'),
('2026-03-27 11:45:00', 'info', 'sensors',      'Relämodul verifierad som aktiv-LOW – LED tänd = GPIO HIGH = relä AV, LED släckt = relä PÅ'),
('2026-03-27 12:00:00', 'info', 'sensors',      'core/test_sensors.py uppdaterad – val 6 (vattenpump) tillagt, fan/lights/heater omplacerade till 7-9'),
('2026-03-27 12:15:00', 'info', 'homekit',      'Bugg fixad i homekit.py – AccessoryDriver anropade 8.8.8.8 vid uppstart, kraschar om nätet ej redo'),
('2026-03-27 12:30:00', 'info', 'homekit',      'homekit.py: _get_local_ip() använder router (192.168.1.1) istället för internet, try/except tillagd'),
('2026-03-27 12:45:00', 'info', 'dashboard',    'Bugg fixad i admin.html – doConfirm() nollställde pendingRelay/pendingState före anrop till setRelay()'),
('2026-03-27 13:00:00', 'info', 'api',          'Reläkontroll via adminpanel fulltestad – PÅ/AV/AUTO för pump, lampa, fläkt och värmare fungerar'),
('2026-03-27 13:15:00', 'info', 'sensors',      'DS18B20 vattentemperatursond konfigurerad – dtoverlay=w1-gpio aktiverat på GPIO 4 (1-Wire)'),
('2026-03-27 13:30:00', 'info', 'main',         'Systemtest klart – alla reläer, manuell override, automatisk styrning och schema verifierade');
