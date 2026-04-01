"""Galaxy map renderer and interaction handler.

Draws:
  - Stars as filled circles coloured by owner
  - Star labels (star_id + planet_type char)
  - In-transit fleet lines from source to destination
  - Selection highlight

Handles:
  - Left-click to select a star
  - Right-click (or second left-click on already-selected) to open fleet dialog
"""
import math
import pygame

from second_conflict.model.constants import (
    PLAYER_COLOURS, EMPIRE_COLOUR, NEUTRAL_COLOUR, EMPIRE_FACTION, FREE_SLOT,
)
from second_conflict.model.game_state import GameState

STAR_RADIUS   = 10
SELECT_RADIUS = 14
FONT_SIZE     = 11
MAP_MARGIN    = 40      # pixels of padding around the star field

_SPRITE_SIZE   = 22   # central star body (px)
_PLANET_RADIUS =  3   # each orbiting planet dot (px)
_ORBIT_RADIUS  = 14   # distance of dots from star centre (px)


class MapView:
    def __init__(self, rect: pygame.Rect, state: GameState):
        self.rect    = rect
        self.state   = state
        self._font   = None
        self._selected_star: int | None = None
        self._on_star_click = None   # callback(star_idx, second_click)
        self._star_sprites: dict = {}   # (colour, size) → pygame.Surface
        self._base_sprite = None        # unscaled source bitmap
        self._sprites_loaded = False
        self._bounds: tuple[int, int] = self._coord_bounds()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_state(self, state: GameState):
        self.state = state
        self._selected_star = None
        self._sprites_loaded = False
        self._star_sprites.clear()
        self._bounds = self._coord_bounds()

    def set_star_click_callback(self, cb):
        """cb(star_idx: int, second_click: bool) → None"""
        self._on_star_click = cb

    @property
    def selected_star(self) -> int | None:
        return self._selected_star

    def select_star(self, idx: int | None):
        self._selected_star = idx

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (1, 3) and self.rect.collidepoint(event.pos):
                idx = self._star_at(event.pos)
                if idx is not None:
                    second = (event.button == 3 or idx == self._selected_star)
                    self._selected_star = idx
                    if self._on_star_click:
                        self._on_star_click(idx, second)
                else:
                    self._selected_star = None

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface):
        if self._font is None:
            self._font = pygame.font.SysFont('monospace', FONT_SIZE)

        # Clip to our rect
        surface.set_clip(self.rect)

        # Background
        surface.fill((0, 0, 0), self.rect)

        # Fleet transit lines
        self._draw_fleet_lines(surface)

        # Load star sprites once (deferred so pygame.display is ready)
        if not self._sprites_loaded:
            self._load_sprites()

        # Stars
        for i, star in enumerate(self.state.stars):
            pos = self._star_pos(star)
            colour = self._faction_colour(star.owner_faction_id)
            half = _SPRITE_SIZE // 2

            # Selection ring
            if i == self._selected_star:
                pygame.draw.circle(surface, (255, 255, 100), pos,
                                   half + _ORBIT_RADIUS + _PLANET_RADIUS + 3, 2)

            # Central star body
            sprite = self._get_sprite(colour, _SPRITE_SIZE)
            if sprite:
                surface.blit(sprite, (pos[0] - half, pos[1] - half))
            else:
                pygame.draw.circle(surface, colour, pos, half)
                pygame.draw.circle(surface, (200, 200, 200), pos, half, 1)

            # Occupation indicator — red dashed ring if troops present
            if getattr(star, 'troops', 0) > 0:
                pygame.draw.circle(surface, (220, 50, 50), pos,
                                   half + _ORBIT_RADIUS + _PLANET_RADIUS + 5, 2)

            # Orbiting planet dots
            num_planets = star.num_planets
            if num_planets:
                planet_col = tuple(min(255, int(c * 0.7)) for c in colour)
                for p in range(num_planets):
                    angle = (2 * math.pi * p / num_planets) - math.pi / 2
                    dx = int(_ORBIT_RADIUS * math.cos(angle))
                    dy = int(_ORBIT_RADIUS * math.sin(angle))
                    pygame.draw.circle(surface, planet_col,
                                       (pos[0] + dx, pos[1] + dy), _PLANET_RADIUS)

            # Label: id + planet type char
            label = self._font.render(
                f"{star.star_id}{star.planet_type}", True, (220, 220, 220)
            )
            label_x = pos[0] + half + _ORBIT_RADIUS + 2
            surface.blit(label, (label_x, pos[1] - FONT_SIZE // 2))

        surface.set_clip(None)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_sprites(self):
        """Load and cache tinted star sprites for every faction colour."""
        self._sprites_loaded = True
        try:
            from second_conflict.assets import get_star_sprite
            for colour in ([EMPIRE_COLOUR, NEUTRAL_COLOUR] + list(PLAYER_COLOURS)):
                surf = get_star_sprite(colour, _SPRITE_SIZE)
                if surf:
                    self._star_sprites[colour] = surf
        except Exception:
            pass

    def _get_sprite(self, colour: tuple, size: int):
        return self._star_sprites.get(colour)

    def _coord_bounds(self) -> tuple[int, int]:
        """Return (max_x, max_y) across all stars, used for scaling."""
        if not self.state.stars:
            return 255, 255
        max_x = max(s.x for s in self.state.stars)
        max_y = max(s.y for s in self.state.stars)
        return max(max_x, 1), max(max_y, 1)

    def _star_pos(self, star) -> tuple[int, int]:
        """Map star (x, y) coordinates to screen pixel position."""
        usable_w = self.rect.width  - 2 * MAP_MARGIN
        usable_h = self.rect.height - 2 * MAP_MARGIN
        max_x, max_y = self._bounds
        px = self.rect.x + MAP_MARGIN + int(star.x / max_x * usable_w)
        py = self.rect.y + MAP_MARGIN + int(star.y / max_y * usable_h)
        return px, py

    def _star_at(self, pos: tuple[int, int]) -> int | None:
        """Return index of the star under cursor, or None."""
        for i, star in enumerate(self.state.stars):
            sp = self._star_pos(star)
            dx = pos[0] - sp[0]
            dy = pos[1] - sp[1]
            if dx * dx + dy * dy <= SELECT_RADIUS * SELECT_RADIUS:
                return i
        return None

    def _faction_colour(self, faction_id: int) -> tuple[int, int, int]:
        if faction_id == EMPIRE_FACTION:
            return EMPIRE_COLOUR
        # Find the player slot index
        player = self.state.player_for_faction(faction_id)
        if player is None:
            return NEUTRAL_COLOUR
        idx = self.state.players.index(player)
        if 0 <= idx < len(PLAYER_COLOURS):
            return PLAYER_COLOURS[idx]
        return NEUTRAL_COLOUR

    def _draw_fleet_lines(self, surface: pygame.Surface):
        """Draw dotted lines and fleet markers for in-transit fleets."""
        from second_conflict.engine.distance import travel_time
        from second_conflict.model.constants import FLEET_TYPE_MISSILE

        for fleet in self.state.fleets_in_transit:
            if fleet.owner_faction_id == FREE_SLOT:
                continue
            if not (0 <= fleet.src_star < len(self.state.stars)):
                continue
            if not (0 <= fleet.dest_star < len(self.state.stars)):
                continue

            src_star = self.state.stars[fleet.src_star]
            dest_star = self.state.stars[fleet.dest_star]
            src_pos  = self._star_pos(src_star)
            dest_pos = self._star_pos(dest_star)
            colour   = self._faction_colour(fleet.owner_faction_id)

            _draw_dashed_line(surface, colour, src_pos, dest_pos, dash=6)

            # Total travel time for this fleet type
            total = travel_time(src_star, dest_star,
                                self.state.options.sim_steps,
                                self.state.options.map_param)
            if fleet.fleet_type_char == FLEET_TYPE_MISSILE:
                total = max(1, total // 2)

            progress = max(0.0, min(1.0, 1.0 - fleet.turns_remaining / total))

            mx = src_pos[0] + progress * (dest_pos[0] - src_pos[0])
            my = src_pos[1] + progress * (dest_pos[1] - src_pos[1])

            # Direction vector toward destination (for arrowhead)
            dx = dest_pos[0] - src_pos[0]
            dy = dest_pos[1] - src_pos[1]
            length = math.hypot(dx, dy) or 1
            ux, uy = dx / length, dy / length

            _draw_fleet_marker(surface, colour, int(mx), int(my),
                               fleet.fleet_type_char, ux, uy)


def _draw_fleet_marker(surface, colour, cx, cy, fleet_type: str,
                       ux: float = 1.0, uy: float = 0.0):
    """Draw a marker + direction arrowhead at (cx, cy).

    ux, uy — unit vector pointing toward destination.
    Missiles ('M') get a square body; all others get a diamond.
    The arrowhead is a small triangle ahead of the marker.
    """
    r = 4
    if fleet_type == 'M':
        pygame.draw.rect(surface, colour, pygame.Rect(cx - 3, cy - 3, 6, 6))
        pygame.draw.rect(surface, (255, 255, 255), pygame.Rect(cx - 3, cy - 3, 6, 6), 1)
    else:
        points = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        pygame.draw.polygon(surface, colour, points)
        pygame.draw.polygon(surface, (200, 200, 200), points, 1)

    # Arrowhead: small triangle offset ahead of the marker body
    tip_x = cx + ux * (r + 5)
    tip_y = cy + uy * (r + 5)
    # perpendicular for arrow wings
    px, py = -uy, ux
    wing = 3
    base_x = cx + ux * (r + 1)
    base_y = cy + uy * (r + 1)
    arrow = [
        (int(tip_x), int(tip_y)),
        (int(base_x + px * wing), int(base_y + py * wing)),
        (int(base_x - px * wing), int(base_y - py * wing)),
    ]
    pygame.draw.polygon(surface, (255, 255, 255), arrow)


def _draw_dashed_line(surface, colour, p1, p2, dash=8):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    pos = 0
    draw = True
    while pos < length:
        seg_end = min(pos + dash, length)
        if draw:
            x1 = int(p1[0] + ux * pos)
            y1 = int(p1[1] + uy * pos)
            x2 = int(p1[0] + ux * seg_end)
            y2 = int(p1[1] + uy * seg_end)
            pygame.draw.line(surface, colour, (x1, y1), (x2, y2), 1)
        pos += dash
        draw = not draw