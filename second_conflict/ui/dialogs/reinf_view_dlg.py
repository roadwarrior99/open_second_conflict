"""Reinforcements dialog — REINFVIEWDLG translation.

Lists all friendly fleets currently in transit destined for the
current player's stars, showing ship counts and turns remaining.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL
from second_conflict.model.constants import SHIP_NAMES, FREE_SLOT
from second_conflict.model.game_state import GameState

_ROW_H   = 18
_HDR_COL = (160, 160, 210)
_SEL_COL = (50, 70, 120)
_ALT_COL = (18, 22, 36)

_COLS = [0, 50, 100, 160, 230, 310]


class ReinfViewDialog(BaseDialog):
    """REINFVIEWDLG — incoming friendly reinforcements."""

    def __init__(self, screen: pygame.Surface, state: GameState,
                 player_faction: int):
        super().__init__(screen, "Incoming Reinforcements", width=500, height=380)
        self.state          = state
        self.player_faction = player_faction
        self._rows   = self._build_rows()
        self._scroll = 0
        self._btn_close_rect = None
        self._hover_close    = False

    def _build_rows(self):
        rows = []
        for fleet in self.state.fleets_in_transit:
            if fleet.owner_faction_id == FREE_SLOT:
                continue
            if fleet.owner_faction_id != self.player_faction:
                continue
            if fleet.dest_star < 0 or fleet.dest_star >= len(self.state.stars):
                continue

            dest_star = self.state.stars[fleet.dest_star]
            src_name  = (f"Star {fleet.src_star}"
                         if 0 <= fleet.src_star < len(self.state.stars)
                         else "?")

            # Summarise ship counts
            ship_parts = []
            for attr, ship_type in [
                ('warships',     1), ('stealthships', 2), ('transports', 3),
                ('missiles',     4), ('scouts',        5), ('probes',    7),
            ]:
                count = getattr(fleet, attr, 0) or 0
                if count > 0:
                    ship_parts.append(f"{SHIP_NAMES.get(ship_type, str(ship_type))}×{count}")

            ships_str = ', '.join(ship_parts) if ship_parts else '—'
            fleet_type = getattr(fleet, 'fleet_type', '?')
            if isinstance(fleet_type, int):
                fleet_type = chr(fleet_type) if 32 <= fleet_type < 128 else '?'

            rows.append((
                src_name,
                f"Star {fleet.dest_star}",
                fleet_type,
                fleet.turns_remaining,
                ships_str,
            ))
        rows.sort(key=lambda r: r[3])   # sort by turns remaining
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

        surface.blit(self._text(f"{len(self._rows)} fleet(s) inbound", TITLE_COL),
                     (x, y))
        y += _ROW_H + 4

        for i, h in enumerate(["From", "To", "Type", "Turns", "Ships"]):
            surface.blit(self._text(h, _HDR_COL), (x + _COLS[i], y))
        y += _ROW_H

        vis = self._visible()
        if not self._rows:
            surface.blit(self._text("No reinforcements in transit.", (140, 140, 160)),
                         (x, y))
        else:
            for ri, (src, dst, ftype, turns, ships) in enumerate(
                    self._rows[self._scroll:self._scroll + vis]):
                row_rect = pygame.Rect(cr.x, y, cr.width, _ROW_H)
                if ri % 2 == 1:
                    pygame.draw.rect(surface, _ALT_COL, row_rect)
                col_warn = (220, 180, 60) if turns <= 1 else TEXT_COL
                for ci, txt in enumerate([src, dst, ftype, str(turns), ships]):
                    surface.blit(self._text(txt, col_warn if ci == 3 else TEXT_COL),
                                 (x + _COLS[ci], y))
                y += _ROW_H

        btn_y = self.rect.bottom - 38
        self._btn_close_rect = pygame.Rect(self.rect.centerx - 40, btn_y, 80, 26)
        self._draw_button(surface, self._btn_close_rect, "Close", self._hover_close)