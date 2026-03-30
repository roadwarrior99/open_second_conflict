"""Planet Detail dialog.

Shows the individual planets within a single star system — their index,
troop count, and occupation status.  Opened from the Planet Administration
overview when a star row is selected.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL
from second_conflict.model.star import Star
from second_conflict.model.game_state import GameState

_ROW_H   = 22
_HDR_COL = (160, 160, 210)
_ALT_COL = (18, 22, 36)
_OCC_COL = (220, 140,  40)   # orange — occupied
_FREE_COL = (80, 200,  80)   # green  — clear

_COLS = [0, 80, 200, 320]   # Planet# | Status | Troops | Notes


class PlanetDetailDialog(BaseDialog):
    """Per-system planet list with occupation detail."""

    def __init__(self, screen: pygame.Surface, star: Star, state: GameState):
        self.star  = star
        self.state = state
        n = star.num_planets
        h = 80 + n * _ROW_H + 100
        super().__init__(screen, f"Star {star.star_id} — Planets", width=480, height=h)
        self._btn_close_rect = None
        self._hover_close    = False

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_close = (self._btn_close_rect and
                                 self._btn_close_rect.collidepoint(event.pos))
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_close_rect and self._btn_close_rect.collidepoint(event.pos):
                self.close(None)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y
        star = self.star

        # System summary
        owner_name = star.owner_name(self.state.players)
        total_troops = star.troops
        surface.blit(self._text(
            f"Owner: {owner_name}   Type: {star.planet_type}   "
            f"Resource: {star.resource}", TITLE_COL), (x, y))
        y += _ROW_H

        if total_troops > 0:
            occ_name = next(
                (p.name for p in self.state.players
                 if p.faction_id == star.troop_faction),
                f"0x{star.troop_faction:02x}"
            )
            surface.blit(self._text(
                f"OCCUPIED by {occ_name} — {total_troops} troops total",
                _OCC_COL), (x, y))
        else:
            surface.blit(self._text("All planets clear.", _FREE_COL), (x, y))
        y += _ROW_H + 4

        # Column headers
        for ci, hdr in enumerate(["Planet", "Status", "Troops", "Notes"]):
            surface.blit(self._text(hdr, _HDR_COL), (x + _COLS[ci], y))
        y += _ROW_H

        n = star.num_planets
        for pi in range(n):
            planet   = star.planets[pi] if pi < len(star.planets) else None
            troops   = planet.troops if planet is not None else 0
            occupied = troops > 0

            row_rect = pygame.Rect(cr.x, y, cr.width, _ROW_H)
            if pi % 2 == 1:
                pygame.draw.rect(surface, _ALT_COL, row_rect)

            status     = "Occupied" if occupied else "Clear"
            status_col = _OCC_COL   if occupied else _FREE_COL
            troops_str = str(troops) if occupied else "—"
            notes      = "Needs bombardment" if occupied else ""

            surface.blit(self._text(f"Planet {pi + 1}"),            (x + _COLS[0], y))
            surface.blit(self._text(status, status_col),             (x + _COLS[1], y))
            surface.blit(self._text(troops_str, status_col),         (x + _COLS[2], y))
            surface.blit(self._text(notes, (160, 160, 160)),         (x + _COLS[3], y))
            y += _ROW_H

        btn_y = self.rect.bottom - 38
        self._btn_close_rect = pygame.Rect(self.rect.centerx - 40, btn_y, 80, 26)
        self._draw_button(surface, self._btn_close_rect, "Close", self._hover_close)