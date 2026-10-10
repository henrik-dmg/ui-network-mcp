"""Helpers that get the client and the site from the lifespan context of a tool call."""

from fastmcp import Context
from fastmcp.exceptions import ToolError

from unifi_mcp.client import JSON, UniFiClient


def client_of(ctx: Context) -> UniFiClient:
    return ctx.lifespan_context["client"]


async def resolve_site(ctx: Context, site_id: str | None) -> str:
    """Use the given site, then the configured default site, then the only site of the console."""
    if site_id:
        return site_id
    state = ctx.lifespan_context
    if state["default_site_id"]:
        return state["default_site_id"]
    sites = await client_of(ctx).get_all("/v1/sites")
    if len(sites) != 1:
        names = ", ".join(f"{site['name']} ({site['id']})" for site in sites) or "none"
        raise ToolError(
            f"The console has more than one site. Give a site_id. Sites: {names}"
        )
    state["default_site_id"] = sites[0]["id"]
    return sites[0]["id"]


async def site_page(
    ctx: Context,
    site_id: str | None,
    resource: str,
    offset: int,
    limit: int,
    filter: str | None = None,
) -> JSON:
    site = await resolve_site(ctx, site_id)
    return await client_of(ctx).get_page(
        f"/v1/sites/{site}/{resource}", offset=offset, limit=limit, filter=filter
    )


async def site_item(
    ctx: Context, site_id: str | None, resource: str, item_id: str
) -> JSON:
    site = await resolve_site(ctx, site_id)
    return await client_of(ctx).get(f"/v1/sites/{site}/{resource}/{item_id}")
