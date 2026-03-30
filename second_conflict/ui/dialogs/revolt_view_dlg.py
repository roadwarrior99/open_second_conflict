"""Revolt Report dialog — REVOLTVIEWDLG translation.

Shows all stars owned by the current player that have negative loyalty
(at risk of revolt) or have already revolted (changed owner this turn).
Distinct from UnrestDialog (UNRESTVIEWDLG) which shows all negative-loyalty
stars across all factions.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL
from second_conflict.model.game_state import GameState

_ROW_H   = 18
_HDR_COL = (160, 160, 210)
_ALT_COL = (18, 22, 36)

_COLS    = [0, 50, 110, 160, 210]

_REVOLT_THRESHOLD = -5   # loyalty at or below this = revolt imminent


class RevoltViewDialog(BaseDialog):
    """REVOLTVIEWDLG — revolt-risk stars owned by the current player."""

    def __init__(self, screen: pygame.Surface, state: GameState,
                 player_faction: int):
        super().__init__(screen, "Revolt Report", width=440, height=360)
        self.state          = state
        self.player_faction = player_faction
        self._rows   = self._build_rows()
        self._scroll = 0
        self._btn_close_rect = None
        self._hover_close    = False

    def _build_rows(self):
        rows = []
        for star in self.state.stars:
            if star.owner_faction_id != self.player_faction:
                continue
            if star.loyalty >= 0:
                continue   # only negative-loyalty stars
            rows.append((star.star_id, star.x, star.y,
                         star.loyalty, star.planet_type, star))
        rows.sort(key=lambda r: r[3])   # most negative first
        return rows

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_close = (self._btn_close_rect and
                                 self._btn_close_rect.collidepoint(event.pos))
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_close_rect and self._btn_close_rect.collidepoint(event.pos):
                self.close(None)
        if event.type == pygame.MOUSEWHEEL:
            vis = self._visible()
            self._scroll = max(0, min(max(0, len(self._rows) - vis),
                                      self._scroll - event.y))

    def _visible(self):
        cr = self._content_rect()
        return max(1, (cr.height - _ROW_H - 50) // _ROW_H)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        title_col = (220, 80, 80) if self._rows else (100, 180, 100)
        title_txt = (f"{len(self._rows)} star(s) at revolt risk"
                     if self._rows else "No stars at revolt risk")
        surface.blit(self._text(title_txt, title_col), (x, y))
        y += _ROW_H + 4

        for i, h in enumerate(["Star", "Coords", "Type", "Loyalty", "Status"]):
            surface.blit(self._text(h, _HDR_COL), (x + _COLS[i], y))
        y += _ROW_H

        vis = self._visible()
        if not self._rows:
            surface.blit(self._text("All planets loyal.", (100, 180, 100)), (x, y))
        else:
            for ri, (star_id, sx, sy, loyalty, ptype, star) in enumerate(
                    self._rows[self._scroll:self._scroll + vis]):
                row_rect = pygame.Rect(cr.x, y, cr.width, _ROW_H)
                if ri % 2 == 1:
                    pygame.draw.rect(surface, _ALT_COL, row_rect)

                status = "REVOLTING" if loyalty <= _REVOLT_THRESHOLD else "Unrest"
                loyalty_col = (220, 60, 60) if loyalty <= _REVOLT_THRESHOLD else (220, 160, 60)
                status_col  = (220, 60, 60) if loyalty <= _REVOLT_THRESHOLD else (220, 160, 60)

                for ci, (txt, col) in enumerate([
                    (str(star_id), TEXT_COL),
                    (f"({sx},{sy})", TEXT_COL),
                    (ptype, TEXT_COL),
                    (str(loyalty), loyalty_col),
                    (status, status_col),
                ]):
                    surface.blit(self._text(txt, col), (x + _COLS[ci], y))
                y += _ROW_H

        btn_y = self.rect.bottom - 38
        self._btn_close_rect = pygame.Rect(self.rect.centerx - 40, btn_y, 80, 26)
        self._draw_button(surface, self._btn_close_rect, "Close", self._hover_close)