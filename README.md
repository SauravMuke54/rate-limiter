# Rate Limiter

A production-oriented rate-limiting reverse proxy built with FastAPI, Redis, and Lua scripting. It sits in front of your backend services, enforces per-host/per-route/per-client request limits atomically in Redis, and forwards allowed traffic upstream.

## Features

- Sliding-window rate limiting via a Redis Lua script (atomic, no race conditions, no boundary-burst issue of naive fixed windows)
- Per-host, per-path routing configuration with longest-prefix matching
- Reverse proxy forwarding to configurable upstream services
- Fails open on Redis errors — a Redis outage doesn't take down the whole API
- `X-RateLimit-*` response headers for observability
- Fully async (FastAPI + httpx + redis.asyncio)
- Test suite (pytest) and CI (GitHub Actions: ruff format, ruff check, pytest)

## How it works

1. A request hits the proxy.
2. `RateLimitMiddleware` resolves the target host + path to a route config (upstream, limit, window).
3. It runs a Redis Lua script atomically: evicts expired entries from a sliding window, counts requests in the current window, and either records this request or rejects it.
4. If the limit is exceeded → `429 Too Many Requests` with a `Retry-After` header.
5. Otherwise → the request is forwarded to the resolved upstream via `httpx`, and the response is returned with rate-limit headers attached.

## Architecture

```
Client
  │
  ▼
Rate Limiter (FastAPI + Middleware)
  │
  ├── resolve_route()  →  per-host/path config (upstream, limit, window)
  ├── Redis (sliding-window Lua script)  →  allow / reject
  │
  └── forward_request()  →  Backend Service (via httpx)
```

## Project layout

```
rate_limiter/
├── pyproject.toml
├── .github/workflows/ci.yml
├── src/
│   ├── app.py                   # FastAPI app + proxy route
│   ├── settings.py              # env-driven config
│   ├── config.py                # ROUTE_CONFIG / DEFAULT_CONFIG
│   ├── state.py                 # shared Redis + httpx clients
│   ├── resolve_route.py         # host/path → route config resolution
│   ├── check_rate_limit.py      # Lua script invocation + fail-open handling
│   ├── rate_limit_middleware.py # request pipeline
│   ├── forward_request.py       # upstream proxying
│   ├── logging_config.py
│   └── script.lua               # sliding-window rate limit script
└── tests/
    ├── test_resolve_route.py
    ├── test_check_rate_limit.py
    ├── test_middleware.py
    └── test_forward_request.py
```

## Getting started

### 1. Install dependencies (Poetry)

```bash
poetry install --with dev
```

### 2. Start Redis

```bash
docker run --name my-redis -p 6379:6379 -d redis
```

If a container with that name already exists:

```bash
docker start my-redis
```

### 3. Configure environment (optional)

Defaults work out of the box; override via env vars or a `.env` file:

```
REDIS_URL=redis://localhost
HTTP_TIMEOUT=10.0
DEFAULT_UPSTREAM=http://www.google.com
DEFAULT_LIMIT=2
DEFAULT_WINDOW=60
LOG_LEVEL=INFO
```

### 4. Run the proxy

```bash
poetry run uvicorn app:app --app-dir src --reload
```

The API docs are available at `http://127.0.0.1:8000/api/v1/docs`.

## Routing configuration

Routes are defined per-host in `src/config.py`, matched by longest path prefix (respecting path-segment boundaries — `/api` matches `/api` and `/api/foo`, but not `/apikeys`):

```python
ROUTE_CONFIG = {
    "api.myapp.com": {
        "/login": {"upstream": "http://auth-service:9000", "limit": 5, "window": 60},
        "/search": {"upstream": "http://search-service:9001", "limit": 100, "window": 60},
    },
}
```

Unmatched hosts/paths fall back to `DEFAULT_CONFIG`.

## Redis key strategy

```
rate_limit:{hostname}:{path}:{client_ip}
```

Each key backs a Redis sorted set used by the sliding-window script — members are timestamped requests, evicted once they fall outside the configured window.

## Why Redis + Lua?

- A single Lua script executes atomically in Redis — no race conditions between reading and updating the count, even under concurrent requests.
- The sliding-window approach (vs. fixed-window) avoids allowing a burst of `2x limit` requests around a window boundary.
- Fast enough to sit in the hot path of every request without material latency.

## Running tests

```bash
poetry run pytest -v
```

## Linting & formatting

```bash
poetry run ruff format --check src
poetry run ruff check src
```

(`tests/` is intentionally excluded from ruff via `extend-exclude` in `pyproject.toml`.)

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR to `main`:
- `ruff format --check`
- `ruff check`
- `pytest`

## Authentication

All non-exempt routes require an `X-API-Key` header. Keys are managed in `src/api_keys.py`.

## Performance & Load Testing

The proxy was load-tested using k6 with a ramp-up scenario reaching 200 virtual users and a concurrent burst scenario, with all requests authenticated via a valid API key.

**[View detailed k6 HTML report](./loadtests/report.html)**

### Results

| Metric          |        Result |
| --------------- | ------------: |
| Total requests  |    **71,229** |
| Throughput      | **547 req/s** |
| 200 Allowed     |       **224** |
| 429 Rejected    |    **71,005** |
| 5xx Errors      |         **0** |
| Unexpected Status |       **0** |
| p50 Latency     |    **2.0 ms** |
| p95 Latency     |    **9.3 ms** |
| p99 Latency     |   **22.9 ms** |
| Max Latency     |  **175.6 ms** |
| Check Pass Rate |      **100%** |

All configured k6 thresholds passed — zero unhandled server errors, sub-second latency at all percentiles, and correct enforcement of both authentication and rate limits under sustained concurrent load.

## Known limitations

- **Authentication**: all non-exempt routes require a valid `X-API-Key` header, checked against `src/api_keys.py`. This closes the IP-spoofing gap (rate limits are keyed by authenticated `client_id`, not client IP), but key management is currently a hardcoded dict — no expiry, rotation, revocation, or per-key scoping (any valid key can call any route). Not yet backed by a secrets manager or database.
- **Public/unauthenticated traffic**: the design assumes every route requires a key. If a genuinely public endpoint is ever added, it will need its own identity/rate-limiting strategy, since there's currently no fallback for unauthenticated callers.
- **Transport security**: API keys are sent as plain headers — this depends on TLS being terminated in front of the proxy (e.g. by a load balancer). The proxy itself doesn't enforce or verify HTTPS.
- **Redis**: single instance, no HA/clustering configured. A Redis outage is handled gracefully (rate limiter fails open rather than 500ing), but there's no automatic failover.

## Contact

Saurav Muke — saurav54muke@gmail.com
