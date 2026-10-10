"""Tools for the device tree of a site."""

from fastmcp import Context, FastMCP

from unifi_mcp.client import JSON
from unifi_mcp.reports import build_topology
from unifi_mcp.server.parameters import READ_ONLY, SiteId
from unifi_mcp.server.sites import client_of, resolve_site


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "topology"})
    async def get_topology(ctx: Context, site_id: SiteId = None) -> JSON:
        """Get the device tree of a site, from the gateway down to each switch and access point.

        Each device shows its state, model, IP address, the number of clients that connect to it,
        and the devices that use it as their uplink. VPN and Teleport clients have no uplink device.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        devices = await client.get_all(f"/v1/sites/{site}/devices")
        details = await client.gather_limited(
            [f"/v1/sites/{site}/devices/{device['id']}" for device in devices]
        )
        clients = await client.get_all(f"/v1/sites/{site}/clients")
        return build_topology(site, details, clients)
