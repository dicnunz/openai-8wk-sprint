from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os

app = FastAPI()
MOCK = os.getenv("MOCK_MODE", "0") == "1"
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None


class GenIn(BaseModel):
    prompt: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/generate")
def generate(inp: GenIn):
    if MOCK:
        return {"text": f"(mock) you said: {inp.prompt}"}
    if not client:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY")
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": inp.prompt}],
            temperature=0.2,
        )
        return {"text": resp.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
