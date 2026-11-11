---
name: health-check
description: Health check of a UniFi network, with a ranked list of its problems. Use when the user asks how the network is, asks for a status report, or asks what needs attention on a UniFi site.
---

# UniFi health check

Make one **ranked** list of the problems of a UniFi site. Each problem has **evidence**: the tool result and the values that show the problem. All tools in this skill are read-only.

## Steps

1. Call `get_site_health`. If the tool asks for a `site_id`, call `list_sites`, and ask the user which site to check. Record each item in `issues`, and each device in `devices.notOnline`.
2. Call `get_device_health`. Record each device that has one of these values:
   - `cpuUtilizationPct` or `memoryUtilizationPct` above 80.
   - `uptimeSec` below 86400. The device restarted in the last 24 hours.
   - A `statisticsError`.
3. Call `get_topology`. For each device that is not online, find its `downlinks`. These devices and their clients have no connection either.
4. Call `get_wifi_overview`. Record each item in `issues`: channel conflicts, transmit retries above 15 %, and disabled broadcasts.
5. Call `get_switch_port_report`. Record each item in `issues`: ports below their maximum speed, and ports with limited PoE power.
6. Give each recorded problem a severity from the table below. Merge the problems that have the same cause. For example, an offline switch and the offline access points behind it are one problem.
7. Write the report.

The check is complete when each item that steps 1 to 5 recorded is in the report, or is in the list of dismissed items with a reason.

## Severity

| Severity | Problems |
|-|-|
| Critical | The gateway is not online. A device that is not online has downlinks. The site has a gateway, but `wans` is empty. |
| High | Another device is not online. CPU or memory is above 90 %. A port has limited PoE power. |
| Medium | CPU or memory is above 80 %. Two access points use the same channel. A radio has more than 15 % transmit retries. A port runs below its maximum speed, for example 100 Mbit/s on a 1 Gbit/s port. One model has different firmware versions. A device restarted in the last 24 hours. |
| Low | A firmware update is available. A device waits for adoption. A WiFi broadcast is disabled. |

A disabled broadcast or a pending device can be intentional. Show these problems, but do not give them a higher severity.

## Report

1. One sentence about the state of the site, for example "The site is healthy, with 2 low problems."
2. A table with the columns Severity, Problem, Device, Evidence, and Next step. Put the most severe problem first.
3. The dismissed items, each with its reason.
4. A short "Not checked" section. The integration API does not show these data: the signal strength of clients, traffic history, events, and alarms. The UniFi Network app shows them.

For a firmware update, a restart, or a change of the WiFi channels, the next step is an action in the UniFi Network app. Some actions have a tool, for example `restart_device`. A tool that changes the network needs the approval of the user first.
