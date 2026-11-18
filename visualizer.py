"""Step-by-step Pygame view of a drone simulation (no animation)."""

import math
import sys

import pygame

from models import Hub, ParsedMap, ZoneType
from scheduler import DronePlan
from simulation import Simulation

Point = tuple[int, int]
WIDTH, HEIGHT = 2500, 1200
SIDE, TOP, BOTTOM = 70, 90, 70
STRETCH = 1
MAX_SHOWN = 3
RINGS: dict[ZoneType, tuple[int, int, int]] = {
    ZoneType.BLOCKED: (230, 60, 60),
    ZoneType.RESTRICTED: (255, 150, 40),
    ZoneType.PRIORITY: (60, 200, 100),
    ZoneType.NORMAL: (240, 240, 240),
}


class PygameRenderer:
    """Draw the map and show drone positions one turn at a time."""

    def __init__(self, parsed_map: ParsedMap, simulation: Simulation) -> None:
        """Store map data and precompute screen positions of the hubs."""
        self._hubs: dict[str, Hub] = {h.name: h for h in parsed_map.hubs}
        self._links = [(link.a, link.b) for link in parsed_map.links]
        self._plans = simulation.plans
        self._turns = simulation.build_turns()
        xs = [h.x for h in parsed_map.hubs]
        ys = [h.y for h in parsed_map.hubs]
        self._origin = (min(xs), max(ys))
        self._span = (max(xs) - min(xs), max(ys) - min(ys))
        self._size = (WIDTH, HEIGHT)

    def run(self) -> None:
        """Open the window; right/space next turn, left back, esc quit.

        Each turn is printed to the terminal the first time it is reached.
        """
        pygame.init()
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Fly-in")
        font = pygame.font.Font(None, 22)
        turn, printed, running = 0, 0, True
        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key in (pygame.K_RIGHT, pygame.K_SPACE):
                            turn = min(turn + 1, len(self._turns))
                            if turn > printed:
                                self._print_turn(turn)
                                printed = turn
                        elif event.key == pygame.K_LEFT:
                            turn = max(turn - 1, 0)
                screen.fill((20, 25, 30))
                self._draw_map(screen, font)
                self._draw_drones(screen, font, turn)
                self._draw_hud(screen, font, turn)
                pygame.display.flip()
        except KeyboardInterrupt:
            print("\nInterrupted by user.",
                  file=sys.stderr)
        finally:
            pygame.quit()

    def _print_turn(self, turn: int) -> None:
        """Print one turn's movements in the official output format."""
        print(" ".join(self._turns[turn - 1].movements), flush=True)

    def _pos(self, name: str) -> Point:
        """Place a hub: map proportions partly stretched, centered (y up)."""
        hub = self._hubs[name]
        room = (WIDTH - 2 * SIDE, HEIGHT - TOP - BOTTOM)
        fit = [room[i] / self._span[i] if self._span[i] else math.inf
               for i in (0, 1)]
        base = min(fit) if min(fit) != math.inf else 0
        scale = [base if f == math.inf else base + (f - base) * STRETCH
                 for f in fit]
        left = (room[0] - self._span[0] * scale[0]) / 2
        up = (room[1] - self._span[1] * scale[1]) / 2
        x = SIDE + left + (hub.x - self._origin[0]) * scale[0]
        y = TOP + up + (self._origin[1] - hub.y) * scale[1]
        return int(x), int(y)

    def _color(self, name: str | None) -> tuple[int, int, int]:
        """Turn a map color name into RGB (gray if unknown or missing)."""
        if name == "rainbow":
            rainbow = pygame.Color(0)
            rainbow.hsva = (
                    (pygame.time.get_ticks()) % 360,
                    100,
                    100,
                    100
            )
            return rainbow.r, rainbow.g, rainbow.b
        try:
            c = pygame.Color(name or "gray")
            return c.r, c.g, c.b
        except ValueError:
            return 128, 128, 128

    def _draw_map(self, screen: pygame.Surface,
                  font: pygame.font.Font) -> None:
        """Draw links, then hubs with their color, zone ring and name."""
        for a, b in self._links:
            pygame.draw.line(screen, (90, 110, 130),
                             self._pos(a), self._pos(b), 3)
        for name, hub in self._hubs.items():
            x, y = self._pos(name)
            pygame.draw.circle(screen, self._color(hub.color), (x, y), 22)
            pygame.draw.circle(screen, RINGS[hub.zone], (x, y), 22, 4)
            label = font.render(name, True, (220, 230, 240))
            drop = 36 + 16 * (hub.x % 2)
            screen.blit(label, label.get_rect(center=(x, y + drop)))

    def _location(self, plan: DronePlan, turn: int) -> tuple[str, str | None]:
        """Return (zone, next_zone); next_zone is set while in flight."""
        i = max(k for k, t in enumerate(plan.turns) if t <= turn)
        if i + 1 < len(plan.turns) and turn > plan.turns[i]:
            if plan.turns[i + 1] - plan.turns[i] == 2:
                return plan.path[i], plan.path[i + 1]
        return plan.path[i], None

    def _draw_drones(self, screen: pygame.Surface, font: pygame.font.Font,
                     turn: int) -> None:
        """Draw undelivered drones; 4 or more on one spot become a counter."""
        spots: dict[Point, list[int]] = {}
        for plan in self._plans:
            if plan.turns[-1] <= turn:
                continue
            here, ahead = self._location(plan, turn)
            x, y = self._pos(here)
            if ahead is not None:
                nx, ny = self._pos(ahead)
                x, y = (x + nx) // 2, (y + ny) // 2
            spots.setdefault((x, y), []).append(plan.drone_id)
        for (x, y), ids in spots.items():
            if len(ids) > MAX_SHOWN:
                self._badge(screen, font, (x, y), f"x{len(ids)}", 17)
                continue
            for k, drone_id in enumerate(ids):
                angle = 2 * math.pi * k / len(ids)
                offset = 0 if len(ids) == 1 else 13
                spot = (x + int(math.cos(angle) * offset),
                        y + int(math.sin(angle) * offset))
                self._badge(screen, font, spot, str(drone_id), 10)

    def _badge(self, screen: pygame.Surface, font: pygame.font.Font,
               spot: Point, text: str, radius: int) -> None:
        """Draw a dark circle with a short label in the middle."""
        pygame.draw.circle(screen, (15, 15, 20), spot, radius)
        label = font.render(text, True, (255, 255, 255))
        screen.blit(label, label.get_rect(center=spot))

    def _draw_hud(self, screen: pygame.Surface, font: pygame.font.Font,
                  turn: int) -> None:
        """Show turn counter, delivered drones and this turn's movements."""
        done = sum(p.turns[-1] <= turn for p in self._plans)
        lines = [
            f"Turn {turn}/{len(self._turns)}   "
            f"delivered {done}/{len(self._plans)}   "
            "[space/right: next | left: back | esc: quit]",
        ]
        for i, text in enumerate(lines):
            screen.blit(font.render(text, True, (220, 230, 240)),
                        (12, 10 + 22 * i))
