# check_rate_limit.py
import os
import time

import state
from logging_config import get_logger

logger = get_logger(__name__)

_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "script.lua")

with open(_SCRIPT_PATH, "r") as file:
    SCRIPT = file.read()

_rate_limit_script = None


def _get_script():
    global _rate_limit_script
    if _rate_limit_script is None:
        if state.redis_client is None:
            raise RuntimeError("redis_client is not initialized yet")  # noqa: TRY003
        _rate_limit_script = state.redis_client.register_script(SCRIPT)
    return _rate_limit_script


async def check_rate_limit(key: str, limit: int, window: int):
    try:
        script = _get_script()
        now_ms = int(time.time() * 1000)
        current, ttl_ms = await script(keys=[key], args=[window, limit, now_ms])
        current = int(current)
        ttl_ms = int(ttl_ms)
    except Exception:
        logger.exception("Rate limiter failed, failing open for key=%s", key)
        return True, limit, window

    allowed = current <= limit
    remaining = max(0, limit - current)
    ttl_seconds = max(0, ttl_ms // 1000)

    return allowed, remaining, ttl_seconds
