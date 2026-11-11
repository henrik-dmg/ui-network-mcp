"""The time when a firewall policy is active. Without a schedule, the policy is always active."""

import datetime
from typing import Annotated, Literal

from pydantic import Field

from ui_network_mcp.models.api_model import ApiModel

Time = Annotated[
    str,
    Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$", description="HH:MM, 24-hour clock."),
]
Weekday = Literal[
    "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"
]
Weekdays = Annotated[list[Weekday], Field(min_length=1)]


class TimeFilter(ApiModel):
    start_time: Time
    stop_time: Time


class EveryDaySchedule(ApiModel):
    mode: Literal["EVERY_DAY"]
    time_filter: TimeFilter


class EveryWeekSchedule(ApiModel):
    mode: Literal["EVERY_WEEK"]
    repeat_on_days: Weekdays
    time_filter: TimeFilter | None = Field(
        None, description="Omit it to make the policy active all day."
    )


class OneTimeSchedule(ApiModel):
    mode: Literal["ONE_TIME_ONLY"]
    date: datetime.date
    time_filter: TimeFilter


class CustomSchedule(ApiModel):
    mode: Literal["CUSTOM"]
    repeat_on_days: Weekdays
    start_date: datetime.date
    stop_date: datetime.date
    time_filter: TimeFilter | None = Field(
        None, description="Omit it to make the policy active all day."
    )


Schedule = Annotated[
    EveryDaySchedule | EveryWeekSchedule | OneTimeSchedule | CustomSchedule,
    Field(discriminator="mode"),
]
