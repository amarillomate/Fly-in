import sys
from pathlib import Path

from pathfinder import Pathfinder
from graph import Graph
from errors import ParseError
from parser import MapParser

def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 main.py <map_file>", file=sys.stderr)
        return 1
    try:
        text = Path(sys.argv[1]).read_text()
        result = MapParser().parse_text(text)
    except FileNotFoundError:
        print(f"Error: file not found: {sys.argv[1]}", file=sys.stderr)
        return 1
    except ParseError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    graph = Graph(result)
    print("Start:", graph.start)
    print("End:", graph.end)
    print("Drones:", graph.drone_count)
    for hub_name in ("start", "goal"):
        print(f"{hub_name} neighbors:", graph.neighbors(hub_name))
    pathfinder = Pathfinder(graph)
    path = pathfinder.find_shortest_path(graph.start, graph.end)
    print("Shortest path:", path)
    print("Path length in hubs:", len(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
