"""Find shortest route through the routing graph."""

import heapq

from graph import Graph


class Pathfinder:
    """Find preferred shortest paths using Dijkstra's algorithm."""

    def __init__(self, graph: Graph) -> None:
        """Store the graph used for pathfinding."""
        self._graph = graph

    def find_shortest_path(self, start: str, end: str) -> list[str]:
        """Return the preferred shortest path from start to end."""
        costs: dict[str, int] = {start: 0}
        previous: dict[str, str | None] = {start: None}
        priority_counts: dict[str, int] = {
            start: self._priority_value(start)
        }
        visited: set[str] = set()
        queue: list[tuple[int, int, str]] = [
            (0, -priority_counts[start], start)
        ]

        while queue:
            current_cost, _, current = heapq.heappop(queue)

            if current in visited:
                continue
            visited.add(current)

            if current == end:
                return self._reconstruct_path(previous, end)

            for neighbor in self._graph.neighbors(current):
                if neighbor in visited:
                    continue

                new_cost = current_cost + self._graph.movement_cost(
                        neighbor
                )
                known_cost = costs.get(neighbor)

                if known_cost is not None and new_cost > known_cost:
                    continue

                new_priority = (
                    priority_counts[current]
                    + self._priority_value(neighbor)
                )

                if self._is_better_candidate(
                    neighbor,
                    new_cost,
                    new_priority,
                    costs,
                    priority_counts,
                ):
                    costs[neighbor] = new_cost
                    priority_counts[neighbor] = new_priority
                    previous[neighbor] = current
                    heapq.heappush(
                        queue,
                        (new_cost, -new_priority, neighbor),
                    )

        raise ValueError(f"No path found from '{start}' to '{end}'")

    def _priority_value(self, hub_name: str) -> int:
        """Return 1 for priority hubs and 0 for any other hub."""
        hub = self._graph.hub(hub_name)
        return int(hub.zone.value == "priority")

    def _is_better_candidate(
        self,
        hub_name: str,
        new_cost: int,
        new_priority: int,
        costs: dict[str, int],
        priority_counts: dict[str, int],
    ) -> bool:
        """Check whether a candidate improves the best known route."""
        known_cost = costs.get(hub_name)
        if known_cost is None or new_cost < known_cost:
            return True

        if new_cost > known_cost:
            return False

        return new_priority > priority_counts.get(hub_name, 0)

    def _reconstruct_path(
        self,
        previous: dict[str, str | None],
        end: str,
    ) -> list[str]:
        """Rebuild the path from the end hub back to the start hub."""
        path: list[str] = []
        current: str | None = end

        while current is not None:
            path.append(current)
            current = previous[current]

        path.reverse()
        return path
