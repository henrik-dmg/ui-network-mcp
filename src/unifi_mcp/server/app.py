from collections.abc import AsyncIterator, Callable
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from unifi_mcp.client import UniFiClient
from unifi_mcp.config import Settings
from unifi_mcp.server.tools import register_all

INSTRUCTIONS = """\
Tools for the UniFi Network API of one UniFi console.
Most tools operate on one site. If you omit site_id, the server uses the configured default site,
or the only site when the console has exactly one. Call list_sites to find site IDs.
Call get_topology first for an overview of how the devices of a site connect.
Call get_site_health for a quick status, and get_firewall_overview to explain what traffic
the firewall allows or blocks.
"""


def build_server(
    client_factory: Callable[[], UniFiClient], default_site_id: str | None = None
) -> FastMCP:
    @lifespan
    async def unifi_lifespan(_server: FastMCP) -> AsyncIterator[dict[str, Any]]:
        client = client_factory()
        try:
            yield {"client": client, "default_site_id": default_site_id}
        finally:
            await client.aclose()

    mcp = FastMCP("UniFi Network", instructions=INSTRUCTIONS, lifespan=unifi_lifespan)
    register_all(mcp)
    return mcp


def create_server() -> FastMCP:
    settings = Settings()
    return build_server(
        lambda: UniFiClient.from_settings(settings), settings.default_site_id
    )
