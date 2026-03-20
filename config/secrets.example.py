"""
HappyFarmer - Secrets Template
config/secrets.example.py
=================================
DENNA FIL AR EN MALL - inte en riktig secrets-fil.

Steg:
  1. Kopiera till Pi:n:
       cp config/secrets.example.py /home/pi/happyfarmer/config/secrets.py
  2. Fyll i dina riktiga nycklar i config/secrets.py
  3. config/secrets.py blockeras av .gitignore - pushas ALDRIG till GitHub

ALLA SOKVAGAR importeras fran config/paths.py.
Aendra BARA BASE_DIR i config/paths.py for att flytta hela installationen.
"""

# Paths importeras automatiskt - ingen hardkodning behovs har
from config.paths import SA_FILE, BASE_DIR

# ── Google Drive ───────────────────────────────────────────────────────────────
GOOGLE_SA_FILE      = SA_FILE        # Pekar pa BASE_DIR/service_account.json
GOOGLE_DRIVE_FOLDER = "HappyFarmer"  # Maste delas med service account

# ── X / Twitter API (valfritt) ─────────────────────────────────────────────────
# Lamna som None om du inte vill anvanda social media
# Se docs/SETUP.md steg 4 for hur du skapar nycklar
SOCIAL_ENABLED         = False
TWITTER_BEARER_TOKEN   = None  # "xxxx..."
TWITTER_API_KEY        = None  # "xxxx..."
TWITTER_API_SECRET     = None  # "xxxx..."
TWITTER_ACCESS_TOKEN   = None  # "xxxx..."
TWITTER_ACCESS_SECRET  = None  # "xxxx..."

# ── Systeminstaellningar ────────────────────────────────────────────────────────
SLEEP_MINUTES     = 5      # Minuter mellan varje loop-cykel
TEMP_MIN          = 18.0   # Under detta: slaa pa vaermaren (Celsius)
TEMP_MAX          = 28.0   # Over detta: slaa pa kylflakten (Celsius)
TIMELAPSE_ENABLED = True   # Aktivera/avaktivera timelapse-fotografering
SENSOR_KEEP_DAYS  = 90     # Dagars sensorhistorik att behaalla i Drive

# ── GPIO-pinnar (BCM-numrering) ────────────────────────────────────────────────
PIN_DHT22        = 4   # Lufttemp + luftfuktighet (DHT22)
PIN_WATER_TEMP   = 17  # Vattentemperatur (DS18B20, 1-Wire)
PIN_PUMP_RELAY   = 22  # Vattenpump
PIN_LIGHT_RELAY  = 23  # Odlingsljus
PIN_FAN_RELAY    = 24  # Kylflakt
PIN_HEATER_RELAY = 25  # Vaermare
