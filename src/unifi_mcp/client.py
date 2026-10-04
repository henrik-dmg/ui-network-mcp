import asyncio
from typing import Any

import httpx
from fastmcp.exceptions import ToolError

from unifi_mcp.config import Settings

JSON = dict[str, Any]

MAX_PAGE_SIZE = 200


class UniFiAPIError(ToolError):
    """An error response from the UniFi Network API. FastMCP sends the message to the MCP client."""

    def __init__(
        self,
        status_code: int,
        message: str,
        code: str | None = None,
        request_id: str | None = None,
    ):
        self.status_code = status_code
        self.code = code
        self.request_id = request_id
        detail = f"UniFi API error {status_code}"
        if code:
            detail += f" ({code})"
        detail += f": {message}"
        if request_id:
            detail += f" [requestId={request_id}]"
        super().__init__(detail)


class UniFiClient:
    """A thin async wrapper around the UniFi Network integration API."""

    def __init__(self, http: httpx.AsyncClient):
        self._http = http

    @classmethod
    def from_settings(cls, settings: Settings) -> "UniFiClient":
        http = httpx.AsyncClient(
            base_url=settings.resolved_base_url,
            headers={
                "X-API-KEY": settings.api_key.get_secret_value(),
                "Accept": "application/json",
            },
            verify=settings.verify_tls,
            timeout=settings.timeout,
        )
        return cls(http)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        params = {
            key: value for key, value in (params or {}).items() if value is not None
        }
        try:
            response = await self._http.get(path, params=params)
        except httpx.HTTPError as error:
            raise UniFiAPIError(0, f"Request to {path} failed: {error}") from error
        if response.is_error:
            raise _error_from_response(response)
        return response.json()

    async def get_page(
        self, path: str, *, offset: int = 0, limit: int = 25, filter: str | None = None
    ) -> JSON:
        return await self.get(
            path, {"offset": offset, "limit": limit, "filter": filter}
        )

    async def get_all(self, path: str, *, filter: str | None = None) -> list[JSON]:
        """Follow the pagination until all items of a list endpoint are read."""
        items: list[JSON] = []
        while True:
            page = await self.get_page(
                path, offset=len(items), limit=MAX_PAGE_SIZE, filter=filter
            )
            data = page.get("data", [])
            items.extend(data)
            if not data or len(items) >= page.get("totalCount", 0):
                return items

    async def gather_limited(
        self, paths: list[str], concurrency: int = 8, return_errors: bool = False
    ) -> list[Any]:
        """Get many single resources, with a limit on the number of parallel requests.

        If return_errors is true, the result has a UniFiAPIError in place of each failed request.
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch(path: str) -> Any:
            async with semaphore:
                try:
                    return await self.get(path)
                except UniFiAPIError as error:
                    if return_errors:
                        return error
                    raise

        return await asyncio.gather(*(fetch(path) for path in paths))


def _error_from_response(response: httpx.Response) -> UniFiAPIError:
    try:
        body = response.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    return UniFiAPIError(
        status_code=response.status_code,
        message=body.get("message") or response.reason_phrase or response.text[:200],
        code=body.get("code"),
        request_id=body.get("requestId"),
    )
