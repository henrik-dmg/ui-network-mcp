import json

import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.exceptions import ToolError

from unifi_mcp.client import UniFiClient
from unifi_mcp.client.redaction import REDACTED, redact
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


def make_server(default_site_id=None, allow_writes=False):
    return build_server(
        lambda: UniFiClient(
            httpx.AsyncClient(base_url=BASE, headers={"X-API-KEY": "key"})
        ),
        default_site_id,
        allow_writes,
    )


@pytest.fixture
def api():
    with respx.mock(base_url=BASE, assert_all_called=False) as mock:
        yield mock


async def test_tools_are_read_only():
    async with Client(make_server()) as client:
        tools = await client.list_tools()
    assert len(tools) == 51
    assert all(tool.annotations.read_only_hint for tool in tools)


async def test_sends_api_key_and_returns_info(api):
    route = api.get("/v1/info").respond(json={"applicationVersion": "11.0.97"})
    async with Client(make_server()) as client:
        result = await client.call_tool("get_application_info")
    assert result.data == {"applicationVersion": "11.0.97"}
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
            "reportFlowEnabled": False,
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
    assert first["reportFlowEnabled"] is False
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


async def test_site_health_lists_the_issues(api):
    devices = [
        {**device(GATEWAY, "Gateway"), "firmwareVersion": "1.0"},
        {
            **device(SWITCH, "Switch 1"),
            "firmwareVersion": "2.0",
            "firmwareUpdatable": True,
        },
        {**device(AP, "Switch 2"), "firmwareVersion": "2.1", "state": "OFFLINE"},
    ]
    devices[0]["model"] = "UDM"
    pending = [
        {"macAddress": "p1", "adoptionTargetSiteIds": [SITE]},
        {"macAddress": "p2", "adoptionTargetSiteIds": ["other"]},
    ]
    api.get(f"/v1/sites/{SITE}/devices").respond(json=page(devices))
    api.get(f"/v1/sites/{SITE}/clients").respond(
        json=page([{"type": "WIRED"}, {"type": "WIRELESS"}, {"type": "WIRELESS"}])
    )
    api.get("/v1/pending-devices").respond(json=page(pending))
    api.get(f"/v1/sites/{SITE}/wans").respond(json=page([{"id": "w", "name": "WAN"}]))

    async with Client(make_server(default_site_id=SITE)) as client:
        health = (await client.call_tool("get_site_health")).data

    assert len(health["issues"]) == 4
    assert health["devices"]["byState"] == {"ONLINE": 2, "OFFLINE": 1}
    assert [d["name"] for d in health["devices"]["notOnline"]] == ["Switch 2"]
    assert health["devices"]["firmwareVersionMismatches"] == {"M": {"2.0": 1, "2.1": 1}}
    assert [d["macAddress"] for d in health["pendingAdoption"]] == ["p1"]
    assert health["clients"]["byType"] == {"WIRED": 1, "WIRELESS": 2}


async def test_device_health_sorts_and_keeps_failed_devices(api):
    devices = [
        device(GATEWAY, "Gateway"),
        device(SWITCH, "Switch"),
        {**device(AP, "AP"), "state": "OFFLINE"},
    ]
    api.get(f"/v1/sites/{SITE}/devices").respond(json=page(devices))
    stats = f"/v1/sites/{SITE}/devices/{{}}/statistics/latest"
    api.get(stats.format(GATEWAY)).respond(
        json={"cpuUtilizationPct": 10, "memoryUtilizationPct": 20}
    )
    api.get(stats.format(SWITCH)).respond(
        json={"cpuUtilizationPct": 90, "uplink": {"rxRateBps": 5}}
    )
    api.get(stats.format(AP)).respond(404, json={"message": "Device is offline"})

    async with Client(make_server(default_site_id=SITE)) as client:
        health = (await client.call_tool("get_device_health")).data

    ap, switch, gateway = health["devices"]
    assert (ap["name"], switch["name"], gateway["name"]) == ("AP", "Switch", "Gateway")
    assert "Device is offline" in ap["statisticsError"]
    assert switch["uplinkRxRateBps"] == 5


