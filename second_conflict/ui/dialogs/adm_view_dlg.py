"""Planet Administration dialog — ADMVIEWDLG translation.

Shows all stars owned by the current player with a 6-column table:
  Star | Coords | Type | Res | WarShips | Stealth

Column tab-stops from original: 50 | 80 | 110 | 140 | 175 | 200
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL
from second_conflict.model.constants import (
    SHIP_NAMES, ShipType, PLAYER_COLOURS, EMPIRE_FACTION,
)
from second_conflict.model.game_state import GameState

_ROW_H   = 18
_HDR_COL = (160, 160, 210)
_SEL_COL = (50, 70, 120)
_ALT_COL = (18, 22, 36)

# Column x-offsets (matching original tab-stops scaled to our dialog width)
_COLS = [0, 50, 90, 130, 165, 210, 260]   # left edges; last entry = right bound


class AdminViewDialog(BaseDialog):
    """ADMVIEWDLG — full planet/star administration list."""

    def __init__(self, screen: pygame.Surface, state: GameState,
                 player_faction: int):
        super().__init__(screen, "Planet Administration", width=500, height=420)
        self.state          = state
        self.player_faction = player_faction

        self._rows   = self._build_rows()
        self._scroll = 0
        self._selected = 0

        self._btn_close_rect = None
        self._hover_close    = False

    # ------------------------------------------------------------------

    def _build_rows(self):
        rows = []
        for star in self.state.stars:
            if star.owner_faction_id != self.player_faction:
                continue
            ws = sum(g.ship_count for g in star.garrison
                     if g.owner_faction_id == self.player_faction
                     and g.ship_type == int(ShipType.WARSHIP))
            ss = sum(g.ship_count for g in star.garrison
                     if g.owner_faction_id == self.player_faction
                     and g.ship_type == int(ShipType.STEALTHSHIP))
            rows.append((star.star_id, star.x, star.y,
                         star.planet_type, star.resource, ws, ss, star))
        rows.sort(key=lambda r: r[0])
        return rows

    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            self._hover_close = (self._btn_close_rect and
                                 self._btn_close_rect.collidepoint(event.pos))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_close_rect and self._btn_close_rect.collidepoint(event.pos):
                self.close(None)
                return
            cr = self._content_rect()
            row_y = cr.y + _ROW_H + 4
            for i, _ in enumerate(self._rows[self._scroll:self._scroll + self._visible()]):
                r = pygame.Rect(cr.x, row_y + i * _ROW_H, cr.width, _ROW_H)
                if r.collidepoint(event.pos):
                    self._selected = self._scroll + i

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._selected = max(0, self._selected - 1)
                self._clamp_scroll()
            elif event.key == pygame.K_DOWN:
                self._selected = min(len(self._rows) - 1, self._selected + 1)
                self._clamp_scroll()
            elif event.key == pygame.K_PAGEUP:
                self._selected = max(0, self._selected - self._visible())
                self._clamp_scroll()
            elif event.key == pygame.K_PAGEDOWN:
                self._selected = min(len(self._rows) - 1,
                                     self._selected + self._visible())
                self._clamp_scroll()

        if event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, min(
                len(self._rows) - self._visible(),
                self._scroll - event.y
            ))

    def _visible(self):
        cr = self._content_rect()
        return max(1, (cr.height - _ROW_H - 50) // _ROW_H)

    def _clamp_scroll(self):
        vis = self._visible()
        if self._selected < self._scroll:
            self._scroll = self._selected
        elif self._selected >= self._scroll + vis:
            self._scroll = self._selected - vis + 1

    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        # Summary line
        total_ws = sum(r[5] for r in self._rows)
        total_ss = sum(r[6] for r in self._rows)
        summary = (f"{len(self._rows)} stars   "
                   f"WarShips: {total_ws}   StealthShips: {total_ss}")
        surface.blit(self._text(summary, TITLE_COL), (x, y))
        y += _ROW_H + 4

        # Header
        headers = ["Star", "Coords", "Type", "Res", "WarShip", "Stealth"]
        for i, h in enumerate(headers):
            surface.blit(self._text(h, _HDR_COL),
                         (x + _COLS[i], y))
        y += _ROW_H

        # Rows
        vis = self._visible()
        for ri, row in enumerate(self._rows[self._scroll:self._scroll + vis]):
            star_id, sx, sy, ptype, res, ws, ss, star = row
            abs_i = self._scroll + ri
            row_rect = pygame.Rect(cr.x, y, cr.width, _ROW_H)

            if abs_i == self._selected:
                pygame.draw.rect(surface, _SEL_COL, row_rect)
            elif ri % 2 == 1:
                pygame.draw.rect(surface, _ALT_COL, row_rect)

            cols = [str(star_id), f"({sx},{sy})", ptype,
                    str(res), str(ws), str(ss)]
            for ci, txt in enumerate(cols):
                color = TEXT_COL
                if ci == 4 and ws == 0:
                    color = (180, 80, 80)   # no warships — highlight
                surface.blit(self._text(txt, color), (x + _COLS[ci], y))
            y += _ROW_H

        # Scroll indicator
        if len(self._rows) > vis:
            scroll_txt = (f"  {self._scroll + 1}–"
                          f"{min(self._scroll + vis, len(self._rows))} "
                          f"of {len(self._rows)}")
            surface.blit(self._text(scroll_txt, (100, 100, 140)),
                         (x, y + 4))

        btn_y = self.rect.bottom - 38
        self._btn_close_rect = pygame.Rect(self.rect.centerx - 40, btn_y, 80, 26)
        self._draw_button(surface, self._btn_close_rect, "Close", self._hover_close)