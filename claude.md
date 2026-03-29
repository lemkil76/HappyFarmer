# Hemma Techstack – Projektöversikt

> Uppdaterad: 2026-03-29 (rev 6)

---

## 1. Syfte & Mål

- **Hemautomation / Smarthome** – Bygga smarthome från grunden
- **Data & AI-experiment** – OpenAI, Anthropic m.fl. via Python
- **Elektronik / Hårdvara** – Projekt med Arduino Uno x2 och sensorer
- **Webbutveckling / Appar** – Bygga och drifta webbapplikationer lokalt

Primärspråk: **Python**. Serverkörning: **Bare metal** (ingen Docker).

---

## 2. Hårdvara – Datorer & Servrar

| Enhet | Modell | Roll |
|---|---|---|
| MacBook Air | – | Huvudutvecklingsmaskin |
| Raspberry Pi 4 | Model B | HappyFarmer hub – GPIO, sensorer, kamera, Flask API (192.168.1.128) |
| Raspberry Pi 5 | Model B 8GB | lacasa – Nginx, MariaDB, PHP, webbserver (192.168.1.129) |
| Synology NAS | DS211+ | Filserver / e-post (192.168.1.100) – ej längre webbserver |
| Raspberry Pi Zero | – | Reserv / ej tilldelad |
| Raspberry Pi 3 | Model B x2 | Reserv / ej tilldelad |
| Arduino Uno | x2 | Sensorer, aktorer, hårdvaruprojekt |
| PC | Windows (äldre) | Sekundär maskin / testmiljö |
| TV | Samsung (stor) x2 | Display / dashboard |
| Mobil | Samsung S23 | Mobil klient |
| Surfplatta | Samsung Galaxy Tab (äldre) | Kontrollpanel / dashboard |

---

## 3. Hårdvara – Sensorer & Komponenter (Inventering)

| Kategori | Produktnamn | Modell | Beskrivning |
|---|---|---|---|
| LCD-skärm | LCD 16x2 Display | SBC-LCD16x2 | Visar text och data, kopplad till mikrokontroller |
| Rörelsesensor | PIR Sensor | HC-SR501 | Rörelsedetektering, säkerhetssystem |
| Relämodul | Relä Modul | JQC-3FF-S-Z | Styr högspänningskretsar med lågspänningssignaler |
| LCD-modul | Grafisk LCD | Varierande | Visar bilder och grafik |
| Ljudsensor | Microphone Module | – | Detekterar ljudnivåer |
| Servomotor | Digital Servomotor | LF-20MG | Styr rörelse i robotar och mekaniska system |
| Rörelsedetektor | IR Rörelsedetektor | IR-1 | Detekterar rörelse i säkerhetssystem |
| SD-kortadapter | microSD till SD Adapter | – | Ansluter microSD till standard SD-kortplats |
| Vattenventil | Vattenventil | VMA422 | Elektriskt styrd ventil för vattenflöde |
| Temperatursond | DS18B20 Temperatursond | VMA324 | Digital temperaturgivare (används i HappyFarmer) |
| pH-sensor | pH-sensor | – | Mäter pH-nivåer i vätskor (används i HappyFarmer) |
| Arduino Uno | Arduino Uno | – | Mikrokontrollerplattform |
| RTC-modul | Real Time Clock | DS3231 | Håller tid och datum, tidsstämpling |
| RF-modul | RF Transceiver Module | RFM69 | Trådlös kommunikation mellan enheter |

---

## 4. HappyFarmer – Aktiv Installation

HappyFarmer är ett automatiserat vertical farming-system på Raspberry Pi 4 (RASP) med Raspberry Pi 5 (lacasa) som webbserver.

### Nätverksinfo

| Enhet | IP | Åtkomst |
|---|---|---|
| Raspberry Pi 4 (RASP) | 192.168.1.128 | `ssh pi@192.168.1.128` |
| Raspberry Pi 5 (lacasa) | 192.168.1.129 | `ssh pi@lacasa` |
| Dashboard | – | `https://lemkil76.duckdns.org/happyfarmer/` |
| Admin | – | `https://lemkil76.duckdns.org/happyfarmer/admin.html` |
| Landningssida | – | `https://lemkil76.duckdns.org/` |

### Arkitektur

```
Browser
  └── Nginx (lacasa:443, HTTPS, Duck DNS + Let's Encrypt)
        ├── /happyfarmer/         → PHP + static files (port 8080)
        ├── /happyfarmer/api/*    → Flask API proxy → RASP:5000
        └── /                    → Landningssida (/var/www/html/)

RASP (Pi 4)
  ├── core/main.py        – Huvudloop, GPIO, sensorer, kamera, timelapse
  ├── core/api.py         – Flask REST API (port 5000, ej exponerad externt)
  └── integrations/
        ├── db.py         – MariaDB på lacasa (192.168.1.129:3306)
        └── cloud_sync.py – SCP latest_image.jpg + relay_states.json → lacasa

lacasa (Pi 5)
  ├── Nginx               – Reverse proxy + statiska filer
  ├── MariaDB 11          – Port 3306, databas: happyfarmer
  ├── PHP 8.4-FPM         – data.php, settings.php, log_event.php
  └── /var/www/happyfarmer/ – Dashboard, admin, API-filer
```

### Repo
```
GitHub: https://github.com/lemkil76/HappyFarmer
RASP:   /home/pi/happyfarmer
lacasa: /home/pi/happyfarmer
Mac:    ~/Documents/Coding/HappyFarmer
```

