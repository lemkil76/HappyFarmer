# Hemma Techstack – Projektöversikt

> Uppdaterad: 2026-03-27 (rev 5)

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
| Raspberry Pi 4 | Model B | HappyFarmer hub (192.168.1.128) |
| Synology NAS | DS211+ | Filserver + webbserver (192.168.1.100) |
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

HappyFarmer är ett automatiserat vertical farming-system på Raspberry Pi 4.

### Nätverksinfo

| Enhet | IP | Åtkomst |
|---|---|---|
| Raspberry Pi 4 | 192.168.1.128 | `ssh pi@192.168.1.128` |
| Synology NAS | 192.168.1.100 | `ssh admin@nas` / `http://nas:5000` |
| Dashboard | – | `http://nas:8080/dashboard/dashboard_wireframe.html` |
| Raspberry Pi 4 | 192.168.1.128 | Fast IP (konfigurerad via nmcli) |


### Repo
```
GitHub: https://github.com/lemkil76/HappyFarmer
Pi:     /home/pi/happyfarmer
Mac:    ~/Documents/Coding/HappyFarmer
```

### Repo-struktur
```
HappyFarmer/
├── config/
│   ├── paths.py              # BASE_DIR + NAS_MOUNT = enda ändringspunkterna
│   └── secrets.example.py
├── core/
│   ├── main.py               # Huvudloop
│   ├── sensors.py            # DHT22, DS18B20, pH, MCP3008, reläer
│   └── test_sensors.py       # Terminalbaserat testprogram
├── integrations/
│   ├── db.py                 # MariaDB-integration
│   ├── cloud_sync.py         # NAS-synk + skriver sample_data.json
│   └── social_media.py       # X/Twitter (SOCIAL_ENABLED=False)
├── dashboard/
│   ├── dashboard_wireframe.html
│   ├── sample_data.json
│   └── latest_image.jpg
├── docs/
│   ├── SETUP.md
│   └── happyfarmer_schema.sql
├── deploy.sh                 # scp -O -r dashboard/ till NAS
└── CLAUDE.md
```

### Viktiga kommandon
```bash
# Från Mac
cd ~/Documents/Coding/HappyFarmer && git pull && sh deploy.sh

# SSH till Pi
ssh pi@192.168.1.128

# På Pi
cd /home/pi/happyfarmer
git pull
python3 -m integrations.db          # testa DB-anslutning
python3 -m integrations.cloud_sync  # synka till NAS
python3 -m core.test_sensors        # testa sensorer
python3 -m core.main                # starta huvudprogrammet

# SSH till NAS
ssh admin@nas
/usr/local/mariadb10/bin/mysql -u root -p   # port 3307
```

### NAS-konfiguration

| Tjänst | Detalj |
|---|---|
| MariaDB | Port 3307, TCP aktiverat, användare `happyfarmer@%` |
| SMB | Vers 1.0 (DS211+ stöder bara SMB1) |
| NAS-mount på Pi | `//192.168.1.100/web` → `/mnt/nas/web` via `/etc/fstab` |
| Web root på NAS | `/volume1/web/happyfarmer/` |
| Dashboard URL | `http://nas:8080/dashboard/` |
| Deploy | `scp -O -r dashboard/ lemkil76@nas:/volume1/web/happyfarmer/dashboard/` |

### Cron på Pi
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

## 5. Synology DS211+ – Tjänster

| Tjänst | Version | Syfte |
|---|---|---|
| MariaDB 10 | 10.3.29 | Databas för HappyFarmer (port 3307) |
| Apache HTTP | 2.4 + PHP 7.0 | HappyFarmer webbapp (port 8080) |
| Synology Mail Server | 1.7.1 | E-postserver |
| SMB | vers 1.0 | Fildelning (Pi + Mac) |

> DS211+ kör kernel 2.6.32, ARM 32-bit, 256 MB RAM.
> Extern åtkomst: `http://lemkil76.synology.me:8080` (router → NAS port 8080, Synology DDNS)

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
- Synology Hyper Backup för NAS-data
- GitHub för all kod
- Time Machine → NAS (SMB)

---

## 9. Nästa steg

- [x] Koppla in sensorer och testa med `python3 -m core.test_sensors`
- [x] Aktivera I2C, SPI, 1-Wire via `sudo raspi-config`
- [x] Installera kamera och testa timelapse
- [x] Konfigurera Twitter/X API (`SOCIAL_ENABLED=True`)
- [x] Starta `python3 -m core.main` + cron för autostart
- [x] Port forwarding för extern åtkomst – `http://lemkil76.synology.me:8080`

---

## 10. Framtida / Nice-to-have

- [ ] VLAN-segmentering i routern (kräver VLAN-kapabel router, t.ex. UniFi/pfSense)
- [ ] SMHI/YR.no väderdata på dashboard
- [ ] Timelapse-visning på dashboard
- [ ] Ny Pi inomhus med Gunicorn + Nginx som ersätter NAS som webbserver
- [ ] Extern åtkomst till admin-panel (Pi port 5000, idag bara lokalt)

---

*Uppdatera detta dokument allteftersom projektet växer.*