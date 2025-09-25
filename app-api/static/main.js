const go = document.getElementById('go');
const ta = document.getElementById('prompt');
const out = document.getElementById('out');
go.onclick = async () => {
  out.textContent = '...';
  const r = await fetch('/generate', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({prompt: ta.value || 'hello'})
  });
  const j = await r.json();
  out.textContent = JSON.stringify(j, null, 2);
};
