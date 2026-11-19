"""API smoke tests: the app starts, serves its JSON endpoints and the frontend.

No Gemini call is made; the live WebSocket path needs a real API key and is
covered by manual or live smoke tests.
"""
from fastapi.testclient import TestClient

from mortgage_advisor.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["model"] and body["voice"]


def test_company():
    r = client.get("/api/company")
    assert r.status_code == 200
    body = r.json()
    assert body["company"] == "HomeFirst AI Lending"
    assert body["agent"] == "Mac"


def test_products():
    r = client.get("/api/products")
    assert r.status_code == 200
    assert "heloc" in r.json()["products"]


def test_usage_totals():
    r = client.get("/api/usage")
    assert r.status_code == 200
    assert "calls" in r.json()


def test_frontend_is_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "Mac" in r.text
    assert client.get("/main.js").status_code == 200
