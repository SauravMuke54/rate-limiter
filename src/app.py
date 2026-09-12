# main.py
from contextlib import asynccontextmanager

import httpx
import state
from config import DEFAULT_CONFIG
from fastapi import FastAPI, Request, status
from forward_request import forward_request
from rate_limit_middleware import RateLimitMiddleware
from redis import asyncio as aioredis
from settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.redis_client = aioredis.from_url(
        settings.redis_url, encoding="utf-8", decode_responses=True
    )
    print("Connected to Redis", await state.redis_client.ping())

    state.http_client = httpx.AsyncClient(timeout=settings.http_timeout)

    try:
        yield
    finally:
        await state.redis_client.close()
        await state.http_client.aclose()


app = FastAPI(
    title="Rate Limiting API",
    description="An API demonstrating rate limiting with FastAPI.",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan
)

app.add_middleware(RateLimitMiddleware)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    return {"status": "ok"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    upstream = getattr(request.state, "upstream", None) or DEFAULT_CONFIG["upstream"]
    response = await forward_request(upstream, request)
    return response