<?php
header('Content-Type: application/json; charset=utf-8');

$cacheDir = '/var/cache/texto2sql-demo';
if (!is_dir($cacheDir)) {
    mkdir($cacheDir, 0777, true);
}

$defaultTtlMinutes = (int)($_ENV['CHAT_CACHE_TTL_MINUTES'] ?? getenv('CHAT_CACHE_TTL_MINUTES') ?: 360);
if ($defaultTtlMinutes <= 0) {
    $defaultTtlMinutes = 360;
}
$maxMessages = (int)($_ENV['CHAT_MAX_MESSAGES'] ?? getenv('CHAT_MAX_MESSAGES') ?: 40);
if ($maxMessages <= 0) {
    $maxMessages = 40;
}

function cache_file(string $cacheDir, string $sessionId): string {
    return $cacheDir . '/session_' . preg_replace('/[^a-zA-Z0-9_-]/', '_', $sessionId) . '.json';
}

function sanitize_ttl(int $ttlMinutes, int $defaultTtlMinutes): int {
    if ($ttlMinutes <= 0) {
        return $defaultTtlMinutes;
    }
    if ($ttlMinutes > 1440) {
        return 1440;
    }
    return $ttlMinutes;
}

function build_default_state(int $ttlMinutes): array {
    return [
        'expires_at' => time() + ($ttlMinutes * 60),
        'ttl_minutes' => $ttlMinutes,
        'history' => [],
        'context_signature' => null,
    ];
}

function load_session(string $cacheDir, string $sessionId, int $defaultTtlMinutes): array {
    $file = cache_file($cacheDir, $sessionId);
    if (!file_exists($file)) {
        return build_default_state($defaultTtlMinutes);
    }

    $raw = file_get_contents($file);
    $data = json_decode((string)$raw, true);
    if (!is_array($data) || (int)($data['expires_at'] ?? 0) < time()) {
        @unlink($file);
        return build_default_state($defaultTtlMinutes);
    }

    if (!isset($data['history']) || !is_array($data['history'])) {
        $data['history'] = [];
    }
    $data['ttl_minutes'] = sanitize_ttl((int)($data['ttl_minutes'] ?? $defaultTtlMinutes), $defaultTtlMinutes);
    $data['context_signature'] = $data['context_signature'] ?? null;
    return $data;
}

