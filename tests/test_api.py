import os
import pathlib

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["MOCK_MODE"] = "1"

from importlib.machinery import SourceFileLoader

from fastapi.testclient import TestClient

mod = SourceFileLoader("app_mod", str(pathlib.Path("app-api/main.py").resolve())).load_module()
client = TestClient(mod.app)


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
