"""The MCP tools, in one module for each tag."""

from fastmcp import FastMCP

from unifi_mcp.server.tools import (
    acl,
    audit,
    clients,
    console,
    devices,
    dns,
    dpi,
    firewall,
    health,
    hotspot,
    networks,
    switching,
    topology,
    vpn,
    wifi,
)


def register_all(mcp: FastMCP) -> None:
    for module in (
        console,
        devices,
        clients,
        networks,
        wifi,
        vpn,
        firewall,
        dpi,
        acl,
        dns,
        switching,
        hotspot,
        topology,
        health,
        audit,
    ):
        module.register(mcp)
