"""Tools for the connected clients."""

import asyncio
from typing import Annotated

from fastmcp import Context, FastMCP
from pydantic import Field

from unifi_mcp.client import JSON
from unifi_mcp.reports import build_client_summary, find_clients
from unifi_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset, SiteId
from unifi_mcp.server.sites import client_of, resolve_site, site_item, site_page


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
