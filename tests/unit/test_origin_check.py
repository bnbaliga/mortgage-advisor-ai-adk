"""The /ws origin check: same-origin pages and listed origins only."""
from mortgage_advisor.api import routes


def test_no_origin_header_is_allowed():
    assert routes.origin_allowed(None, "api.example.com")


def test_same_origin_is_allowed():
    assert routes.origin_allowed("https://api.example.com", "api.example.com")


def test_listed_origin_is_allowed(monkeypatch):
    monkeypatch.setattr(routes, "ALLOWED_ORIGINS", ["https://my-project.web.app"])
    assert routes.origin_allowed("https://my-project.web.app/", "backend.run.app")


def test_unlisted_origin_is_rejected(monkeypatch):
    monkeypatch.setattr(routes, "ALLOWED_ORIGINS", ["https://my-project.web.app"])
    assert not routes.origin_allowed("https://evil.example", "backend.run.app")
