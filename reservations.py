"""Track time-based capacity reservation for drones."""

from models import Hub, Link, ParsedMap


class ReservationTable:
    """Track zone and link occupancy for every simulation turn."""

    def __init__(self, parsed_map: ParsedMap) -> None:
        """Create empty reservation tables from a parsed map."""
        self._parsed_map = parsed_map
        self._hubs: dict[str, Hub] = {
            hub.name: hub for hub in parsed_map.hubs
        }
        self._links: dict[frozenset[str], Link] = {
                frozenset((link.a, link.b)): link
                for link in parsed_map.links
        }
        self._zone_occupancy: dict[tuple[str, int], int] = {}
        self._link_occupancy: dict[tuple[frozenset[str], int], int] = {}

    def can_enter_zone(self, hub_name: str, turn: int) -> bool:
        """Check whether a hub has free capacity at a given turn."""
        hub = self._hubs[hub_name]
        capacity = hub.capacity

        if capacity is None:
            return True

        current = self._zone_occupancy.get((hub_name, turn), 0)
        return current < capacity

    def can_use_link(
        self,
        first: str,
        second: str,
        turn: int,
    ) -> bool:
        """Check whether a link has free capacity at a given turn."""
        link = self._links[frozenset((first, second))]
        key = (frozenset((first, second)), turn)
        current = self._link_occupancy.get(key, 0)
        return current < link.max_link_capacity

    def reserve_zone(self, hub_name: str, turn: int) -> None:
        """Reserve one unit of capacity in a hub for a given turn."""
        key = (hub_name, turn)
        self._zone_occupancy[key] = (
            self._zone_occupancy.get(key, 0) + 1
        )

    def reserve_link(
        self,
        first: str,
        second: str,
        turn: int,
    ) -> None:
        """Reserve one unit of capacity in a link for a given turn."""
        key = (frozenset((first, second)), turn)
        self._link_occupancy[key] = (
            self._link_occupancy.get(key, 0) + 1
        )

    def reserve_path(
        self,
        path: list[str],
        arrival_turns: list[int],
    ) -> None:
        """Reserve every zone and link used by a planned path."""
        if len(path) != len(arrival_turns):
            raise ValueError(
                "Path and arrival turns must have the same length"
            )

        for index, hub_name in enumerate(path):
            self.reserve_zone(hub_name, arrival_turns[index])

            if index == 0:
                continue

            previous = path[index - 1]
            if previous == hub_name:
                continue

            departure_turn = arrival_turns[index - 1]
            arrival_turn = arrival_turns[index]
            for turn in range(departure_turn, arrival_turn):
                self.reserve_link(previous, hub_name, turn)

    def zone_occupancy(self, hub_name: str, turn: int) -> int:
        """Return how many drones are reserved in a hub at a turn."""
        return self._zone_occupancy.get((hub_name, turn), 0)

    def link_occupancy(
        self,
        first: str,
        second: str,
        turn: int,
    ) -> int:
        """Return how many drones are reserved on a link at a turn."""
        key = (frozenset((first, second)), turn)
        return self._link_occupancy.get(key, 0)
