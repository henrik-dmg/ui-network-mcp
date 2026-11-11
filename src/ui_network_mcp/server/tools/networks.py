"""Tools for the networks, the WAN interfaces, and the RADIUS profiles."""

import asyncio

from fastmcp import Context, FastMCP

from ui_network_mcp.client import JSON
from ui_network_mcp.reports import build_network_map
from ui_network_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset, SiteId
from ui_network_mcp.server.sites import client_of, resolve_site, site_item, site_page


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "networks"})
    async def list_networks(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the networks (VLANs) of a site."""
        return await site_page(ctx, site_id, "networks", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "networks"})
    async def get_network(
        ctx: Context, network_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get the full configuration of one network: VLAN, DHCP, IPv4, and IPv6 settings."""
        return await site_item(ctx, site_id, "networks", network_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "networks"})
    async def get_network_references(
        ctx: Context, network_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get the resources that use one network: clients, devices, Wi-Fi broadcasts, routes, and NAT rules.

        Call this tool before you change or remove a network.
        """
        return await site_item(ctx, site_id, "networks", f"{network_id}/references")

    @mcp.tool(annotations=READ_ONLY, tags={"read", "networks"})
    async def list_wans(
        ctx: Context, site_id: SiteId = None, limit: Limit = 25, offset: Offset = 0
    ) -> JSON:
        """List the WAN interfaces of a site."""
        return await site_page(ctx, site_id, "wans", offset, limit)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "networks"})
    async def list_radius_profiles(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the RADIUS profiles of a site."""
        return await site_page(ctx, site_id, "radius/profiles", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "networks"})
    async def get_network_map(ctx: Context, site_id: SiteId = None) -> JSON:
        """Get all networks of a site, sorted by VLAN ID.

        Each network shows its VLAN ID, its IPv4 subnet, its DHCP mode, its firewall zone, and the
        WiFi broadcasts that use it. The issues list VLAN IDs that more than one network uses.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        networks, zones, broadcasts = await asyncio.gather(
            client.get_all(f"/v1/sites/{site}/networks"),
            client.get_all(f"/v1/sites/{site}/firewall/zones"),
            client.get_all(f"/v1/sites/{site}/wifi/broadcasts"),
        )
        details = await client.gather_limited(
            [f"/v1/sites/{site}/networks/{network['id']}" for network in networks]
        )
        return build_network_map(site, details, zones, broadcasts)
