"""Tools for the ACL rules."""

from fastmcp import Context, FastMCP

from ui_network_mcp.client import JSON
from ui_network_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset, SiteId
from ui_network_mcp.server.sites import client_of, resolve_site, site_item, site_page


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "acl"})
    async def list_acl_rules(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the ACL rules of a site. The switches apply these rules to traffic in a network.

        Filterable properties include type, id, enabled, name, action, index, networkId, and
        metadata.origin.
        """
        return await site_page(ctx, site_id, "acl-rules", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "acl"})
    async def get_acl_rule(
        ctx: Context, acl_rule_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one ACL rule: action, source, destination, and the devices that apply it."""
        return await site_item(ctx, site_id, "acl-rules", acl_rule_id)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "acl"})
    async def get_acl_rule_ordering(ctx: Context, site_id: SiteId = None) -> JSON:
        """Get the order of the user-defined ACL rules of a site."""
        site = await resolve_site(ctx, site_id)
        return await client_of(ctx).get(f"/v1/sites/{site}/acl-rules/ordering")
