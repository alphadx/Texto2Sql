<?php

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
    $columns = $json['columnas'] ?? $json['columns'] ?? [];
    if (empty($columns) && isset($json['filas'][0]) && is_array($json['filas'][0])) {
        return array_map(static fn($idx) => 'col_' . $idx, array_keys($json['filas'][0]));
    }
    if (empty($columns) && isset($json['rows'][0]) && is_array($json['rows'][0])) {
        return array_map(static fn($idx) => 'col_' . $idx, array_keys($json['rows'][0]));
    }

    return array_map(static function ($col) {
        if (is_array($col)) {
            return (string)($col['nombre'] ?? $col['name'] ?? json_encode($col));
        }
        return (string)$col;
    }, $columns);
}

function extract_error(array $json): ?string {
    if (!empty($json['error']) && is_string($json['error'])) {
        return $json['error'];
    }

    if (isset($json['errores'])) {
        if (is_string($json['errores']) && trim($json['errores']) !== '') {
            return $json['errores'];
        }
        if (is_array($json['errores'])) {
            $parts = [];
            foreach ($json['errores'] as $value) {
                if (is_string($value) && trim($value) !== '') {
                    $parts[] = $value;
                }
            }
            if (!empty($parts)) {
                return implode(' | ', $parts);
            }
        }
    }

    if (isset($json['detail'])) {
        if (is_string($json['detail']) && trim($json['detail']) !== '') {
            return $json['detail'];
        }
        if (is_array($json['detail'])) {
            if (!empty($json['detail']['error']) && is_string($json['detail']['error'])) {
                return $json['detail']['error'];
            }
            if (!empty($json['detail']['message']) && is_string($json['detail']['message'])) {
                return $json['detail']['message'];
            }
        }
    }

    return null;
}

function extract_sql(array $json): ?string {
    $sql = $json['sql_generado'] ?? $json['sql'] ?? null;
    return is_string($sql) && trim($sql) !== '' ? $sql : null;
}

function extract_formal_text(array $json): ?string {
    $formal = $json['texto_formal'] ?? null;
    return is_string($formal) && trim($formal) !== '' ? $formal : null;
}

function sanitize_sensitive_text(?string $value): ?string {
    if ($value === null) {
        return null;
    }

    $patterns = [
        '/(api[_-]?key\\s*[=:]\\s*)([^\\s,;]+)/i' => '$1***',
        '/(token\\s*[=:]\\s*)([^\\s,;]+)/i' => '$1***',
        '/(password\\s*[=:]\\s*)([^\\s,;]+)/i' => '$1***',
        '/(authorization:\\s*bearer\\s+)([^\\s,;]+)/i' => '$1***',
    ];

    $sanitized = $value;
    foreach ($patterns as $pattern => $replacement) {
        $sanitized = preg_replace($pattern, $replacement, $sanitized) ?? $sanitized;
    }
    return $sanitized;
}

function sanitize_url_for_logs(string $url): string {
    $parts = parse_url($url);
    if (!is_array($parts)) {
        return $url;
    }

    $scheme = isset($parts['scheme']) ? $parts['scheme'] . '://' : '';
    $host = $parts['host'] ?? '';
    $port = isset($parts['port']) ? ':' . $parts['port'] : '';
    $path = $parts['path'] ?? '';
    $query = isset($parts['query']) ? '?' . $parts['query'] : '';
    return $scheme . $host . $port . $path . $query;
}

function classify_error_type(string $curlError, int $httpCode): string {
    if ($curlError !== '') {
        return 'connectivity';
    }
    if ($httpCode === 401 || $httpCode === 403) {
        return 'auth';
    }
    if ($httpCode === 400 || $httpCode === 404 || $httpCode === 422) {
        return 'validation';
    }
    if ($httpCode >= 500) {
        return 'execution';
    }
    if ($httpCode >= 400) {
        return 'api_error';
    }
    return 'none';
}

