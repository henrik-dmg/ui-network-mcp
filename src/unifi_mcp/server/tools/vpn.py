"""Tools for the VPN servers and the site-to-site tunnels."""

from fastmcp import Context, FastMCP

from unifi_mcp.client import JSON
from unifi_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset, SiteId
from unifi_mcp.server.sites import site_page


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "vpn"})
    async def list_vpn_servers(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the VPN servers of a site.

        Filterable properties include type, id, name, enabled, and metadata.origin.
        """
        return await site_page(ctx, site_id, "vpn/servers", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "vpn"})
    async def list_site_to_site_tunnels(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the site-to-site VPN tunnels of a site.

        Filterable properties include type, id, name, metadata.origin, and metadata.source.
        """
        return await site_page(
            ctx, site_id, "vpn/site-to-site-tunnels", offset, limit, filter
        )
