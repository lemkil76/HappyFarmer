#!/bin/bash
# HappyFarmer - Deploy script
# Kopierar dashboard-filer fran lokalt repo till NAS.
#
# Kor fran repots rot:
#   cd ~/Documents/Coding/HappyFarmer && sh deploy.sh

NAS_USER="lemkil76"
NAS_HOST="nas"
NAS_WEB="/volume1/web/happyfarmer"

echo "============================"
echo "NAS_USER : $NAS_USER"
echo "NAS_HOST : $NAS_HOST"
echo "NAS_PATH : $NAS_WEB"
echo "============================"
echo ""

echo "Kopierar dashboard-filer till NAS via scp..."
echo ""

# dashboard.html -> NAS-roten (http://nas:8080/dashboard.html)
scp -O dashboard/dashboard.html lemkil76@192.168.1.100:$NAS_WEB/dashboard.html

# Assets (sample_data.json) -> dashboard/-mappen
scp -O dashboard/sample_data.json lemkil76@192.168.1.100:$NAS_WEB/dashboard/sample_data.json

# PHP live-API -> api/-mappen
ssh lemkil76@192.168.1.100 "mkdir -p $NAS_WEB/api"
scp -O dashboard/api/data.php      lemkil76@192.168.1.100:$NAS_WEB/api/data.php
scp -O dashboard/api/settings.php  lemkil76@192.168.1.100:$NAS_WEB/api/settings.php
scp -O dashboard/api/log_event.php lemkil76@192.168.1.100:$NAS_WEB/api/log_event.php
scp -O dashboard/api/admin_redirect.php lemkil76@192.168.1.100:$NAS_WEB/api/admin_redirect.php

if [ $? -ne 0 ]; then
  echo ""
  echo "FEL: scp misslyckades."
  exit 1
fi

# Injicera DB-lösenord i PHP-filer direkt efter kopiering
# Lösenordet läses ur secrets.py på Pi (aldrig i git)
DB_PASS=$(ssh -o ConnectTimeout=5 pi@192.168.1.128 "cd /home/pi/happyfarmer && python3 -c \"from config.secrets import DB_PASS; print(DB_PASS)\" 2>/dev/null")
if [ -n "$DB_PASS" ]; then
  ssh lemkil76@192.168.1.100 "
    sed -i \"s/define('DB_PASS', '');/define('DB_PASS', '$DB_PASS');/\" $NAS_WEB/api/data.php
    sed -i \"s/define('DB_PASS',   '');/define('DB_PASS',   '$DB_PASS');/\" $NAS_WEB/api/settings.php
    sed -i \"s/define('DB_PASS',    '');/define('DB_PASS',    '$DB_PASS');/\" $NAS_WEB/api/log_event.php
    sed -i \"s/define('DB_PASS',   '');/define('DB_PASS',   '$DB_PASS');/\" $NAS_WEB/api/admin_redirect.php
  "
  echo "DB-lösenord injicerat automatiskt."
else
  echo "OBS: Kunde inte hämta DB_PASS – sätt det manuellt i api/data.php och api/settings.php på NAS."
fi

echo ""
echo "Deploy klar!"
echo "Dashboard : http://$NAS_HOST:8080/dashboard.html"
echo "Live API  : http://$NAS_HOST:8080/api/data.php"
echo "Inställn. : http://$NAS_HOST:8080/api/settings.php"
