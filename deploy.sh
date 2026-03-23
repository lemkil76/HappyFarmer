#!/bin/bash
# HappyFarmer - Deploy script
# Kopierar dashboard-filer fran lokalt repo till NAS.
#
# Kor fran repots rot:
#   cd ~/Documents/Coding/HappyFarmer && sh deploy.sh

NAS_USER="lemkil76"
NAS_HOST="nas"
NAS_PATH="/volume1/web/happyfarmer"

# Debug - visa full sokvag
echo "============================"
echo "NAS_USER : $NAS_USER"
echo "NAS_HOST : $NAS_HOST"
echo "NAS_PATH : $NAS_PATH"
echo "Mal      : $NAS_USER@$NAS_HOST:$NAS_PATH/dashboard/"
echo "============================"
echo ""

echo "Kopierar dashboard/ till NAS..."
echo ""

rsync -avz --progress \
  --exclude='.DS_Store' \
    dashboard/ \
      $NAS_USER@$NAS_HOST:$NAS_PATH/dashboard/

      if [ $? -eq 0 ]; then
        echo ""
          echo "Deploy klar!"
            echo "Dashboard: http://$NAS_HOST:8080/dashboard/dashboard_wireframe.html"
            else
              echo ""
                echo "FEL: rsync misslyckades."
                  exit 1
                  fi
