"""Tools for the adopted devices, the pending devices, and the device tags."""

from typing import Annotated

from fastmcp import Context, FastMCP
from pydantic import Field

from unifi_mcp.client import JSON
from unifi_mcp.server.parameters import (
    ADDITIVE_WRITE,
    DESTRUCTIVE_WRITE,
    READ_ONLY,
    WRITE_TAG,
    Filter,
    Limit,
    Offset,
    SiteId,
)
from unifi_mcp.server.sites import client_of, resolve_site, site_item, site_page

WRITE_TAGS = {WRITE_TAG, "devices"}


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

    @mcp.tool(annotations=ADDITIVE_WRITE, tags=WRITE_TAGS)
    async def adopt_device(
        ctx: Context,
        mac_address: Annotated[
            str,
            Field(
                min_length=1,
                description="The MAC address from list_pending_devices.",
            ),
        ],
        ignore_device_limit: Annotated[
            bool,
            Field(
                description="Adopt the device also when the console has its maximum number of devices."
            ),
        ] = False,
        site_id: SiteId = None,
    ) -> JSON:
        """Adopt a pending device into a site. The result is the adopted device with its ID.

        Call list_pending_devices for the MAC addresses of the devices that wait for adoption.
        """
        site = await resolve_site(ctx, site_id)
        return await client_of(ctx).post(
            f"/v1/sites/{site}/devices",
            {"macAddress": mac_address, "ignoreDeviceLimit": ignore_device_limit},
        )

    @mcp.tool(annotations=DESTRUCTIVE_WRITE, tags=WRITE_TAGS)
    async def remove_device(
        ctx: Context, device_id: str, site_id: SiteId = None
    ) -> JSON:
        """Remove (unadopt) a device from a site. You cannot undo this.

        If the device is online, the console resets the device to the factory settings. The
        clients that connect through the device lose their connection. Call get_device first to
        make sure that the ID is the ID of the correct device.
        """
        site = await resolve_site(ctx, site_id)
        await client_of(ctx).delete(f"/v1/sites/{site}/devices/{device_id}")
        return {"removedDeviceId": device_id}

    @mcp.tool(annotations=DESTRUCTIVE_WRITE, tags=WRITE_TAGS)
    async def restart_device(
        ctx: Context, device_id: str, site_id: SiteId = None
    ) -> JSON:
        """Restart an adopted device.

        The device is offline for some minutes. The clients that connect through the device lose
        their connection during this time. If the device is the gateway, the site has no
        internet access during this time.
        """
        site = await resolve_site(ctx, site_id)
        await client_of(ctx).post(
            f"/v1/sites/{site}/devices/{device_id}/actions", {"action": "RESTART"}
        )
        return {"deviceId": device_id, "action": "RESTART"}

    @mcp.tool(annotations=DESTRUCTIVE_WRITE, tags=WRITE_TAGS)
    async def power_cycle_port(
        ctx: Context,
        device_id: str,
        port_idx: Annotated[
            int,
            Field(ge=1, description="The idx of the port in the result of get_device."),
        ],
        site_id: SiteId = None,
    ) -> JSON:
        """Turn the PoE power of a switch port off and on again.

        This restarts the device that gets its power from the port, for example an access point
        or a camera. The port must supply PoE power. Call get_switch_port_report or get_device
        to find the port.
        """
        site = await resolve_site(ctx, site_id)
        await client_of(ctx).post(
            f"/v1/sites/{site}/devices/{device_id}/interfaces/ports/{port_idx}/actions",
            {"action": "POWER_CYCLE"},
        )
        return {"deviceId": device_id, "portIdx": port_idx, "action": "POWER_CYCLE"}
