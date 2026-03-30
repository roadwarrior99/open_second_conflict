"""Scout Report dialog — SCOUTVIEWDLG translation.

Lists all non-owned stars with known garrison/intelligence info.
In the original, only stars that have been scouted appear; since we
have no fog-of-war, all non-owned stars are shown.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL
from second_conflict.model.constants import EMPIRE_FACTION, PLAYER_COLOURS
from second_conflict.model.game_state import GameState

_ROW_H   = 18
_HDR_COL = (160, 160, 210)
_SEL_COL = (50, 70, 120)
_ALT_COL = (18, 22, 36)

_COLS = [0, 50, 145, 230, 290, 380]   # Star | Coords | Owner | Type | WarShips | Total


class ScoutViewDialog(BaseDialog):
    """SCOUTVIEWDLG — intelligence report on non-owned star systems."""

    def __init__(self, screen: pygame.Surface, state: GameState,
                 player_faction: int):
        super().__init__(screen, "Scout Report", width=600, height=400)
        self.state          = state
        self.player_faction = player_faction
        self._rows   = self._build_rows()
        self._scroll = 0
        self._selected = 0
        self._btn_close_rect = None
        self._hover_close    = False

    def _build_rows(self):
        rows = []
        for star in self.state.stars:
            if star.owner_faction_id == self.player_faction:
                continue
            owner = self.state.player_for_faction(star.owner_faction_id)
            if star.owner_faction_id == EMPIRE_FACTION:
                owner_name = "Empire"
            elif owner:
                owner_name = owner.name[:8]
            else:
                owner_name = f"?{star.owner_faction_id:02x}"

            ws    = star.warships
            total = star.warships + star.transports + star.stealthships + star.missiles
            rows.append((star.star_id, star.x, star.y,
                         owner_name, star.planet_type, ws, total, star))
        rows.sort(key=lambda r: r[0])
        return rows

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_close = (self._btn_close_rect and
                                 self._btn_close_rect.collidepoint(event.pos))
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_close_rect and self._btn_close_rect.collidepoint(event.pos):
                self.close(None); return
            cr = self._content_rect()
            row_y = cr.y + _ROW_H + 4
            for i, _ in enumerate(self._rows[self._scroll:self._scroll + self._visible()]):
                r = pygame.Rect(cr.x, row_y + i * _ROW_H, cr.width, _ROW_H)
                if r.collidepoint(event.pos):
                    new_sel = self._scroll + i
                    if new_sel == self._selected:
                        self._open_planet_detail()
                    else:
                        self._selected = new_sel
                    break
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._selected = max(0, self._selected - 1)
            elif event.key == pygame.K_DOWN:
                self._selected = min(len(self._rows) - 1, self._selected + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._open_planet_detail()
            self._clamp_scroll()
        if event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, min(
                max(0, len(self._rows) - self._visible()),
                self._scroll - event.y))

    def _visible(self):
        cr = self._content_rect()
        return max(1, (cr.height - _ROW_H - 50) // _ROW_H)

    def _open_planet_detail(self):
        if not self._rows or self._selected >= len(self._rows):
            return
        star = self._rows[self._selected][-1]
        from second_conflict.ui.dialogs.planet_detail_dlg import PlanetDetailDialog
        PlanetDetailDialog(self.screen, star, self.state).run()

    def _clamp_scroll(self):
        vis = self._visible()
        if self._selected < self._scroll:
            self._scroll = self._selected
        elif self._selected >= self._scroll + vis:
            self._scroll = self._selected - vis + 1

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        surface.blit(self._text(f"{len(self._rows)} enemy/neutral systems", TITLE_COL),
                     (x, y))
        y += _ROW_H + 4

        for i, h in enumerate(["Star", "Coords", "Owner", "Type", "WarShips", "Total"]):
            surface.blit(self._text(h, _HDR_COL), (x + _COLS[i], y))
        y += _ROW_H

        vis = self._visible()
        for ri, row in enumerate(self._rows[self._scroll:self._scroll + vis]):
            star_id, sx, sy, owner, ptype, ws, total, star = row
            abs_i = self._scroll + ri
            row_rect = pygame.Rect(cr.x, y, cr.width, _ROW_H)
            if abs_i == self._selected:
                pygame.draw.rect(surface, _SEL_COL, row_rect)
            elif ri % 2 == 1:
                pygame.draw.rect(surface, _ALT_COL, row_rect)

            for ci, txt in enumerate([str(star_id), f"({sx},{sy})",
                                       owner, ptype, str(ws), str(total)]):
                surface.blit(self._text(txt), (x + _COLS[ci], y))
            y += _ROW_H

        if len(self._rows) > vis:
            surface.blit(self._text(
                f"  {self._scroll+1}–{min(self._scroll+vis,len(self._rows))} "
                f"of {len(self._rows)}", (100, 100, 140)), (x, y + 4))

        btn_y = self.rect.bottom - 38
        self._btn_close_rect = pygame.Rect(self.rect.centerx - 40, btn_y, 80, 26)
        self._draw_button(surface, self._btn_close_rect, "Close", self._hover_close)