function save_session(string $cacheDir, string $sessionId, array $payload): void {
    file_put_contents(cache_file($cacheDir, $sessionId), json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

function extract_columns(array $json): array {
    $columns = $json['columnas'] ?? [];
    if (empty($columns) && isset($json['filas'][0]) && is_array($json['filas'][0])) {
        return array_map(static fn($idx) => 'col_' . $idx, array_keys($json['filas'][0]));
    }

    return array_map(static function ($col) {
        if (is_array($col)) {
            return (string)($col['nombre'] ?? json_encode($col));
        }
        return (string)$col;
    }, $columns);
}

function call_api(string $message, string $sessionId, array $params): array {
    $apiUrl = $params['api_url'] ?? ($_ENV['NL2SQL_API_URL'] ?? getenv('NL2SQL_API_URL') ?: 'http://host.docker.internal:5000/nl2sql/query');
    $apiToken = $params['api_bearer'] ?? ($_ENV['NL2SQL_API_KEY'] ?? getenv('NL2SQL_API_KEY') ?: '');

    $apiProvider = $params['llm_provider'] ?? ($_ENV['NL2SQL_API_PROVIDER'] ?? getenv('NL2SQL_API_PROVIDER') ?: null);
    $apiModel = $params['llm_model'] ?? ($_ENV['NL2SQL_MODEL'] ?? getenv('NL2SQL_MODEL') ?: null);
    $llmApiKey = $params['llm_api_key'] ?? ($_ENV['LLM_API_KEY'] ?? getenv('LLM_API_KEY') ?: null);
    $llmBaseUrl = $params['llm_base_url'] ?? ($_ENV['LLM_BASE_URL'] ?? getenv('LLM_BASE_URL') ?: null);

    $payload = [
        'host' => $params['db_host'] ?? ($_ENV['MYSQL_HOST'] ?? getenv('MYSQL_HOST') ?: '127.0.0.1'),
        'usuario' => $params['db_user'] ?? ($_ENV['MYSQL_DEMO_USER'] ?? getenv('MYSQL_DEMO_USER') ?: 'demo'),
        'contraseña' => $params['db_password'] ?? ($_ENV['MYSQL_DEMO_PASSWORD'] ?? getenv('MYSQL_DEMO_PASSWORD') ?: 'demo1234'),
        'puerto' => (int)($params['db_port'] ?? ($_ENV['MYSQL_PORT'] ?? getenv('MYSQL_PORT') ?: 3306)),
        'nombre_bd' => $params['db_name'] ?? ($_ENV['MYSQL_DEMO_DB'] ?? getenv('MYSQL_DEMO_DB') ?: 'sakila'),
        'motor_bd' => $params['db_engine'] ?? 'mysql',
        'consulta_nl' => $message,
        'session_id' => $sessionId,
        'llm_provider' => $apiProvider,
        'llm_model' => $apiModel,
        'llm_api_key' => $llmApiKey,
        'llm_base_url' => $llmBaseUrl,
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
        'columnas' => extract_columns($json),
        'filas' => is_array($json['filas'] ?? null) ? $json['filas'] : [],
        'error' => $json['errores'] ?? null,
        'sql_generado' => $json['sql_generado'] ?? null,
        'http_code' => $httpCode,
    ];
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($method === 'POST') {
    $input = json_decode((string)file_get_contents('php://input'), true);
    if (!is_array($input)) {
        http_response_code(422);
        echo json_encode(['error' => 'Body JSON inválido']);
        exit;
    }

    $sessionId = (string)($input['session_id'] ?? 'default');
    $message = trim((string)($input['message'] ?? ''));
    if ($message === '') {
        http_response_code(422);
        echo json_encode(['error' => 'Mensaje requerido']);
        exit;
    }

    $params = is_array($input['params'] ?? null) ? $input['params'] : [];
    $requestedTtl = isset($params['ttl_minutes']) ? (int)$params['ttl_minutes'] : $defaultTtlMinutes;
    $ttlMinutes = sanitize_ttl($requestedTtl, $defaultTtlMinutes);
    $contextSignature = isset($params['context_signature']) ? (string)$params['context_signature'] : null;

    $state = load_session($cacheDir, $sessionId, $defaultTtlMinutes);

    // Si el contexto de DB/LLM cambia, limpiamos el historial para evitar mezclar hilos.
    if ($contextSignature && $state['context_signature'] && $contextSignature !== $state['context_signature']) {
        $state['history'] = [];
    }

    $state['context_signature'] = $contextSignature;
    $state['ttl_minutes'] = $ttlMinutes;
    $state['expires_at'] = time() + ($ttlMinutes * 60);

    $state['history'][] = ['role' => 'user', 'text' => $message, 'ts' => time()];

    $result = call_api($message, $sessionId, $params);
    $assistantText = isset($result['error']) && $result['error']
        ? $result['error']
        : ('SQL: ' . ($result['sql_generado'] ?? 'N/A'));

    $state['history'][] = [
        'role' => 'assistant',
        'text' => $assistantText,
        'ts' => time(),
        'result' => [
            'columnas' => $result['columnas'] ?? [],
            'filas' => $result['filas'] ?? [],
            'sql_generado' => $result['sql_generado'] ?? null,
            'error' => $result['error'] ?? null,
        ],
    ];

    if (count($state['history']) > $maxMessages) {
        $state['history'] = array_slice($state['history'], -1 * $maxMessages);
    }

    save_session($cacheDir, $sessionId, $state);
    echo json_encode([
        'ok' => true,
        'session_id' => $sessionId,
        'ttl_minutes' => $ttlMinutes,
        'context_signature' => $state['context_signature'],
        'history' => $state['history'],
    ]);
    exit;
}

$sessionId = (string)($_GET['session_id'] ?? 'default');
$state = load_session($cacheDir, $sessionId, $defaultTtlMinutes);

echo json_encode([
    'session_id' => $sessionId,
    'ttl_minutes' => $state['ttl_minutes'] ?? $defaultTtlMinutes,
    'context_signature' => $state['context_signature'] ?? null,
    'history' => $state['history'] ?? [],
]);
