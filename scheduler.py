"""Plan drone routes while respecting shared capacity constraints."""

from dataclasses import dataclass

from errors import SchedulingError
from graph import Graph
from models import ParsedMap
from pathfinder import Pathfinder
from reservations import ReservationTable
from spacetime_pathfinder import SpaceTimePathfinder


@dataclass(frozen=True)
class DronePlan:
    """Route of one drone: hubs visited and the turn of each arrival."""

    drone_id: int
    path: list[str]
    turns: list[int]


class Scheduler:
    """Plan every drone one after another using shared reservations."""

    def __init__(self, parsed_map: ParsedMap, graph: Graph) -> None:
        """Store the parsed map and the graph built from it."""
        self._parsed_map = parsed_map
        self._graph = graph

    def schedule(self) -> list[DronePlan]:
        """Return one plan per drone, or raise SchedulingError."""
        max_turn = self._compute_max_turn()
        reservations = ReservationTable(self._parsed_map)
        finder = SpaceTimePathfinder(self._graph, reservations, max_turn)
        plans: list[DronePlan] = []

        for drone_id in range(1, self._graph.drone_count + 1):
            found = finder.find_path(self._graph.start, self._graph.end, 0)
            if found is None:
                raise SchedulingError(f"no route found for drone D{drone_id}")
            path, turns = found
            reservations.reserve_path(path, turns)
            plans.append(DronePlan(drone_id, path, turns))

        return plans

    def _compute_max_turn(self) -> int:
        """Return a turn limit that always allows every drone to arrive."""
        start, end = self._graph.start, self._graph.end
        try:
            shortest = Pathfinder(self._graph).find_shortest_path(start, end)
        except ValueError as exc:
            raise SchedulingError(
                f"no route from '{start}' to '{end}'"
            ) from exc

        alone_cost = sum(self._graph.movement_cost(h) for h in shortest[1:])
        return alone_cost * self._graph.drone_count
