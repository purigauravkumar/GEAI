import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.security import api_key_middleware


app = FastAPI()
app.middleware("http")(api_key_middleware)


@app.get("/")
def root():
    return {"ok": True}


@app.get("/protected")
def protected():
    return {"ok": True}


def test_missing_key_configuration_returns_503(monkeypatch):
    monkeypatch.delenv("GEAI_API_KEY", raising=False)
    client = TestClient(app)
    response = client.get("/protected")
    assert response.status_code == 503


def test_invalid_key_returns_401(monkeypatch):
    monkeypatch.setenv("GEAI_API_KEY", "correct-secret")
    client = TestClient(app)
    response = client.get(
        "/protected",
        headers={"X-GEAI-API-Key": "wrong-secret"},
    )
    assert response.status_code == 401


def test_valid_key_is_accepted(monkeypatch):
    monkeypatch.setenv("GEAI_API_KEY", "correct-secret")
    client = TestClient(app)
    response = client.get(
        "/protected",
        headers={"X-GEAI-API-Key": "correct-secret"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_public_root_does_not_require_key(monkeypatch):
    monkeypatch.delenv("GEAI_API_KEY", raising=False)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
