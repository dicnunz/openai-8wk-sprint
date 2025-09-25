import os
import pathlib

import pytest
from importlib.machinery import SourceFileLoader
from fastapi.testclient import TestClient

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["MOCK_MODE"] = "1"

DB_FILE = pathlib.Path("tests/api-log.db")
if DB_FILE.exists():
    DB_FILE.unlink()
os.environ["DB_PATH"] = str(DB_FILE)

mod = SourceFileLoader("app_mod", str(pathlib.Path("app-api/main.py").resolve())).load_module()
client = TestClient(mod.app)


@pytest.fixture(autouse=True)
def clear_logs():
    mod._init_db()  # type: ignore[attr-defined]
    with mod._db() as con:  # type: ignore[attr-defined]
        con.execute("DELETE FROM logs")
    yield


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_generate_mock():
    response = client.post("/generate", json={"prompt": "hi"})
    assert response.status_code == 200
    assert "(mock)" in response.json()["text"]


def test_title_mock():
    response = client.post("/title", json={"text": "hello world"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["text"].startswith("hello")


def test_title_blank_defaults():
    response = client.post("/title", json={"text": "   "})
    assert response.status_code == 200
    assert response.json()["text"] == "Untitled"


def test_summarize_mock_truncates():
    text = "lorem " * 100
    response = client.post("/summarize", json={"text": text})
    assert response.status_code == 200
    summary = response.json()["text"]
    assert summary.endswith("...")
    assert len(summary) <= 153


def test_summarize_blank():
    response = client.post("/summarize", json={"text": ""})
    assert response.status_code == 200
    assert response.json()["text"] == "No content."


def test_keywords_mock():
    response = client.post("/keywords", json={"text": "alpha beta gamma delta alpha"})
    assert response.status_code == 200
    keywords = response.json()["keywords"]
    assert sorted(keywords) == keywords  # alphabetical order in mock mode
    assert "alpha" in keywords and len(keywords) == len(set(keywords))


def test_static_ui_served():
    response = client.get("/ui")
    assert response.status_code == 200
    assert "<select" in response.text


def test_history_empty_when_no_calls():
    response = client.get("/history")
    assert response.status_code == 200
    assert response.json() == []


def test_history_records_latest_calls():
    client.post("/generate", json={"prompt": "one"})
    client.post("/title", json={"text": "second title"})
    response = client.get("/history", params={"limit": 5})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    first = payload[0]
    assert first["mode"] == "title"
    assert first["output"]["text"].startswith("second")
    assert first["ts"].endswith("Z")
    assert payload[1]["mode"] == "generate"