async def test_dpi_applications_send_the_filter(api):
    route = api.get("/v1/dpi/applications").respond(
        json=page([{"id": 7, "name": "Steam"}])
    )
    async with Client(make_server()) as client:
        result = await client.call_tool(
            "list_dpi_applications", {"filter": "name.like('Ste*')"}
        )
    assert route.calls.last.request.url.params["filter"] == "name.like('Ste*')"
    assert result.data["data"] == [{"id": 7, "name": "Steam"}]


async def test_wifi_overview_finds_channel_conflicts(api):
    ap2 = "aaaaaaaa-0000-0000-0000-000000000004"
    devices = [
        {**device(SWITCH, "Switch"), "interfaces": ["ports"]},
        {**device(AP, "AP 1"), "interfaces": ["radios"]},
        {**device(ap2, "AP 2"), "interfaces": ["ports", "radios"]},
    ]
    api.get(f"/v1/sites/{SITE}/devices").respond(json=page(devices))
    for device_id, name, channel in [(AP, "AP 1", 6), (ap2, "AP 2", 6)]:
        radios = [
            {
                "frequencyGHz": 2.4,
                "channel": channel,
                "channelWidthMHz": 20,
                "txPowerMode": "AUTO",
            }
        ]
        api.get(f"/v1/sites/{SITE}/devices/{device_id}").respond(
            json={**device(device_id, name), "interfaces": {"radios": radios}}
        )
    api.get(f"/v1/sites/{SITE}/devices/{AP}/statistics/latest").respond(
        json={"interfaces": {"radios": [{"frequencyGHz": 2.4, "txRetriesPct": 30}]}}
    )
    api.get(f"/v1/sites/{SITE}/devices/{ap2}/statistics/latest").respond(
        404, json={"message": "No statistics"}
    )
    broadcasts = [
        {
            "id": "w1",
            "name": "Home",
            "enabled": True,
            "network": {"type": "NATIVE"},
            "securityConfiguration": {"type": "WPA2_PERSONAL"},
        },
        {
            "id": "w2",
            "name": "IoT",
            "enabled": False,
            "network": {"type": "SPECIFIC", "networkId": "n2"},
            "securityConfiguration": {"type": "WPA2_PERSONAL"},
        },
    ]
    api.get(f"/v1/sites/{SITE}/wifi/broadcasts").respond(json=page(broadcasts))
    api.get(f"/v1/sites/{SITE}/networks").respond(
        json=page(
            [
                {"id": "n1", "name": "Default", "default": True},
                {"id": "n2", "name": "Things"},
            ]
        )
    )
    api.get(f"/v1/sites/{SITE}/clients").respond(
        json=page(
            [
                {"type": "WIRELESS", "uplinkDeviceId": AP},
                {"type": "WIRELESS", "uplinkDeviceId": AP},
                {"type": "WIRED", "uplinkDeviceId": SWITCH},
            ]
        )
    )

    async with Client(make_server(default_site_id=SITE)) as client:
        overview = (await client.call_tool("get_wifi_overview")).data

    assert [b["network"] for b in overview["broadcasts"]] == ["Default", "Things"]
    first, second = overview["accessPoints"]
    assert (first["name"], first["wirelessClients"]) == ("AP 1", 2)
    assert first["radios"][0]["txRetriesPct"] == 30
    assert first["radios"][0]["txPowerMode"] == "AUTO"
    assert "No statistics" in second["statisticsError"]
    assert overview["wirelessClientCount"] == 2
    assert len(overview["issues"]) == 3
    assert "channel 6" in overview["issues"][0]


