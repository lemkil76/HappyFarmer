<?php
/**
 * HappyFarmer – Live API
 * dashboard/api/data.php
 *
 * Använder MariaDB-klienten via shell_exec() istället för mysqli-extension,
 * eftersom mysqli.so inte är aktiverat i Synology Web Station (DS211+).
 *
 * INSTALLATION PÅ NAS:
 *   1. Kopiera dashboard/api/ till /volume1/web/happyfarmer/api/
 *   2. Sätt DB_PASS till rätt lösenord (redigeras DIREKT på NAS efter deploy)
 *   3. Testa: curl http://nas:8080/api/data.php
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-store, no-cache, must-revalidate');

// ── Databasinställningar ────────────────────────────────────────────────────
define('DB_HOST', '127.0.0.1');
define('DB_PORT', '3306');
define('DB_NAME', 'happyfarmer');
define('DB_USER', 'happyfarmer');
define('DB_PASS', '');   // ← Fyll i på NAS. Aldrig i git.
define('MYSQL_BIN', '/usr/bin/mysql');

// ── DB-konnektivitetstest ────────────────────────────────────────────────────
$db_test = shell_exec(sprintf(
    'timeout 3 %s --connect-timeout=2 --default-character-set=utf8mb4 -h %s -P %s -u %s -p%s %s -e "SELECT 1" 2>/dev/null',
    MYSQL_BIN, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME
));
if (empty(trim((string)$db_test))) {
    http_response_code(503);
    echo json_encode(['error' => 'MariaDB ej tillgänglig – dashboard visar cachad data']);
    exit;
}

// ── Kör en SQL-fråga och returnera array av assoc-arrays ────────────────────
function db_query($sql) {
    $pass = escapeshellarg(DB_PASS);
    $db   = escapeshellarg(DB_NAME);
    $sql_e = escapeshellarg($sql);
    $cmd  = sprintf(
        'timeout 5 %s --connect-timeout=3 --default-character-set=utf8mb4 -h %s -P %s -u %s -p%s %s --batch --skip-column-names -e %s 2>/dev/null',
        MYSQL_BIN, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME, $sql_e
    );
    $output = shell_exec($cmd);
    if ($output === null || trim($output) === '') return [];

    // Hämta kolumnnamn med en SHOW-fråga
    $col_cmd = sprintf(
        'timeout 5 %s --connect-timeout=3 --default-character-set=utf8mb4 -h %s -P %s -u %s -p%s %s --batch -e %s 2>/dev/null',
        MYSQL_BIN, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME,
        escapeshellarg($sql . ' LIMIT 0')
    );
    $header_output = shell_exec($col_cmd);
    if (!$header_output) return [];

    $header_lines = explode("\n", trim($header_output));
    $columns = explode("\t", $header_lines[0]);

    $rows = [];
    foreach (explode("\n", trim($output)) as $line) {
        if ($line === '') continue;
        $vals = explode("\t", $line);
        $row  = [];
        foreach ($columns as $i => $col) {
            $v = isset($vals[$i]) ? $vals[$i] : null;
            $row[$col] = ($v === 'NULL') ? null : $v;
        }
        $rows[] = $row;
    }
    return $rows;
}

// ── Enklare funktion för frågor med känd kolumnlista ───────────────────────
function db_query_cols($sql, $columns) {
    $cmd = sprintf(
        'timeout 5 %s --connect-timeout=3 -h %s -P %s -u %s -p%s %s --batch --skip-column-names -e %s 2>/dev/null',
        MYSQL_BIN, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME,
        escapeshellarg($sql)
    );
    $output = shell_exec($cmd);
    if ($output === null || trim($output) === '') return [];

    $rows = [];
    foreach (explode("\n", trim($output)) as $line) {
        if ($line === '') continue;
        $vals = explode("\t", $line);
        $row  = [];
        foreach ($columns as $i => $col) {
            $v = isset($vals[$i]) ? $vals[$i] : null;
            $row[$col] = ($v === 'NULL') ? null : $v;
        }
        $rows[] = $row;
    }
    return $rows;
}

$now   = new DateTime();
$today = $now->format('Y-m-d');

// ── Senaste avläsning ────────────────────────────────────────────────────────
$latest_rows = db_query_cols(
    'SELECT recorded_at, air_temp_c, humidity_pct, water_temp_c, ph, lux, lux_description, loop_count FROM senaste_avlasning LIMIT 1',
    ['recorded_at','air_temp_c','humidity_pct','water_temp_c','ph','lux','lux_description','loop_count']
);
$latest = $latest_rows ? $latest_rows[0] : [];

// ── Aktuatortillstånd – relay_states.json (SCP:ad från Pi) med DB-fallback ───
$actuator_states = ['pump'=>'unknown','grow_lights'=>'unknown','fan'=>'unknown','heater'=>'unknown'];
$relay_states_file = __DIR__ . '/relay_states.json';
if (file_exists($relay_states_file)) {
    $rs = @json_decode(file_get_contents($relay_states_file), true);
    if ($rs) {
        foreach (['pump','grow_lights','fan','heater'] as $k) {
            if (isset($rs[$k])) $actuator_states[$k] = $rs[$k];
        }
    }
} else {
    // Fallback: hämta senaste kända tillstånd från actuator_events i DB
    foreach (['pump','grow_lights','fan','heater'] as $device) {
        $rows = db_query_cols(
            sprintf("SELECT state FROM actuator_events WHERE device='%s' ORDER BY created_at DESC LIMIT 1", $device),
            ['state']
        );
        if ($rows) $actuator_states[$device] = $rows[0]['state'];
    }
}

// ── Dagssammanfattning ───────────────────────────────────────────────────────
$sum_rows = db_query_cols(
    "SELECT antal_avlasningar, lufttemp_medel, lufttemp_min, lufttemp_max,
            fuktighet_medel, vattentemp_medel, ph_medel, lux_medel
     FROM dagssammanfattning WHERE datum = '$today' LIMIT 1",
    ['antal_avlasningar','lufttemp_medel','lufttemp_min','lufttemp_max',
     'fuktighet_medel','vattentemp_medel','ph_medel','lux_medel']
);
$summary = $sum_rows ? $sum_rows[0] : [];

// ── Sensorhistorik (medel per 2h, senaste 24h) ───────────────────────────────
// bucket 0 = äldst (24–22h sedan), bucket 11 = senast (2–0h sedan)
$hist_rows = db_query_cols(
    'SELECT FLOOR(TIMESTAMPDIFF(MINUTE, DATE_SUB(NOW(), INTERVAL 24 HOUR), recorded_at) / 120) AS bucket,
            ROUND(AVG(air_temp_c),1) AS air_temp_c,
            ROUND(AVG(humidity_pct),1) AS humidity_pct,
            ROUND(AVG(water_temp_c),1) AS water_temp_c,
            ROUND(AVG(ph),2) AS ph,
            ROUND(AVG(lux),0) AS lux
     FROM sensor_readings
     WHERE recorded_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
       AND recorded_at < NOW()
     GROUP BY bucket
     HAVING bucket >= 0 AND bucket <= 11
     ORDER BY bucket ASC
     LIMIT 12',
    ['bucket','air_temp_c','humidity_pct','water_temp_c','ph','lux']
);

// ── Senaste sociala inlägg ───────────────────────────────────────────────────
$post_rows = db_query_cols(
    'SELECT post_id, posted_at, message, likes, retweets, type FROM social_posts ORDER BY posted_at DESC LIMIT 2',
    ['post_id','posted_at','message','likes','retweets','type']
);

// ── Systeminfo från sample_data.json (uptime/loop_count/sim_mode) ────────────
$sys = [
    'loop_count'      => !empty($latest['loop_count']) ? (int)$latest['loop_count'] : 0,
    'uptime_hours'    => 0.0,
    'simulation_mode' => false,
];
$sample_file = __DIR__ . '/../dashboard/sample_data.json';
if (file_exists($sample_file)) {
    $jdata = @json_decode(file_get_contents($sample_file), true);
    if ($jdata && isset($jdata['system'])) {
        $s = $jdata['system'];
        if ($sys['loop_count'] === 0 && !empty($s['loop_count'])) {
            $sys['loop_count'] = (int)$s['loop_count'];
        }
        $sys['uptime_hours']    = (float)($s['uptime_hours']    ?? 0.0);
        $sys['simulation_mode'] = (bool) ($s['simulation_mode'] ?? false);
    }
}

// ── Hjälpfunktioner ──────────────────────────────────────────────────────────
function fval($v) { return ($v !== null && $v !== '') ? (float)$v : null; }
function ival($v) { return ($v !== null && $v !== '') ? (int)$v   : null; }
function col_f($rows, $key) {
    return array_map(function($r) use ($key) {
        return ($r[$key] !== null) ? (float)$r[$key] : null;
    }, $rows);
}
function col_i($rows, $key) {
    return array_map(function($r) use ($key) {
        return ($r[$key] !== null) ? (int)$r[$key] : null;
    }, $rows);
}

// ── Bygg svaret ──────────────────────────────────────────────────────────────
$data = [
    '_comment'        => 'Live data fran MariaDB · api/data.php · ' . $now->format('c'),
    '_format_version' => '1.0',
    '_generated'      => $now->format('c'),

    'latest_image' => [
        'filename'    => 'latest_image.jpg',
        'captured_at' => $now->format('c'),
        'resolution'  => '1920x1080',
    ],

    'current_readings' => [
        'timestamp'           => $latest['recorded_at'] ?? $now->format('c'),
        'air_temperature_c'   => fval($latest['air_temp_c']   ?? null),
        'humidity_pct'        => fval($latest['humidity_pct'] ?? null),
        'water_temperature_c' => fval($latest['water_temp_c'] ?? null),
        'ph'                  => fval($latest['ph']            ?? null),
        'lux'                 => ival($latest['lux']           ?? null),
        'lux_description'     => $latest['lux_description']   ?? 'okand',
    ],

    'actuator_states' => $actuator_states,

    'system' => [
        'loop_count'        => $sys['loop_count'],
        'sleep_minutes'     => 5,
        'drive_sync_status' => 'live',
        'drive_sync_last'   => $now->format('c'),
        'uptime_hours'      => $sys['uptime_hours'],
        'simulation_mode'   => $sys['simulation_mode'],
    ],

    'pump_schedule' => [
        'on_seconds'            => 1800,
        'off_seconds'           => 900,
        'next_cycle_in_minutes' => 0,
        'cycles_today'          => (int)($summary['antal_avlasningar'] ?? 0),
    ],

    'light_schedule' => [
        'on_hour'    => 6,
        'off_hour'   => 23,
        'light_hours'=> 5,
        'today'      => [
            ['start'=>'06:00','end'=>'11:00','status'=>'done',  'label'=>'Morgon'],
            ['start'=>'11:30','end'=>'12:00','status'=>'active','label'=>'Middag'],
            ['start'=>'12:15','end'=>'12:45','status'=>'next',  'label'=>'Eftermiddag'],
            ['start'=>'18:00','end'=>'23:00','status'=>'next',  'label'=>'Kvaell'],
        ],
    ],

    'social_media' => [
        'enabled'            => false,
        'platform'           => 'X / Twitter',
        'handle'             => '@lemkil76',
        'recent_posts'       => array_map(function($p) {
            return [
                'id'        => (string)($p['post_id']   ?? ''),
                'posted_at' => (string)($p['posted_at'] ?? ''),
                'text'      => (string)($p['message']   ?? ''),
                'likes'     => (int)   ($p['likes']     ?? 0),
                'retweets'  => (int)   ($p['retweets']  ?? 0),
                'type'      => (string)($p['type']      ?? 'sensor_update'),
            ];
        }, $post_rows),
        'next_post_in_loops' => 0,
    ],

    'sensor_history' => [
        'description'        => 'Medelvarde per 2h senaste 24h – bucket 0=aldst, 11=senast',
        'interval_minutes'   => 120,
        'buckets'            => col_i($hist_rows, 'bucket'),
        'air_temperature_c'  => col_f($hist_rows, 'air_temp_c'),
        'humidity_pct'       => col_f($hist_rows, 'humidity_pct'),
        'water_temperature_c'=> col_f($hist_rows, 'water_temp_c'),
        'ph'                 => col_f($hist_rows, 'ph'),
        'lux'                => col_i($hist_rows, 'lux'),
    ],

    'thresholds' => [
        'temp_min_c'       => 18.0,
        'temp_max_c'       => 28.0,
        'ph_min'           => 5.5,
        'ph_max'           => 7.5,
        'humidity_min_pct' => 50.0,
        'humidity_max_pct' => 80.0,
        'lux_max'          => 12000,
    ],

    'daily_summary' => [
        'date'                   => $today,
        'air_temp_avg_c'         => fval($summary['lufttemp_medel']   ?? null),
        'air_temp_min_c'         => fval($summary['lufttemp_min']     ?? null),
        'air_temp_max_c'         => fval($summary['lufttemp_max']     ?? null),
        'water_temp_avg_c'       => fval($summary['vattentemp_medel'] ?? null),
        'humidity_avg_pct'       => fval($summary['fuktighet_medel']  ?? null),
        'ph_avg'                 => fval($summary['ph_medel']         ?? null),
        'lux_avg'                => ival($summary['lux_medel']        ?? null),
        'pump_cycles'            => (int)($summary['antal_avlasningar'] ?? 0),
        'images_captured_lowres' => 0,
        'images_captured_hires'  => 0,
        'social_posts'           => count($post_rows),
    ],
];

echo json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