### Repo-struktur
```
HappyFarmer/
├── config/
│   ├── paths.py              # BASE_DIR = enda ändringspunkten
│   └── secrets.example.py
├── core/
│   ├── main.py               # Huvudloop
│   ├── api.py                # Flask REST API
│   ├── sensors.py            # DHT22, DS18B20, pH, MCP3008, reläer
│   └── test_sensors.py       # Terminalbaserat testprogram
├── integrations/
│   ├── db.py                 # MariaDB-integration (lacasa)
│   ├── cloud_sync.py         # SCP-synk till lacasa
│   └── social_media.py       # X/Twitter
├── dashboard/
│   ├── dashboard.html
│   ├── admin.html
│   ├── api/
│   │   ├── data.php
│   │   ├── settings.php
│   │   └── log_event.php
│   └── sample_data.json
├── docs/
│   ├── SETUP.md
│   └── happyfarmer_schema.sql
├── deploy.sh                 # Deployer dashboard/ till lacasa via SCP + git pull
└── CLAUDE.md
```

### Viktiga kommandon
```bash
# Från Mac – deploya
cd ~/Documents/Coding/HappyFarmer && git pull && sh deploy.sh

# SSH
ssh pi@192.168.1.128   # RASP (Pi 4)
ssh pi@lacasa          # lacasa (Pi 5)

# På RASP
cd /home/pi/happyfarmer
git pull
python3 -m integrations.db          # testa DB-anslutning
python3 -m integrations.cloud_sync  # synka till lacasa
python3 -m core.test_sensors        # testa sensorer
python3 -m core.main                # starta huvudprogrammet

# På lacasa – MariaDB
sudo mysql happyfarmer
mysql -u happyfarmer -phappyfarmer happyfarmer   # från LAN

# Nginx
sudo nginx -t && sudo systemctl reload nginx
sudo tail -f /var/log/nginx/error.log
```

### Cron på RASP
```
*/15 * * * * cd /home/pi/happyfarmer && python3 -m integrations.cloud_sync
@reboot sleep 30 && cd /home/pi/happyfarmer && python3 -m core.main
```

### GPIO-pinnar (BCM)

| GPIO | Sensor/Aktuator |
|---|---|
| 4 | DHT22 (lufttemp + fuktighet) |
| 17 | DS18B20 (vattentemp, 1-Wire) |
| 22 | Pump-relä |
| 23 | Ljus-relä |
| 24 | Fläkt-relä |
| 25 | Värmare-relä |

---

## 5. lacasa (Pi 5) – Tjänster

| Tjänst | Version | Syfte |
|---|---|---|
| Nginx | 1.26 | Reverse proxy + statisk webbserver |
| MariaDB | 11.x | Databas för HappyFarmer (port 3306) |
| PHP-FPM | 8.4 | Live data API, inställningar |
| Certbot | – | Let's Encrypt TLS-certifikat |
| UFW | – | Brandvägg: 22/80/443 öppna, 5000 blockerad, 3306 LAN-only |

> Extern åtkomst: `https://lemkil76.duckdns.org` (Duck DNS + Let's Encrypt)

---

## 6. Nätverksarkitektur

| VLAN | Namn | Enheter |
|---|---|---|
| VLAN 10 | Management | MacBook Air, Raspberry Pi, NAS |
| VLAN 20 | IoT | Arduino, smarta enheter |
| VLAN 30 | Media | TV:ar, surfplatta |
| VLAN 40 | Gäst | Samsung S23, övriga |

---

## 7. AI-experiment
```python
import anthropic
client = anthropic.Anthropic(api_key="...")
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hej!"}]
)
```

| Leverantör | Styrka |
|---|---|
| Anthropic (Claude) | Lång kontext, instruktionsföljning |
| OpenAI (GPT) | Brett ekosystem, function calling |
| Google Gemini | Multimodal, gratis-tier |

> Lagra API-nycklar i `.env` med `python-dotenv`. Aldrig i Git.

---

## 8. Säkerhet & Backup

- SSH-nycklar istället för lösenord
- Separata VLAN begränsar skadeyta
- GitHub för all kod
- Time Machine → NAS (SMB)

---

## 9. Nästa steg

- [x] Koppla in sensorer och testa med `python3 -m core.test_sensors`
- [x] Aktivera I2C, SPI, 1-Wire via `sudo raspi-config`
- [x] Installera kamera och testa timelapse
- [x] Konfigurera Twitter/X API
- [x] Starta `python3 -m core.main` + cron för autostart
- [x] Migrera till lacasa (Pi 5) – Nginx, MariaDB, PHP, HTTPS
- [x] Duck DNS + Let's Encrypt – `https://lemkil76.duckdns.org`
- [x] Admin-panel med token-autentisering via Nginx

---

## 10. Framtida / Nice-to-have

- [ ] VLAN-segmentering i routern (kräver VLAN-kapabel router, t.ex. UniFi/pfSense)
- [ ] SMHI/YR.no väderdata på dashboard
- [ ] Timelapse-visning på dashboard
- [ ] DHT22 lufttemperatur-fix (GPIO 4, "Unable to set line 17 to input")
- [ ] Säkerhetskopia av timelapse-bilder från RASP till lacasa
- [ ] Garage Opener-projekt

---

*Uppdatera detta dokument allteftersom projektet växer.*
