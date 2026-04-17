"""HTTP — make HTTP requests on behalf of the persona."""

import httpx

from application.platform.tool import tool


@tool("Make an HTTP request to a URL. Use for fetching web pages, calling APIs, "
      "downloading content, or checking if a service is reachable. "
      "Returns the response body as text. For binary content, returns a summary of the response.")
async def request(method: str, url: str, body: str = "", headers: str = "") -> str:
    """Make an HTTP request and return the response text.

    method: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS.
    url: the full URL to request.
    body: request body as a string (for POST/PUT/PATCH). Empty string for no body.
    headers: headers as key:value pairs separated by newlines. Empty string for no extra headers.
    """
    parsed_headers = {}
    if headers:
        for line in headers.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                parsed_headers[key.strip()] = value.strip()

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                content=body if body else None,
                headers=parsed_headers if parsed_headers else None,
            )
            content_type = response.headers.get("content-type", "")
            if "text" in content_type or "json" in content_type or "xml" in content_type:
                return f"[{response.status_code}] {response.text[:10000]}"
            return f"[{response.status_code}] Binary response, {len(response.content)} bytes, content-type: {content_type}"
    except httpx.ConnectError as e:
        return f"[error] Could not connect: {e}"
    except httpx.TimeoutException:
        return "[error] Request timed out after 30 seconds"
    except Exception as e:
        return f"[error] {e}"