async def test_switch_port_report_lists_slow_ports(api):
    devices = [
        {**device(SWITCH, "Switch"), "interfaces": ["ports"]},
        {**device(AP, "AP"), "interfaces": ["radios"]},
    ]
    api.get(f"/v1/sites/{SITE}/devices").respond(json=page(devices))
    ports = [
        {"idx": 1, "state": "UP", "speedMbps": 100, "maxSpeedMbps": 1000},
        {
            "idx": 2,
            "state": "UP",
            "speedMbps": 1000,
            "maxSpeedMbps": 1000,
            "poe": {"enabled": True, "state": "LIMITED", "standard": "802.3at"},
        },
        {"idx": 3, "state": "DOWN", "maxSpeedMbps": 1000},
    ]
    detail = api.get(f"/v1/sites/{SITE}/devices/{SWITCH}").respond(
        json={**device(SWITCH, "Switch"), "interfaces": {"ports": ports}}
    )
    ap_detail = api.get(f"/v1/sites/{SITE}/devices/{AP}")
    api.get(f"/v1/sites/{SITE}/clients").respond(
        json=page([{"type": "WIRED", "uplinkDeviceId": SWITCH}])
    )

    async with Client(make_server(default_site_id=SITE)) as client:
        report = (await client.call_tool("get_switch_port_report")).data

    assert detail.called and not ap_detail.called
    [switch] = report["devices"]
    assert switch["wiredClients"] == 1
    assert switch["portsByState"] == {"UP": 2, "DOWN": 1}
    assert switch["poePortsByState"] == {"LIMITED": 1}
    assert [port["idx"] for port in switch["portsBelowMaxSpeed"]] == [1]
    assert len(report["issues"]) == 2


async def test_network_map_shows_zones_and_duplicate_vlans(api):
    networks = [
        {"id": "n1", "name": "Default", "vlanId": 1, "default": True},
        {"id": "n2", "name": "IoT", "vlanId": 20},
        {"id": "n3", "name": "Cameras", "vlanId": 20},
    ]
    api.get(f"/v1/sites/{SITE}/networks").respond(json=page(networks))
    api.get(f"/v1/sites/{SITE}/networks/n1").respond(
        json={
            **networks[0],
            "ipv4Configuration": {
                "hostIpAddress": "192.168.1.1",
                "prefixLength": 24,
                "dhcpConfiguration": {"mode": "SERVER"},
            },
        }
    )
    api.get(f"/v1/sites/{SITE}/networks/n2").respond(json=networks[1])
    api.get(f"/v1/sites/{SITE}/networks/n3").respond(json=networks[2])
    api.get(f"/v1/sites/{SITE}/firewall/zones").respond(
        json=page([{"id": "z1", "name": "Internal", "networkIds": ["n1"]}])
    )
    api.get(f"/v1/sites/{SITE}/wifi/broadcasts").respond(
        json=page([{"id": "w1", "name": "Home", "network": {"type": "NATIVE"}}])
    )

    async with Client(make_server(default_site_id=SITE)) as client:
        network_map = (await client.call_tool("get_network_map")).data

    default = network_map["networks"][0]
    assert default["subnet"] == "192.168.1.1/24"
    assert default["dhcp"] == "SERVER"
    assert default["zone"] == "Internal"
    assert default["wifiBroadcasts"] == ["Home"]
    assert network_map["issues"] == [
        "More than one network uses VLAN 20: IoT, Cameras."
    ]


async def test_client_summary_counts_by_uplink_device(api):
    clients = [
        {"id": "c1", "type": "WIRED", "uplinkDeviceId": SWITCH, "connectedAt": "1"},
        {"id": "c2", "type": "WIRELESS", "uplinkDeviceId": AP, "connectedAt": "3"},
        {"id": "c3", "type": "WIRELESS", "uplinkDeviceId": AP, "connectedAt": "2"},
        {"id": "c4", "type": "VPN", "access": {"type": "DEFAULT"}},
    ]
    api.get(f"/v1/sites/{SITE}/clients").respond(json=page(clients))
    api.get(f"/v1/sites/{SITE}/devices").respond(
        json=page([device(SWITCH, "Switch"), device(AP, "AP")])
    )

    async with Client(make_server(default_site_id=SITE)) as client:
        summary = (await client.call_tool("get_client_summary")).data

    assert summary["byType"] == {"WIRED": 1, "WIRELESS": 2, "VPN": 1}
    assert summary["withoutUplinkDevice"] == 1
    assert [row["name"] for row in summary["byUplinkDevice"]] == ["AP", "Switch"]
    assert [row["id"] for row in summary["newest"]] == ["c2", "c3", "c1"]
    assert summary["newest"][0]["uplinkDeviceName"] == "AP"


