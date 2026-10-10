"""Tools for the Wi-Fi broadcasts."""

from fastmcp import Context, FastMCP

from unifi_mcp.client import JSON
from unifi_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset, SiteId
from unifi_mcp.server.sites import site_item, site_page


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "wifi"})
    async def list_wifi_broadcasts(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the Wi-Fi networks (SSIDs) of a site."""
        return await site_page(ctx, site_id, "wifi/broadcasts", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "wifi"})
    async def get_wifi_broadcast(
        ctx: Context, wifi_broadcast_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get the full configuration of one Wi-Fi broadcast: network, security, bands, and devices."""
        return await site_item(ctx, site_id, "wifi/broadcasts", wifi_broadcast_id)
