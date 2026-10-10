"""Tools for the DNS policies."""

from fastmcp import Context, FastMCP

from unifi_mcp.client import JSON
from unifi_mcp.server.parameters import READ_ONLY, Filter, Limit, Offset, SiteId
from unifi_mcp.server.sites import site_item, site_page


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY, tags={"read", "dns"})
    async def list_dns_policies(
        ctx: Context,
        site_id: SiteId = None,
        filter: Filter = None,
        limit: Limit = 25,
        offset: Offset = 0,
    ) -> JSON:
        """List the DNS policies (local DNS records and forward rules) of a site.

        Filterable properties include type, id, enabled, domain, ipv4Address, ipv6Address, and
        targetDomain.
        """
        return await site_page(ctx, site_id, "dns/policies", offset, limit, filter)

    @mcp.tool(annotations=READ_ONLY, tags={"read", "dns"})
    async def get_dns_policy(
        ctx: Context, dns_policy_id: str, site_id: SiteId = None
    ) -> JSON:
        """Get one DNS policy."""
        return await site_item(ctx, site_id, "dns/policies", dns_policy_id)
