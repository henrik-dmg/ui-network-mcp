"""Tools for the firewall zones, the firewall policies, and the traffic matching lists."""

import asyncio

from fastmcp import Context, FastMCP

from ui_network_mcp.client import JSON
from ui_network_mcp.reports import build_firewall_overview, collect_ids
from ui_network_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset, SiteId
from ui_network_mcp.server.sites import client_of, resolve_site, site_item, site_page


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def list_firewall_zones(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the firewall zones of a site and the networks in each zone.

        Filterable properties include id, name, metadata.origin, and metadata.configurable.
        """
        return await site_page(ctx, site_id, "firewall/zones", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def get_firewall_zone(
        ctx: Context, firewall_zone_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one firewall zone and the IDs of its networks."""
        return await site_item(ctx, site_id, "firewall/zones", firewall_zone_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def list_firewall_policies(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the firewall policies of a site. Each policy applies to one source zone and one destination zone.

        Filterable properties include id, name, source.zoneId, destination.zoneId, and metadata.origin.
        For a readable overview of all policies, call get_firewall_overview.
        """
        return await site_page(ctx, site_id, "firewall/policies", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def get_firewall_policy(
        ctx: Context, firewall_policy_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one firewall policy: action, source, destination, protocol, schedule, logging, and flow reports."""
        return await site_item(ctx, site_id, "firewall/policies", firewall_policy_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def get_firewall_policy_ordering(
        ctx: Context,
        source_firewall_zone_id: str,
        destination_firewall_zone_id: str,
        site_id: SiteId = None,
    ) -> JSON:
        """Get the order of the user-defined firewall policies for one pair of zones.

        The result has the policy IDs before and after the system-defined policies.
        """
        site = await resolve_site(ctx, site_id)
        return await client_of(ctx).get(
            f"/v1/sites/{site}/firewall/policies/ordering",
            {
                "sourceFirewallZoneId": source_firewall_zone_id,
                "destinationFirewallZoneId": destination_firewall_zone_id,
            },
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def list_traffic_matching_lists(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the traffic matching lists of a site. These are named lists of ports or IP addresses.

        Firewall policies refer to these lists by ID. Filterable properties are id and name.
        """
        return await site_page(
            ctx, site_id, "traffic-matching-lists", offset, limit, filter
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def get_traffic_matching_list(
        ctx: Context, traffic_matching_list_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one traffic matching list and its ports or IP addresses."""
        return await site_item(
            ctx, site_id, "traffic-matching-lists", traffic_matching_list_id
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "firewall"})
    async def get_firewall_overview(ctx: Context, site_id: SiteId = None) -> JSON:
        """Get all firewall zones and policies of a site, grouped by source zone and destination zone.

        In each zone pair, the policies are in the order of their index. The traffic filters show
        the names of the networks, VPN servers, VPN tunnels, traffic matching lists, and DPI
        applications next to their IDs.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        resources = {
            "zones": "firewall/zones",
            "policies": "firewall/policies",
            "networks": "networks",
            "trafficMatchingLists": "traffic-matching-lists",
            "vpnServers": "vpn/servers",
            "siteToSiteVpnTunnels": "vpn/site-to-site-tunnels",
        }
        lists = await asyncio.gather(
            *(client.get_all(f"/v1/sites/{site}/{path}") for path in resources.values())
        )
        data = dict(zip(resources, lists, strict=True))
        policies = data.pop("policies")
        zones = data.pop("zones")
        if collect_ids(policies, "applicationIds"):
            data["applications"] = await client.get_all("/v1/dpi/applications")
        if collect_ids(policies, "applicationCategoryIds"):
            data["applicationCategories"] = await client.get_all("/v1/dpi/categories")
        names = {
            kind: {item["id"]: item.get("name") for item in items}
            for kind, items in data.items()
        }
        return build_firewall_overview(site, zones, policies, names)
