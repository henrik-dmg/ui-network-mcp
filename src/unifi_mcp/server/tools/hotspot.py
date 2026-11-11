"""Tools for the hotspot vouchers."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastmcp import Context, FastMCP
from pydantic import Field

from unifi_mcp.client import JSON
from unifi_mcp.models import request_body
from unifi_mcp.reports import build_voucher_summary
from unifi_mcp.server.parameters import (
    ADDITIVE_WRITE,
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
from unifi_mcp.server.sites import client_of, resolve_site, site_item, site_page

WRITE_TAGS = {WRITE_TAG, "hotspot"}


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

    @mcp.tool(annotations=ADDITIVE_WRITE, tags=WRITE_TAGS)
    async def create_vouchers(
        ctx: Context,
        name: Annotated[
            str,
            Field(min_length=1, description="A note that all new vouchers get."),
        ],
        time_limit_minutes: Annotated[
            int,
            Field(
                ge=1,
                le=1_000_000,
                description="How long a voucher gives access, from the first guest that uses it.",
            ),
        ],
        count: Annotated[
            int, Field(ge=1, le=1000, description="The number of vouchers.")
        ] = 1,
        authorized_guest_limit: Annotated[
            int | None,
            Field(
                ge=1,
                description="The number of different guests that can use one voucher.",
            ),
        ] = None,
        data_usage_limit_mbytes: DataUsageLimit = None,
        rx_rate_limit_kbps: RxRateLimit = None,
        tx_rate_limit_kbps: TxRateLimit = None,
        site_id: SiteId = None,
    ) -> JSON:
        """Create one or more Hotspot vouchers. The result has the new vouchers with their codes.

        All guests of one voucher share the same expiry time. Without authorized_guest_limit,
        any number of guests can use a voucher.
        """
        site = await resolve_site(ctx, site_id)
        body = request_body(
            name=name,
            count=count,
            time_limit_minutes=time_limit_minutes,
            authorized_guest_limit=authorized_guest_limit,
            data_usage_limit_m_bytes=data_usage_limit_mbytes,
            rx_rate_limit_kbps=rx_rate_limit_kbps,
            tx_rate_limit_kbps=tx_rate_limit_kbps,
        )
        return await client_of(ctx).post(f"/v1/sites/{site}/hotspot/vouchers", body)

    @mcp.tool(annotations=DESTRUCTIVE_WRITE, tags=WRITE_TAGS)
    async def delete_voucher(
        ctx: Context, voucher_id: str, site_id: SiteId = None
    ) -> JSON:
        """Delete one Hotspot voucher. You cannot undo this. The result has the number of deleted vouchers."""
        site = await resolve_site(ctx, site_id)
        return await client_of(ctx).delete(
            f"/v1/sites/{site}/hotspot/vouchers/{voucher_id}"
        )

    @mcp.tool(annotations=DESTRUCTIVE_WRITE, tags=WRITE_TAGS)
    async def delete_vouchers(
        ctx: Context,
        filter: Annotated[
            str,
            Field(
                min_length=1,
                description="The filter that selects the vouchers to delete, for example expired.eq(true).",
            ),
        ],
        site_id: SiteId = None,
    ) -> JSON:
        """Delete all Hotspot vouchers that the filter selects. You cannot undo this.

        The filter has the same properties as in list_vouchers. Call list_vouchers with the same
        filter first to make sure that the filter selects only the correct vouchers. The result
        has the number of deleted vouchers.
        """
        site = await resolve_site(ctx, site_id)
        return await client_of(ctx).delete(
            f"/v1/sites/{site}/hotspot/vouchers", {"filter": filter}
        )
