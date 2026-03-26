#!/bin/bash
# HappyFarmer - Deploy script
# Kopierar dashboard-filer fran lokalt repo till NAS.
#
# Kor fran repots rot:
#   cd ~/Documents/Coding/HappyFarmer && sh deploy.sh

NAS_USER="lemkil76"
NAS_HOST="nas"
NAS_PATH="/volume1/web/happyfarmer/dashboard"

echo "============================"
echo "NAS_USER : $NAS_USER"
echo "NAS_HOST : $NAS_HOST"
echo "NAS_PATH : $NAS_PATH"
echo "============================"
echo ""

echo "Kopierar dashboard/ till NAS via scp..."
echo ""

scp -O -r dashboard/dashboard_wireframe.html dashboard/sample_data.json lemkil76@192.168.1.100:/volume1/web/happyfarmer/dashboard/

if [ $? -eq 0 ]; then
  echo ""
    echo "Deploy klar!"
      echo "Dashboard: http://$NAS_HOST:8080/dashboard/dashboard_wireframe.html"
      else
        echo ""
          echo "FEL: scp misslyckades."
            exit 1
            fi
