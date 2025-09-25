from __future__ import annotations

import json
import os
from pathlib import Path

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


class GenIn(BaseModel):
    prompt: str


class TextIn(BaseModel):
    text: str


class RewriteIn(BaseModel):
    text: str
    tone: str = "concise"


def _openai():
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY")
    return client


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/generate")
def generate(inp: GenIn):
    if MOCK:
        return {"text": f"(mock) you said: {inp.prompt}"}
    try:
        client = _openai()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": inp.prompt}],
            temperature=0.2,
        )
        return {"text": resp.choices[0].message.content}
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - network failures
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/title")
def title(inp: TextIn):
    text = inp.text.strip()
    if MOCK:
        return {"text": text[:60] or "Untitled"}
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
        return {"text": resp.choices[0].message.content.strip()[:60]}
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - network failures
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/summarize")
def summarize(inp: TextIn):
    text = inp.text.strip()
    if MOCK:
        if not text:
            return {"text": "No content."}
        snippet = text[:150]
        if len(text) > 150:
            snippet += "..."
        return {"text": snippet}
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
        return {"text": resp.choices[0].message.content.strip()}
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - network failures
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/keywords")
def keywords(inp: TextIn):
    if MOCK:
        words = [w.strip(".,!?;:").lower() for w in inp.text.split()]
        uniq = sorted({w for w in words if len(w) > 3})[:8]
        return {"keywords": uniq}
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
        return {"keywords": keywords_list}
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - network failures
        raise HTTPException(status_code=500, detail=str(exc))


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="ui")
