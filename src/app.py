from fastapi import FastAPI, Request, status
from rate_limit_middleware import RateLimitMiddleware
from contextlib import asynccontextmanager
from redis import asyncio as aioredis
from forward_request import forward_request
import globvar as gv
# Declare a global Redis client variable
redis_client : aioredis.Redis = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = aioredis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
    print("Connected to Redis", await redis_client.ping())
    try:
        yield
    finally:
        await redis_client.close()

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
async def proxy(path: str,request:Request):
    response = await forward_request(gv.upstream, request)
    return response

