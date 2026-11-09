import sys
from pathlib import Path

from simulation import Simulation, format_turns
from errors import ParseError, SchedulingError
from graph import Graph
from parser import MapParser
from scheduler import Scheduler


def main() -> int:
    """Parse the map, plan every drone and print the plans."""
    if len(sys.argv) != 2:
        print("Usage: python3 main.py <map_file>", file=sys.stderr)
        return 1
    try:
        text = Path(sys.argv[1]).read_text()
        parsed = MapParser().parse_text(text)
        graph = Graph(parsed)
        plans = Scheduler(parsed, graph).schedule()
        simulation = Simulation(plans)
        turns = simulation.build_turns()
        print(format_turns(turns))
    except FileNotFoundError:
        print(f"Error: file not found: {sys.argv[1]}", file=sys.stderr)
        return 1
    except (ParseError, SchedulingError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    for plan in plans:
        print(f"D{plan.drone_id}: {plan.path} {plan.turns}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