async def test_find_client_matches_name_ip_and_mac(api):
    clients = [
        {"id": "c1", "name": "Office Laptop", "ipAddress": "10.0.0.5"},
        {"id": "c2", "name": "Phone", "macAddress": "AA:BB:CC:00:11:22"},
        {"id": "c3", "name": "TV", "ipAddress": "10.0.1.9", "uplinkDeviceId": AP},
    ]
    api.get(f"/v1/sites/{SITE}/clients").respond(json=page(clients))
    api.get(f"/v1/sites/{SITE}/devices").respond(json=page([device(AP, "AP")]))

    async with Client(make_server(default_site_id=SITE)) as client:

        async def ids(query):
            result = (await client.call_tool("find_client", {"query": query})).data
            return [row["id"] for row in result["clients"]]

        assert await ids("laptop") == ["c1"]
        assert await ids("aabb.cc00") == ["c2"]
        assert await ids("10.0.1") == ["c3"]


async def test_find_unused_objects(api):
    resources = {
        "networks": [
            {"id": "n1", "name": "Default", "default": True},
            {"id": "n2", "name": "Old", "enabled": False},
            {"id": "n3", "name": "Used"},
        ],
        "firewall/zones": [
            {
                "id": "z1",
                "name": "Empty",
                "networkIds": [],
                "metadata": {"origin": "USER_DEFINED"},
            },
            {
                "id": "z2",
                "name": "External",
                "networkIds": [],
                "metadata": {"origin": "SYSTEM_DEFINED"},
            },
        ],
        "firewall/policies": [
            {
                "id": "p1",
                "name": "Allow web",
                "destination": {
                    "trafficFilter": {"portFilter": {"trafficMatchingListId": "t1"}}
                },
            }
        ],
        "traffic-matching-lists": [
            {"id": "t1", "name": "Web"},
            {"id": "t2", "name": "Unused"},
        ],
        "device-tags": [{"id": "d1", "name": "Empty tag", "deviceIds": []}],
        "wifi/broadcasts": [],
        "acl-rules": [],
        "dns/policies": [{"id": "s1", "domain": "old.lan", "enabled": False}],
    }
    for path, items in resources.items():
        api.get(f"/v1/sites/{SITE}/{path}").respond(json=page(items))
    references = f"/v1/sites/{SITE}/networks/{{}}/references"
    api.get(references.format("n1")).respond(json={"referenceResources": []})
    api.get(references.format("n2")).respond(json={"referenceResources": []})
    api.get(references.format("n3")).respond(
        json={"referenceResources": [{"resourceType": "CLIENT", "referenceCount": 2}]}
    )

    async with Client(make_server(default_site_id=SITE)) as client:
        audit = (await client.call_tool("find_unused_objects")).data

    assert audit["unusedTrafficMatchingLists"] == [{"id": "t2", "name": "Unused"}]
    assert [n["name"] for n in audit["networksWithoutReferences"]] == ["Old"]
    assert audit["customZonesWithoutNetworks"] == [{"id": "z1", "name": "Empty"}]
    assert audit["deviceTagsWithoutDevices"] == [{"id": "d1", "name": "Empty tag"}]
    assert audit["disabled"] == {
        "networks": [{"id": "n2", "name": "Old"}],
        "dnsPolicies": [{"id": "s1", "name": "old.lan"}],
    }


