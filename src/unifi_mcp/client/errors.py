import httpx
from fastmcp.exceptions import ToolError


class UniFiAPIError(ToolError):
    """An error response from the UniFi Network API. FastMCP sends the message to the MCP client."""

    def __init__(
        self,
        status_code: int,
        message: str,
        code: str | None = None,
        request_id: str | None = None,
        hint: str | None = None,
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
        if hint:
            detail += f" {hint}"
        super().__init__(detail)

    @classmethod
    def from_response(cls, response: httpx.Response) -> UniFiAPIError:
        """Make an error from an error response. The body of the response is optional."""
        try:
            body = response.json()
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}
        hint = None
        if response.status_code in (401, 403) and response.request.method != "GET":
            hint = "Make sure that the API key has write access."
        return cls(
            status_code=response.status_code,
            message=body.get("message")
            or response.reason_phrase
            or response.text[:200],
            code=body.get("code"),
            request_id=body.get("requestId"),
            hint=hint,
        )
