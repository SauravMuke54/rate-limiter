# config.py
from settings import settings

ROUTE_CONFIG = {
    "localhost": {
        "/": {"upstream": "http://localhost:9100", "limit": 50, "window": 60},
        "/api": {"upstream": "http://localhost:9101", "limit": 2, "window": 60},
    },
    "api.myapp.com": {
        "/login": {"upstream": "http://localhost:9000", "limit": 5, "window": 60},
        "/search": {"upstream": "http://localhost:9001", "limit": 100, "window": 60},
    },
    "admin.myapp.com": {
        "/": {"upstream": "http://localhost:9002", "limit": 20, "window": 60},
    },
}

DEFAULT_CONFIG = {
    "upstream": settings.default_upstream,
    "limit": settings.default_limit,
    "window": settings.default_window,
}