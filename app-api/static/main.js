const go = document.getElementById('go');
const mode = document.getElementById('mode');
const ta = document.getElementById('prompt');
const out = document.getElementById('out');

go.onclick = async () => {
  out.textContent = '...';
  const endpoint = '/' + mode.value;
  const body =
    mode.value === 'generate' ? {prompt: ta.value} :
    {text: ta.value};

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });

  out.textContent = JSON.stringify(await response.json(), null, 2);
};
