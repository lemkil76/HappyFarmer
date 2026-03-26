-- ============================================================
-- HappyFarmer - MariaDB Schema
-- docs/happyfarmer_schema.sql
-- Revised by Claude - 2026-03-24
--
-- Installera:
--   /usr/local/mariadb10/bin/mysql -u root -p < happyfarmer_schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS happyfarmer
  CHARACTER SET utf8 COLLATE utf8_general_ci;

USE happyfarmer;

-- ============================================================
-- sensor_readings
-- En rad per loop-cykel (var 5:e minut som standard)
-- ============================================================
CREATE TABLE IF NOT EXISTS sensor_readings (
    id               INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    recorded_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    air_temp_c       DECIMAL(5,2)  DEFAULT NULL,
    humidity_pct     DECIMAL(5,2)  DEFAULT NULL,
    water_temp_c     DECIMAL(5,2)  DEFAULT NULL,
    ph               DECIMAL(4,2)  DEFAULT NULL,
    lux              INT UNSIGNED  DEFAULT NULL,
    lux_description  VARCHAR(20)   DEFAULT NULL,
    loop_count       INT UNSIGNED  DEFAULT NULL,
    PRIMARY KEY (id),
    INDEX idx_recorded_at (recorded_at)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ============================================================
-- actuator_events
-- Loggar varje gang pump/ljus/flakt/varmare slas pa/av
-- ============================================================
CREATE TABLE IF NOT EXISTS actuator_events (
    id           INT UNSIGNED       NOT NULL AUTO_INCREMENT,
    occurred_at  DATETIME           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actuator     VARCHAR(20)        NOT NULL,
    state        ENUM('on','off')   NOT NULL,
    trigger_src  VARCHAR(30)        DEFAULT NULL,
    duration_sec INT UNSIGNED       DEFAULT NULL,
    PRIMARY KEY (id),
    INDEX idx_occurred_at (occurred_at),
    INDEX idx_actuator (actuator)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ============================================================
-- timelapse_images
-- Metadata per bild (filen lagras pa NAS)
-- ============================================================
CREATE TABLE IF NOT EXISTS timelapse_images (
    id          INT UNSIGNED              NOT NULL AUTO_INCREMENT,
    captured_at DATETIME                  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    filename    VARCHAR(100)              NOT NULL,
    resolution  VARCHAR(20)               DEFAULT '640x480',
    type        ENUM('lowres','hires')    NOT NULL DEFAULT 'lowres',
    nas_path    VARCHAR(255)              DEFAULT NULL,
    synced      TINYINT(1)               NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    INDEX idx_captured_at (captured_at)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ============================================================
-- timelapse_videos
-- Metadata for byggda MP4-filer
-- ============================================================
CREATE TABLE IF NOT EXISTS timelapse_videos (
    id          INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    built_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    filename    VARCHAR(100)  NOT NULL,
    nas_path    VARCHAR(255)  DEFAULT NULL,
    period_from DATE          DEFAULT NULL,
    period_to   DATE          DEFAULT NULL,
    frame_count INT UNSIGNED  DEFAULT NULL,
    PRIMARY KEY (id),
    INDEX idx_built_at (built_at)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ============================================================
-- social_posts
-- Loggar varje inlagg pa X/Twitter
-- ============================================================
CREATE TABLE IF NOT EXISTS social_posts (
    id        INT UNSIGNED                              NOT NULL AUTO_INCREMENT,
    posted_at DATETIME                                  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    platform  VARCHAR(20)                               NOT NULL DEFAULT 'twitter',
    post_id   VARCHAR(30)                               DEFAULT NULL,
    type      ENUM('sensor_update','timelapse','manual') NOT NULL,
    message   TEXT                                      DEFAULT NULL,
    likes     INT UNSIGNED                              DEFAULT 0,
    retweets  INT UNSIGNED                              DEFAULT 0,
    PRIMARY KEY (id),
    INDEX idx_posted_at (posted_at)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ============================================================
-- system_events
-- Startar, stopp, fel och systeminfo
-- ============================================================
CREATE TABLE IF NOT EXISTS system_events (
    id          INT UNSIGNED                      NOT NULL AUTO_INCREMENT,
    occurred_at DATETIME                          NOT NULL DEFAULT CURRENT_TIMESTAMP,
    level       ENUM('info','warning','error')    NOT NULL DEFAULT 'info',
    source      VARCHAR(30)                       DEFAULT NULL,
    message     TEXT                              NOT NULL,
    PRIMARY KEY (id),
    INDEX idx_occurred_at (occurred_at),
    INDEX idx_level (level)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ============================================================
-- Vy: senaste_avlasning
-- ============================================================
CREATE OR REPLACE VIEW senaste_avlasning AS
  SELECT * FROM sensor_readings
  ORDER BY recorded_at DESC LIMIT 1;

-- ============================================================
-- Vy: dagssammanfattning
-- ============================================================
CREATE OR REPLACE VIEW dagssammanfattning AS
  SELECT
    DATE(recorded_at)          AS datum,
    COUNT(*)                   AS antal_avlasningar,
    ROUND(AVG(air_temp_c),1)   AS lufttemp_medel,
    ROUND(MIN(air_temp_c),1)   AS lufttemp_min,
    ROUND(MAX(air_temp_c),1)   AS lufttemp_max,
    ROUND(AVG(humidity_pct),1) AS fuktighet_medel,
    ROUND(AVG(water_temp_c),1) AS vattentemp_medel,
    ROUND(AVG(ph),2)           AS ph_medel,
    ROUND(AVG(lux),0)          AS lux_medel
  FROM sensor_readings
  GROUP BY DATE(recorded_at)
  ORDER BY datum DESC;

-- ============================================================
-- system_updates
-- Loggar apt-uppdateringar pa Pi:n
-- ============================================================
CREATE TABLE IF NOT EXISTS system_updates (
    id                INT UNSIGNED                              NOT NULL AUTO_INCREMENT,
    updated_at        DATETIME                                  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status            ENUM('success','failed','no_updates')     NOT NULL,
    packages_updated  INT UNSIGNED                              DEFAULT 0,
    packages_list     TEXT                                      DEFAULT NULL,
    os_version        VARCHAR(100)                              DEFAULT NULL,
    kernel_version    VARCHAR(50)                               DEFAULT NULL,
    python_version    VARCHAR(20)                               DEFAULT NULL,
    duration_sec      INT UNSIGNED                              DEFAULT NULL,
    notes             TEXT                                      DEFAULT NULL,
    PRIMARY KEY (id),
    INDEX idx_updated_at (updated_at)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ============================================================
-- Testdata
-- ============================================================
INSERT INTO sensor_readings
  (air_temp_c, humidity_pct, water_temp_c, ph, lux, lux_description, loop_count)
VALUES (22.5, 64.0, 20.1, 6.5, 8240, 'dag', 1);

INSERT INTO system_events (level, source, message)
VALUES ('info', 'main', 'HappyFarmer schema installerat och klart');

-- ============================================================
-- Verifiera
-- ============================================================
SHOW TABLES;
SELECT * FROM senaste_avlasning;
SELECT * FROM dagssammanfattning;
