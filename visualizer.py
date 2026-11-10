"""Render the drone simulation with Pygame."""

import math

import pygame

from models import Hub, ParsedMap, ZoneType
from scheduler import DronePlan
from simulation import Simulation

Color = tuple[int, int, int]
Point = tuple[float, float]

BACKGROUND: Color = (20, 25, 30)
CONNECTION: Color = (80, 100, 120)
ACTIVE_CONNECTION: Color = (80, 220, 140)
WHITE: Color = (255, 255, 255)
LIGHT_TEXT: Color = (220, 230, 240)
DARK_TEXT: Color = (20, 25, 30)
START_RING: Color = (80, 220, 200)
END_RING: Color = (255, 210, 80)
BLOCKED_RING: Color = (240, 70, 70)
PRIORITY_RING: Color = (80, 220, 110)
RESTRICTED_RING: Color = (255, 160, 60)
DEFAULT_HUB: Color = (180, 200, 220)

ZONE_RINGS: dict[ZoneType, Color] = {
    ZoneType.BLOCKED: BLOCKED_RING,
    ZoneType.PRIORITY: PRIORITY_RING,
    ZoneType.RESTRICTED: RESTRICTED_RING,
}

ANIMATION_DURATION = 0.5
DELIVERY_DISPLAY_DURATION = 0.5
TARGET_FPS = 60


