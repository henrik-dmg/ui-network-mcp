"""Tools for the applications and categories that Deep Packet Inspection (DPI) recognizes."""

from fastmcp import Context, FastMCP

from ui_network_mcp.client import JSON
from ui_network_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset
from ui_network_mcp.server.sites import client_of


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "dpi"})
    async def list_dpi_applications(
        ctx: Context, filter: Filter = None, limit: Limit = 25, offset: Offset = 0
    ) -> JSON:
        """List the applications that DPI recognizes. Firewall policies refer to them by ID.

        Filterable properties are id and name, for example name.like('*Netflix*').
        """
        return await client_of(ctx).get_page(
            "/v1/dpi/applications", offset=offset, limit=limit, filter=filter
        )

    @mcp.tool(annotations=READ_ONLY, tags={"read", "dpi"})
    async def list_dpi_categories(
        ctx: Context, filter: Filter = None, limit: Limit = 25, offset: Offset = 0
    ) -> JSON:
        """List the application categories that DPI recognizes. Firewall policies refer to them by ID.

        Filterable properties are id and name.
        """
        return await client_of(ctx).get_page(
            "/v1/dpi/categories", offset=offset, limit=limit, filter=filter
        )
