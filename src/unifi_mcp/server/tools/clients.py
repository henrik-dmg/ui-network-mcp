"""Tools for the connected clients."""

from fastmcp import Context, FastMCP

from unifi_mcp.client import JSON
from unifi_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset, SiteId
from unifi_mcp.server.sites import site_item, site_page


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "clients"})
    async def list_clients(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the connected clients of a site: wired, wireless, VPN, and Teleport.

        Filterable properties include type (WIRED, WIRELESS, VPN, TELEPORT), macAddress, ipAddress,
        connectedAt, and access.type.
        """
        return await site_page(ctx, site_id, "clients", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "clients"})
    async def get_client(ctx: Context, client_id: str, site_id: SiteId = None) -> JSON:
        """Get the details of one connected client."""
        return await site_item(ctx, site_id, "clients", client_id)
