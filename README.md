*This project has been created as part of the 42 curriculum by andrgarc.*

# Fly-in

## Description

Fly-in is a drone routing simulator. Given a map of zones and bidirectional connections, it plans a route for every drone from the unique start hub to the unique end hub.

The goal is to deliver all drones in the fewest possible simulation turns while respecting zone capacities, connection capacities, movement costs and collision rules.

### Features

- Map parser with line and column error messages.
- Validation of names, coordinates, capacities, zone types and connections.
- Graph construction from the parsed map.
- Space-time pathfinding with a shared reservation table.
- Turn-by-turn terminal output.
- Graphical simulation with Pygame CE.

### Project structure

- `main.py`: entry point.
- `parser.py`, `transformer.py`, `models.py`, `map.lark`: parsing and validation.
- `graph.py`: zone graph.
- `pathfinder.py`, `spacetime_pathfinder.py`: route search.
- `reservations.py`: shared capacity reservations.
- `scheduler.py`: drone planning.
- `simulation.py`: turn-by-turn simulation.
- `visualizer.py`: Pygame visualization.
- `errors.py`: parsing and scheduling errors.
- `maps/`: provided maps.
- `mapas_prueba/`: our own test maps.

## Instructions

### Requirements

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/)

### Installation

```bash
make install
```

This creates the virtual environment and installs the dependencies locked in `uv.lock`.

### Execution

```bash
make run MAP=maps/easy/01_linear_path.txt
```

Or directly:

```bash
uv run python main.py maps/easy/01_linear_path.txt
uv run python main.py maps/easy/01_linear_path.txt --no-visual
```

### Other commands

```bash
make debug MAP=maps/easy/01_linear_path.txt
make lint
make lint-strict
make clean
```

### Map format

```text
nb_drones: 2
start_hub: start 0 0 [color=green]
hub: room 3 4 [zone=normal color=blue max_drones=2]
end_hub: goal 10 10 [color=yellow]
connection: start-room [max_link_capacity=2]
```

Comments start with `#`. Zone names cannot contain dashes or spaces. Coordinates must be non-negative integers.

| Zone type | Movement cost |
|---|---|
| `normal` | 1 turn |
| `priority` | 1 turn, preferred |
| `restricted` | 2 turns |
| `blocked` | Not enterable |

## Resources

- [Lark documentation](https://lark-parser.readthedocs.io/)
- [Pydantic documentation](https://docs.pydantic.dev/)
- [Pygame CE documentation](https://pyga.me/docs/)
- [uv documentation](https://docs.astral.sh/uv/)

### Use of AI

AI was used for:

- Designing parser error messages and validation rules.
- Debugging parsing, pathfinding and scheduling issues.
- Reviewing typing, linting and Makefile configuration.
- Drafting docstrings and this README.

All generated content was reviewed, tested and understood by the author.

## Algorithm

### Overview

Drones are planned one at a time. Each one gets a conflict-free route that takes into account everything already reserved by the previous drones.

### Steps

1. A standard pathfinder computes the shortest route from start to end. Its cost gives an upper bound on the turns needed.
2. A space-time pathfinder searches over (hub, turn) states, so a drone can wait when moving would break a capacity rule.
3. The chosen route is stored in a reservation table (zone occupancy and link usage per turn).
4. The process repeats for every drone.

### Rules respected

- Zone capacity (`max_drones`) and link capacity (`max_link_capacity`).
- Unlimited capacity in the start and end hubs.
- Restricted zones take 2 turns and cannot be waited on mid-transit.
- Blocked zones are never entered.
- Priority zones are preferred among equal-cost routes.

### Design choice

Planning drones sequentially keeps the algorithm simple and the reservation table explicit. It does not guarantee a global optimum, but it gives valid schedules and is fast on the provided maps.

## Visual representation

By default the program opens a Pygame window showing zones (with their colors), connections and the drones moving turn by turn. This makes the topology, bottlenecks and waiting drones easy to see.

With `--no-visual`, the simulation is printed to the terminal. Each line is one turn and lists the movements of that turn.

## Example inputs and outputs

### Input

```text
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: middle 1 0 [color=blue max_drones=2]
end_hub: goal 2 0 [color=yellow]

connection: start-middle [max_link_capacity=2]
connection: middle-goal [max_link_capacity=2]
```

### Output

```text
D1-middle D2-middle
D1-goal D2-goal
```

### Error example

```text
Error: Line 5, column 1: y: Input should be greater than or equal to 0
```
