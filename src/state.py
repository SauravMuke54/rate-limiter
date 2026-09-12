# state.py
from typing import Optional
import httpx
from redis import asyncio as aioredis

redis_client: Optional[aioredis.Redis] = None
http_client: Optional[httpx.AsyncClient] = None