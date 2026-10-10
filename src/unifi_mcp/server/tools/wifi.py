"""Tools for the Wi-Fi broadcasts."""

import asyncio

from fastmcp import Context, FastMCP

from unifi_mcp.client import JSON
from unifi_mcp.reports import build_wifi_overview
from unifi_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset, SiteId
from unifi_mcp.server.sites import client_of, resolve_site, site_item, site_page


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

    @mcp.tool(annotations=READ_ONLY, tags={"read", "wifi"})
    async def get_wifi_overview(ctx: Context, site_id: SiteId = None) -> JSON:
        """Get the WiFi broadcasts, the radios of each access point, and the wireless clients of a site.

        Each access point shows its wireless client count and, for each radio, the channel, the
        channel width, the WLAN standard, and the share of retried transmissions. The issues list
        online access points that use the same channel on the same band, radios with many
        retries, and disabled WiFi broadcasts.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        broadcasts, networks, devices, clients = await asyncio.gather(
            client.get_all(f"/v1/sites/{site}/wifi/broadcasts"),
            client.get_all(f"/v1/sites/{site}/networks"),
            client.get_all(f"/v1/sites/{site}/devices"),
            client.get_all(f"/v1/sites/{site}/clients"),
        )
        ids = [d["id"] for d in devices if "radios" in d.get("interfaces", [])]
        details, statistics = await asyncio.gather(
            client.gather_limited([f"/v1/sites/{site}/devices/{i}" for i in ids]),
            client.gather_limited(
                [f"/v1/sites/{site}/devices/{i}/statistics/latest" for i in ids],
                return_errors=True,
            ),
        )
        return build_wifi_overview(
            site, broadcasts, networks, details, statistics, clients
        )
