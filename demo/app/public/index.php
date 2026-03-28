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
      <input id="api_bearer" type="password" placeholder="API Bearer (opcional)" />
      <input id="db_host" placeholder="DB host (opcional)" />
      <input id="db_port" placeholder="DB port (opcional)" />
      <input id="db_name" placeholder="DB name (opcional)" />
      <input id="db_user" placeholder="DB user (opcional)" />
      <input id="db_password" type="password" placeholder="DB password (opcional)" />
      <select id="db_engine">
        <option value="">DB engine (default)</option>
        <option value="mysql">mysql</option>
        <option value="mariadb">mariadb</option>
        <option value="postgres">postgres</option>
        <option value="sqlsrv">sqlsrv</option>
        <option value="sybase">sybase</option>
        <option value="sqlite">sqlite</option>
      </select>
      <input id="llm_provider" list="llm_provider_options" placeholder="LLM provider (opcional)" />
      <input id="llm_model" placeholder="LLM model (opcional)" />
      <input id="llm_base_url" placeholder="LLM base URL (opcional)" />
      <input id="llm_api_key" type="password" placeholder="LLM API key (opcional)" />
      <input id="ttl_minutes" placeholder="TTL minutos (opcional)" />
    </div>
  </details>
      <datalist id="llm_provider_options">
        <option value="openai"></option>
        <option value="deepseek"></option>
        <option value="mistral"></option>
        <option value="huggingface"></option>
        <option value="anthropic"></option>
        <option value="claude"></option>
        <option value="gemini"></option>
        <option value="llama"></option>
        <option value="copilot"></option>
      </datalist>

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

document.getElementById('chatForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = document.getElementById('message').value.trim();
  if (!message) return;
  document.getElementById('message').value = '';

  const params = gatherParams();
  const rotated = maybeRotateSession(params);

  setBusy(true, rotated ? 'Contexto cambió: iniciando nueva sesión...' : 'Consultando API...');
  try {
    await fetch('chat.php', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        session_id: sessionId,
        message,
        params,
      })
    });
    await fetchHistory();
  } finally {
    setBusy(false);
  }
});

fetchHistory();
</script>
</body>
</html>
