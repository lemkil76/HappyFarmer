<?php
/**
 * HappyFarmer – Logga händelse till system_events
 * dashboard/api/log_event.php
 *
 * POST { "level": "warn|error|info", "source": "dashboard", "message": "..." }
 * → skriver en rad till system_events-tabellen
 *
 * Används av dashboarden för att logga t.ex. timeout mot Pi/MariaDB.
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Method not allowed']);
    exit;
}

define('DB_HOST',    '127.0.0.1');
define('DB_PORT',    '3306');
define('DB_NAME',    'happyfarmer');
define('DB_USER',    'happyfarmer');
define('DB_PASS',    '');   // ← Injiceras av deploy.sh
define('MYSQL_BIN',  '/usr/bin/mysql');

$body = json_decode(file_get_contents('php://input'), true);
if (!$body) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Invalid JSON']);
    exit;
}

// Sanera indata
$allowed_levels = ['info', 'warn', 'error', 'debug'];
$level   = in_array($body['level']  ?? '', $allowed_levels) ? $body['level'] : 'info';
$source  = preg_replace('/[^a-z0-9_]/', '', strtolower($body['source']  ?? 'dashboard'));
$message = substr(trim($body['message'] ?? ''), 0, 500);

if ($message === '') {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'message required']);
    exit;
}

$sql = sprintf(
    "INSERT INTO system_events (level, source, message) VALUES ('%s', '%s', '%s');",
    addslashes($level),
    addslashes($source),
    addslashes($message)
);

$cmd = sprintf(
    'timeout 5 %s --connect-timeout=3 -h %s -P %s -u %s -p%s %s -e %s 2>&1',
    MYSQL_BIN, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME,
    escapeshellarg($sql)
);

$result = shell_exec($cmd);
$ok     = ($result === null || trim($result) === '');

echo json_encode(['ok' => $ok]);
