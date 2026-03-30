"""System / planet info panel — translation of SYSLINEWNDPROC + PLTLINEWNDPROC.

Renders as a horizontal strip below the galaxy map.  Shows full detail for
the currently selected star:

  Left column (SYSLINEWNDPROC):
    Star id, coordinates, owner, planet type, resource, base production

  Right column (PLTLINEWNDPROC):
    Garrison breakdown by faction and ship type

When no star is selected the strip shows a status bar with current player
and turn info.
"""
import pygame
from second_conflict.model.constants import (
    PLAYER_COLOURS, EMPIRE_COLOUR, NEUTRAL_COLOUR, EMPIRE_FACTION,
    SHIP_NAMES, ShipType,
)
from second_conflict.model.game_state import GameState

_BG     = (12, 14, 22)
_BORDER = (50, 55, 80)
_LABEL  = (130, 130, 160)
_VALUE  = (210, 210, 210)
_FONT_SIZE = 12
_PAD    = 8


class SysInfoPanel:
    def __init__(self, rect: pygame.Rect, state: GameState):
        self.rect  = rect
        self.state = state
        self._font = None

    def set_state(self, state: GameState):
        self.state = state

    def draw(self, surface: pygame.Surface, selected_star_idx: int | None = None):
        if self._font is None:
            self._font = pygame.font.SysFont('monospace', _FONT_SIZE)

        surface.fill(_BG, self.rect)
        pygame.draw.line(surface, _BORDER,
                         (self.rect.x, self.rect.y),
                         (self.rect.right, self.rect.y))

        if selected_star_idx is None:
            self._draw_status_bar(surface)
        else:
            self._draw_star_info(surface, selected_star_idx)

    # ------------------------------------------------------------------

    def _draw_status_bar(self, surface: pygame.Surface):
        x = self.rect.x + _PAD
        y = self.rect.y + _PAD
        player = self.state.current_player()
        if player:
            pidx   = self.state.players.index(player)
            colour = PLAYER_COLOURS[pidx] if pidx < len(PLAYER_COLOURS) else (180, 180, 180)
            pygame.draw.rect(surface, colour, (x, y + 1, 10, 10))
            line = (f"  {player.name}   "
                    f"Turn {self.state.turn}   "
                    f"Stars: {player.empire_size}   "
                    f"Credits: {player.credits}   "
                    f"Fleet: {player.fleet_count}")
            surface.blit(self._font.render(line, True, _VALUE), (x + 14, y))

    def _draw_star_info(self, surface: pygame.Surface, idx: int):
        if idx >= len(self.state.stars):
            return
        star = self.state.stars[idx]
        owner_player = self.state.player_for_faction(star.owner_faction_id)
        owner_name = (
            "The Empire" if star.owner_faction_id == EMPIRE_FACTION
            else (owner_player.name if owner_player else f"0x{star.owner_faction_id:02x}")
        )

        # Left section: star stats
        lx = self.rect.x + _PAD
        y  = self.rect.y + _PAD

        left_fields = [
            ("Star",     f"{star.star_id}"),
            ("Coords",   f"({star.x}, {star.y})"),
            ("Type",     str(star.planet_type)),
            ("Resource", str(star.resource)),
            ("Owner",    owner_name),
        ]
        col_w = 130
        for label, value in left_fields:
            lbl = self._font.render(f"{label}:", True, _LABEL)
            val = self._font.render(value,        True, _VALUE)
            surface.blit(lbl, (lx, y))
            surface.blit(val, (lx + 60, y))
            lx += col_w
            if lx + col_w > self.rect.centerx:
                lx = self.rect.x + _PAD
                y += _FONT_SIZE + 3

        # Right section: garrison breakdown
        rx = self.rect.centerx + _PAD
        y  = self.rect.y + _PAD

        # Aggregate by (faction, ship_type)
        garrison_rows: list[tuple] = []
        faction_seen: set[int] = set()
        for g in star.garrison:
            if g.ship_count <= 0:
                continue
            faction_seen.add(g.owner_faction_id)
            p = self.state.player_for_faction(g.owner_faction_id)
            fname = (
                "Empire" if g.owner_faction_id == EMPIRE_FACTION
                else (p.name[:6] if p else f"0x{g.owner_faction_id:02x}")
            )
            ship_name = SHIP_NAMES.get(g.ship_type, f"T{g.ship_type}")
            garrison_rows.append((fname, ship_name, g.ship_count))

        if not garrison_rows:
            surface.blit(self._font.render("No garrison", True, _LABEL), (rx, y))
        else:
            for fname, sname, count in garrison_rows[:5]:  # cap rows to panel height
                line = f"{fname:<7} {sname:<12} {count:>4}"
                surface.blit(self._font.render(line, True, _VALUE), (rx, y))
                y += _FONT_SIZE + 2