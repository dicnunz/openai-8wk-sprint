import os
import pathlib

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ["MOCK_MODE"] = "1"

# Load app from file so the hyphen in app-api is not a problem
from importlib.machinery import SourceFileLoader

mod = SourceFileLoader("app_mod", str(pathlib.Path("app-api/main.py").resolve())).load_module()

from fastapi.testclient import TestClient

client = TestClient(mod.app)


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_generate_mock():
    response = client.post("/generate", json={"prompt": "hi"})
    assert response.status_code == 200
    assert "(mock)" in response.json()["text"]