function human_error_message(string $errorType, int $httpCode, ?string $apiError = null): ?string {
    $apiError = sanitize_sensitive_text($apiError);
    $apiError = $apiError !== null ? trim($apiError) : '';
    $suffix = $apiError !== '' ? ': ' . $apiError : '';

    return match ($errorType) {
        'connectivity' => 'Falla de conectividad con la API' . $suffix,
        'auth' => 'Error de autenticación/autorización con la API (HTTP ' . $httpCode . ')' . $suffix,
        'validation' => 'Error de validación en la solicitud (HTTP ' . $httpCode . ')' . $suffix,
        'execution' => 'Error interno al ejecutar la consulta en la API (HTTP ' . $httpCode . ')' . $suffix,
        'api_error' => 'Error de API (HTTP ' . $httpCode . ')' . $suffix,
        default => $apiError !== '' ? $apiError : null,
    };
}

function build_canonical_response(array $json, int $httpCode, int $latencyMs, int $requestTs): array {
    $rows = [];
    if (is_array($json['filas'] ?? null)) {
        $rows = $json['filas'];
    } elseif (is_array($json['rows'] ?? null)) {
        $rows = $json['rows'];
    }

    $errorFromBody = extract_error($json);
    $errorType = classify_error_type('', $httpCode);
    $humanError = human_error_message($errorType, $httpCode, $errorFromBody);

    return [
        'columnas' => extract_columns($json),
        'filas' => $rows,
        'error' => $humanError,
        'sql_generado' => extract_sql($json),
        'texto_formal' => extract_formal_text($json),
        'http_code' => $httpCode,
        'error_type' => $humanError !== null ? $errorType : 'none',
        'request_ts' => $requestTs,
        'latency_ms' => $latencyMs,
    ];
}

function call_api(string $message, string $sessionId, array $params): array {
    $apiUrl = $params['api_url'] ?? ($_ENV['NL2SQL_API_URL'] ?? getenv('NL2SQL_API_URL') ?: 'http://host.docker.internal:5000/nl2sql/query');
    $safeApiUrl = sanitize_url_for_logs($apiUrl);
    $correlationId = $params['correlation_id'] ?? bin2hex(random_bytes(8));
    $apiToken = $params['api_bearer'] ?? ($_ENV['NL2SQL_API_KEY'] ?? getenv('NL2SQL_API_KEY') ?: '');
    $httpTimeoutSeconds = (int)($params['http_timeout_seconds'] ?? ($_ENV['DEMO_NL2SQL_HTTP_TIMEOUT_SECONDS'] ?? getenv('DEMO_NL2SQL_HTTP_TIMEOUT_SECONDS') ?: 900));
    if ($httpTimeoutSeconds <= 0) {
        $httpTimeoutSeconds = 900;
    }

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

    $requestTs = time();
    $start = microtime(true);
    $ch = curl_init($apiUrl);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_HTTPHEADER => array_filter([
            'Content-Type: application/json',
            'X-Correlation-Id: ' . $correlationId,
            $apiToken !== '' ? 'Authorization: Bearer ' . $apiToken : null,
        ]),
        CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE),
        CURLOPT_TIMEOUT => $httpTimeoutSeconds,
    ]);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    curl_close($ch);
    $latencyMs = (int)round((microtime(true) - $start) * 1000);

    if ($curlError !== '') {
        return [
            'error' => human_error_message('connectivity', $httpCode, $curlError),
            'columnas' => [],
            'filas' => [],
            'sql_generado' => null,
            'texto_formal' => null,
            'http_code' => $httpCode,
            'error_type' => 'connectivity',
            'request_ts' => $requestTs,
            'latency_ms' => $latencyMs,
            'correlation_id' => $correlationId,
            'api_url' => $safeApiUrl,
        ];
    }

    $json = json_decode((string)$response, true);
    if (!is_array($json)) {
        return [
            'error' => 'La API devolvió un body no JSON (HTTP ' . $httpCode . ')',
            'columnas' => [],
            'filas' => [],
            'sql_generado' => null,
            'texto_formal' => null,
            'http_code' => $httpCode,
            'error_type' => classify_error_type('', $httpCode),
            'request_ts' => $requestTs,
            'latency_ms' => $latencyMs,
            'correlation_id' => $correlationId,
            'api_url' => $safeApiUrl,
        ];
    }

    $canonical = build_canonical_response($json, $httpCode, $latencyMs, $requestTs);
    $canonical['correlation_id'] = $correlationId;
    $canonical['api_url'] = $safeApiUrl;
    return $canonical;
}
