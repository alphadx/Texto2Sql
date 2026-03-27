<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Texto2SQL Demo Chat</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #111827; color: #f9fafb; }
    .wrap { max-width: 960px; margin: 0 auto; padding: 20px; }
    .chat { background: #1f2937; border-radius: 10px; padding: 16px; min-height: 320px; }
    .msg { margin-bottom: 12px; padding: 10px; border-radius: 8px; }
    .user { background: #374151; }
    .bot { background: #0f766e; }
    .meta { font-size: 12px; opacity: 0.8; }
    form { display: grid; grid-template-columns: 1fr auto; gap: 8px; margin-top: 12px; }
    input, button { padding: 10px; border-radius: 8px; border: none; }
    table { width: 100%; border-collapse: collapse; margin-top: 14px; background: #0b1220; }
    th, td { border: 1px solid #374151; padding: 8px; font-size: 14px; }
  </style>
</head>
<body>
<div class="wrap">
  <h1>Demo NL→SQL</h1>
  <p>Chat con historial en caché (TTL configurable, default 360 minutos).</p>
  <div id="chat" class="chat"></div>
  <form id="chatForm">
    <input id="message" name="message" placeholder="Ej: Top 5 películas por arriendo" required />
    <button type="submit">Enviar</button>
  </form>

  <h2>Resultado de tabla</h2>
  <div id="tableWrap"></div>
</div>
<script>
const sessionId = localStorage.getItem('demoSession') || crypto.randomUUID();
localStorage.setItem('demoSession', sessionId);

function renderHistory(history) {
  const chat = document.getElementById('chat');
  chat.innerHTML = '';
  history.forEach(item => {
    const div = document.createElement('div');
    div.className = `msg ${item.role === 'user' ? 'user' : 'bot'}`;
    div.innerHTML = `<div>${item.text}</div><div class="meta">${new Date(item.ts * 1000).toLocaleString()}</div>`;
    chat.appendChild(div);
  });
  chat.scrollTop = chat.scrollHeight;
}

function renderTable(payload) {
  const wrap = document.getElementById('tableWrap');
  if (!payload || !payload.columnas || !payload.filas) {
    wrap.innerHTML = '<em>Sin resultados todavía.</em>';
    return;
  }
  const head = payload.columnas.map(c => `<th>${c}</th>`).join('');
  const rows = payload.filas.map(r => `<tr>${r.map(v => `<td>${v ?? ''}</td>`).join('')}</tr>`).join('');
  wrap.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`;
}

async function fetchHistory() {
  const res = await fetch(`chat.php?session_id=${encodeURIComponent(sessionId)}`);
  const data = await res.json();
  renderHistory(data.history || []);
  renderTable(data.last_result || null);
}

document.getElementById('chatForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = document.getElementById('message').value.trim();
  if (!message) return;
  document.getElementById('message').value = '';
  await fetch('chat.php', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({session_id: sessionId, message})
  });
  await fetchHistory();
});

fetchHistory();
</script>
</body>
</html>
