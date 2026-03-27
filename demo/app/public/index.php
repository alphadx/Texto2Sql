<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Texto2SQL Demo Chat</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #111827; color: #f9fafb; }
    .wrap { max-width: 980px; margin: 0 auto; padding: 20px; }
    .chat { background: #1f2937; border-radius: 10px; padding: 16px; min-height: 360px; }
    .msg { margin-bottom: 12px; padding: 10px; border-radius: 8px; }
    .user { background: #374151; }
    .bot { background: #0f766e; }
    .meta { font-size: 12px; opacity: 0.8; margin-top: 4px; }
    .cfg { background: #0b1220; border-radius: 10px; padding: 12px; margin-bottom: 12px; }
    .cfg-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .cfg input, .cfg select { width: 100%; box-sizing: border-box; }
    form { display: grid; grid-template-columns: 1fr auto; gap: 8px; margin-top: 12px; }
    input, button, select { padding: 10px; border-radius: 8px; border: none; }
    button { cursor: pointer; }
    .status { font-size: 13px; opacity: 0.8; margin-top: 8px; }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; background: #0b1220; }
    th, td { border: 1px solid #374151; padding: 8px; font-size: 13px; }
  </style>
</head>
<body>
<div class="wrap">
  <h1>Demo NL→SQL</h1>
  <p>Una sola página de chat. Cada respuesta conserva su tabla y se guarda en caché por TTL (default 360 min).</p>

  <details class="cfg">
    <summary><strong>Parámetros del test</strong> (conexión DB + TTL)</summary>
    <div class="cfg-grid" style="margin-top:10px;">
      <input id="db_host" placeholder="DB host" />
      <input id="db_port" placeholder="DB port" />
      <input id="db_name" placeholder="DB name" />
      <input id="db_user" placeholder="DB user" />
      <input id="db_password" placeholder="DB password" />
      <select id="db_engine">
        <option value="mysql">mysql</option>
        <option value="postgres">postgres</option>
        <option value="sqlsrv">sqlsrv</option>
      </select>
      <input id="ttl_minutes" placeholder="TTL minutos" />
      <input id="llm_provider" placeholder="LLM provider (opcional)" />
      <input id="llm_model" placeholder="LLM model (opcional)" />
      <input id="llm_base_url" placeholder="LLM base URL (opcional)" />
      <input id="llm_api_key" placeholder="LLM API key (opcional)" />
    </div>
  </details>

  <div id="chat" class="chat"></div>
  <form id="chatForm">
    <input id="message" name="message" placeholder="Ej: Top 5 películas por arriendo" required />
    <button id="sendBtn" type="submit">Enviar</button>
  </form>
  <div id="status" class="status"></div>
</div>
<script>
const sessionId = localStorage.getItem('demoSession') || crypto.randomUUID();
localStorage.setItem('demoSession', sessionId);

const defaults = {
  db_host: localStorage.getItem('db_host') || '127.0.0.1',
  db_port: localStorage.getItem('db_port') || '3306',
  db_name: localStorage.getItem('db_name') || 'sakila',
  db_user: localStorage.getItem('db_user') || 'demo',
  db_password: localStorage.getItem('db_password') || 'demo1234',
  db_engine: localStorage.getItem('db_engine') || 'mysql',
  ttl_minutes: localStorage.getItem('ttl_minutes') || '360',
  llm_provider: localStorage.getItem('llm_provider') || '',
  llm_model: localStorage.getItem('llm_model') || '',
  llm_base_url: localStorage.getItem('llm_base_url') || '',
  llm_api_key: localStorage.getItem('llm_api_key') || '',
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

function gatherParams() {
  const keys = ['db_host','db_port','db_name','db_user','db_password','db_engine','ttl_minutes','llm_provider','llm_model','llm_base_url','llm_api_key'];
  const params = {};
  keys.forEach(k => {
    const v = (document.getElementById(k)?.value || '').trim();
    if (v !== '') {
      params[k] = v;
      localStorage.setItem(k, v);
    }
  });
  params.ttl_minutes = Number(params.ttl_minutes || 360);
  return params;
}

function setBusy(isBusy, text='') {
  document.getElementById('sendBtn').disabled = isBusy;
  document.getElementById('status').textContent = text;
}

async function fetchHistory() {
  const res = await fetch(`chat.php?session_id=${encodeURIComponent(sessionId)}`);
  const data = await res.json();
  renderHistory(data.history || []);
  const ttl = data.ttl_minutes || defaults.ttl_minutes;
  document.getElementById('status').textContent = `session=${sessionId} · ttl=${ttl} min`;
}

document.getElementById('chatForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = document.getElementById('message').value.trim();
  if (!message) return;
  document.getElementById('message').value = '';

  setBusy(true, 'Consultando API...');
  try {
    await fetch('chat.php', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        session_id: sessionId,
        message,
        params: gatherParams(),
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
