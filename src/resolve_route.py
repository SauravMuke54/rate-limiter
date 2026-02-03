from config import ROUTE_CONFIG, DEFAULT_CONFIG

def resolve_route(host: str, path: str):
    host_config = ROUTE_CONFIG.get(host)

    if not host_config:
        return DEFAULT_CONFIG

    # longest prefix match
    matched = DEFAULT_CONFIG
    max_len = 0

    for route, cfg in host_config.items():
        if path.startswith(route) and len(route) > max_len:
            matched = cfg
            max_len = len(route)

    return matched
