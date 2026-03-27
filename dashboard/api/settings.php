<?php
/**
 * HappyFarmer – Inställnings-API
 * dashboard/api/settings.php
 *
 * GET  (no params)          → {"theme":"dark"|"light"}          ← bakåtkompatibelt
 * GET  ?key=<key>           → {"value":"..."}
 * POST {"theme":"..."}      → {"ok":true,"theme":"..."}         ← bakåtkompatibelt
 * POST {"key":"...","value":"..."} → {"ok":true,"key":"..."}
 *
 * Används av dashboard.html och admin.html.
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
define('DB_PASS',   '');   // ← Injiceras av deploy.sh

function db_run($sql) {
    $cmd = sprintf(
        '%s -h %s -P %s -u %s -p%s %s --batch --skip-column-names -e %s 2>/dev/null',
        MYSQL_BIN, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME,
        escapeshellarg($sql)
    );
    return trim(shell_exec($cmd) ?? '');
}

function db_set($key, $value) {
    $k = addslashes($key);
    $v = addslashes($value);
    db_run("INSERT INTO settings (key_name, value)
            VALUES ('$k', '$v')
            ON DUPLICATE KEY UPDATE value='$v', updated_at=NOW()");
}

function db_get($key) {
    $k = addslashes($key);
    return db_run("SELECT value FROM settings WHERE key_name='$k' LIMIT 1");
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $body = json_decode(file_get_contents('php://input'), true) ?? [];

    // Generisk key/value (nytt format)
    if (isset($body['key'])) {
        $key   = trim($body['key']   ?? '');
        $value = trim($body['value'] ?? '');
        if (!$key) {
            http_response_code(400);
            echo json_encode(['error' => 'key saknas']);
            exit;
        }
        db_set($key, $value);
        echo json_encode(['ok' => true, 'key' => $key]);
        exit;
    }

    // Bakåtkompatibelt: {"theme":"dark"}
    $theme = $body['theme'] ?? '';
    if (!in_array($theme, ['dark', 'light'], true)) {
        http_response_code(400);
        echo json_encode(['error' => 'Ogiltigt tema – ange dark eller light']);
        exit;
    }
    db_set('theme', $theme);
    echo json_encode(['ok' => true, 'theme' => $theme]);

} else {
    // GET
    $key = $_GET['key'] ?? '';
    if ($key) {
        $val = db_get($key);
        echo json_encode(['value' => $val === '' ? null : $val]);
    } else {
        // Bakåtkompatibelt: returnera tema
        $val   = db_get('theme');
        $theme = in_array($val, ['dark', 'light'], true) ? $val : 'dark';
        echo json_encode(['theme' => $theme]);
    }
}
