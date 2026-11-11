"""Tools for the LAGs, the MC-LAG domains, and the switch stacks."""

import asyncio

from fastmcp import Context, FastMCP

from ui_network_mcp.client import JSON
from ui_network_mcp.reports import build_switch_ports
from ui_network_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset, SiteId
from ui_network_mcp.server.sites import client_of, resolve_site, site_item, site_page


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "switching"})
    async def list_lags(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the link aggregation groups (LAGs) of the switches of a site.

        Filterable properties include id, type, switchStackId, mcLagDomainId, and metadata.origin.
        """
        return await site_page(ctx, site_id, "switching/lags", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "switching"})
    async def get_lag(ctx: Context, lag_id: str, site_id: SiteId = None) -> JSON:
        """Get one link aggregation group (LAG). The type is LOCAL, MULTI_CHASSIS, or SWITCH_STACK."""
        return await site_item(ctx, site_id, "switching/lags", lag_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "switching"})
    async def list_mc_lag_domains(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the MC-LAG domains of a site. An MC-LAG domain is a pair of switches that share LAGs."""
        return await site_page(
            ctx, site_id, "switching/mc-lag-domains", offset, limit, filter
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "switching"})
    async def get_mc_lag_domain(
        ctx: Context, mc_lag_domain_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one MC-LAG domain: its peer switches and its LAGs."""
        return await site_item(
            ctx, site_id, "switching/mc-lag-domains", mc_lag_domain_id
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "switching"})
    async def list_switch_stacks(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the switch stacks of a site."""
        return await site_page(
            ctx, site_id, "switching/switch-stacks", offset, limit, filter
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "switching"})
    async def get_switch_stack(
        ctx: Context, switch_stack_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one switch stack: its member units and its LAGs."""
        return await site_item(ctx, site_id, "switching/switch-stacks", switch_stack_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "switching", "devices"})
    async def get_switch_port_report(
        ctx: Context, site_id: SiteId = None, device_id: str | None = None
    ) -> JSON:
        """Get the ports of each device of a site that has ports, or of one device.

        Each device shows its wired client count, its ports by state, its PoE ports by state, and
        each port with its speed, maximum speed, and PoE state. The issues list ports that run
        below their maximum speed and ports with limited PoE power. A slow port can have a bad
        cable, or a connected device that supports only a lower speed.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        devices, clients = await asyncio.gather(
            client.get_all(f"/v1/sites/{site}/devices"),
            client.get_all(f"/v1/sites/{site}/clients"),
        )
        ids = [
            d["id"]
            for d in devices
            if "ports" in d.get("interfaces", []) and device_id in (None, d["id"])
        ]
        details = await client.gather_limited(
            [f"/v1/sites/{site}/devices/{i}" for i in ids]
        )
        return build_switch_ports(site, details, clients)
