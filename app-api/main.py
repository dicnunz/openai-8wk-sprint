from __future__ import annotations

import datetime
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK = os.getenv("MOCK_MODE", "0") == "1"
DB_PATH = os.getenv("DB_PATH", str((Path(__file__).parent / "data.db").resolve()))


def _db() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _init_db() -> None:
    with _db() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL,
                input TEXT NOT NULL,
                output TEXT NOT NULL,
                ts TEXT NOT NULL
            )
            """
        )


def _log(mode: str, input_text: str, output_obj: dict[str, Any]) -> None:
    payload = json.dumps(output_obj)
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    with _db() as con:
        con.execute(
            "INSERT INTO logs(mode, input, output, ts) VALUES(?, ?, ?, ?)",
            (mode, input_text, payload, timestamp),
        )


class GenIn(BaseModel):
    prompt: str


class TextIn(BaseModel):
    text: str


def _openai():
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY")
    return client


@app.on_event("startup")
def startup() -> None:
    _init_db()


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/generate")
def generate(inp: GenIn):
    if MOCK:
        result = {"text": f"(mock) you said: {inp.prompt}"}
        _log("generate", inp.prompt, result)
        return result
    try:
        client = _openai()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": inp.prompt}],
            temperature=0.2,
        )
        result = {"text": resp.choices[0].message.content}
        _log("generate", inp.prompt, result)
        return result
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - network failures
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/title")
def title(inp: TextIn):
    text = inp.text.strip()
    if MOCK:
        result = {"text": text[:60] or "Untitled"}
        _log("title", inp.text, result)
        return result
    try:
        client = _openai()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return a short, punchy title under 60 chars."},
                {"role": "user", "content": inp.text},
            ],
            temperature=0.1,
        )
        result = {"text": resp.choices[0].message.content.strip()[:60]}
        _log("title", inp.text, result)
        return result
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - network failures
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/summarize")
def summarize(inp: TextIn):
    text = inp.text.strip()
    if MOCK:
        if not text:
            result = {"text": "No content."}
            _log("summarize", inp.text, result)
            return result
        snippet = text[:150]
        if len(text) > 150:
            snippet += "..."
        result = {"text": snippet}
        _log("summarize", inp.text, result)
        return result
    try:
        client = _openai()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Summarize in one clear sentence."},
                {"role": "user", "content": inp.text},
            ],
            temperature=0.2,
        )
        result = {"text": resp.choices[0].message.content.strip()}
        _log("summarize", inp.text, result)
        return result
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - network failures
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/keywords")
def keywords(inp: TextIn):
    if MOCK:
        words = [w.strip(".,!?;:").lower() for w in inp.text.split()]
        uniq = sorted({w for w in words if len(w) > 3})[:8]
        result = {"keywords": uniq}
        _log("keywords", inp.text, result)
        return result
    try:
        client = _openai()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Extract 5–10 key terms as a JSON array of strings."},
                {"role": "user", "content": inp.text},
            ],
            temperature=0.2,
        )
        content = resp.choices[0].message.content
        try:
            data = json.loads(content)
            if not isinstance(data, list):
                raise ValueError("Keywords must be a list")
            keywords_list = [str(item) for item in data]
        except (json.JSONDecodeError, ValueError):
            keywords_list = [kw.strip() for kw in content.split(",") if kw.strip()]
        result = {"keywords": keywords_list}
        _log("keywords", inp.text, result)
        return result
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - network failures
        raise HTTPException(status_code=500, detail=str(exc))


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="ui")


@app.get("/history")
def history(limit: int = 10):
    limited = max(1, min(limit, 100))
    with _db() as con:
        rows = con.execute(
            "SELECT id, mode, input, output, ts FROM logs ORDER BY id DESC LIMIT ?",
            (limited,),
        ).fetchall()

    history_items = []
    for row in rows:
        output_raw = row[3]
        try:
            output_obj: Any = json.loads(output_raw)
        except json.JSONDecodeError:
            output_obj = output_raw
        history_items.append(
            {
                "id": row[0],
                "mode": row[1],
                "input": row[2],
                "output": output_obj,
                "ts": row[4],
            }
        )
    return history_items
