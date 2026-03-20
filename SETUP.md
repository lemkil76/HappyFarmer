# HappyFarmer - Setup Guide

Komplett installationsguide for Raspberry Pi + Google Drive-synk.

---

## 1. Klona repot till Pi:n

```bash
cd /home/pi
git clone https://github.com/lemkil76/HappyFarmer.git happyfarmer
cd happyfarmer
```

---

## 2. Installera Python-beroenden

```bash
pip install tweepy \
            google-api-python-client \
                        google-auth \
                                    Adafruit-DHT \
                                                RPi.GPIO
                                                ```

                                                > Notera: `Adafruit-DHT` och `RPi.GPIO` kräver riktig Raspberry Pi-hårdvara.

                                                ---

                                                ## 3. Konfigurera Google Drive (gratis, ~5 min)

                                                ### 3a. Skapa ett Google Cloud-projekt

                                                1. Ga till [console.cloud.google.com](https://console.cloud.google.com)
                                                2. Klicka **New Project** → ge det ett namn, t.ex. `happyfarmer`
                                                3. Klicka **Create**

                                                ### 3b. Aktivera Google Drive API

                                                1. I ditt projekt, ga till **APIs & Services → Library**
                                                2. Sok efter `Google Drive API`
                                                3. Klicka **Enable**

                                                ### 3c. Skapa ett Service Account

                                                1. Ga till **APIs & Services → Credentials**
                                                2. Klicka **Create Credentials → Service Account**
                                                3. Ge det ett namn, t.ex. `happyfarmer-pi`
                                                4. Klicka **Create and Continue → Done**

                                                ### 3d. Ladda ner nyckel-filen

                                                1. Klicka pa ditt nya service account i listan
                                                2. Ga till fliken **Keys**
                                                3. Klicka **Add Key → Create new key → JSON**
                                                4. En fil laddas ner automatiskt

                                                ### 3e. Kopiera nyckeln till Pi:n

                                                ```bash
                                                # Kopiera fran din dator till Pi:n via scp
                                                scp ~/Downloads/happyfarmer-pi-xxxx.json pi@raspberrypi.local:/home/pi/happyfarmer/service_account.json
                                                ```

                                                ### 3f. Dela Google Drive-mappen med service account

                                                1. Oppna [drive.google.com](https://drive.google.com) pa din dator
                                                2. Skapa en ny mapp och kalla den `HappyFarmer`
                                                3. Hogerklicka pa mappen → **Share**
                                                4. Klistra in service account-epostadressen (se JSON-filen, faltet `client_email`)
                                                5. Ge den **Editor**-rattigheter
                                                6. Klicka **Share**

                                                > Nu kan Pi:n ladda upp filer till just den mappen.

                                                ---

                                                ## 4. Konfigurera X/Twitter API (valfritt)

                                                Om du vill aktivera sociala medieposter i `TwitterPOC.py`:

                                                1. Ga till [developer.x.com](https://developer.x.com) och skapa ett gratiskonto
                                                2. Skapa en app och generera nycklar under **Keys and Tokens**
                                                3. Lagg till miljovariablerna i `/home/pi/.bashrc`:

                                                ```bash
                                                export HAPPYFARMER_BEARER_TOKEN="din_bearer_token"
                                                export HAPPYFARMER_API_KEY="din_api_key"
                                                export HAPPYFARMER_API_SECRET="din_api_secret"
                                                export HAPPYFARMER_ACCESS_TOKEN="din_access_token"
                                                export HAPPYFARMER_ACCESS_SECRET="din_access_secret"
                                                ```

                                                4. Aktivera: `source ~/.bashrc`

                                                > Tips: Om du inte vill anvanda Twitter satts `SOCIAL_ENABLED = False` i `main.py`.

                                                ---

                                                ## 5. Testa installationen

                                                ```bash
                                                # Testa Google Drive-synken manuellt
                                                python3 /home/pi/happyfarmer/cloud_sync.py

                                                # Testa huvudprogrammet (avbryt med Ctrl+C)
                                                python3 /home/pi/happyfarmer/main.py
                                                ```

                                                ---

                                                ## 6. Starta automatiskt vid boot

                                                ### Lagg till cron-jobb

                                                ```bash
                                                crontab -e
                                                ```

                                                Lagg till dessa rader i slutet:

                                                ```cron
                                                # Starta HappyFarmer vid boot
                                                @reboot sleep 30 && /usr/bin/python3 /home/pi/happyfarmer/main.py >> /home/pi/happyfarmer/boot.log 2>&1

                                                # Synka till Google Drive var 15:e minut
                                                */15 * * * * /usr/bin/python3 /home/pi/happyfarmer/cloud_sync.py
                                                ```

                                                > `sleep 30` ger naetverket tid att ansluta innan programmet startar.

                                                ---

                                                ## 7. Mappstruktur pa Pi:n

                                                ```
                                                /home/pi/happyfarmer/
                                                    main.py                  <- huvudprogrammet
                                                        cloud_sync.py            <- Google Drive-synk
                                                            TwitterPOC.py            <- social media-integration
                                                                service_account.json     <- Google-nyckel (ALDRIG till GitHub!)
                                                                    happyfarmer.log          <- huvudlogg
                                                                        sync.log                 <- synk-logg
                                                                            data/
                                                                                    sensors_YYYY-MM-DD.csv   <- daglig sensordata
                                                                                        timelapse/
                                                                                                *.jpg                <- bilder (raderas efter uppladdning)
                                                                                                        *.mp4                <- videor (raderas efter uppladdning)
                                                                                                        ```
                                                                                                        
                                                                                                        ---
                                                                                                        
                                                                                                        ## 8. Mappstruktur i Google Drive
                                                                                                        
                                                                                                        ```
                                                                                                        HappyFarmer/              <- dela denna med service account
                                                                                                            sensors/
                                                                                                                    sensors_2026-03-20.csv
                                                                                                                            sensors_2026-03-21.csv
                                                                                                                                    ...
                                                                                                                                        timelapse/
                                                                                                                                                images/
                                                                                                                                                            20260320_120000_lowres.jpg
                                                                                                                                                                        ...
                                                                                                                                                                                videos/
                                                                                                                                                                                            timelapse_2026-03-20.mp4
                                                                                                                                                                                                        ...
                                                                                                                                                                                                            logs/
                                                                                                                                                                                                                    happyfarmer.log
                                                                                                                                                                                                                    ```
                                                                                                                                                                                                                    
                                                                                                                                                                                                                    ---
                                                                                                                                                                                                                    
                                                                                                                                                                                                                    ## 9. Gallring och lagring
                                                                                                                                                                                                                    
                                                                                                                                                                                                                    `cloud_sync.py` gallrar automatiskt sensor-CSV-filer som ar aeldre an **90 dagar** (koers kl 03:00 varje natt). Du kan aendra detta i `cloud_sync.py`:
                                                                                                                                                                                                                    
                                                                                                                                                                                                                    ```python
                                                                                                                                                                                                                    purge_old_sensor_files(service, folders, keep_days=90)
                                                                                                                                                                                                                    ```
                                                                                                                                                                                                                    
                                                                                                                                                                                                                    Timelapse-bilder och videor gallras **inte** automatiskt i Drive — det goer du manuellt eller via Google Drive-papperskorgen.
                                                                                                                                                                                                                    
                                                                                                                                                                                                                    ---
                                                                                                                                                                                                                    
                                                                                                                                                                                                                    ## Felsoekning
                                                                                                                                                                                                                    
                                                                                                                                                                                                                    | Problem | Losning |
                                                                                                                                                                                                                    |---|---|
                                                                                                                                                                                                                    | `service_account.json saknas` | Se steg 3d-3e ovan |
                                                                                                                                                                                                                    | `403 Forbidden` fran Drive | Kontrollera att service account har Editor-rattigheter pa mappen |
                                                                                                                                                                                                                    | `DHT22 read failed` | Kontrollera GPIO-pin och kablar |
                                                                                                                                                                                                                    | Ingen naetverk vid boot | Oka `sleep 30` till `sleep 60` i cron |
