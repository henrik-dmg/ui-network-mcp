from typing import Annotated, Literal

from pydantic import Field

from ui_network_mcp.models.api_model import ApiModel


class AllowAction(ApiModel):
    """Allow the matched traffic."""

    type: Literal["ALLOW"]
    allow_return_traffic: bool = Field(
        True,
        description="Also allow the return traffic. The console adds a derived policy for the opposite zone pair.",
    )


class BlockAction(ApiModel):
    """Drop the matched traffic and send no reply."""

    type: Literal["BLOCK"]


class RejectAction(ApiModel):
    """Drop the matched traffic and send a reject reply."""

    type: Literal["REJECT"]


FirewallPolicyAction = Annotated[
    AllowAction | BlockAction | RejectAction, Field(discriminator="type")
]
