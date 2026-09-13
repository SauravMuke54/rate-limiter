# tests/test_resolve_route.py
"""
Tests for resolve_route.py — longest-prefix matching and path-segment
boundary logic. Uses a fixed test-only route config (via monkeypatch)
so these tests never break when config.py's real upstreams change
(e.g. swapping in local mock upstreams for load testing).
"""
import pytest
import resolve_route as resolve_route_module
from resolve_route import resolve_route

TEST_ROUTE_CONFIG = {
    "localhost": {
        "/": {"upstream": "http://catchall-upstream", "limit": 50, "window": 60},
        "/api": {"upstream": "http://api-upstream", "limit": 2, "window": 60},
    },
    "api.myapp.com": {
        "/login": {"upstream": "http://login-upstream", "limit": 5, "window": 60},
        "/search": {"upstream": "http://search-upstream", "limit": 100, "window": 60},
    },
    "admin.myapp.com": {
        "/": {"upstream": "http://admin-upstream", "limit": 20, "window": 60},
    },
}

TEST_DEFAULT_CONFIG = {
    "upstream": "http://default-upstream",
    "limit": 2,
    "window": 60,
}


@pytest.fixture(autouse=True)
def use_test_config(monkeypatch):
    """Point resolve_route at a fixed test config, independent of config.py's real values."""
    monkeypatch.setattr(resolve_route_module, "ROUTE_CONFIG", TEST_ROUTE_CONFIG)
    monkeypatch.setattr(resolve_route_module, "DEFAULT_CONFIG", TEST_DEFAULT_CONFIG)


def test_exact_match():
    cfg = resolve_route("api.myapp.com", "/login")
    assert cfg["upstream"] == "http://login-upstream"
    assert cfg["limit"] == 5


def test_unknown_host_returns_default():
    cfg = resolve_route("unknown-host.com", "/anything")
    assert cfg == TEST_DEFAULT_CONFIG


def test_unknown_path_falls_back_to_default_when_no_catchall():
    cfg = resolve_route("api.myapp.com", "/nonexistent")
    assert cfg == TEST_DEFAULT_CONFIG


def test_catchall_route_matches_unregistered_path():
    cfg = resolve_route("localhost", "/some/random/path")
    assert cfg["upstream"] == "http://catchall-upstream"


def test_prefix_boundary_falls_back_to_catchall_not_similar_route():
    """Regression test: '/api' must NOT match '/apikeys'."""
    cfg = resolve_route("localhost", "/apikeys")
    assert cfg["upstream"] == "http://catchall-upstream"


def test_prefix_match_with_trailing_segment():
    cfg = resolve_route("localhost", "/api/v1/foo")
    assert cfg["upstream"] == "http://api-upstream"
    assert cfg["limit"] == 2


def test_prefix_exact_no_trailing_slash_still_matches():
    cfg = resolve_route("localhost", "/api")
    assert cfg["upstream"] == "http://api-upstream"


def test_longest_prefix_wins_over_catchall():
    cfg = resolve_route("localhost", "/api")
    assert cfg["upstream"] == "http://api-upstream"


def test_admin_host_catchall():
    cfg = resolve_route("admin.myapp.com", "/dashboard")
    assert cfg["upstream"] == "http://admin-upstream"
    assert cfg["limit"] == 20