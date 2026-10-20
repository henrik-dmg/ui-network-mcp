"""Annotated parameter types and annotations that the tools share."""

from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from unifi_mcp.client import MAX_PAGE_SIZE

FILTER_HELP = (
    "Optional filter expression, for example name.like('AP*') or "
    "and(state.eq('ONLINE'), model.eq('U7PG2')). The filterable properties differ per endpoint."
)

READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, open_world_hint=True
)
# The tools with the write tag change the network. The server hides them unless
# UNIFI_ALLOW_WRITES is true.
WRITE_TAG = "write"
# A write that adds an object and changes no existing object.
ADDITIVE_WRITE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)
# A write that changes or deletes an existing object.
DESTRUCTIVE_WRITE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)

SiteId = Annotated[
    str | None, Field(description="Site ID. Omit it to use the default site.")
]
Filter = Annotated[str | None, Field(description=FILTER_HELP)]
Limit = Annotated[int, Field(ge=1, le=MAX_PAGE_SIZE, description="Page size (1-200).")]
Offset = Annotated[int, Field(ge=0, description="Number of items to skip.")]
