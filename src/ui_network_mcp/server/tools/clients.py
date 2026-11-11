"""Tools for the connected clients."""

import asyncio
from typing import Annotated

from fastmcp import Context, FastMCP
from pydantic import Field

from ui_network_mcp.client import JSON
from ui_network_mcp.models import request_body
from ui_network_mcp.reports import build_client_summary, find_clients
from ui_network_mcp.server.parameters import (
    DESTRUCTIVE_WRITE,
    READ_ONLY,
    WRITE_TAG,
    DataUsageLimit,
    Filter,
    Limit,
    Offset,
    RxRateLimit,
    SiteId,
    TxRateLimit,
)
from ui_network_mcp.server.sites import client_of, resolve_site, site_item, site_page

WRITE_TAGS = {WRITE_TAG, "clients"}


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "clients"})
    async def list_clients(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the connected clients of a site: wired, wireless, VPN, and Teleport.

        Filterable properties include type (WIRED, WIRELESS, VPN, TELEPORT), macAddress, ipAddress,
        connectedAt, and access.type.
        """
        return await site_page(ctx, site_id, "clients", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "clients"})
    async def get_client(ctx: Context, client_id: str, site_id: SiteId = None) -> JSON:
        """Get the details of one connected client."""
        return await site_item(ctx, site_id, "clients", client_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "clients"})
    async def get_client_summary(ctx: Context, site_id: SiteId = None) -> JSON:
        """Get a summary of the connected clients of a site.

        The summary counts the clients by type, by access type, and by uplink device, and lists
        the clients that connected most recently.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        clients, devices = await asyncio.gather(
            client.get_all(f"/v1/sites/{site}/clients"),
            client.get_all(f"/v1/sites/{site}/devices"),
        )
        return build_client_summary(site, clients, devices)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "clients"})
    async def find_client(
        ctx: Context,
        query: Annotated[
            str,
            Field(
                min_length=1,
                description="Part of the name, IP address, or MAC address of the client.",
            ),
        ],
        site_id: SiteId = None,
    ) -> JSON:
        """Find the connected clients whose name, IP address, or MAC address contains the query.

        The search ignores case and the separators in MAC addresses. Each client shows the name and
        model of the device that it connects to.
        """
        site = await resolve_site(ctx, site_id)
        client = client_of(ctx)
        clients, devices = await asyncio.gather(
            client.get_all(f"/v1/sites/{site}/clients"),
            client.get_all(f"/v1/sites/{site}/devices"),
        )
        return find_clients(site, query, clients, devices)

    @mcp.tool(annotations=DESTRUCTIVE_WRITE, tags=WRITE_TAGS)
    async def authorize_guest(
        ctx: Context,
        client_id: str,
        time_limit_minutes: Annotated[
            int | None,
            Field(
                ge=1,
                le=1_000_000,
                description="How long the guest has access. Omit it to use the default of the site.",
            ),
        ] = None,
        data_usage_limit_mbytes: DataUsageLimit = None,
        rx_rate_limit_kbps: RxRateLimit = None,
        tx_rate_limit_kbps: TxRateLimit = None,
        site_id: SiteId = None,
    ) -> JSON:
        """Give a connected guest client access to the network.

        The client must be a guest. If the guest already has access, the console cancels that
        access, gives new access with the new limits, and sets the traffic counters of the guest
        to zero. The result shows the new access and the cancelled access.
        """
        site = await resolve_site(ctx, site_id)
        body = request_body(
            action="AUTHORIZE_GUEST_ACCESS",
            time_limit_minutes=time_limit_minutes,
            data_usage_limit_m_bytes=data_usage_limit_mbytes,
            rx_rate_limit_kbps=rx_rate_limit_kbps,
            tx_rate_limit_kbps=tx_rate_limit_kbps,
        )
        return await client_of(ctx).post(
            f"/v1/sites/{site}/clients/{client_id}/actions", body
        )

    @mcp.tool(annotations=DESTRUCTIVE_WRITE, tags=WRITE_TAGS)
    async def unauthorize_guest(
        ctx: Context, client_id: str, site_id: SiteId = None
    ) -> JSON:
        """Cancel the network access of a guest client and disconnect the client.

        The result shows the cancelled access.
        """
        site = await resolve_site(ctx, site_id)
        return await client_of(ctx).post(
            f"/v1/sites/{site}/clients/{client_id}/actions",
            {"action": "UNAUTHORIZE_GUEST_ACCESS"},
        )
