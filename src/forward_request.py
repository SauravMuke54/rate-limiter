import httpx
from fastapi import Request, Response

async def forward_request(upstream:str,request: Request):
    url = f"{upstream}{request.url.path}"
    headers = dict(request.headers)
    headers.pop("host", None)  # Remove host header to avoid conflicts

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=await request.body(),
            params=request.query_params,
        )

    return Response(content=response.content,status_code=response.status_code,headers=dict(response.headers),media_type=response.headers.get("content-type"))
