"""Tools for the adopted devices, the pending devices, and the device tags."""

from fastmcp import Context, FastMCP

from unifi_mcp.client import JSON
from unifi_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset, SiteId
from unifi_mcp.server.sites import client_of, site_item, site_page


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "devices"})
    async def list_devices(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the adopted devices (gateways, switches, access points) of a site.

        Filterable properties include name, model, state, macAddress, ipAddress, and firmwareVersion.
        """
        return await site_page(ctx, site_id, "devices", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "devices"})
    async def get_device(ctx: Context, device_id: str, site_id: SiteId = None) -> JSON:
        """Get the details of one adopted device: ports, radios, uplink, and firmware."""
        return await site_item(ctx, site_id, "devices", device_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "devices"})
    async def get_device_statistics(
        ctx: Context, device_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get the latest statistics of one device: uptime, CPU, memory, load, uplink rates, and radios."""
        return await site_item(
            ctx, site_id, "devices", f"{device_id}/statistics/latest"
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "devices"})
    async def list_pending_devices(
        ctx: Context, filter: Filter = None, limit: Limit = 25, offset: Offset = 0
    ) -> JSON:
        """List the devices on the console that wait for adoption."""
        return await client_of(ctx).get_page(
            "/v1/pending-devices", offset=offset, limit=limit, filter=filter
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "devices"})
    async def list_device_tags(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the device tags of a site. Wi-Fi broadcasts can use a tag to select their devices."""
        return await site_page(ctx, site_id, "device-tags", offset, limit, filter)
