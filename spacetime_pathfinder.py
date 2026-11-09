"""Find capacity-aware paths through a time-expanded graph."""

import heapq
from dataclasses import dataclass, field

from models import ZoneType
from graph import Graph
from reservations import ReservationTable

State = tuple[str, int]
Score = tuple[int, int, int]


@dataclass
class SearchContext:
    """Mutable data of one Dijkstra search for a single drone."""

    scores: dict[State, Score] = field(default_factory=dict)
    previous: dict[State, State | None] = field(default_factory=dict)
    visited: set[State] = field(default_factory=set)
    queue: list[tuple[Score, str, int]] = field(default_factory=list)


class SpaceTimePathfinder:
    """Find a valid path for one drone using reservations."""

    def __init__(
        self,
        graph: Graph,
        reservations: ReservationTable,
        max_turn: int,
    ) -> None:
        """Store the graph, reservations and search limit."""
        self._graph = graph
        self.reservations = reservations
        self._max_turn = max_turn

    def find_path(
        self,
        start: str,
        end: str,
        initial_turn: int,
    ) -> tuple[list[str], list[int]] | None:
        """Return a path and its arrival turns, or None if unreachable."""
        ctx = SearchContext()
        start_state: State = (start, initial_turn)
        ctx.scores[start_state] = (0, 0, 0)
        ctx.previous[start_state] = None
        heapq.heappush(ctx.queue, ((0, 0, 0), start, initial_turn))

        while ctx.queue:
            score, hub_name, turn = heapq.heappop(ctx.queue)
            state: State = (hub_name, turn)

            if (score != ctx.scores[state] or state in ctx.visited):
                continue
            ctx.visited.add(state)

            if hub_name == end:
                return self._reconstruct_path(ctx.previous, state)

            self._explore_wait(ctx, state, score)
            self._explore_moves(ctx, state, score)

        return None

    def _explore_wait(
        self,
        ctx: SearchContext,
        state: State,
        score: Score,
    ) -> None:
        """Explore staying in the current hub for one turn."""
        hub_name, turn = state
        next_turn = turn + 1

        if next_turn > self._max_turn:
            return
        if not self.reservations.can_enter_zone(hub_name, next_turn):
            return

        self._relax(ctx, state, (hub_name, next_turn), score)

    def _explore_moves(
        self,
        ctx: SearchContext,
        state: State,
        score: Score,
    ) -> None:
        """Explore moving from the current hub to adjacent hubs."""
        hub_name, turn = state

        for neighbor in self._graph.neighbors(hub_name):
            arrival_turn = turn + self._graph.movement_cost(neighbor)

            if arrival_turn > self._max_turn:
                continue
            if not self._link_is_free(hub_name, neighbor, turn, arrival_turn):
                continue
            if not self.reservations.can_enter_zone(neighbor, arrival_turn):
                continue

            self._relax(ctx, state, (neighbor, arrival_turn), score)

    def _link_is_free(
        self,
        first: str,
        second: str,
        departure_turn: int,
        arrival_turn: int,
    ) -> bool:
        """Check the link has capacity during every turn of the transit."""
        return all(
            self.reservations.can_use_link(first, second, turn)
            for turn in range(departure_turn, arrival_turn)
        )

    def _relax(
        self,
        ctx: SearchContext,
        current_state: State,
        next_state: State,
        current_score: Score,
    ) -> None:
        """Save next_state if it improves the best known cost."""
        if next_state in ctx.visited:
            return

        new_score = self._next_score(current_state, next_state, current_score)
        known_score = ctx.scores.get(next_state)
        if known_score is not None and new_score >= known_score:
            return

        ctx.scores[next_state] = new_score
        ctx.previous[next_state] = current_state
        heapq.heappush(ctx.queue, (new_score, next_state[0], next_state[1]))

    def _next_score(
        self,
        current_state: State,
        next_state: State,
        current_score: Score,
    ) -> Score:
        """Return (turns, -priority hubs, moves) after reaching next_state."""
        turns, negative_priority, moves = current_score
        current_hub, current_turn = current_state
        next_hub, next_turn = next_state

        if current_hub != next_hub:
            moves += 1
            if self._graph.hub(next_hub).zone is ZoneType.PRIORITY:
                negative_priority -= 1

        return (turns + next_turn - current_turn, negative_priority, moves)

    def _reconstruct_path(
        self,
        previous: dict[State, State | None],
        end_state: State,
    ) -> tuple[list[str], list[int]]:
        """Rebuild hub names and arrival turns from previous states."""
        path: list[str] = []
        turns: list[int] = []
        current: State | None = end_state

        while current is not None:
            hub_name, turn = current
            path.append(hub_name)
            turns.append(turn)
            current = previous[current]

        path.reverse()
        turns.reverse()
        return path, turns
