"""Run the Fly-in drone routing simulation from a map file."""

import sys
from pathlib import Path

from errors import ParseError, SchedulingError
from graph import Graph
from parser import MapParser
from scheduler import Scheduler
from simulation import Simulation, format_turns
from visualizer import PygameRenderer


def main() -> int:
    """Parse a map, schedule drones and display the simulation."""
    args = sys.argv[1:]

    if not args:
        print(
            "Usage: python3 main.py <map_file> [--no-visual]",
            file=sys.stderr,
        )
        return 1

    map_path = args[0]
    show_visual = "--no-visual" not in args

    try:
        text = Path(map_path).read_text()
        parsed = MapParser().parse_text(text)
        graph = Graph(parsed)
        plans = Scheduler(parsed, graph).schedule()
        simulation = Simulation(plans)

        if show_visual:
            renderer = PygameRenderer(parsed, simulation)
            renderer.run()
        else:
            print(format_turns(simulation.build_turns()))

        return 0

    except FileNotFoundError:
        print(f"Error: file not found: {map_path}", file=sys.stderr)
        return 1
    except (ParseError, SchedulingError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
