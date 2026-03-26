-- ============================================================
-- HappyFarmer – System Events 2026-03-26
-- Loggar dagens arbete i kronologisk ordning
--
-- Kör på NAS:
--   /usr/local/mariadb10/bin/mysql -u root -p happyfarmer < docs/system_events_2026-03-26.sql
-- ============================================================

USE happyfarmer;

INSERT INTO system_events (occurred_at, level, source, message) VALUES
('2026-03-26 09:00:00', 'info', 'main',         'Twitter/X API-uppkoppling påbörjad – tweepy och python-dotenv installerade på Pi'),
('2026-03-26 09:15:00', 'info', 'social_media',  'Twitter Developer App skapad och kopplad till Free-projekt i Developer Portal'),
('2026-03-26 09:30:00', 'info', 'social_media',  'OAuth 1.0 nycklar konfigurerade i .env: BEARER_TOKEN, API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET'),
('2026-03-26 09:45:00', 'info', 'social_media',  'Twitter API verifierad och funktionell – integrations/social_media.py körs utan fel'),
('2026-03-26 10:00:00', 'info', 'api',           'core/api.py skapad – Flask REST API som daemon-tråd med token-autentisering'),
('2026-03-26 10:15:00', 'info', 'api',           'API-endpoints: /api/login, /api/status, /api/relay/<name>, /api/auto, /api/camera, /api/schedule'),
('2026-03-26 10:30:00', 'info', 'dashboard',     'dashboard/admin.html skapad – lösenordsskyddad adminpanel med mörkt tema och Font Awesome-ikoner'),
('2026-03-26 10:45:00', 'info', 'dashboard',     'Admin: reläkontroll för pump, odlingslampa, fläkt och värmare med PÅ/AV/AUTO-knappar'),
('2026-03-26 11:00:00', 'info', 'dashboard',     'Admin: bekräftelsemodal vid manuell override – automatiskt schema pausas och kvitteras av användaren'),
('2026-03-26 11:15:00', 'info', 'dashboard',     'Admin: kameratrigger, schema-editorer för pump/luftning/belysning och återgång till automatik'),
('2026-03-26 11:30:00', 'info', 'main',          'core/main.py uppdaterad – startar Flask API-tråd vid uppstart, injicerar kamera-callback'),
('2026-03-26 11:45:00', 'info', 'main',          'core/main.py: kontrollerar manuella overrides innan pump-, ljus- och klimatstyrning'),
('2026-03-26 12:00:00', 'info', 'main',          'core/main.py: läser schema dynamiskt från delad API-state utan omstart av huvudloop'),
('2026-03-26 12:15:00', 'info', 'api',           'Flask admin-API live på http://rasp:5000/admin – testat och verifierat i webbläsare'),
('2026-03-26 12:30:00', 'info', 'dashboard',     'dashboard_wireframe.html omdesignad – mörkt tema (#0d1117) matchar adminpanelens formspråk'),
('2026-03-26 12:45:00', 'info', 'dashboard',     'Dashboard: Font Awesome-ikoner, omdesignade pills, sparklines och dagssammanfattning uppdaterade'),
('2026-03-26 13:00:00', 'info', 'dashboard',     'Dashboard: Admin-länkknapp tillagd i headern – länk till http://rasp:5000/admin'),
('2026-03-26 13:15:00', 'info', 'db',            'Ny tabell system_updates skapad i MariaDB – loggar apt-uppdateringar på Pi:n'),
('2026-03-26 13:30:00', 'info', 'db',            'integrations/db.py: log_system_update(), get_last_system_update(), get_system_updates() tillagda'),
('2026-03-26 13:45:00', 'info', 'main',          'integrations/system_updater.py skapad – kör apt update/upgrade och loggar resultat till MariaDB'),
('2026-03-26 14:00:00', 'info', 'api',           'API-endpoints tillagda: /api/sysupdate/status, /api/sysupdate/check, /api/sysupdate/run'),
('2026-03-26 14:15:00', 'info', 'dashboard',     'Admin: ny sektion Systemuppdatering – visar senaste uppdatering och möjlighet att köra apt upgrade');
