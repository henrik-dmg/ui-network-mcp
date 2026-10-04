import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.exceptions import ToolError

from unifi_mcp.client import UniFiClient
from unifi_mcp.server import build_server

BASE = "https://console.test/proxy/network/integration"
SITE = "11111111-1111-1111-1111-111111111111"
GATEWAY = "aaaaaaaa-0000-0000-0000-000000000001"
SWITCH = "aaaaaaaa-0000-0000-0000-000000000002"
AP = "aaaaaaaa-0000-0000-0000-000000000003"


def page(data, total=None):
    return {
        "offset": 0,
        "limit": 200,
        "count": len(data),
        "totalCount": len(data) if total is None else total,
        "data": data,
    }


def device(device_id, name, uplink=None):
    body = {
        "id": device_id,
        "name": name,
        "model": "M",
        "state": "ONLINE",
        "ipAddress": "10.0.0.1",
        "macAddress": "m",
    }
    if uplink:
        body["uplink"] = {"deviceId": uplink}
    return body


def make_server(default_site_id=None):
    return build_server(
        lambda: UniFiClient(
            httpx.AsyncClient(base_url=BASE, headers={"X-API-KEY": "key"})
        ),
        default_site_id,
    )


@pytest.fixture
def api():
    with respx.mock(base_url=BASE, assert_all_called=False) as mock:
        yield mock


async def test_tools_are_read_only():
    async with Client(make_server()) as client:
        tools = await client.list_tools()
    assert len(tools) == 32
    assert all(tool.annotations.read_only_hint for tool in tools)


async def test_sends_api_key_and_returns_info(api):
    route = api.get("/v1/info").respond(json={"applicationVersion": "10.6.106"})
    async with Client(make_server()) as client:
        result = await client.call_tool("get_application_info")
    assert result.data == {"applicationVersion": "10.6.106"}
    assert route.calls.last.request.headers["X-API-KEY"] == "key"


async def test_single_site_is_used_by_default(api):
    api.get("/v1/sites").respond(
        json=page([{"id": SITE, "name": "Default", "internalReference": "default"}])
    )
    devices = api.get(f"/v1/sites/{SITE}/devices").respond(json=page([]))
    async with Client(make_server()) as client:
        await client.call_tool(
            "list_devices", {"filter": "state.eq('ONLINE')", "limit": 10}
        )
    params = devices.calls.last.request.url.params
    assert params["filter"] == "state.eq('ONLINE')"
    assert params["limit"] == "10"


async def test_many_sites_require_a_site_id(api):
    sites = [
        {"id": SITE, "name": "A", "internalReference": "a"},
        {"id": "other", "name": "B", "internalReference": "b"},
    ]
    api.get("/v1/sites").respond(json=page(sites))
    async with Client(make_server()) as client:
        with pytest.raises(ToolError, match="more than one site"):
            await client.call_tool("list_clients")


async def test_configured_default_site_skips_the_lookup(api):
    sites = api.get("/v1/sites")
    api.get(f"/v1/sites/{SITE}/networks").respond(json=page([]))
    async with Client(make_server(default_site_id=SITE)) as client:
        await client.call_tool("list_networks")
    assert not sites.called


async def test_api_errors_reach_the_caller(api):
    api.get(f"/v1/sites/{SITE}/devices/missing").respond(
        404,
        json={
            "statusCode": 404,
            "code": "api.not-found",
            "message": "Device not found",
        },
    )
    async with Client(make_server(default_site_id=SITE)) as client:
        with pytest.raises(ToolError, match="Device not found"):
            await client.call_tool("get_device", {"device_id": "missing"})


async def test_topology_builds_the_device_tree(api):
    api.get(f"/v1/sites/{SITE}/devices").respond(
        json=page([{"id": GATEWAY}, {"id": SWITCH}, {"id": AP}])
    )
    api.get(f"/v1/sites/{SITE}/devices/{GATEWAY}").respond(
        json=device(GATEWAY, "Gateway")
    )
    api.get(f"/v1/sites/{SITE}/devices/{SWITCH}").respond(
        json=device(SWITCH, "Switch", uplink=GATEWAY)
    )
    api.get(f"/v1/sites/{SITE}/devices/{AP}").respond(
        json=device(AP, "AP", uplink=SWITCH)
    )
    clients = [
        {"id": "c1", "type": "WIRED", "uplinkDeviceId": SWITCH},
        {"id": "c2", "type": "WIRELESS", "uplinkDeviceId": AP},
        {"id": "c3", "type": "WIRELESS", "uplinkDeviceId": AP},
        {"id": "c4", "type": "VPN"},
    ]
    api.get(f"/v1/sites/{SITE}/clients").respond(json=page(clients))

    async with Client(make_server(default_site_id=SITE)) as client:
        topology = (await client.call_tool("get_topology")).data

    assert topology["clientsWithoutUplinkDevice"] == {"VPN": 1}
    [gateway] = topology["roots"]
    [switch] = gateway["downlinks"]
    [ap] = switch["downlinks"]
    assert (gateway["name"], switch["name"], ap["name"]) == ("Gateway", "Switch", "AP")
    assert switch["clients"] == {"WIRED": 1}
    assert ap["clients"] == {"WIRELESS": 2}


