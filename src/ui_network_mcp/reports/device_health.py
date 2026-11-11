from ui_network_mcp.client import JSON
from ui_network_mcp.reports.device_summary import device_summary


def build_device_health(
    site_id: str, devices: list[JSON], statistics: list[JSON | Exception]
) -> JSON:
    """Combine each device with its statistics, and sort the devices that need attention first."""
    rows = []
    for device, stats in zip(devices, statistics, strict=True):
        row = device_summary(device, "state")
        if isinstance(stats, Exception):
            row["statisticsError"] = str(stats)
        else:
            row.update(
                {
                    key: stats.get(key)
                    for key in (
                        "uptimeSec",
                        "cpuUtilizationPct",
                        "memoryUtilizationPct",
                        "loadAverage1Min",
                        "loadAverage5Min",
                        "loadAverage15Min",
                        "lastHeartbeatAt",
                    )
                }
            )
            uplink = stats.get("uplink") or {}
            row["uplinkRxRateBps"] = uplink.get("rxRateBps")
            row["uplinkTxRateBps"] = uplink.get("txRateBps")
            radios = (stats.get("interfaces") or {}).get("radios")
            if radios:
                row["radios"] = radios
        rows.append({key: value for key, value in row.items() if value is not None})

    def attention(row: JSON) -> tuple[bool, float]:
        usage = max(
            row.get("cpuUtilizationPct") or 0, row.get("memoryUtilizationPct") or 0
        )
        return (row.get("state") == "ONLINE", -usage)

    return {
        "siteId": site_id,
        "deviceCount": len(devices),
        "devices": sorted(rows, key=attention),
    }
