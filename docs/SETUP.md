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
2. Klicka **New Project** och ge det ett namn, t.ex. `happyfarmer`
3. Klicka **Create**

### 3b. Aktivera Google Drive API

1. Ga till **APIs & Services → Library**
2. Sok efter `Google Drive API` och klicka **Enable**

### 3c. Skapa ett Service Account

1. Ga till **APIs & Services → Credentials**
2. Klicka **Create Credentials → Service Account**
3. Ge det ett namn, t.ex. `happyfarmer-pi`
4. Klicka **Create and Continue → Done**

### 3d. Ladda ner nyckel-filen

1. Klicka pa service account i listan
2. Ga till fliken **Keys → Add Key → Create new key → JSON**
3. En fil laddas ner automatiskt

### 3e. Kopiera nyckeln till Pi:n

```bash
scp ~/Downloads/happyfarmer-pi-xxxx.json pi@raspberrypi.local:/home/pi/happyfarmer/service_account.json
```

### 3f. Dela Google Drive-mappen med service account

1. Oppna [drive.google.com](https://drive.google.com)
2. Skapa en ny mapp och kalla den `HappyFarmer`
3. Hogerklicka → **Share**
4. Klistra in service account-epostadressen (fran JSON-filen, faltet `client_email`)
5. Ge den **Editor**-rattigheter och klicka **Share**

---

## 4. Konfigurera X/Twitter API (valfritt)

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

> Tips: Satt `SOCIAL_ENABLED = False` i `config/secrets.py` om du inte vill anvanda Twitter.

---

## 5. Konfigurera paths (valfritt)

Alla sokvagar definieras i **`config/paths.py`**.
Om du installerar HappyFarmer pa ett annat stalle an `/home/pi/happyfarmer`,
aendra bara denna ena variabel:

```python
# config/paths.py
BASE_DIR = Path("/din/anpassade/sokvag")
```

Alla andra sokvagar (data, timelapse, loggar, credentials) uppdateras automatiskt.

---

## 6. Konfigurera secrets

```bash
cp config/secrets.example.py /home/pi/happyfarmer/config/secrets.py
nano /home/pi/happyfarmer/config/secrets.py   # fyll i dina vaerden
```

`config/secrets.py` blockeras av `.gitignore` och pushas aldrig till GitHub.

---

## 7. Testa installationen

```bash
# Testa Google Drive-synken
python3 -m integrations.cloud_sync

# Testa huvudprogrammet (avbryt med Ctrl+C)
python3 -m core.main
```

---

## 8. Starta automatiskt vid boot

```bash
crontab -e
```

Lagg till i slutet:

```cron
# Starta HappyFarmer vid boot
@reboot sleep 30 && /usr/bin/python3 -m core.main >> /home/pi/happyfarmer/boot.log 2>&1

# Synka till Google Drive var 15:e minut
*/15 * * * * cd /home/pi/happyfarmer && /usr/bin/python3 -m integrations.cloud_sync
```

> `sleep 30` ger naetverket tid att ansluta. `cd` kravs for att Python-importerna ska fungera.

---

## 9. Mappstruktur pa Pi:n

```
/home/pi/happyfarmer/           <- BASE_DIR (aendra i config/paths.py)
    core/
        main.py                 <- huvudprogrammet
    integrations/
        social_media.py         <- X/Twitter-integration
        cloud_sync.py           <- Google Drive-synk
    config/
        paths.py                <- CENTRAL PATH-KONFIGURATION
        secrets.example.py      <- mall (finns i GitHub)
        secrets.py              <- dina nycklar (ALDRIG till GitHub)
    dashboard/
        dashboard_wireframe.html
    docs/
        SETUP.md
        HappyFarmer_workflow_revised_by_claude.svg
    service_account.json        <- Google-nyckel (ALDRIG till GitHub)
    happyfarmer.log             <- huvudlogg
    sync.log                    <- synk-logg
    data/
        sensors_YYYY-MM-DD.csv  <- daglig sensordata
    timelapse/
        *.jpg                   <- raderas efter Drive-uppladdning
        *.mp4                   <- raderas efter Drive-uppladdning
```

---

## 10. Mappstruktur i Google Drive

```
HappyFarmer/
    sensors/
        sensors_2026-03-20.csv
        ...
    timelapse/
        images/
            20260320_120000_lowres.jpg
            ...
        videos/
            timelapse_2026-03-20.mp4
    logs/
        happyfarmer.log
```

---

## 11. Gallring och lagring

`integrations/cloud_sync.py` gallrar automatiskt sensor-CSV-filer aeldre an **90 dagar**
(koers kl 03:00 varje natt). Aendra i `config/secrets.py`:

```python
SENSOR_KEEP_DAYS = 90
```

---

## Felsoekning

| Problem | Losning |
|---|---|
| `service_account.json saknas` | Se steg 3d–3e |
| `403 Forbidden` fran Drive | Kontrollera Editor-rattigheter pa mappen |
| `DHT22 read failed` | Kontrollera GPIO-pin 4 och kablar |
| Ingen naetverk vid boot | Oka `sleep 30` till `sleep 60` i cron |
| `ModuleNotFoundError: config` | Kör alltid fran `/home/pi/happyfarmer` eller med `python3 -m` |
