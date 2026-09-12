# rate_limit_middleware.py
"""
A middleware component for rate limiting API requests based on the
requested host (from the Host header) and path.
"""
from check_rate_limit import check_rate_limit
from fastapi import Request
from fastapi.responses import JSONResponse
from resolve_route import resolve_route
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):

    EXEMPT_PATHS = {"/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json", "/health"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Use the Host header (the target host the client asked for),
        # not request.client.host (which is the client's IP address).
        hostname = request.headers.get("host", "").split(":")[0] or request.client.host
        print(f"Request from {request.client.host} to {hostname}{path}")

        try:
            route_cfg = resolve_route(hostname, path)
        except Exception as exc:
            print(f"Failed to resolve route for {hostname}{path}: {exc}")
            return JSONResponse(
                status_code=502,
                content={"error": "Unable to resolve upstream route"},
            )

        if not route_cfg:
            return JSONResponse(
                status_code=404,
                content={"error": "No route configured for this host/path"},
            )

        upstream = route_cfg["upstream"]
        limit = route_cfg["limit"]
        window = route_cfg["window"]

        # Make the resolved upstream available to the route handler.
        request.state.upstream = upstream

        key = f"rate_limit:{hostname}:{path}:{request.client.host}"

        allowed, remaining, ttl = await check_rate_limit(
            key=key,
            limit=limit,
            window=window
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": ttl
                },
                headers={
                    "Retry-After": str(ttl)
                }
            )

        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(ttl)
        return response