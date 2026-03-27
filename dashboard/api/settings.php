<?php
/**
 * HappyFarmer – Inställnings-API
 * dashboard/api/settings.php
 *
 * GET  → {"theme":"dark"|"light"}
 * POST {"theme":"dark"|"light"} → {"ok":true,"theme":"..."}
 *
 * Används av dashboard.html och admin.html för att läsa/spara tema
 * i MariaDB så att inställningen är gemensam för båda sidor.
 *
 * DB-tabell krävs (kör en gång på NAS):
 *   CREATE TABLE IF NOT EXISTS settings (
 *     key_name   VARCHAR(50)  NOT NULL,
 *     value      VARCHAR(255) NOT NULL,
 *     updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
 *                             ON UPDATE CURRENT_TIMESTAMP,
 *     PRIMARY KEY (key_name)
 *   ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
 *   INSERT INTO settings (key_name, value) VALUES ('theme','dark')
 *     ON DUPLICATE KEY UPDATE key_name=key_name;
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Cache-Control: no-store');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

define('MYSQL_BIN', '/usr/local/mariadb10/bin/mysql');
define('DB_HOST',   '127.0.0.1');
define('DB_PORT',   '3307');
define('DB_NAME',   'happyfarmer');
define('DB_USER',   'happyfarmer');
define('DB_PASS',   '');   // ← Fyll i på NAS efter deploy

function db_run($sql) {
    $cmd = sprintf(
        '%s -h %s -P %s -u %s -p%s %s --batch --skip-column-names -e %s 2>/dev/null',
        MYSQL_BIN, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME,
        escapeshellarg($sql)
    );
    return trim(shell_exec($cmd) ?? '');
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $body  = json_decode(file_get_contents('php://input'), true) ?? [];
    $theme = $body['theme'] ?? '';
    if (!in_array($theme, ['dark', 'light'], true)) {
        http_response_code(400);
        echo json_encode(['error' => 'Ogiltigt tema – ange dark eller light']);
        exit;
    }
    db_run("INSERT INTO settings (key_name, value)
            VALUES ('theme', '$theme')
            ON DUPLICATE KEY UPDATE value='$theme', updated_at=NOW()");
    echo json_encode(['ok' => true, 'theme' => $theme]);
} else {
    $val   = db_run("SELECT value FROM settings WHERE key_name='theme' LIMIT 1");
    $theme = in_array($val, ['dark', 'light'], true) ? $val : 'dark';
    echo json_encode(['theme' => $theme]);
}
