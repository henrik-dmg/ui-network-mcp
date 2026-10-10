"""Tools for the hotspot vouchers."""

from fastmcp import Context, FastMCP

from unifi_mcp.client import JSON
from unifi_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset, SiteId
from unifi_mcp.server.sites import site_item, site_page


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "hotspot"})
    async def list_vouchers(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the hotspot vouchers of a site.

        Filterable properties include id, name, code, createdAt, activatedAt, expiresAt, expired,
        and authorizedGuestCount.
        """
        return await site_page(ctx, site_id, "hotspot/vouchers", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "hotspot"})
    async def get_voucher(
        ctx: Context, voucher_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one hotspot voucher: code, limits, guest count, and expiry."""
        return await site_item(ctx, site_id, "hotspot/vouchers", voucher_id)