async def test_voucher_summary_counts_and_hides_codes(api):
    vouchers = [
        {"id": "v1", "code": "111", "expired": True},
        {
            "id": "v2",
            "code": "222",
            "activatedAt": "2026-01-01T00:00:00Z",
            "expiresAt": "2000-01-01T00:00:00Z",
            "authorizedGuestCount": 1,
            "authorizedGuestLimit": 1,
        },
        {"id": "v3", "code": "333", "expiresAt": "2999-01-01T00:00:00Z"},
    ]
    api.get(f"/v1/sites/{SITE}/hotspot/vouchers").respond(json=page(vouchers))

    async with Client(make_server(default_site_id=SITE)) as client:
        summary = (await client.call_tool("get_voucher_summary")).data

    assert (summary["expired"], summary["active"], summary["unused"]) == (1, 1, 1)
    assert [v["id"] for v in summary["expiringSoon"]] == ["v2"]
    assert [v["id"] for v in summary["fullyUsed"]] == ["v2"]
    assert "code" not in summary["fullyUsed"][0]


POLICIES = f"/v1/sites/{SITE}/firewall/policies"
WRITE_TOOLS = {
    "create_firewall_policy",
    "update_firewall_policy",
    "delete_firewall_policy",
    "reorder_firewall_policies",
    "adopt_device",
    "remove_device",
    "restart_device",
    "power_cycle_port",
    "authorize_guest",
    "unauthorize_guest",
    "create_vouchers",
    "delete_voucher",
    "delete_vouchers",
}
DEVICES = f"/v1/sites/{SITE}/devices"
CLIENTS = f"/v1/sites/{SITE}/clients"
VOUCHERS = f"/v1/sites/{SITE}/hotspot/vouchers"


def sent_json(route):
    return json.loads(route.calls.last.request.content)


async def test_write_tools_need_allow_writes():
    async with Client(make_server(allow_writes=True)) as client:
        tools = await client.list_tools()
    writes = {tool.name for tool in tools if not tool.annotations.read_only_hint}
    assert len(tools) == 64
    assert writes == WRITE_TOOLS


async def test_hidden_write_tools_cannot_be_called(api):
    route = api.delete(f"{POLICIES}/p1")
    async with Client(make_server(default_site_id=SITE)) as client:
        with pytest.raises(ToolError):
            await client.call_tool(
                "delete_firewall_policy", {"firewall_policy_id": "p1"}
            )
    assert not route.called


async def test_create_firewall_policy_sends_the_api_body(api):
    route = api.post(POLICIES).respond(201, json={"id": "p1"})
    ports = {
        "type": "PORTS",
        "items": [
            {"type": "PORT_NUMBER", "value": 53},
            {"type": "PORT_NUMBER_RANGE", "start": 8000, "stop": 8080},
        ],
    }
    schedule = {
        "mode": "EVERY_WEEK",
        "repeatOnDays": ["SATURDAY"],
        "timeFilter": {"startTime": "22:00", "stopTime": "06:00"},
    }
    async with Client(make_server(SITE, allow_writes=True)) as client:
        result = await client.call_tool(
            "create_firewall_policy",
            {
                "name": "Block DNS",
                "action": {"type": "REJECT"},
                "source": {"zoneId": "z1"},
                "destination": {
                    "zoneId": "z2",
                    "trafficFilter": {"type": "PORT", "portFilter": ports},
                },
                "schedule": schedule,
            },
        )

    assert result.data == {"id": "p1"}
    # The body includes the default values of the models.
    sent_ports = ports | {"matchOpposite": False}
    assert sent_json(route) == {
        "name": "Block DNS",
        "enabled": True,
        "action": {"type": "REJECT"},
        "source": {"zoneId": "z1"},
        "destination": {
            "zoneId": "z2",
            "trafficFilter": {"type": "PORT", "portFilter": sent_ports},
        },
        "ipProtocolScope": {"ipVersion": "IPV4_AND_IPV6"},
        "schedule": schedule,
        "loggingEnabled": False,
        "reportFlowEnabled": True,
    }


