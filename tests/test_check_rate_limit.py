# tests/test_check_rate_limit.py
import pytest
from unittest.mock import AsyncMock, MagicMock
import check_rate_limit
import state


@pytest.fixture(autouse=True)
def reset_script_cache():
    check_rate_limit._rate_limit_script = None
    yield
    check_rate_limit._rate_limit_script = None


def make_mock_redis_client(script_return_value=None, script_side_effect=None):
    """
    register_script() is SYNCHRONOUS in redis.asyncio and returns a
    callable Script object; only calling that Script object is async.
    """
    mock_script = AsyncMock(
        return_value=script_return_value, side_effect=script_side_effect
    )
    mock_client = MagicMock()  # not AsyncMock — register_script itself is sync
    mock_client.register_script = MagicMock(return_value=mock_script)
    return mock_client, mock_script


@pytest.mark.asyncio
async def test_allows_request_under_limit():
    state.redis_client, _ = make_mock_redis_client(script_return_value=(3, 45000))

    allowed, remaining, ttl = await check_rate_limit.check_rate_limit(
        key="test:key", limit=5, window=60
    )

    assert allowed is True
    assert remaining == 2  # 5 - 3
    assert ttl == 45


@pytest.mark.asyncio
async def test_rejects_request_over_limit():
    state.redis_client, _ = make_mock_redis_client(script_return_value=(6, 30000))

    allowed, remaining, ttl = await check_rate_limit.check_rate_limit(
        key="test:key", limit=5, window=60
    )

    assert allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_fails_open_on_redis_error():
    state.redis_client, _ = make_mock_redis_client(
        script_side_effect=ConnectionError("Redis unreachable")
    )

    allowed, remaining, ttl = await check_rate_limit.check_rate_limit(
        key="test:key", limit=5, window=60
    )

    assert allowed is True
    assert remaining == 5
    assert ttl == 60


@pytest.mark.asyncio
async def test_fails_open_on_malformed_script_result():
    state.redis_client, _ = make_mock_redis_client(
        script_return_value=("not_a_number", "also_not_a_number")
    )

    allowed, remaining, ttl = await check_rate_limit.check_rate_limit(
        key="test:key", limit=5, window=60
    )

    assert allowed is True


@pytest.mark.asyncio
async def test_raises_if_redis_client_never_initialized():
    state.redis_client = None
    check_rate_limit._rate_limit_script = None

    allowed, remaining, ttl = await check_rate_limit.check_rate_limit(
        key="test:key", limit=5, window=60
    )
    assert allowed is True
