from typing import Literal

from pydantic import Field

from ui_network_mcp.models.api_model import ApiModel
from ui_network_mcp.models.firewall.traffic_filters import (
    DestinationTrafficFilter,
    SourceTrafficFilter,
)

ConnectionState = Literal["NEW", "INVALID", "ESTABLISHED", "RELATED"]
IpsecFilter = Literal["MATCH_ENCRYPTED", "MATCH_NOT_ENCRYPTED"]


class FirewallPolicySource(ApiModel):
    zone_id: str = Field(description="The firewall zone where the traffic comes from.")
    traffic_filter: SourceTrafficFilter | None = Field(
        None, description="Omit it to match all traffic from the zone."
    )


class FirewallPolicyDestination(ApiModel):
    zone_id: str = Field(description="The firewall zone where the traffic goes to.")
    traffic_filter: DestinationTrafficFilter | None = Field(
        None, description="Omit it to match all traffic to the zone."
    )
