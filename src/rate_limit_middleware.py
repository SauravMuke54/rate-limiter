# rate_limit_middleware.py
from typing import ClassVar

from api_keys import resolve_client_id
from check_rate_limit import check_rate_limit
from fastapi import Request
from fastapi.responses import JSONResponse
from logging_config import get_logger
from resolve_route import resolve_route
from starlette.middleware.base import BaseHTTPMiddleware

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS: ClassVar[set[str]] = {
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
        "/health",
    }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # --- NEW: authenticate the request ---
        api_key = request.headers.get("x-api-key")
        client_id = resolve_client_id(api_key)
        if client_id is None:
            logger.warning("Rejected request with missing/invalid API key for %s", path)
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or invalid API key"},
            )
        # --------------------------------------

        hostname = request.headers.get("host", "").split(":")[0] or request.client.host
        logger.debug("Incoming request from client=%s to %s%s", client_id, hostname, path)

        try:
            route_cfg = resolve_route(hostname, path)
        except Exception:
            logger.exception("Failed to resolve route for %s%s", hostname, path)
            return JSONResponse(
                status_code=502,
                content={"error": "Unable to resolve upstream route"},
            )

        if not route_cfg:
            logger.warning("No route config found for %s%s", hostname, path)
            return JSONResponse(
                status_code=404,
                content={"error": "No route configured for this host/path"},
            )

        upstream = route_cfg["upstream"]
        limit = route_cfg["limit"]
        window = route_cfg["window"]

        request.state.upstream = upstream

        # --- CHANGED: key by client_id instead of client IP ---
        key = f"rate_limit:{hostname}:{path}:{client_id}"
        # --------------------------------------------------------

        allowed, remaining, ttl = await check_rate_limit(key=key, limit=limit, window=window)

        if not allowed:
            logger.warning(
                "Rate limit exceeded: host=%s path=%s client=%s limit=%s window=%s",
                hostname,
                path,
                client_id,
                limit,
                window,
            )
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": ttl},
                headers={"Retry-After": str(ttl)},
            )

        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(ttl)
        return response