@pytest.mark.parametrize(
    "change",
    [
        # A MAC address filter is only for the source.
        {"destination": {"zoneId": "z2", "trafficFilter": {"type": "MAC_ADDRESS"}}},
        # ICMP is only for IPv4.
        {
            "ip_protocol_scope": {
                "ipVersion": "IPV4_AND_IPV6",
                "protocolFilter": {
                    "type": "NAMED_PROTOCOL",
                    "protocol": {"name": "ICMP"},
                },
            }
        },
        {"action": {"type": "ALLOW", "unknown": True}},
    ],
)
async def test_create_firewall_policy_checks_the_body(api, change):
    route = api.post(POLICIES)
    arguments = {
        "name": "Bad",
        "action": {"type": "BLOCK"},
        "source": {"zoneId": "z1"},
        "destination": {"zoneId": "z2"},
    }
    async with Client(make_server(SITE, allow_writes=True)) as client:
        with pytest.raises(ToolError):
            await client.call_tool("create_firewall_policy", arguments | change)
    assert not route.called


@pytest.mark.parametrize(
    ("arguments", "body"),
    [
        ({"logging_enabled": True}, {"loggingEnabled": True}),
        ({"report_flow_enabled": False}, {"reportFlowEnabled": False}),
        (
            {"logging_enabled": True, "report_flow_enabled": False},
            {"loggingEnabled": True, "reportFlowEnabled": False},
        ),
    ],
)
async def test_update_of_only_the_patch_fields_sends_a_patch(api, arguments, body):
    route = api.patch(f"{POLICIES}/p1").respond(json={"id": "p1"})
    async with Client(make_server(SITE, allow_writes=True)) as client:
        await client.call_tool(
            "update_firewall_policy", {"firewall_policy_id": "p1"} | arguments
        )
    assert sent_json(route) == body


async def test_update_merges_the_changes_into_the_policy(api):
    policy = {
        "name": "Guests",
        "enabled": True,
        "action": {"type": "BLOCK"},
        "source": {"zoneId": "z1"},
        "destination": {"zoneId": "z2"},
        "ipProtocolScope": {"ipVersion": "IPV4"},
        "schedule": {
            "mode": "EVERY_DAY",
            "timeFilter": {"startTime": "08:00", "stopTime": "18:00"},
        },
        "loggingEnabled": False,
        "reportFlowEnabled": True,
    }
    response_only = {"id": "p1", "index": 10000, "metadata": {"origin": "USER_DEFINED"}}
    api.get(f"{POLICIES}/p1").respond(json=policy | response_only)
    route = api.put(f"{POLICIES}/p1").respond(json={"id": "p1"})

    async with Client(make_server(SITE, allow_writes=True)) as client:
        await client.call_tool(
            "update_firewall_policy",
            {
                "firewall_policy_id": "p1",
                "enabled": False,
                "action": {"type": "ALLOW"},
                "clear": ["schedule"],
            },
        )

    del policy["schedule"]
    assert sent_json(route) == policy | {
        "enabled": False,
        "action": {"type": "ALLOW", "allowReturnTraffic": True},
    }


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({}, "at least one field"),
        ({"clear": ["description"], "description": "x"}, "clear"),
    ],
)
async def test_update_rejects_unclear_changes(api, arguments, message):
    async with Client(make_server(SITE, allow_writes=True)) as client:
        with pytest.raises(ToolError, match=message):
            await client.call_tool(
                "update_firewall_policy", {"firewall_policy_id": "p1"} | arguments
            )


async def test_delete_firewall_policy_returns_the_id(api):
    route = api.delete(f"{POLICIES}/p1").respond(200)
    async with Client(make_server(SITE, allow_writes=True)) as client:
        result = await client.call_tool(
            "delete_firewall_policy", {"firewall_policy_id": "p1"}
        )
    assert route.called
    assert result.data == {"deletedFirewallPolicyId": "p1"}


