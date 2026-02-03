# config.py

ROUTE_CONFIG = {
    "localhost":{
        "/": {
            "upstream": "http://local-service:8000",
            "limit": 50,
            "window": 60
        },
        "/api": {
            "upstream": "http://google.com",
            "limit": 2,
            "window": 60
        }
    },
    "api.myapp.com": {
        "/login": {
            "upstream": "http://auth-service:9000",
            "limit": 5,
            "window": 60
        },
        "/search": {
            "upstream": "http://search-service:9001",
            "limit": 100,
            "window": 60
        }
    },
    "admin.myapp.com": {
        "/": {
            "upstream": "http://admin-service:9002",
            "limit": 20,
            "window": 60
        }
    }
}

DEFAULT_CONFIG = {
    "upstream": "http://www.google.com",
    "limit": 2,
    "window": 60
}
