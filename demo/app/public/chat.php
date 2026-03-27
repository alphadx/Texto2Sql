<?php
header('Content-Type: application/json; charset=utf-8');

$cacheDir = '/var/cache/texto2sql-demo';
if (!is_dir($cacheDir)) {
    mkdir($cacheDir, 0777, true);
}

$ttlMinutes = (int)($_ENV['CHAT_CACHE_TTL_MINUTES'] ?? getenv('CHAT_CACHE_TTL_MINUTES') ?: 360);
if ($ttlMinutes <= 0) {
    $ttlMinutes = 360;
}
$ttlSeconds = $ttlMinutes * 60;

function cache_file(string $cacheDir, string $sessionId): string {
    return $cacheDir . '/session_' . preg_replace('/[^a-zA-Z0-9_-]/', '_', $sessionId) . '.json';
}

function load_session(string $cacheDir, string $sessionId): array {
    global $ttlSeconds;
    $file = cache_file($cacheDir, $sessionId);
    if (!file_exists($file)) {
        return ['expires_at' => time() + $ttlSeconds, 'history' => [], 'last_result' => null];
    }

    $raw = file_get_contents($file);
    $data = json_decode($raw, true);
    if (!is_array($data) || (int)($data['expires_at'] ?? 0) < time()) {
        @unlink($file);
        return ['expires_at' => time() + $ttlSeconds, 'history' => [], 'last_result' => null];
    }
    return $data;
}

function save_session(string $cacheDir, string $sessionId, array $payload): void {
    file_put_contents(cache_file($cacheDir, $sessionId), json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

function call_api(string $message): array {
    $apiUrl = $_ENV['NL2SQL_API_URL'] ?? getenv('NL2SQL_API_URL') ?: 'http://host.docker.internal:5000/nl2sql/query';
    $apiToken = $_ENV['NL2SQL_API_KEY'] ?? getenv('NL2SQL_API_KEY') ?: '';
    $apiProvider = $_ENV['NL2SQL_API_PROVIDER'] ?? getenv('NL2SQL_API_PROVIDER') ?: 'openai';
    $apiModel = $_ENV['NL2SQL_MODEL'] ?? getenv('NL2SQL_MODEL') ?: 'gpt-4.1-mini';

    $payload = [
        'host' => $_ENV['MYSQL_HOST'] ?? getenv('MYSQL_HOST') ?: '127.0.0.1',
        'usuario' => $_ENV['MYSQL_DEMO_USER'] ?? getenv('MYSQL_DEMO_USER') ?: 'demo',
        'contraseña' => $_ENV['MYSQL_DEMO_PASSWORD'] ?? getenv('MYSQL_DEMO_PASSWORD') ?: 'demo1234',
        'puerto' => (int)($_ENV['MYSQL_PORT'] ?? getenv('MYSQL_PORT') ?: 3306),
        'nombre_bd' => $_ENV['MYSQL_DEMO_DB'] ?? getenv('MYSQL_DEMO_DB') ?: 'sakila',
        'motor_bd' => 'mysql',
        'consulta_nl' => $message,
        'session_id' => 'demo-' . md5($message . microtime(true)),
        'llm_provider' => $apiProvider,
        'llm_model' => $apiModel,
    ];

    $ch = curl_init($apiUrl);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_HTTPHEADER => array_filter([
            'Content-Type: application/json',
            $apiToken !== '' ? 'Authorization: Bearer ' . $apiToken : null,
        ]),
        CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE),
        CURLOPT_TIMEOUT => 60,
    ]);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);

    if ($error) {
        return ['error' => 'Error al conectar API: ' . $error, 'columnas' => [], 'filas' => []];
    }

    $json = json_decode((string)$response, true);
    if (!is_array($json)) {
        return ['error' => 'Respuesta API inválida (' . $httpCode . ')', 'columnas' => [], 'filas' => []];
    }

    return [
        'columnas' => array_map(fn($c) => is_array($c) ? ($c['nombre'] ?? json_encode($c)) : (string)$c, $json['columnas'] ?? []),
        'filas' => $json['filas'] ?? [],
        'error' => $json['errores'] ?? null,
        'sql_generado' => $json['sql_generado'] ?? null,
    ];
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$sessionId = $_GET['session_id'] ?? null;

if ($method === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);
    $sessionId = $input['session_id'] ?? $sessionId ?? 'default';
    $message = trim((string)($input['message'] ?? ''));

    if ($message === '') {
        http_response_code(422);
        echo json_encode(['error' => 'Mensaje requerido']);
        exit;
    }

    $state = load_session($cacheDir, $sessionId);
    $state['history'][] = ['role' => 'user', 'text' => $message, 'ts' => time()];

    $result = call_api($message);
    $botText = isset($result['error']) && $result['error'] ? $result['error'] : ('SQL: ' . ($result['sql_generado'] ?? 'N/A'));
    $state['history'][] = ['role' => 'assistant', 'text' => $botText, 'ts' => time()];
    $state['last_result'] = $result;
    $state['expires_at'] = time() + $ttlSeconds;

    save_session($cacheDir, $sessionId, $state);
    echo json_encode(['ok' => true, 'history' => $state['history'], 'last_result' => $state['last_result']]);
    exit;
}

$sessionId = $sessionId ?: 'default';
$state = load_session($cacheDir, $sessionId);
echo json_encode(['history' => $state['history'], 'last_result' => $state['last_result']]);
