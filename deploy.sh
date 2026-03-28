#!/bin/bash
# HappyFarmer - Deploy script
# Kopierar dashboard-filer fran lokalt repo till lacasa (Pi 5).
#
# Kor fran repots rot:
#   cd ~/Documents/Coding/HappyFarmer && sh deploy.sh

LACASA_USER="pi"
LACASA_HOST="lacasa"
LACASA_WEB="/var/www/happyfarmer"

echo "============================"
echo "HOST     : $LACASA_HOST"
echo "USER     : $LACASA_USER"
echo "WEB_PATH : $LACASA_WEB"
echo "============================"
echo ""

# Las DB-losenord fran lokal .env (aldrig i git)
DB_PASS=""
if [ -f "$(dirname "$0")/.env" ]; then
  DB_PASS=$(grep '^DB_PASS=' "$(dirname "$0")/.env" | cut -d'=' -f2-)
fi

if [ -z "$DB_PASS" ]; then
  echo "OBS: Ingen .env hittad. Ange DB_PASS manuellt:"
  read -r -s -p "DB_PASS: " DB_PASS
  echo ""
fi

echo "Kopierar dashboard-filer till lacasa via scp..."
echo ""

# Skapa mappstruktur pa lacasa
ssh "$LACASA_USER@$LACASA_HOST" "mkdir -p $LACASA_WEB/api $LACASA_WEB/dashboard"

# dashboard.html -> webbrot
scp dashboard/dashboard.html "$LACASA_USER@$LACASA_HOST:$LACASA_WEB/dashboard.html"

# admin.html -> webbrot
scp dashboard/admin.html "$LACASA_USER@$LACASA_HOST:$LACASA_WEB/admin.html"

# Assets
scp dashboard/sample_data.json  "$LACASA_USER@$LACASA_HOST:$LACASA_WEB/dashboard/sample_data.json"
scp dashboard/sample_image.jpg  "$LACASA_USER@$LACASA_HOST:$LACASA_WEB/dashboard/sample_image.jpg"

# PHP live-API
scp dashboard/api/data.php          "$LACASA_USER@$LACASA_HOST:$LACASA_WEB/api/data.php"
scp dashboard/api/settings.php      "$LACASA_USER@$LACASA_HOST:$LACASA_WEB/api/settings.php"
scp dashboard/api/log_event.php     "$LACASA_USER@$LACASA_HOST:$LACASA_WEB/api/log_event.php"
scp dashboard/api/admin_redirect.php "$LACASA_USER@$LACASA_HOST:$LACASA_WEB/api/admin_redirect.php"

if [ $? -ne 0 ]; then
  echo ""
  echo "FEL: scp misslyckades."
  exit 1
fi

# Injicera DB-losenord i PHP-filer pa lacasa
ssh "$LACASA_USER@$LACASA_HOST" "
  sed -i \"s/define('DB_PASS', '');/define('DB_PASS', '$DB_PASS');/\" $LACASA_WEB/api/data.php
  sed -i \"s/define('DB_PASS',   '');/define('DB_PASS',   '$DB_PASS');/\" $LACASA_WEB/api/settings.php
  sed -i \"s/define('DB_PASS',    '');/define('DB_PASS',    '$DB_PASS');/\" $LACASA_WEB/api/log_event.php
  sed -i \"s/define('DB_PASS',   '');/define('DB_PASS',   '$DB_PASS');/\" $LACASA_WEB/api/admin_redirect.php
"
echo "DB-losenord injicerat."

# Git pull pa lacasa (Flask serverar admin.html fran repot)
echo "Git pull pa lacasa..."
ssh "$LACASA_USER@$LACASA_HOST" "cd /home/pi/happyfarmer && git pull"

# Git pull pa RASP (sensorer och core)
echo "Git pull pa RASP..."
ssh -o ConnectTimeout=5 pi@RASP "cd /home/pi/happyfarmer && git pull" || echo "OBS: RASP ej nåbar"

echo ""
echo "Deploy klar!"
echo "Dashboard : https://lemkil76.duckdns.org/happyfarmer/dashboard.html"
echo "Admin     : https://lemkil76.duckdns.org/happyfarmer/admin.html"
