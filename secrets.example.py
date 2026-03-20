"""
HappyFarmer - Secrets Template
===============================
DETTA AR EN MALL - inte en riktig secrets-fil.

Instruktioner:
  1. Kopiera den har filen till Pi:n:
       cp secrets.example.py /home/pi/happyfarmer/secrets.py
  2. Fyll i dina riktiga nycklar i secrets.py
  3. secrets.py blockeras av .gitignore och pushas ALDRIG till GitHub

Anvandning i koden:
  from secrets import GOOGLE_SA_FILE, SOCIAL_ENABLED, ...
"""

# Google Drive
GOOGLE_SA_FILE      = "/home/pi/happyfarmer/service_account.json"
GOOGLE_DRIVE_FOLDER = "HappyFarmer"

# X / Twitter API (valfritt - lamna som None om ej anvands)
SOCIAL_ENABLED         = False
TWITTER_BEARER_TOKEN   = None  # "xxxx..."
TWITTER_API_KEY        = None  # "xxxx..."
TWITTER_API_SECRET     = None  # "xxxx..."
TWITTER_ACCESS_TOKEN   = None  # "xxxx..."
TWITTER_ACCESS_SECRET  = None  # "xxxx..."

# Systeminstaellningar
SLEEP_MINUTES     = 5
TEMP_MIN          = 18.0
TEMP_MAX          = 28.0
TIMELAPSE_ENABLED = True
SENSOR_KEEP_DAYS  = 90

# GPIO-pinnar (BCM-numrering)
PIN_DHT22        = 4
PIN_WATER_TEMP   = 17
PIN_PUMP_RELAY   = 22
PIN_LIGHT_RELAY  = 23
PIN_FAN_RELAY    = 24
PIN_HEATER_RELAY = 25