class PygameRenderer:
    """Draw the map and animate a planned simulation with Pygame."""

    def __init__(
        self,
        parsed_map: ParsedMap,
        simulation: Simulation,
    ) -> None:
        """Create the window and calculate drawing sizes and hub positions."""
        self._map = parsed_map
        self._simulation = simulation
        self._plans = simulation.plans
        self._turns = simulation.build_turns()
        self._margin = 100
        self._status_height = 140

        self._turn = 0
        self._is_animating = False
        self._animation_progress = 0.0
        self._elapsed_seconds = 0.0
        self._delivery_times: dict[int, float] = {}
        self._auto_mode = False

        self._itineraries = [
            list(zip(plan.path, plan.turns)) for plan in self._plans
        ]

        pygame.init()

        info = pygame.display.Info()
        width = int(info.current_w * 0.75)
        height = int(info.current_h * 0.75)

        self._screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Fly-in - Drone simulation")

        self._calculate_positions()

        min_distance = self._get_min_hub_distance()
        self._hub_radius = int(min(70, max(18, min_distance / 4)))
        font_size = max(18, int(self._hub_radius * 0.45))
        self._font = pygame.font.Font(None, font_size)
        self._marker_font = pygame.font.Font(None, 34)
        self._drone_radius = max(5, min(11, self._hub_radius // 3))

    def run(self) -> None:
        """Handle manual, automatic, reset and exit controls each frame."""
        running = True
        clock = pygame.time.Clock()

        while running:
            delta_seconds = clock.tick(TARGET_FPS) / 1000
            self._update_animation(delta_seconds)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self._handle_key(event.key)

            if self._auto_mode:
                self._start_animation()

            self._screen.fill(BACKGROUND)
            self._draw_connections()
            self._draw_hubs()
            self._draw_drones()
            self._draw_hover_label()
            self._draw_status()
            pygame.display.flip()

        pygame.quit()

    def _handle_key(self, key: int) -> bool:
        """Apply a keyboard action and return False to close the window."""
        if key == pygame.K_ESCAPE:
            return False
        if key == pygame.K_a:
            self._auto_mode = not self._auto_mode
        elif key == pygame.K_SPACE:
            self._start_animation()
        elif key == pygame.K_r:
            self._auto_mode = False
            self._turn = 0
            self._is_animating = False
            self._animation_progress = 0.0
            self._elapsed_seconds = 0.0
            self._delivery_times.clear()
        return True

    def _calculate_positions(self) -> None:
        """Scale and centre map coordinates within the drawing area."""
        hubs = self._map.hubs
        if not hubs:
            return

        min_x = min(hub.x for hub in hubs)
        max_x = max(hub.x for hub in hubs)
        min_y = min(hub.y for hub in hubs)
        max_y = max(hub.y for hub in hubs)

        map_width = max(max_x - min_x, 1)
        map_height = max(max_y - min_y, 1)

        screen_width, screen_height = self._screen.get_size()
        available_width = screen_width - 2 * self._margin
        available_height = (
            screen_height - 2 * self._margin - self._status_height
        )

        scale_x = available_width / map_width
        scale_y = available_height / map_height
        scale = min(scale_x, scale_y)

        offset_x = self._margin + (
            available_width - map_width * scale
        ) / 2
        offset_y = (
            self._status_height
            + self._margin
            + (available_height - map_height * scale) / 2
        )

        self._positions = {
            hub: (
                (hub.x - min_x) * scale + offset_x,
                (max_y - hub.y) * scale + offset_y,
            )
            for hub in hubs
        }

    def _get_min_hub_distance(self) -> float:
        """Return the closest distance between hub centres in pixels."""
        positions = list(self._positions.values())
        if len(positions) < 2:
            return 200.0

        return min(
            math.dist(first, second)
            for index, first in enumerate(positions)
            for second in positions[index + 1:]
        )

    def _start_animation(self) -> None:
        """Start one turn animation unless busy or already finished."""
        if self._is_animating or self._is_finished():
            return

        self._animation_progress = 0.0
        self._is_animating = True

    def _update_animation(self, delta_seconds: float) -> None:
        """Advance the animation and commit a turn when it completes."""
        self._elapsed_seconds += delta_seconds

        if self._is_animating:
            self._animation_progress += (
                delta_seconds / ANIMATION_DURATION
            )

            if self._animation_progress >= 1.0:
                self._finish_turn()

        for plan in self._plans:
            if plan.turns[-1] <= self._turn:
                self._delivery_times.setdefault(
                    plan.drone_id, self._elapsed_seconds
                )

    def _finish_turn(self) -> None:
        """Commit the current turn and print its movements once."""
        if self._turn < len(self._turns):
            turn = self._turns[self._turn]
            if turn.movements:
                print(" ".join(turn.movements))

        self._turn += 1
        self._animation_progress = 0.0
        self._is_animating = False

    def _is_finished(self) -> bool:
        """Return whether every drone has reached the end hub."""
        return all(
            plan.turns[-1] <= self._turn for plan in self._plans
        )

    def _fractional_turn(self) -> float:
        """Return the current visual time, including the running turn."""
        return self._turn + self._animation_progress

    def _get_drone_position(
        self,
        plan: DronePlan,
        turn: float,
    ) -> Point:
        """Interpolate a drone's pixel position at a fractional turn."""
        itinerary = self._itineraries[self._plans.index(plan)]
        final_turn = plan.turns[-1]
        final_hub = plan.path[-1]

        if turn >= final_turn:
            return self._positions[self._hub_by_name(final_hub)]

        for index in range(1, len(itinerary)):
            previous_hub, previous_turn = itinerary[index - 1]
            next_hub, next_turn = itinerary[index]

            if previous_turn <= turn <= next_turn:
                progress = (turn - previous_turn) / (
                    next_turn - previous_turn
                )
                x1, y1 = self._positions[
                    self._hub_by_name(previous_hub)
                ]
                x2, y2 = self._positions[self._hub_by_name(next_hub)]

                return (
                    x1 + (x2 - x1) * progress,
                    y1 + (y2 - y1) * progress,
                )

        return self._positions[self._hub_by_name(plan.path[0])]

    def _hub_by_name(self, name: str) -> Hub:
        """Return a hub by its name."""
        for hub in self._map.hubs:
            if hub.name == name:
                return hub
        raise ValueError(f"Unknown hub: {name}")

    def _draw_connections(self) -> None:
        """Draw every graph connection behind the hubs."""
        active = self._active_connections()

        for link in self._map.links:
            start = self._positions[self._hub_by_name(link.a)]
            end = self._positions[self._hub_by_name(link.b)]
            key = frozenset((link.a, link.b))

            color = (
                ACTIVE_CONNECTION
                if key in active
                else CONNECTION
            )
            pygame.draw.line(self._screen, color, start, end, 3)

    def _active_connections(self) -> set[frozenset[str]]:
        """Return the connections crossed during the current animation."""
        turn = self._fractional_turn()
        active: set[frozenset[str]] = set()

        for plan in self._plans:
            for index in range(1, len(plan.path)):
                departure = plan.turns[index - 1]
                arrival = plan.turns[index]

                if departure <= turn < arrival:
                    active.add(
                        frozenset(
                            (plan.path[index - 1], plan.path[index])
                        )
                    )

        return active

    def _draw_hubs(self) -> None:
        """Draw hubs with colours, zone rings and fitting labels."""
        for hub in self._map.hubs:
            position = self._positions[hub]
            hub_color = self._get_hub_color(hub.color)
            text_color = self._get_text_color(hub_color)

            pygame.draw.circle(
                self._screen,
                hub_color,
                position,
                self._hub_radius,
            )

            if hub.role.value == "start":
                pygame.draw.circle(
                    self._screen,
                    START_RING,
                    position,
                    self._hub_radius + 5,
                    3,
                )
            elif hub.role.value == "end":
                pygame.draw.circle(
                    self._screen,
                    END_RING,
                    position,
                    self._hub_radius + 5,
                    3,
                )

            self._draw_hub_name(hub, position, text_color)
            self._draw_zone_ring(hub, position)

    def _draw_hub_name(
        self,
        hub: Hub,
        position: Point,
        text_color: Color,
    ) -> None:
        """Draw a hub name inside it when it fits."""
        text = self._font.render(hub.name, True, text_color)
        text_width, text_height = text.get_size()
        available = 2 * (self._hub_radius - 6)
        diagonal = math.hypot(text_width, text_height)

        if diagonal <= available:
            self._screen.blit(
                text,
                text.get_rect(center=position),
            )

    def _draw_zone_ring(self, hub: Hub, position: Point) -> None:
        """Draw the coloured ring that identifies the hub zone."""
        ring_color = ZONE_RINGS.get(hub.zone)
        if ring_color is None:
            return

        offset = 5
        if hub.role.value in {"start", "end"}:
            offset = 10

        pygame.draw.circle(
            self._screen,
            ring_color,
            position,
            self._hub_radius + offset,
            3,
        )

    def _get_drone_groups(
        self,
    ) -> dict[tuple[int, int], list[DronePlan]]:
        """Group visible drones that share a pixel position."""
        turn = self._fractional_turn()
        groups: dict[tuple[int, int], list[DronePlan]] = {}

        for plan in self._plans:
            arrival_time = self._delivery_times.get(plan.drone_id)

            if arrival_time is not None:
                shown_for = (
                    self._elapsed_seconds - arrival_time
                )
                if shown_for >= DELIVERY_DISPLAY_DURATION:
                    continue

            position = self._get_drone_position(plan, turn)
            pixel_position = (
                round(position[0]),
                round(position[1]),
            )
            groups.setdefault(pixel_position, []).append(plan)

        return groups

    def _draw_drones(self) -> None:
        """Draw drone markers and counts for overlapping drones."""
        groups = self._get_drone_groups()
        hub_positions = {
            (round(x), round(y))
            for x, y in self._positions.values()
        }

        for position in groups:
            pygame.draw.circle(
                self._screen,
                WHITE,
                position,
                self._drone_radius,
            )
            pygame.draw.circle(
                self._screen,
                DARK_TEXT,
                position,
                self._drone_radius,
                1,
            )

        for (x, y), drones in groups.items():
            if len(drones) <= 1:
                continue

            text = self._marker_font.render(
                f"x{len(drones)}",
                True,
                WHITE,
                DARK_TEXT,
            )
            offset = (
                self._hub_radius + 10
                if (x, y) in hub_positions
                else self._drone_radius + 4
            )
            text_rect = text.get_rect(midleft=(x + offset, y))
            text_rect.clamp_ip(self._screen.get_rect())
            self._screen.blit(text, text_rect)

    def _draw_hover_label(self) -> None:
        """Show a long hub name when the pointer hovers over it."""
        mouse_x, mouse_y = pygame.mouse.get_pos()

        for hub, position in self._positions.items():
            if math.dist((mouse_x, mouse_y), position) > self._hub_radius:
                continue

            text = self._font.render(hub.name, True, LIGHT_TEXT)
            text_width, text_height = text.get_size()
            available = 2 * (self._hub_radius - 6)

            if math.hypot(text_width, text_height) > available:
                self._screen.blit(
                    text,
                    text.get_rect(
                        midtop=(
                            position[0],
                            position[1] + self._hub_radius + 4,
                        )
                    ),
                )

            break

    def _draw_status(self) -> None:
        """Display turn progress, delivered drones and control hints."""
        last_turn = max(
            (plan.turns[-1] for plan in self._plans),
            default=0,
        )
        total = len(self._plans)
        delivered = sum(
            plan.turns[-1] <= self._turn for plan in self._plans
        )

        summary = (
            f"Turno: {self._turn} / {last_turn}    "
            f"Entregados: {delivered} / {total}"
        )

        if self._is_finished():
            status = "Simulación finalizada"
        elif self._is_animating:
            status = "En movimiento..."
        else:
            status = "Listo para el siguiente turno"

        messages = [
            summary,
            "Espacio: turno · A: modo auto · R: reiniciar · Esc: salir",
            status,
        ]

        for index, message in enumerate(messages):
            text = self._marker_font.render(message, True, LIGHT_TEXT)
            self._screen.blit(text, (20, 12 + index * 42))

    def _get_hub_color(self, color: str | None) -> pygame.Color:
        """Resolve a Pygame colour, with a neutral fallback."""
        if color is None:
            return pygame.Color(DEFAULT_HUB)

        try:
            return pygame.Color(color)
        except ValueError:
            return pygame.Color(DEFAULT_HUB)

    @staticmethod
    def _get_text_color(
        background: pygame.Color,
    ) -> tuple[int, int, int]:
        """Choose light or dark text for contrast against a hub colour."""
        brightness = background.grayscale().r

        if brightness < 128:
            return (245, 245, 245)
        return DARK_TEXT
