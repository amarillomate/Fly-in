"""Build a routing graph from a validated parsed map."""

from collections import defaultdict

from models import Hub, HubRole, Link, ParsedMap, ZoneType


class Graph:
    """A routing graph built from a validated parsed map."""

    def __init__(self, parsed_map: ParsedMap) -> None:
        """Build adjacency lists and movement costs from a parsed map."""
        self._parsed_map = parsed_map
        self._hubs: dict[str, Hub] = {
            hub.name: hub for hub in parsed_map.hubs
        }
        self._adjacency: dict[str, list[str]] = defaultdict(list)
        self._links: dict[frozenset[str, Link]] = {}
        self._start = self._find_role_hub(HubRole.START)
        self._end = self._find_role_hub(HubRole.END)

        self._build_links()
        self._build_adjacency()

    @property
    def start(self) -> str:
        """Return the name of the start hub."""
        return self._start.name

    @property
    def end(self) -> str:
        """Return the name of the end hub."""
        return self._end.name

    @property
    def drone_count(self) -> int:
        """Return the number of drones to route."""
        return self._parsed_map.nb_drones

    def neighbors(self, hub_name: str) -> list[str]:
        """Return reachable neighbor hub names, excluding blocked hubs."""
        return list(self._adjacency[hub_name])

    def movement_cost(self, destination: str) -> str:
        """Return the number od turns required to enter a destination hub."""
        hub = self._hubs[destination]
        if hub.zone is ZoneType.RESTRICTED:
            return 2
        return 1

    def link(self, first: str, second: str) -> Link:
        """Return the link between two hubs."""
        key = frozenset((first, second))
        return self._links[key]

    def hub(self, hub_name: str) -> Hub:
        """Return a hub by name."""
        return self._hubs[hub_name]

    def _find_role_hub(self, role: HubRole) -> Hub:
        """Return the unique hub with the given role."""
        matches = [
            hub for hub in self._parsed_map.hubs
            if hub.role is role
                ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one {role.value} hub, "
                f"found {len(matches)}"
            )
        return matches[0]

    def _build_links(self) -> None:
        """Index every connection by its unordered pair of hub names."""
        for link in self._parsed_map.links:
            key = frozenset((link.a, link.b))
            self._links[key] = link

    def _build_adjacency(self) -> None:
        """Build bidirectional adjacency lists without blocked hubs."""
        for link in self._parsed_map.links:
            first = self._hubs[link.a]
            second = self._hubs[link.b]

            if first.zone is not ZoneType.BLOCKED:
                self._adjacency[link.a].append(link.b)
            if second.zone is not ZoneType.BLOCKED:
                self._adjacency[link.b].append(link.a)
