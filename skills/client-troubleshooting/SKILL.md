---
name: client-troubleshooting
description: Troubleshooting of one client on a UniFi network, such as a laptop, phone, or TV that is slow, drops its connection, or has no connection. Use when the user asks why a device on the UniFi network is slow, offline, or unstable.
---

# UniFi client troubleshooting

Find the probable **cause** of the problem of one client. Examine each device on the **path** from the client to the gateway. All tools in this skill are read-only, except `authorize_guest` in step 3.

## Limits of the API

The integration API does not show the signal strength of a client, the traffic of a client, the history of its connections, or the switch port of a wired client. Tell the user about these limits when they are important for the problem. The UniFi Network app shows these data.

## Steps

1. Call `find_client` with the name, the IP address, or the MAC address that the user gives.
   - If there is no match, the client is not connected now: the API shows only connected clients. Tell this to the user, and ask for another name, the IP address, or the MAC address. If the client is still not found, continue with step 5 for the device that the client usually connects to, if the user knows it.
   - If there is more than one match, ask the user which client.
2. Call `get_client` with the client ID. Record `type`, `connectedAt`, and `access`.
   - A `connectedAt` in the last minutes can show that the client connects again and again.
3. If `access.type` is `GUEST` and `access.authorized` is false, the client has no access to the network. That is the probable cause. `authorize_guest` gives access, but it changes the network: show the change and get the approval of the user first. If `access.authorization.expiresAt` is soon, tell the user.
4. Call `get_device` and `get_device_statistics` for the `uplinkDeviceId` of the client. Record the state, `cpuUtilizationPct`, `memoryUtilizationPct`, `uptimeSec`, and the uplink rates.
5. Examine the connection of the client:
   - For a `WIRELESS` client, call `get_wifi_overview`. Find the access point of the client in `accessPoints`. Record its radios (channel, channel width, transmit retries), its number of wireless clients, and each item in `issues` that names this access point.
   - For a `WIRED` client, call `get_switch_port_report`. Find the uplink device in `devices`. Record its ports below the maximum speed and its ports with limited PoE power. The API does not show which port the client uses, so these ports are only possible causes.
   - For a `VPN` or `TELEPORT` client, the client connects through the internet. Examine the WAN of the site with `get_site_health`.
6. Call `get_topology`. Follow the uplinks from the uplink device of the client to the gateway. Record each device on this path that is not online, has CPU or memory above 80 %, or restarted in the last 24 hours (`get_device_health` shows these values for all devices).

The examination is complete when each device on the path from the client to the gateway was examined, and each recorded value is in the report.

## Probable causes

| Evidence | Probable cause |
|-|-|
| The client is a guest without authorization. | The client has no access to the network. |
| A device on the path is not online, or restarted recently. | The connection breaks at that device. |
| The access point uses the same channel as another access point, or has more than 15 % transmit retries. | Radio interference or a weak signal. |
| The access point has many more wireless clients than the other access points. | The access point is overloaded. |
| A port of the uplink switch runs below its maximum speed, for example at 100 Mbit/s. | A bad cable or a bad connector. |
| A device on the path has CPU or memory above 90 %. | The device is overloaded. |

## Report

1. The client: name, type, IP address, uplink device, and the time of the connection.
2. The probable causes, the most probable first, each with its evidence.
3. The next steps for the user. A step that changes the network, for example `restart_device` or `power_cycle_port`, needs the approval of the user first.
4. The data that the API cannot show, if they are important for this problem.
