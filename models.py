"""Data models for the Fly-in map, validated with Pydantic"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator, PositiveInt


class ZoneType(str, Enum):
    """Allowed zone types and their meaning for movement."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class HubRole(str, Enum):
    """Role of a hub inside the network."""

    START = "start"
    END = "end"
    REGULAR = "regular"


class Hub(BaseModel):
    """Config zone of the network."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    x: int
    y: int
    role: HubRole = HubRole.REGULAR
    zone: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1
    line: int
    column: int

    @property
    def capacity(self) -> int | None:
        """Return the drone capacity, or None if unlimited."""

        if self.role is not HubRole.REGULAR:
            return None
        return self.max_drones

    @model_validator(mode="after")
    def _validate_capacity(self) -> "Hub":
        if self.role is HubRole.REGULAR and self.max_drones < 1:
            raise ValueError(
                f"max_drones must be a positive integer, got {self.max_drones}"
            )
        return self


class Link(BaseModel):
    """A bidirectional connection between two hubs"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    a: str
    b: str
    max_link_capacity: PositiveInt = 1
    line: int
    column: int


class ParsedMap(BaseModel):
    """Result of parsing a map file."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    nb_drones: PositiveInt
    hubs: list[Hub]
    links: list[Link]
