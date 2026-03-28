<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Texto2SQL Demo Chat</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #111827; color: #f9fafb; }
    .wrap { max-width: 1080px; margin: 0 auto; padding: 20px; }
    .chat { background: #1f2937; border-radius: 10px; padding: 16px; min-height: 360px; }
    .msg { margin-bottom: 12px; padding: 10px; border-radius: 8px; }
    .user { background: #374151; }
    .bot { background: #0f766e; }
    .meta { font-size: 12px; opacity: 0.8; margin-top: 4px; }
    .cfg { background: #0b1220; border-radius: 10px; padding: 12px; margin-bottom: 12px; }
    .cfg-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
    .cfg input, .cfg select { width: 100%; box-sizing: border-box; }
    form { display: grid; grid-template-columns: 1fr auto; gap: 8px; margin-top: 12px; }
    input, button, select { padding: 10px; border-radius: 8px; border: none; }
    button { cursor: pointer; }
    .status { font-size: 13px; opacity: 0.85; margin-top: 8px; }
    .hint { font-size: 12px; opacity: 0.8; margin-top: 6px; color: #d1d5db; }
    .alert {
      margin-top: 10px;
      padding: 8px 10px;
      border-radius: 8px;
      font-size: 13px;
      background: #1e3a8a;
      color: #dbeafe;
      display: none;
    }
    .alert.warn {
      background: #7c2d12;
      color: #ffedd5;
    }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; background: #0b1220; }
    th, td { border: 1px solid #374151; padding: 8px; font-size: 13px; }
  </style>
</head>
<body>
<div class="wrap">
  <h1>Demo NL→SQL</h1>
  <p>Todos los parámetros de ejecución son editables. Si cambias contexto DB/LLM, se inicia nueva sesión automáticamente.</p>

  <details class="cfg" open>
    <summary><strong>Parámetros de ejecución API</strong></summary>
    <div class="cfg-grid" style="margin-top:10px;">
      <input id="api_url" placeholder="API URL (opcional)" />
      <input id="api_bearer" type="password" placeholder="API Bearer (opcional)" autocomplete="off" />
      <input id="db_host" placeholder="DB host (opcional)" />
      <input id="db_port" placeholder="DB port (opcional)" />
      <input id="db_name" placeholder="DB name (opcional)" />
      <input id="db_user" placeholder="DB user (opcional)" />
      <input id="db_password" type="password" placeholder="DB password (opcional)" autocomplete="off" />
      <select id="db_engine">
        <option value="">DB engine (default)</option>
        <option value="mysql">mysql</option>
        <option value="mariadb">mariadb</option>
        <option value="postgres">postgres</option>
        <option value="sqlsrv">sqlsrv</option>
        <option value="sybase">sybase</option>
        <option value="sqlite">sqlite</option>
      </select>

      <select id="llm_provider">
        <option value="">LLM provider (default)</option>
        <option value="openai">openai</option>
        <option value="deepseek">deepseek</option>
        <option value="mistral">mistral</option>
        <option value="huggingface">huggingface</option>
        <option value="anthropic">anthropic</option>
        <option value="claude">claude</option>
        <option value="gemini">gemini</option>
        <option value="llama">llama</option>
        <option value="copilot">copilot</option>
      </select>
      <input id="llm_model" placeholder="LLM model (opcional)" />
      <input id="llm_base_url" placeholder="LLM base URL (opcional)" />
      <input id="llm_api_key" type="password" placeholder="LLM API key (opcional)" autocomplete="off" />
      <input id="ttl_minutes" placeholder="TTL minutos (opcional)" />
    </div>
    <div id="providerHint" class="hint">Sugerencia proveedor/modelo: usa un proveedor conocido para autocompletar placeholders.</div>
    <div id="dbHint" class="hint">Sugerencia DB: al elegir motor, se sugiere puerto por defecto.</div>
    <div id="formAlert" class="alert"></div>
  </details>

  <div id="chat" class="chat"></div>
  <form id="chatForm">
    <input id="message" name="message" placeholder="Ej: Top 5 películas por arriendo" required />
    <button id="sendBtn" type="submit">Enviar</button>
  </form>
  <div id="status" class="status"></div>
</div>
<script>
function newSessionId() {
  return crypto.randomUUID();
}

let sessionId = localStorage.getItem('demoSession') || newSessionId();
localStorage.setItem('demoSession', sessionId);

const providerSuggestions = {
  openai: { model: 'gpt-4o-mini', baseUrl: 'https://api.openai.com/v1' },
  deepseek: { model: 'deepseek-chat', baseUrl: 'https://api.deepseek.com/v1' },
  mistral: { model: 'mistral-small-latest', baseUrl: 'https://api.mistral.ai/v1' },
  huggingface: { model: 'meta-llama/Meta-Llama-3-8B-Instruct', baseUrl: 'https://api-inference.huggingface.co/models' },
  anthropic: { model: 'claude-3-5-sonnet-latest', baseUrl: 'https://api.anthropic.com/v1' },
  claude: { model: 'claude-3-5-sonnet-latest', baseUrl: 'https://api.anthropic.com/v1' },
  gemini: { model: 'gemini-1.5-flash', baseUrl: 'https://generativelanguage.googleapis.com/v1beta' },
  llama: { model: 'meta-llama/Meta-Llama-3.1-8B-Instruct', baseUrl: 'https://api.llama.com/v1' },
  copilot: { model: 'gpt-4o-mini', baseUrl: 'https://api.githubcopilot.com' },
};

const enginePortSuggestions = {
  mysql: 3306,
  mariadb: 3306,
  postgres: 5432,
  sqlsrv: 1433,
  sybase: 5000,
};

const allowedDbEngines = new Set(['mysql', 'mariadb', 'postgres', 'sqlsrv', 'sybase', 'sqlite']);

const persistentKeys = [
  'api_url', 'db_host', 'db_port', 'db_name', 'db_user', 'db_engine',
  'llm_provider', 'llm_model', 'llm_base_url', 'ttl_minutes'
];
const sensitiveKeys = ['api_bearer', 'db_password', 'llm_api_key'];

const defaults = {
  api_url: localStorage.getItem('api_url') || '',
  api_bearer: '',
  db_host: localStorage.getItem('db_host') || '',
  db_port: localStorage.getItem('db_port') || '',
  db_name: localStorage.getItem('db_name') || '',
  db_user: localStorage.getItem('db_user') || '',
  db_password: '',
  db_engine: localStorage.getItem('db_engine') || '',
  llm_provider: localStorage.getItem('llm_provider') || '',
  llm_model: localStorage.getItem('llm_model') || '',
  llm_base_url: localStorage.getItem('llm_base_url') || '',
  llm_api_key: '',
  ttl_minutes: localStorage.getItem('ttl_minutes') || '',
};

Object.entries(defaults).forEach(([k, v]) => {
  const el = document.getElementById(k);
  if (el) el.value = v;
});

function showAlert(msg, type='info') {
  const el = document.getElementById('formAlert');
  if (!msg) {
    el.style.display = 'none';
    el.textContent = '';
    el.classList.remove('warn');
    return;
  }
  el.textContent = msg;
  el.style.display = 'block';
  el.classList.toggle('warn', type === 'warn');
}

function applyProviderHints() {
  const provider = (document.getElementById('llm_provider')?.value || '').trim().toLowerCase();
  const modelEl = document.getElementById('llm_model');
  const baseUrlEl = document.getElementById('llm_base_url');
  const hintEl = document.getElementById('providerHint');

  const suggestion = providerSuggestions[provider];
  if (!suggestion) {
    modelEl.placeholder = 'LLM model (opcional)';
    baseUrlEl.placeholder = 'LLM base URL (opcional)';
    hintEl.textContent = 'Sugerencia proveedor/modelo: usa un proveedor conocido para autocompletar placeholders.';
    return;
  }

  modelEl.placeholder = `Ej. ${suggestion.model}`;
  baseUrlEl.placeholder = `Ej. ${suggestion.baseUrl}`;
  hintEl.textContent = `Proveedor ${provider}: modelo sugerido "${suggestion.model}" y base URL "${suggestion.baseUrl}".`;
}

function applyDbHints() {
  const engine = (document.getElementById('db_engine')?.value || '').trim().toLowerCase();
  const portEl = document.getElementById('db_port');
  const hintEl = document.getElementById('dbHint');

  if (!engine) {
    hintEl.textContent = 'Sugerencia DB: al elegir motor, se sugiere puerto por defecto.';
    return;
  }

  if (!allowedDbEngines.has(engine)) {
    hintEl.textContent = `Motor no soportado: ${engine}. Usa uno de ${Array.from(allowedDbEngines).join(', ')}.`;
    return;
  }

  const suggested = enginePortSuggestions[engine];
  if (suggested && !portEl.value.trim()) {
    portEl.placeholder = `Ej. ${suggested}`;
  }
  hintEl.textContent = suggested
    ? `Motor ${engine}: puerto sugerido ${suggested}.`
    : `Motor ${engine}: no requiere puerto típico (revisa configuración específica).`;
}

function validateClientParams(params) {
  const engine = (params.db_engine || '').toLowerCase();
  if (engine && !allowedDbEngines.has(engine)) {
    return `DB engine no soportado: ${engine}`;
  }

  if (params.db_port) {
    const n = Number(params.db_port);
    if (!Number.isInteger(n) || n <= 0 || n > 65535) {
      return 'DB port debe ser un entero entre 1 y 65535';
    }
  }

  if (params.ttl_minutes !== undefined) {
    const ttl = Number(params.ttl_minutes);
    if (!Number.isInteger(ttl) || ttl <= 0 || ttl > 1440) {
      return 'TTL debe ser entero entre 1 y 1440 minutos';
    }
  }

  return null;
}

function tableHTML(result) {
  if (!result || !Array.isArray(result.columnas) || !Array.isArray(result.filas) || result.columnas.length === 0) {
    return '<em>Sin tabla en esta respuesta.</em>';
  }
  const head = result.columnas.map(c => `<th>${c}</th>`).join('');
  const rows = result.filas.map(r => `<tr>${(Array.isArray(r) ? r : [r]).map(v => `<td>${v ?? ''}</td>`).join('')}</tr>`).join('');
  return `<table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`;
}

function renderHistory(history) {
  const chat = document.getElementById('chat');
  chat.innerHTML = '';
  (history || []).forEach(item => {
    const div = document.createElement('div');
    div.className = `msg ${item.role === 'user' ? 'user' : 'bot'}`;
    const ts = new Date((item.ts || 0) * 1000).toLocaleString();
    div.innerHTML = `<div>${item.text || ''}</div><div class="meta">${ts}</div>`;

    if (item.role === 'assistant' && item.result) {
      const resultWrap = document.createElement('div');
      resultWrap.innerHTML = tableHTML(item.result);
      div.appendChild(resultWrap);
    }

    chat.appendChild(div);
  });
  chat.scrollTop = chat.scrollHeight;
}

function contextSignature(params) {
  // Ambigüedad resuelta: reiniciar hilo cuando cambia endpoint+DB+modelo/proveedor LLM.
  const signaturePayload = {
    api_url: params.api_url || '',
    db_engine: params.db_engine || '',
    db_host: params.db_host || '',
    db_port: params.db_port || '',
    db_name: params.db_name || '',
    db_user: params.db_user || '',
    llm_provider: params.llm_provider || '',
    llm_model: params.llm_model || '',
    llm_base_url: params.llm_base_url || '',
  };
  return btoa(unescape(encodeURIComponent(JSON.stringify(signaturePayload))));
}

function gatherParams() {
  const keys = [...persistentKeys, ...sensitiveKeys];
  const params = {};

  keys.forEach(k => {
    const v = (document.getElementById(k)?.value || '').trim();
    if (v !== '') {
      params[k] = v;
      if (persistentKeys.includes(k)) {
        localStorage.setItem(k, v);
      }
    }
  });

  if (params.ttl_minutes && Number(params.ttl_minutes) > 0) {
    params.ttl_minutes = Number(params.ttl_minutes);
  } else {
    delete params.ttl_minutes;
  }

  params.context_signature = contextSignature(params);
  return params;
}

function maybeRotateSession(params) {
  const currentSignature = params.context_signature;
  const lastSignature = localStorage.getItem('lastContextSignature') || '';
  if (currentSignature !== lastSignature) {
    sessionId = newSessionId();
    localStorage.setItem('demoSession', sessionId);
    localStorage.setItem('lastContextSignature', currentSignature);
    showAlert('Se detectó cambio de contexto (DB/LLM/API): se inició una sesión nueva.', 'info');
    return true;
  }
  return false;
}

function setBusy(isBusy, text='') {
  document.getElementById('sendBtn').disabled = isBusy;
  document.getElementById('status').textContent = text;
}

async function fetchHistory() {
  const res = await fetch(`chat.php?session_id=${encodeURIComponent(sessionId)}`);
  const data = await res.json();
  renderHistory(data.history || []);
  const ttl = data.ttl_minutes || 'default';
  document.getElementById('status').textContent = `session=${sessionId} · ttl=${ttl} min`;
}

document.getElementById('llm_provider').addEventListener('change', applyProviderHints);
document.getElementById('db_engine').addEventListener('change', applyDbHints);

document.getElementById('chatForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = document.getElementById('message').value.trim();
  if (!message) return;
  document.getElementById('message').value = '';

  const params = gatherParams();
  const clientValidationError = validateClientParams(params);
  if (clientValidationError) {
    showAlert(clientValidationError, 'warn');
    return;
  }

  const rotated = maybeRotateSession(params);

  setBusy(true, rotated ? 'Contexto cambió: iniciando nueva sesión...' : 'Consultando API...');
  try {
    const response = await fetch('chat.php', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        session_id: sessionId,
        message,
        params,
      })
    });

    if (!response.ok) {
      showAlert(`La API del demo respondió HTTP ${response.status}.`, 'warn');
    } else {
      showAlert('');
    }

    await fetchHistory();
  } finally {
    setBusy(false);
  }
});

applyProviderHints();
applyDbHints();
fetchHistory();
</script>
</body>
</html>
