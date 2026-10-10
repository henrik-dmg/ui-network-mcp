from datetime import datetime, timedelta

from unifi_mcp.client import JSON


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def voucher_row(voucher: JSON) -> JSON:
    """Return the main fields of a voucher. The row does not include the secret code."""
    row = {
        key: voucher.get(key)
        for key in (
            "id",
            "name",
            "createdAt",
            "activatedAt",
            "expiresAt",
            "authorizedGuestCount",
            "authorizedGuestLimit",
        )
    }
    return {key: value for key, value in row.items() if value is not None}


def build_voucher_summary(
    site_id: str, vouchers: list[JSON], now: datetime, expiring_within: timedelta
) -> JSON:
    """Count the vouchers by status, and list the vouchers that expire soon or are fully used.

    A voucher is expired, active (a guest used it), or unused.
    """
    expired = [voucher for voucher in vouchers if voucher.get("expired")]
    valid = [voucher for voucher in vouchers if not voucher.get("expired")]
    active = [voucher for voucher in valid if voucher.get("activatedAt")]
    unused = [voucher for voucher in valid if not voucher.get("activatedAt")]

    expiring = []
    for voucher in valid:
        expires_at = parse_time(voucher.get("expiresAt"))
        if expires_at and expires_at <= now + expiring_within:
            expiring.append(voucher)
    fully_used = [
        voucher
        for voucher in valid
        if voucher.get("authorizedGuestLimit") is not None
        and voucher.get("authorizedGuestCount", 0) >= voucher["authorizedGuestLimit"]
    ]

    return {
        "siteId": site_id,
        "total": len(vouchers),
        "expired": len(expired),
        "active": len(active),
        "unused": len(unused),
        "authorizedGuests": sum(
            voucher.get("authorizedGuestCount", 0) for voucher in vouchers
        ),
        "expiringSoon": [
            voucher_row(voucher)
            for voucher in sorted(expiring, key=lambda voucher: voucher["expiresAt"])
        ],
        "fullyUsed": [voucher_row(voucher) for voucher in fully_used],
    }
