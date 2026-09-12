# resolve_route.py
from config import DEFAULT_CONFIG, ROUTE_CONFIG


def resolve_route(host: str, path: str) -> dict:
    """
    Look up the route config for a given host and path using
    longest-prefix matching, respecting path-segment boundaries
    (so "/api" matches "/api" and "/api/foo" but not "/apikeys").
    Falls back to DEFAULT_CONFIG if no host or no path matches.
    """
    host_config = ROUTE_CONFIG.get(host)

    if not host_config:
        return DEFAULT_CONFIG

    matched = DEFAULT_CONFIG
    max_len = -1

    for route, cfg in host_config.items():
        if route == "/":
            is_match = True
        else:
            is_match = path == route or path.startswith(route + "/")

        if is_match and len(route) > max_len:
            matched = cfg
            max_len = len(route)

    return matched