# forward_request.py
import httpx
from fastapi import Request, Response
from logging_config import get_logger
import state

logger = get_logger(__name__)

EXCLUDED_RESPONSE_HEADERS = {
    "content-encoding",
    "content-length",
    "transfer-encoding",
    "connection",
}


async def forward_request(upstream: str, request: Request) -> Response:
    url = f"{upstream}{request.url.path}"
    headers = dict(request.headers)
    headers.pop("host", None)

    try:
        response = await state.http_client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=await request.body(),
            params=request.query_params,
        )
    except httpx.TimeoutException:
        logger.error("Upstream timeout: %s %s", request.method, url)
        return Response(content=b"Upstream request timed out", status_code=504)
    except httpx.ConnectError:
        logger.error("Upstream connection failed: %s %s", request.method, url)
        return Response(content=b"Could not connect to upstream", status_code=502)
    except httpx.HTTPError as exc:
        logger.error(
            "Upstream request failed: %s %s - %s",
            request.method,
            url,
            exc,
            exc_info=True,
        )
        return Response(
            content=f"Upstream request failed: {exc}".encode(), status_code=502
        )

    response_headers = {
        k: v
        for k, v in response.headers.items()
        if k.lower() not in EXCLUDED_RESPONSE_HEADERS
    }

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("content-type"),
    )
