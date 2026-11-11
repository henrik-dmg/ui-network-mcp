"""Tools for the console and its sites."""

from fastmcp import Context, FastMCP

from ui_network_mcp.client import JSON
from ui_network_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset
from ui_network_mcp.server.sites import client_of


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read"})
    async def get_application_info(ctx: Context) -> JSON:
        """Get the version of the UniFi Network application. Use it to test the connection."""
        return await client_of(ctx).get("/v1/info")

    @mcp.tool(annotations=READ_ONLY, tags={"read"})
    async def list_sites(
        ctx: Context, filter: Filter = None, limit: Limit = 25, offset: Offset = 0
    ) -> JSON:
        """List the sites on the console. Most other tools need a site ID from this list."""
        return await client_of(ctx).get_page(
            "/v1/sites", offset=offset, limit=limit, filter=filter
        )
