#!/bin/bash
# HappyFarmer - Deploy script
# Kopierar dashboard-filer fran lokalt repo till NAS.
#
# Kor fran repots rot:
#   cd ~/Documents/Coding/HappyFarmer && sh deploy.sh
#
# Slipp losenord - lagg till SSH-nyckel en gang:
#   ssh-keygen -t ed25519 -C "happyfarmer"
#   ssh-copy-id lemkil76@nas

NAS_USER="lemkil76"
NAS_HOST="nas"
NAS_PATH="/web/happyfarmer/dashboard"

echo "Hamtar senaste koden fran GitHub..."
git pull

if [ $? -ne 0 ]; then
  echo "FEL: git pull misslyckades. Avbryter."
    exit 1
    fi

    echo ""
    echo "Kopierar dashboard/ till ${NAS_USER}@${NAS_HOST}:${NAS_PATH}..."
    echo ""

    rsync -avz --progress \
      --exclude='.DS_Store' \
        dashboard/ \
          ${NAS_USER}@${NAS_HOST}:${NAS_PATH}/

          if [ $? -eq 0 ]; then
            echo ""
              echo "Deploy klar!"
                echo "Dashboard: http://${NAS_HOST}:8080/dashboard/dashboard_wireframe.html"
                else
                  echo ""
                    echo "FEL: rsync misslyckades. Kontrollera:"
                      echo "  - NAS narbar:         ping ${NAS_HOST}"
                        echo "  - SSH fungerar:       ssh ${NAS_USER}@${NAS_HOST}"
                          echo "  - Skrivbehorighet:    ssh ${NAS_USER}@${NAS_HOST} touch ${NAS_PATH}/test.txt"
                            exit 1
                            fi
