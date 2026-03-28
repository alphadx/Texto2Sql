<?php

require_once __DIR__ . '/../demo/app/public/chat_adapter.php';

function assert_true(bool $condition, string $label): void {
    if (!$condition) {
        fwrite(STDERR, "[FAIL] $label\n");
        exit(1);
    }
    fwrite(STDOUT, "[OK] $label\n");
}

$legacy = build_canonical_response([
    'columnas' => ['nombre'],
    'filas' => [['Ana']],
    'sql_generado' => 'SELECT nombre FROM clientes',
], 200, 12, 1700000000);
assert_true($legacy['columnas'][0] === 'nombre', 'parsea columnas legacy');
assert_true($legacy['filas'][0][0] === 'Ana', 'parsea filas legacy');
assert_true($legacy['sql_generado'] === 'SELECT nombre FROM clientes', 'parsea sql_generado legacy');
assert_true($legacy['error'] === null, 'sin error en respuesta 200 válida');

$current = build_canonical_response([
    'columns' => ['name'],
    'rows' => [['Ana']],
    'sql' => 'SELECT name FROM customers',
], 200, 14, 1700000010);
assert_true($current['columnas'][0] === 'name', 'parsea columns actual');
assert_true($current['filas'][0][0] === 'Ana', 'parsea rows actual');
assert_true($current['sql_generado'] === 'SELECT name FROM customers', 'parsea sql actual');

$detailError = build_canonical_response([
    'detail' => ['error' => 'token inválido'],
], 401, 20, 1700000020);
assert_true($detailError['error_type'] === 'auth', 'clasifica 401 como auth');
assert_true(str_contains((string)$detailError['error'], 'token inválido'), 'propaga detail.error');

$listError = build_canonical_response([
    'errores' => ['campo A faltante', 'campo B inválido'],
], 422, 22, 1700000030);
assert_true($listError['error_type'] === 'validation', 'clasifica 422 como validation');
assert_true(str_contains((string)$listError['error'], 'campo A faltante'), 'concatena errores[]');

$stringDetail = build_canonical_response([
    'detail' => 'modelo no soportado',
], 400, 24, 1700000040);
assert_true(str_contains((string)$stringDetail['error'], 'modelo no soportado'), 'parsea detail string');

$inferredColumns = extract_columns([
    'rows' => [
        ['id' => 1, 'name' => 'Ana'],
    ],
]);
assert_true($inferredColumns[0] === 'col_id', 'infiere columnas si faltan nombres');

$safeText = sanitize_sensitive_text('api_key=abc123 token=zzz password=qwerty');
assert_true(str_contains((string)$safeText, 'api_key=***'), 'enmascara api_key');
assert_true(str_contains((string)$safeText, 'token=***'), 'enmascara token');
assert_true(str_contains((string)$safeText, 'password=***'), 'enmascara password');

$safeUrl = sanitize_url_for_logs('https://user:secret@example.com:8443/nl2sql/query?x=1');
assert_true($safeUrl === 'https://example.com:8443/nl2sql/query?x=1', 'sanitiza userinfo en URL');

fwrite(STDOUT, "\nHarness OK\n");
