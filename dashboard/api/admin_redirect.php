<?php
/**
 * HappyFarmer – Admin-redirect
 * dashboard/api/admin_redirect.php
 *
 * Kontrollerar om Pi/Flask svarar innan omdirigering till adminsidan.
 * Om Pi är nere visas en snygg felsida istället för webbläsarens ERR-sida.
 *
 * Knappen i dashboard.html pekar hit: api/admin_redirect.php
 */

header('Cache-Control: no-store, no-cache, must-revalidate');
header('Pragma: no-cache');

define('DB_HOST',   '127.0.0.1');
define('DB_PORT',   '3307');
define('DB_NAME',   'happyfarmer');
define('DB_USER',   'happyfarmer');
define('DB_PASS',   '');   // ← Injiceras av deploy.sh
define('MYSQL_BIN', '/usr/local/mariadb10/bin/mysql');

// Använd Pi:ns IP direkt + curl via shell_exec
// --connect-timeout 2: max 2 sek att etablera TCP
// --max-time 3:       max 3 sek totalt inkl. HTTP-svar
$http_code = trim((string) shell_exec(
    'curl -s -o /dev/null -w "%{http_code}"'
    . ' --connect-timeout 2 --max-time 3'
    . ' http://192.168.1.128:5000/api/status 2>/dev/null'
));
$reachable = ($http_code === '200');

if ($reachable) {
    header('Location: http://rasp:5000/admin');
    exit;
}

// Pi är nere – logga till system_events (en gång per nedtid via INSERT IGNORE på unik nyckel)
$msg = addslashes('Adminsidan ej nåbar – Pi/Flask svarar inte (HTTP ' . ($http_code ?: '000') . ')');
$sql = "INSERT INTO system_events (level, source, message)"
     . " SELECT 'warn','admin_redirect','$msg'"
     . " FROM DUAL WHERE NOT EXISTS ("
     . "   SELECT 1 FROM system_events"
     . "   WHERE source='admin_redirect'"
     . "   AND occurred_at > NOW() - INTERVAL 30 MINUTE"
     . " ) LIMIT 1;";
$cmd = sprintf(
    'timeout 3 %s --connect-timeout=2 -h %s -P %s -u %s -p%s %s -e %s 2>/dev/null',
    MYSQL_BIN, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME,
    escapeshellarg($sql)
);
shell_exec($cmd);

// Pi är nere – visa felsida
?><!DOCTYPE html>
<html lang="sv">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HappyFarmer – Admin ej tillgänglig</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #0d1117; color: #e6edf3;
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
    }
    .card {
      background: #161b22; border: 1px solid #30363d;
      border-radius: 12px; padding: 40px 48px;
      text-align: center; max-width: 420px; width: 90%;
    }
    .icon { font-size: 48px; color: #f85149; margin-bottom: 20px; }
    h1 { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
    p  { font-size: 14px; color: #8b949e; line-height: 1.6; margin-bottom: 24px; }
    .btn {
      display: inline-flex; align-items: center; gap: 8px;
      background: #21262d; color: #e6edf3;
      border: 1px solid #30363d; border-radius: 8px;
      padding: 10px 20px; font-size: 14px; font-weight: 500;
      text-decoration: none; cursor: pointer;
      transition: background 0.15s;
    }
    .btn:hover { background: #30363d; }
    .time { font-size: 11px; color: #8b949e; margin-top: 20px; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon"><i class="fa-solid fa-circle-exclamation"></i></div>
    <h1>Adminsidan är inte tillgänglig</h1>
    <p>Raspberry Pi svarar inte just nu.<br>
       Systemet kan vara i omstart eller ha tappat nätverksanslutningen.</p>
    <a href="javascript:history.back()" class="btn">
      <i class="fa-solid fa-arrow-left"></i> Tillbaka till dashboard
    </a>
    <div class="time">Kontrollerades <?= date('H:i:s') ?></div>
  </div>
</body>
</html>
