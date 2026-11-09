"""Data models for the Fly-in map, validated with Pydantic"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, PositiveInt, model_validator


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
    max_drones: PositiveInt = 1
    line: int

    @property
    def capacity(self) -> int | None:
        """Return the drone capacity, or None if unlimited."""

        if self.role is not HubRole.REGULAR:
            return None
        return self.max_drones


class Link(BaseModel):
    """A bidirectional connection between two hubs"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    a: str
    b: str
    max_link_capacity: PositiveInt = 1
    line: int


class ParsedMap(BaseModel):
    """Result of parsing a map file."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    nb_drones: PositiveInt
    hubs: list[Hub]
    links: list[Link]

    @model_validator(mode="after")
    def check_network(self) -> "ParsedMap":
        """Validate rules that involve the whole network."""
        starts = [h for h in self.hubs if h.role is HubRole.START]
        ends = [h for h in self.hubs if h.role is HubRole.END]
        if len(starts) != 1:
            raise ValueError(
                f"excepted exactly 1 start_hub, found {len(starts)}"
            )
        if len(ends) != 1:
            raise ValueError(
                f"expected exactly 1 end_hub, found {len(ends)}"
            )

        names = [h.name for h in self.hubs]
        if len(names) != len(set(names)):
            dupes = sorted({n for n in names if names.count(n) > 1})
            raise ValueError(
                f"duplicated hub name(s): {', '.join(dupes)}"
            )

        known = set(names)
        seen: set[frozenset[str]] = set()
        for link in self.links:
            for end in (link.a, link.b):
                if end not in known:
                    raise ValueError(
                        f"line {link.line}: connection to unknown hub "
                        f"'{end}'"
                    )
            if link.a == link.b:
                raise ValueError(
                    f"line {link.line}: connection '{link.a}' links "
                    f"'{link.a}-{link.b}'"
                )
            key = frozenset((link.a, link.b))
            if key in seen:
                raise ValueError(
                    f"line {link.line}: duplicated connection "
                    f"'{link.a}-{link.b}'"
                )
            seen.add(key)
        return self
