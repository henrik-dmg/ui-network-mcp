"""Tools for the health of a site and its devices."""

import asyncio

from fastmcp import Context, FastMCP

from ui_network_mcp.client import JSON
from ui_network_mcp.reports import build_device_health, build_site_health
from ui_network_mcp.server.parameters import READ_ONLY, SiteId
from ui_network_mcp.server.sites import client_of, resolve_site


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "health"})
    async def get_site_health(ctx: Context, site_id: SiteId = None) -> JSON:
        """Get a health summary of a site. Use it to answer "is everything OK?".

        The summary has a list of issues, the devices by state, the devices that are not online,
        the available firmware updates, models with different firmware versions, the devices that
        wait for adoption, the WAN interfaces, and the clients by type.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        devices, clients, pending, wans = await asyncio.gather(
            client.get_all(f"/v1/sites/{site}/devices"),
            client.get_all(f"/v1/sites/{site}/clients"),
            client.get_all("/v1/pending-devices"),
            client.get_all(f"/v1/sites/{site}/wans"),
        )
        return build_site_health(site, devices, clients, pending, wans)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "health", "devices"})
    async def get_device_health(ctx: Context, site_id: SiteId = None) -> JSON:
        """Get the latest statistics of all devices of a site, with the device that needs most attention first.

        The devices that are not online come first. The other devices follow, sorted by their
        highest CPU or memory use. Each device shows uptime, CPU, memory, load, and uplink rates.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        devices = await client.get_all(f"/v1/sites/{site}/devices")
        statistics = await client.gather_limited(
            [
                f"/v1/sites/{site}/devices/{device['id']}/statistics/latest"
                for device in devices
            ],
            return_errors=True,
        )
        return build_device_health(site, devices, statistics)