async def test_get_all_follows_pagination(api):
    first = [{"id": str(i)} for i in range(200)]
    api.get("/v1/sites", params={"offset": "0"}).respond(json=page(first, total=201))
    api.get("/v1/sites", params={"offset": "200"}).respond(
        json=page([{"id": "200"}], total=201)
    )
    client = UniFiClient(httpx.AsyncClient(base_url=BASE))
    assert len(await client.get_all("/v1/sites")) == 201


async def test_firewall_policy_ordering_sends_the_zone_pair(api):
    route = api.get(f"/v1/sites/{SITE}/firewall/policies/ordering").respond(
        json={"orderedFirewallPolicyIds": {"beforeSystemDefined": ["p1"]}}
    )
    async with Client(make_server(default_site_id=SITE)) as client:
        await client.call_tool(
            "get_firewall_policy_ordering",
            {"source_firewall_zone_id": "z1", "destination_firewall_zone_id": "z2"},
        )
    params = route.calls.last.request.url.params
    assert params["sourceFirewallZoneId"] == "z1"
    assert params["destinationFirewallZoneId"] == "z2"


async def test_firewall_overview_groups_policies_and_adds_names(api):
    zones = [
        {"id": "z-lan", "name": "Internal", "networkIds": ["n1"]},
        {"id": "z-wan", "name": "External", "networkIds": []},
    ]
    policies = [
        {
            "id": "p2",
            "name": "Allow DNS",
            "index": 20,
            "action": {"type": "ALLOW"},
            "source": {"zoneId": "z-lan"},
            "destination": {"zoneId": "z-wan"},
        },
        {
            "id": "p1",
            "name": "Block games",
            "index": 10,
            "action": {"type": "BLOCK"},
            "source": {
                "zoneId": "z-lan",
                "trafficFilter": {
                    "type": "NETWORK",
                    "networkFilter": {"matchOpposite": False, "networkIds": ["n1"]},
                },
            },
            "destination": {
                "zoneId": "z-wan",
                "trafficFilter": {
                    "type": "APPLICATION",
                    "applicationFilter": {"applicationIds": [7]},
                },
            },
        },
    ]
    api.get(f"/v1/sites/{SITE}/firewall/zones").respond(json=page(zones))
    api.get(f"/v1/sites/{SITE}/firewall/policies").respond(json=page(policies))
    api.get(f"/v1/sites/{SITE}/networks").respond(
        json=page([{"id": "n1", "name": "Home"}])
    )
    for path in ["traffic-matching-lists", "vpn/servers", "vpn/site-to-site-tunnels"]:
        api.get(f"/v1/sites/{SITE}/{path}").respond(json=page([]))
    api.get("/v1/dpi/applications").respond(json=page([{"id": 7, "name": "Steam"}]))
    categories = api.get("/v1/dpi/categories")

    async with Client(make_server(default_site_id=SITE)) as client:
        overview = (await client.call_tool("get_firewall_overview")).data

    assert not categories.called
    assert overview["zones"][0]["networks"] == ["Home"]
    [pair] = overview["zonePairs"]
    assert (pair["sourceZone"], pair["destinationZone"]) == ("Internal", "External")
    first, second = pair["policies"]
    assert (first["id"], second["id"]) == ("p1", "p2")
    assert first["sourceFilter"]["networkFilter"]["networkNames"] == ["Home"]
    assert first["destinationFilter"]["applicationFilter"]["applicationNames"] == [
        "Steam"
    ]


async def test_network_references_use_the_references_path(api):
    route = api.get(f"/v1/sites/{SITE}/networks/n1/references").respond(
        json={"referenceResources": []}
    )
    async with Client(make_server(default_site_id=SITE)) as client:
        result = await client.call_tool("get_network_references", {"network_id": "n1"})
    assert route.called
    assert result.data == {"referenceResources": []}
