"""
A middleware component for rate limiting API requests based on user hosts.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from check_rate_limit import check_rate_limit
from resolve_route import resolve_route
from forward_request import forward_request
import globvar as gv

class RateLimitMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        """
            Middleware to limit the rate of incoming requests based on client IP.
        """
        hostname = request.client.host
        path = request.url.path
        print(f"Request from {hostname} to {path}")

        if path in ["/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json", "/health"]:
            return await call_next(request)

        key = f"rate_limit:{path}:{hostname}"

        route_cfg = resolve_route(hostname, path)

        gv.upstream = route_cfg["upstream"]
        gv.limit = route_cfg["limit"]
        gv.window = route_cfg["window"]


        allowed, remaining, ttl = await check_rate_limit(
            key=key,
            limit=gv.limit,
            window=gv.window
        ) 
        
        if not allowed:
            return JSONResponse(status_code=429, content={
                    "error": "Rate limit exceeded",
                    "retry_after": ttl
                },
                headers={
                    "Retry-After": str(ttl)
                })
        
        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(5)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(ttl)
        return response


        

