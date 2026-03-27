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

# Assets (sample_data.json, latest_image.jpg) -> dashboard/-mappen
scp -O dashboard/sample_data.json lemkil76@192.168.1.100:$NAS_WEB/dashboard/sample_data.json

if [ $? -eq 0 ]; then
  echo ""
  echo "Deploy klar!"
  echo "Dashboard: http://$NAS_HOST:8080/dashboard.html"
else
  echo ""
  echo "FEL: scp misslyckades."
  exit 1
fi
