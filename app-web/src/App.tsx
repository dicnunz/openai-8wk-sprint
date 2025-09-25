import React, { useEffect, useMemo, useState } from "react";

type Mode = "generate" | "title" | "summarize" | "keywords";

type HistoryRecord = {
  id: string;
  mode: Mode;
  prompt?: string;
  text?: string;
  created_at: string;
  response: unknown;
};

const DEFAULT_API_BASE = "https://openai-8wk-sprint-api.onrender.com";

export default function App(): JSX.Element {
  const [mode, setMode] = useState<Mode>("generate");
  const [text, setText] = useState("");
  const [token, setToken] = useState<string>(() =>
    localStorage.getItem("api_token") ?? ""
  );
  const [response, setResponse] = useState<unknown | "...">(null);
  const [history, setHistory] = useState<HistoryRecord[]>([]);

  const apiBase = useMemo(
    () => import.meta.env.VITE_API_BASE ?? DEFAULT_API_BASE,
    []
  );

  useEffect(() => {
    localStorage.setItem("api_token", token);
  }, [token]);

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function callApi() {
    setResponse("...");
    const payload = mode === "generate" ? { prompt: text } : { text };

    const res = await fetch(`${apiBase}/${mode}`, {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify(payload),
    });

    const json = await res.json();
    setResponse(json);
    await refresh();
  }

  async function refresh() {
    const res = await fetch(`${apiBase}/history?limit=10`, {
      headers: buildHeaders(),
    });

    if (!res.ok) {
      setHistory([]);
      return;
    }

    const json = (await res.json()) as HistoryRecord[];
    setHistory(json);
  }

  function buildHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    return headers;
  }

  return (
    <div
      style={{
        fontFamily:
          "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
        margin: 24,
        maxWidth: 960,
      }}
    >
      <h1>app-web</h1>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 24,
          alignItems: "start",
        }}
      >
        <div>
          <label htmlFor="mode">Mode</label>
          <br />
          <select
            id="mode"
            value={mode}
            onChange={(event) => setMode(event.target.value as Mode)}
          >
            <option value="generate">/generate</option>
            <option value="title">/title</option>
            <option value="summarize">/summarize</option>
            <option value="keywords">/keywords</option>
          </select>
          <br />
          <br />
          <textarea
            placeholder="Type text or prompt"
            value={text}
            onChange={(event) => setText(event.target.value)}
            style={{ width: "100%", height: 160 }}
          />
          <br />
          <button type="button" onClick={() => void callApi()}>
            Send
          </button>
          <h3>Response</h3>
          <pre>
            {response
              ? JSON.stringify(response, null, 2)
              : "Use the form to send a request."}
          </pre>
        </div>
        <div>
          <label htmlFor="apiBase">API base</label>
          <input
            id="apiBase"
            style={{ width: "100%" }}
            value={apiBase}
            readOnly
          />
          <br />
          <br />
          <label htmlFor="token">Bearer token (optional)</label>
          <input
            id="token"
            style={{ width: "100%" }}
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder="Paste token if configured on the server"
          />
          <h3>History</h3>
          <pre>{JSON.stringify(history, null, 2)}</pre>
          <button type="button" onClick={() => void refresh()}>
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
}
