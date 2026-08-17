import pytest

from backend.crawler import validate_url


def test_private_ipv4_is_blocked(monkeypatch):
    monkeypatch.setattr(
        "backend.crawler.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 80))],
    )
    with pytest.raises(ValueError, match="private or special-use"):
        validate_url("http://example.com/")


def test_private_ipv6_is_blocked(monkeypatch):
    monkeypatch.setattr(
        "backend.crawler.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("::1", 80))],
    )
    with pytest.raises(ValueError, match="private or special-use"):
        validate_url("http://example.com/")


def test_localhost_hostname_is_blocked():
    with pytest.raises(ValueError, match="local hostnames"):
        validate_url("http://localhost:8000/")


def test_non_http_scheme_is_blocked():
    with pytest.raises(ValueError, match="only http and https"):
        validate_url("file:///etc/passwd")


def test_embedded_credentials_are_blocked():
    with pytest.raises(ValueError, match="embedded credentials"):
        validate_url("https://user:password@example.com/")


def test_public_host_is_allowed(monkeypatch):
    monkeypatch.setattr(
        "backend.crawler.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    assert validate_url("https://example.com/path?x=1") == "https://example.com/path?x=1"
