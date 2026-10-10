"""The MCP tools, in one module for each tag."""

from fastmcp import FastMCP

from unifi_mcp.server.tools import (
    acl,
    clients,
    console,
    devices,
    dns,
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
        acl,
        dns,
        switching,
        hotspot,
        topology,
        health,
    ):
        module.register(mcp)
