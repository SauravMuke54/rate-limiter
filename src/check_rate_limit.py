# from app import redis_client
from redis import asyncio as aioredis

with open("script.lua", "r") as file:
    SCRIPT = file.read()

redis_client = aioredis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)

rate_limit_script = redis_client.register_script(SCRIPT)

async def check_rate_limit(key: str , limit:int, window:int):

    current , ttl = await rate_limit_script(
        keys=[key],
        args=[window]
    )

    current = int(current)
    ttl = int(ttl)

    allowed = current <= limit
    remaining = max(0, limit - current)

    return allowed, remaining, ttl
