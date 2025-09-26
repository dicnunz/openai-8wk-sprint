from __future__ import annotations

import contextlib
import datetime as _dt
import json
import os
import pathlib
import sqlite3
import typing as t

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI()

MOCK = os.getenv("MOCK_MODE", "0") == "1"
_DB_PATH = pathlib.Path(os.getenv("DB_PATH", "api-log.db")).resolve()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _timestamp() -> str:
    """Return an ISO8601 timestamp ending with Z."""

    return (
        _dt.datetime.now(_dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _init_db() -> None:
    """Initialise the sqlite database if required."""

    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                mode TEXT NOT NULL,
                input TEXT NOT NULL,
                output TEXT NOT NULL
            )
            """
        )


@contextlib.contextmanager
def _db() -> t.Iterator[sqlite3.Connection]:
    """Context manager that yields a sqlite connection."""

    con = sqlite3.connect(_DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _record_log(mode: str, inp: t.Mapping[str, t.Any], out: t.Mapping[str, t.Any]) -> None:
    payload_in = json.dumps(inp, ensure_ascii=False)
    payload_out = json.dumps(out, ensure_ascii=False)
    with _db() as con:
        con.execute(
            "INSERT INTO logs (ts, mode, input, output) VALUES (?, ?, ?, ?)",
            (_timestamp(), mode, payload_in, payload_out),
        )
        con.commit()


def _ensure_api_key() -> None:
    if not client.api_key:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY")


class GenIn(BaseModel):
    prompt: str


class TextIn(BaseModel):
    text: str


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


def _clean_text(value: str) -> str:
    return value.strip()


def _mock_generate(prompt: str) -> str:
    return f"(mock) you said: {prompt}"


def _mock_title(text: str) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return "Untitled"
    words = cleaned.split()
    title = " ".join(words[:12])
    return title[:80]


def _mock_summary(text: str) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return "No content."
    if len(cleaned) <= 150:
        return cleaned
    clipped = cleaned[:150].rstrip()
    return f"{clipped}..."


def _mock_keywords(text: str) -> list[str]:
    import re

    words = re.findall(r"\b\w+\b", text.lower())
    return sorted(set(words))


@app.post("/generate")
def generate(inp: GenIn) -> dict[str, str]:
    if MOCK:
        payload = {"text": _mock_generate(inp.prompt)}
    else:
        _ensure_api_key()
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": inp.prompt}],
                temperature=0.2,
            )
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        payload = {"text": resp.choices[0].message.content}

    _record_log("generate", inp.model_dump(), payload)
    return payload


@app.post("/title")
def title(inp: TextIn) -> dict[str, str]:
    cleaned = _clean_text(inp.text)
    if MOCK:
        result = _mock_title(inp.text)
    else:
        if not cleaned:
            result = "Untitled"
        else:
            _ensure_api_key()
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Provide a concise title."},
                        {"role": "user", "content": cleaned},
                    ],
                    temperature=0.1,
                )
            except Exception as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=500, detail=str(exc)) from exc
            result = resp.choices[0].message.content
    if not cleaned:
        result = "Untitled"
    elif not result.strip():
        result = "Untitled"
    payload = {"text": result}
    _record_log("title", inp.model_dump(), payload)
    return payload


@app.post("/summarize")
def summarize(inp: TextIn) -> dict[str, str]:
    cleaned = _clean_text(inp.text)
    if MOCK:
        summary = _mock_summary(inp.text)
    else:
        if not cleaned:
            summary = "No content."
        else:
            _ensure_api_key()
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Summarize the following text."},
                        {"role": "user", "content": cleaned},
                    ],
                    temperature=0.3,
                )
            except Exception as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=500, detail=str(exc)) from exc
            summary = resp.choices[0].message.content

    payload = {"text": summary if cleaned else "No content."}
    _record_log("summarize", inp.model_dump(), payload)
    return payload


@app.post("/keywords")
def keywords(inp: TextIn) -> dict[str, list[str]]:
    cleaned = _clean_text(inp.text)
    if MOCK:
        words = _mock_keywords(inp.text)
    else:
        if not cleaned:
            words = []
        else:
            _ensure_api_key()
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "Extract distinct keywords as a comma separated list.",
                        },
                        {"role": "user", "content": cleaned},
                    ],
                    temperature=0.0,
                )
            except Exception as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=500, detail=str(exc)) from exc
            words = [w.strip().lower() for w in resp.choices[0].message.content.split(",") if w.strip()]
            words = sorted(dict.fromkeys(words))

    payload = {"keywords": words}
    _record_log("keywords", inp.model_dump(), payload)
    return payload


@app.get("/history")
def history(limit: int = 10) -> list[dict[str, t.Any]]:
    with _db() as con:
        cur = con.execute(
            "SELECT ts, mode, input, output FROM logs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = [
            {
                "ts": row["ts"],
                "mode": row["mode"],
                "input": json.loads(row["input"]),
                "output": json.loads(row["output"]),
            }
            for row in cur.fetchall()
        ]
    return rows


@app.get("/ui")
def ui() -> FileResponse:
    static_dir = pathlib.Path(__file__).parent / "static"
    return FileResponse(static_dir / "index.html")


_init_db()