async def test_reorder_sends_the_zone_pair_and_the_order(api):
    route = api.put(f"{POLICIES}/ordering").respond(json={})
    async with Client(make_server(SITE, allow_writes=True)) as client:
        await client.call_tool(
            "reorder_firewall_policies",
            {
                "source_firewall_zone_id": "z1",
                "destination_firewall_zone_id": "z2",
                "before_system_defined": ["p2", "p1"],
                "after_system_defined": [],
            },
        )
    params = route.calls.last.request.url.params
    assert (params["sourceFirewallZoneId"], params["destinationFirewallZoneId"]) == (
        "z1",
        "z2",
    )
    assert sent_json(route) == {
        "orderedFirewallPolicyIds": {
            "beforeSystemDefined": ["p2", "p1"],
            "afterSystemDefined": [],
        }
    }


async def test_rejected_writes_mention_the_api_key(api):
    api.delete(f"{POLICIES}/p1").respond(403, json={"message": "Forbidden"})
    async with Client(make_server(SITE, allow_writes=True)) as client:
        with pytest.raises(ToolError, match="Forbidden.*write access"):
            await client.call_tool(
                "delete_firewall_policy", {"firewall_policy_id": "p1"}
            )


async def test_adopt_device_sends_the_mac_address(api):
    route = api.post(DEVICES).respond(json={"id": GATEWAY})
    async with Client(make_server(SITE, allow_writes=True)) as client:
        result = await client.call_tool(
            "adopt_device", {"mac_address": "aa:bb:cc:00:00:01"}
        )
    assert result.data == {"id": GATEWAY}
    assert sent_json(route) == {
        "macAddress": "aa:bb:cc:00:00:01",
        "ignoreDeviceLimit": False,
    }


async def test_remove_device_returns_the_id(api):
    route = api.delete(f"{DEVICES}/{AP}")
    async with Client(make_server(SITE, allow_writes=True)) as client:
        result = await client.call_tool("remove_device", {"device_id": AP})
    assert route.called
    assert result.data == {"removedDeviceId": AP}


@pytest.mark.parametrize(
    ("tool", "arguments", "path", "expected"),
    [
        (
            "restart_device",
            {"device_id": AP},
            f"{DEVICES}/{AP}/actions",
            {"deviceId": AP, "action": "RESTART"},
        ),
        (
            "power_cycle_port",
            {"device_id": SWITCH, "port_idx": 5},
            f"{DEVICES}/{SWITCH}/interfaces/ports/5/actions",
            {"deviceId": SWITCH, "portIdx": 5, "action": "POWER_CYCLE"},
        ),
    ],
)
async def test_device_actions_send_the_action(api, tool, arguments, path, expected):
    route = api.post(path)
    async with Client(make_server(SITE, allow_writes=True)) as client:
        result = await client.call_tool(tool, arguments)
    assert sent_json(route) == {"action": expected["action"]}
    assert result.data == expected


async def test_power_cycle_port_rejects_a_port_index_below_one(api):
    route = api.post(f"{DEVICES}/{SWITCH}/interfaces/ports/0/actions")
    async with Client(make_server(SITE, allow_writes=True)) as client:
        with pytest.raises(ToolError):
            await client.call_tool(
                "power_cycle_port", {"device_id": SWITCH, "port_idx": 0}
            )
    assert not route.called


async def test_authorize_guest_sends_only_the_given_limits(api):
    response = {"action": "AUTHORIZE_GUEST_ACCESS", "grantedAuthorization": {}}
    route = api.post(f"{CLIENTS}/c1/actions").respond(json=response)
    async with Client(make_server(SITE, allow_writes=True)) as client:
        result = await client.call_tool(
            "authorize_guest",
            {
                "client_id": "c1",
                "time_limit_minutes": 60,
                "data_usage_limit_mbytes": 500,
            },
        )
    assert result.data == response
    assert sent_json(route) == {
        "action": "AUTHORIZE_GUEST_ACCESS",
        "timeLimitMinutes": 60,
        "dataUsageLimitMBytes": 500,
    }


