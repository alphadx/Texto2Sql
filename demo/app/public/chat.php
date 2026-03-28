<?php

require_once __DIR__ . '/chat_adapter.php';

function apply_demo_security_headers(): void {
    header('Content-Type: application/json; charset=utf-8');
    header('X-Content-Type-Options: nosniff');
    header('X-Frame-Options: DENY');
    header('Referrer-Policy: no-referrer');
    header('Permissions-Policy: geolocation=(), microphone=(), camera=()');

    $allowedOrigin = $_ENV['NL2SQL_DEMO_ALLOWED_ORIGIN'] ?? getenv('NL2SQL_DEMO_ALLOWED_ORIGIN') ?: '';
    if ($allowedOrigin !== '') {
        header('Access-Control-Allow-Origin: ' . $allowedOrigin);
        header('Vary: Origin');
        header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
        header('Access-Control-Allow-Headers: Content-Type, Authorization, X-Correlation-Id');
    }
}

apply_demo_security_headers();
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'OPTIONS') {
    http_response_code(204);
    exit;
}

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

function demo_log_event(array $event): void {
    $logPath = '/var/log/texto2sql-demo/chat.log';
    $event['api_url'] = isset($event['api_url']) && is_string($event['api_url'])
        ? sanitize_url_for_logs($event['api_url'])
        : null;
    $event['error'] = isset($event['error']) && is_string($event['error'])
        ? sanitize_sensitive_text($event['error'])
        : null;

    $line = json_encode($event, JSON_UNESCAPED_UNICODE);
    if (!is_string($line)) {
        return;
    }

    $dir = dirname($logPath);
    if (!is_dir($dir)) {
        @mkdir($dir, 0777, true);
    }
    @file_put_contents($logPath, $line . PHP_EOL, FILE_APPEND);
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
    $params['correlation_id'] = $params['correlation_id'] ?? bin2hex(random_bytes(8));
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
    if (isset($result['error']) && $result['error']) {
        $assistantText = $result['error'];
    } else {
        $formalText = $result['texto_formal'] ?? 'No disponible en respuesta API';
        $sqlText = $result['sql_generado'] ?? 'No disponible en respuesta API';
        $assistantText = "Texto formal: {$formalText}\nSQL: {$sqlText}";
    }

    $state['history'][] = [
        'role' => 'assistant',
        'text' => $assistantText,
        'ts' => time(),
        'result' => [
            'columnas' => $result['columnas'] ?? [],
            'filas' => $result['filas'] ?? [],
            'sql_generado' => $result['sql_generado'] ?? null,
            'texto_formal' => $result['texto_formal'] ?? null,
            'error' => $result['error'] ?? null,
            'http_code' => $result['http_code'] ?? null,
            'error_type' => $result['error_type'] ?? 'none',
            'request_ts' => $result['request_ts'] ?? null,
            'latency_ms' => $result['latency_ms'] ?? null,
            'correlation_id' => $result['correlation_id'] ?? $params['correlation_id'],
        ],
    ];

    demo_log_event([
        'ts' => time(),
        'session_id' => $sessionId,
        'correlation_id' => $result['correlation_id'] ?? $params['correlation_id'],
        'api_url' => $result['api_url'] ?? ($params['api_url'] ?? null),
        'http_code' => $result['http_code'] ?? null,
        'latency_ms' => $result['latency_ms'] ?? null,
        'error_type' => $result['error_type'] ?? 'none',
    ]);

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
