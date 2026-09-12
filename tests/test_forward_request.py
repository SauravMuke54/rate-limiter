"""
Tests for forward_request.py — header sanitization and error handling
when the upstream is unreachable or times out.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from fastapi import Request
import state
from forward_request import forward_request


def make_mock_request(method="GET", path="/foo", headers=None, body=b""):
    headers = headers or {"host": "localhost", "x-api-key": "abc123"}
    req = MagicMock(spec=Request)
    req.method = method
    req.url.path = path
    req.headers = headers
    req.query_params = {}
    req.body = AsyncMock(return_value=body)
    return req


@pytest.mark.asyncio
async def test_strips_hop_by_hop_response_headers():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"ok": true}'
    mock_response.headers = {
        "content-type": "application/json",
        "content-length": "9999",  # stale upstream value
        "content-encoding": "gzip",
        "connection": "keep-alive",
        "x-custom-header": "keep-me",
    }

    state.http_client = AsyncMock()
    state.http_client.request = AsyncMock(return_value=mock_response)

    request = make_mock_request()
    response = await forward_request("http://upstream", request)

    # content-length is recomputed by Starlette based on actual content,
    # NOT the stale value from the upstream — this is correct behavior.
    assert response.headers["content-length"] == str(len(mock_response.content))
    assert "content-encoding" not in response.headers
    assert "connection" not in response.headers
    assert response.headers.get("x-custom-header") == "keep-me"


@pytest.mark.asyncio
async def test_host_header_removed_before_forwarding():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b""
    mock_response.headers = {}

    state.http_client = AsyncMock()
    state.http_client.request = AsyncMock(return_value=mock_response)

    request = make_mock_request(headers={"host": "localhost", "x-api-key": "abc123"})
    await forward_request("http://upstream", request)

    sent_headers = state.http_client.request.call_args.kwargs["headers"]
    assert "host" not in sent_headers
    assert sent_headers["x-api-key"] == "abc123"


@pytest.mark.asyncio
async def test_returns_504_on_timeout():
    state.http_client = AsyncMock()
    state.http_client.request = AsyncMock(
        side_effect=httpx.TimeoutException("timed out")
    )

    request = make_mock_request()
    response = await forward_request("http://upstream", request)

    assert response.status_code == 504


@pytest.mark.asyncio
async def test_returns_502_on_connect_error():
    state.http_client = AsyncMock()
    state.http_client.request = AsyncMock(side_effect=httpx.ConnectError("refused"))

    request = make_mock_request()
    response = await forward_request("http://upstream", request)

    assert response.status_code == 502
