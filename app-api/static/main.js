const go = document.getElementById('go');
const mode = document.getElementById('mode');
const ta = document.getElementById('prompt');
const out = document.getElementById('out');
const historyBox = document.getElementById('history');

async function refreshHistory() {
  try {
    const response = await fetch('/history');
    const payload = await response.json();
    historyBox.textContent = JSON.stringify(payload, null, 2);
  } catch (err) {
    historyBox.textContent = `Failed to load history: ${err}`;
  }
}

document.getElementById('refresh').onclick = refreshHistory;

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
  refreshHistory();
};

refreshHistory();
