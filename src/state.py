# state.py

import httpx
from redis import asyncio as aioredis

redis_client: aioredis.Redis | None = None
http_client: httpx.AsyncClient | None = None