async def test_unauthorize_guest_sends_the_action(api):
    route = api.post(f"{CLIENTS}/c1/actions").respond(
        json={"action": "UNAUTHORIZE_GUEST_ACCESS", "revokedAuthorization": {}}
    )
    async with Client(make_server(SITE, allow_writes=True)) as client:
        await client.call_tool("unauthorize_guest", {"client_id": "c1"})
    assert sent_json(route) == {"action": "UNAUTHORIZE_GUEST_ACCESS"}


async def test_create_vouchers_sends_the_limits(api):
    route = api.post(VOUCHERS).respond(201, json={"vouchers": [{"id": "v1"}]})
    async with Client(make_server(SITE, allow_writes=True)) as client:
        result = await client.call_tool(
            "create_vouchers",
            {
                "name": "Conference",
                "time_limit_minutes": 480,
                "count": 20,
                "authorized_guest_limit": 1,
                "rx_rate_limit_kbps": 10000,
            },
        )
    assert result.data == {"vouchers": [{"id": "v1"}]}
    assert sent_json(route) == {
        "name": "Conference",
        "count": 20,
        "timeLimitMinutes": 480,
        "authorizedGuestLimit": 1,
        "rxRateLimitKbps": 10000,
    }


@pytest.mark.parametrize(
    "change", [{"count": 1001}, {"time_limit_minutes": 0}, {"tx_rate_limit_kbps": 1}]
)
async def test_create_vouchers_checks_the_limits(api, change):
    route = api.post(VOUCHERS)
    arguments = {"name": "Guests", "time_limit_minutes": 60} | change
    async with Client(make_server(SITE, allow_writes=True)) as client:
        with pytest.raises(ToolError):
            await client.call_tool("create_vouchers", arguments)
    assert not route.called


async def test_delete_voucher_returns_the_deleted_count(api):
    api.delete(f"{VOUCHERS}/v1").respond(json={"vouchersDeleted": 1})
    async with Client(make_server(SITE, allow_writes=True)) as client:
        result = await client.call_tool("delete_voucher", {"voucher_id": "v1"})
    assert result.data == {"vouchersDeleted": 1}


async def test_delete_vouchers_sends_the_filter(api):
    route = api.delete(VOUCHERS).respond(json={"vouchersDeleted": 3})
    async with Client(make_server(SITE, allow_writes=True)) as client:
        result = await client.call_tool(
            "delete_vouchers", {"filter": "expired.eq(true)"}
        )
    assert route.calls.last.request.url.params["filter"] == "expired.eq(true)"
    assert result.data == {"vouchersDeleted": 3}


async def test_wifi_passphrases_are_redacted(api):
    broadcast = {
        "id": "w1",
        "name": "Home",
        "securityConfiguration": {
            "type": "WPA2_PERSONAL",
            "passphrase": "correct horse",
            "presharedKeys": [{"passphrase": "battery staple", "network": {}}],
        },
    }
    api.get(f"/v1/sites/{SITE}/wifi/broadcasts/w1").respond(json=broadcast)
    async with Client(make_server(SITE)) as client:
        result = await client.call_tool(
            "get_wifi_broadcast", {"wifi_broadcast_id": "w1"}
        )
    security = result.data["securityConfiguration"]
    assert security["passphrase"] == REDACTED
    assert security["presharedKeys"][0]["passphrase"] == REDACTED
    assert "correct horse" not in result.content[0].text


async def test_writes_refuse_the_redaction_placeholder(api):
    route = api.post(VOUCHERS)
    client = UniFiClient(httpx.AsyncClient(base_url=BASE))
    with pytest.raises(ToolError, match="REDACTED"):
        await client.post(VOUCHERS, {"security": {"passphrase": REDACTED}})
    assert not route.called


def test_redact_keeps_empty_secrets_and_other_values():
    assert redact({"passphrase": None, "items": [1, {"name": "a"}]}) == {
        "passphrase": None,
        "items": [1, {"name": "a"}],
    }
