import time
import state

with open("script.lua", "r") as file:
    SCRIPT = file.read()

_rate_limit_script = None


def _get_script():
    global _rate_limit_script
    if _rate_limit_script is None:
        if state.redis_client is None:
            raise RuntimeError("redis_client is not initialized yet")
        _rate_limit_script = state.redis_client.register_script(SCRIPT)
    return _rate_limit_script


async def check_rate_limit(key: str, limit: int, window: int):
    try:
        script = _get_script()
        now_ms = int(time.time() * 1000)
        current, ttl_ms = await script(
            keys=[key],
            args=[window, limit, now_ms]
        )
        current = int(current)
        ttl_ms = int(ttl_ms)
    except Exception as exc:
        print(f"[check_rate_limit] Redis error, failing open: {exc}")
        return True, limit, window

    allowed = current <= limit
    remaining = max(0, limit - current)
    ttl_seconds = max(0, ttl_ms // 1000)  # convert ms -> s for headers

    return allowed, remaining, ttl_seconds