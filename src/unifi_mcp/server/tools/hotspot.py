"""Tools for the hotspot vouchers."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastmcp import Context, FastMCP
from pydantic import Field

from unifi_mcp.client import JSON
from unifi_mcp.reports import build_voucher_summary
from unifi_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset, SiteId
from unifi_mcp.server.sites import client_of, resolve_site, site_item, site_page


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

    @mcp.tool(annotations=READ_ONLY, tags={"read", "hotspot"})
    async def get_voucher_summary(
        ctx: Context,
        site_id: SiteId = None,
        expiring_within_hours: Annotated[
            int,
            Field(
                ge=1,
                description="A voucher that expires in this time is in expiringSoon.",
            ),
        ] = 24,
    ) -> JSON:
        """Get a summary of the Hotspot vouchers of a site.

        The summary counts the expired, active, and unused vouchers and the authorized guests. It
        lists the vouchers that expire soon and the vouchers that reached their guest limit. It
        does not show the voucher codes.
        """
        site = await resolve_site(ctx, site_id)
        vouchers = await client_of(ctx).get_all(f"/v1/sites/{site}/hotspot/vouchers")
        return build_voucher_summary(
            site,
            vouchers,
            datetime.now(UTC),
            timedelta(hours=expiring_within_hours),
        )
