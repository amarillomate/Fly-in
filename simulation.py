from dataclasses import dataclass, field

from scheduler import DronePlan


@dataclass(frozen=True)
class Turn:
    """All movements that happen during one simulation turn."""

    number: int
    movements: list[str] = field(default_factory=list)


class Simulation:
    """Convert scheduled drone plans into simulation turns."""

    def __init__(self, plans: list[DronePlan]) -> None:
        """Store the plans produced by the scheduler."""
        self._plans = plans

    def build_turns(self) -> list[Turn]:
        """Return every turn with the movements that occur in it."""
        total = max(plans.turns[-1] for plans in self._plans)
        turns = [Turn(number=turn) for turn in range(1, total + 1)]

        for plan in self._plans:
            self._add_plan(plan, turns)

        return turns

    @property
    def plans(self) -> list[DronePlan]:
        """Return the drone plans used by this simulation."""
        return self._plans

    def _add_plan(self, plan: DronePlan, turns: list[Turn]) -> None:
        """Add every movement of one drone to the matching turns."""
        path, turns_taken = plan.path, plan.turns

        for index in range(1, len(path)):
            previous = path[index - 1]
            current = path[index]
            departure = turns_taken[index - 1]
            arrival = turns_taken[index]
            drone = f"D{plan.drone_id}"

            if previous == current:
                continue

            if arrival - departure == 1:
                turns[arrival - 1].movements.append(f"{drone}-{current}")
                continue

            link_name = self._link_name(previous, current)
            turns[departure].movements.append(f"{drone}-{link_name}")
            turns[arrival - 1].movements.append(f"{drone}-{current}")

    @staticmethod
    def _link_name(first: str, second: str) -> str:
        """Return the connection name used while a drone is in transit."""
        return f"{first}-{second}"


def format_turns(turns: list[Turn]) -> str:
    """Format simulation turns as the output lines required."""
    lines = []
    for turn in turns:
        if turn.movements:
            lines.append(" ".join(turn.movements))
    return "\n".join(lines)
