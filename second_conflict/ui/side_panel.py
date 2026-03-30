"""Side panel — player stats strip and End Turn button.

Renders on the right side of the screen:
  - Current player name + colour swatch
  - Turn number
  - Stats: empire_size, production, fleet_count, credits
  - Selected star info (if any)
  - "End Turn" button
"""
import pygame
from second_conflict.model.constants import PLAYER_COLOURS, EMPIRE_COLOUR, EMPIRE_FACTION
from second_conflict.model.game_state import GameState

PANEL_BG   = (20, 20, 30)
TEXT_COL   = (210, 210, 210)
LABEL_COL  = (140, 140, 160)
BTN_NORMAL = (50, 90, 160)
BTN_HOVER  = (80, 130, 210)
BTN_TEXT   = (255, 255, 255)
DIVIDER    = (60, 60, 80)

_FONT_TITLE_SIZE = 16
_FONT_BODY_SIZE  = 13
_BTN_H           = 36
_BTN_MARGIN      = 14


class SidePanel:
    def __init__(self, rect: pygame.Rect, state: GameState):
        self.rect  = rect
        self.state = state
        self._font_title = None
        self._font_body  = None
        self._btn_rect: pygame.Rect | None = None
        self._on_end_turn = None
        self._hovering_btn = False

    def set_state(self, state: GameState):
        self.state = state

    def set_end_turn_callback(self, cb):
        self._on_end_turn = cb

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEMOTION:
            self._hovering_btn = (
                self._btn_rect is not None and
                self._btn_rect.collidepoint(event.pos)
            )
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_rect and self._btn_rect.collidepoint(event.pos):
                if self._on_end_turn:
                    self._on_end_turn()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, selected_star_idx: int | None = None):
        if self._font_title is None:
            self._font_title = pygame.font.SysFont('monospace', _FONT_TITLE_SIZE, bold=True)
            self._font_body  = pygame.font.SysFont('monospace', _FONT_BODY_SIZE)

        surface.fill(PANEL_BG, self.rect)

        x = self.rect.x + 10
        y = self.rect.y + 10
        w = self.rect.width - 20

        # Current player
        player = self.state.current_player()
        if player:
            idx = self.state.players.index(player)
            colour = PLAYER_COLOURS[idx] if idx < len(PLAYER_COLOURS) else (180, 180, 180)
            pygame.draw.rect(surface, colour, (x, y, 14, 14))
            name_surf = self._font_title.render(player.name, True, TEXT_COL)
            surface.blit(name_surf, (x + 18, y))
            y += 22

        # Turn counter
        turn_surf = self._font_body.render(f"Turn {self.state.turn}", True, LABEL_COL)
        surface.blit(turn_surf, (x, y))
        y += 20

        # Divider
        pygame.draw.line(surface, DIVIDER, (x, y), (x + w, y))
        y += 8

        # Player stats
        if player:
            stats = [
                ("Stars",      player.empire_size),
                ("Production", player.production),
                ("Fleets",     player.fleet_count),
                ("Credits",    player.credits),
            ]
            for label, val in stats:
                lbl = self._font_body.render(f"{label}:", True, LABEL_COL)
                val_s = self._font_body.render(str(val), True, TEXT_COL)
                surface.blit(lbl, (x, y))
                surface.blit(val_s, (x + w - val_s.get_width(), y))
                y += 18

        y += 8
        pygame.draw.line(surface, DIVIDER, (x, y), (x + w, y))
        y += 8

        # Selected star info
        if selected_star_idx is not None and selected_star_idx < len(self.state.stars):
            star = self.state.stars[selected_star_idx]
            owner = self.state.player_for_faction(star.owner_faction_id)
            owner_name = (
                "The Empire" if star.owner_faction_id == EMPIRE_FACTION
                else (owner.name if owner else f"0x{star.owner_faction_id:02x}")
            )
            star_lines = [
                f"Star {star.star_id}  ({star.x},{star.y})",
                f"Type: {star.planet_type}   Res: {star.resource}",
                f"Owner: {owner_name}",
            ]
            # Ship summary
            if star.warships:     star_lines.append(f"  WarShips:    {star.warships}")
            if star.transports:   star_lines.append(f"  TranSports:  {star.transports}")
            if star.stealthships: star_lines.append(f"  StealthShps: {star.stealthships}")
            if star.missiles:     star_lines.append(f"  Missiles:    {star.missiles}")
            # Occupation
            occupied = sum(1 for p in star.planets
                           if p.owner_faction_id != star.owner_faction_id and p.troops > 0)
            if occupied:
                star_lines.append(f"  Occupied: {occupied} planet(s)")

            hdr = self._font_body.render("Selected Star", True, LABEL_COL)
            surface.blit(hdr, (x, y))
            y += 18
            for line in star_lines:
                surf = self._font_body.render(line, True, TEXT_COL)
                surface.blit(surf, (x, y))
                y += 16

        # "End Turn" button pinned to bottom
        btn_y = self.rect.bottom - _BTN_H - _BTN_MARGIN
        self._btn_rect = pygame.Rect(x, btn_y, w, _BTN_H)
        btn_col = BTN_HOVER if self._hovering_btn else BTN_NORMAL
        pygame.draw.rect(surface, btn_col, self._btn_rect, border_radius=4)
        btn_label = self._font_title.render("End Turn", True, BTN_TEXT)
        bx = self._btn_rect.centerx - btn_label.get_width() // 2
        by = self._btn_rect.centery - btn_label.get_height() // 2
        surface.blit(btn_label, (bx, by))