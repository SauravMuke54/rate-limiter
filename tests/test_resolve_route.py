"""
Tests for resolve_route.py — specifically the longest-prefix matching
and path-segment boundary logic that was buggy in earlier iterations.
"""

import pytest
from resolve_route import resolve_route
from config import ROUTE_CONFIG, DEFAULT_CONFIG


def test_exact_match():
    cfg = resolve_route("api.myapp.com", "/login")
    assert cfg["upstream"] == "http://auth-service:9000"
    assert cfg["limit"] == 5


def test_unknown_host_returns_default():
    cfg = resolve_route("unknown-host.com", "/anything")
    assert cfg == DEFAULT_CONFIG


def test_unknown_path_falls_back_to_default_when_no_catchall():
    # api.myapp.com has no "/" catch-all route
    cfg = resolve_route("api.myapp.com", "/nonexistent")
    assert cfg == DEFAULT_CONFIG


def test_catchall_route_matches_unregistered_path():
    # localhost has a "/" route which should catch anything not more specific
    cfg = resolve_route("localhost", "/some/random/path")
    assert cfg["upstream"] == "http://local-service:8000"


def test_prefix_boundary_falls_back_to_catchall_not_similar_route():
    """
    /apikeys on localhost should hit the "/" catch-all (local-service),
    not the "/api" route (google.com), since it's not actually under /api.
    """
    cfg = resolve_route("localhost", "/apikeys")
    assert cfg["upstream"] == "http://local-service:8000"


def test_prefix_match_with_trailing_segment():
    cfg = resolve_route("localhost", "/api/v1/foo")
    assert cfg["upstream"] == "http://google.com"
    assert cfg["limit"] == 2


def test_prefix_exact_no_trailing_slash_still_matches():
    cfg = resolve_route("localhost", "/api")
    assert cfg["upstream"] == "http://google.com"


def test_longest_prefix_wins_over_catchall():
    cfg = resolve_route("localhost", "/api")
    # "/api" (len 4) should win over "/" (len 1, catch-all)
    assert cfg["upstream"] == "http://google.com"


def test_admin_host_catchall():
    cfg = resolve_route("admin.myapp.com", "/dashboard")
    assert cfg["upstream"] == "http://admin-service:9002"
    assert cfg["limit"] == 20
