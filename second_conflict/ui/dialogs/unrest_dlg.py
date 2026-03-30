"""Unrest view dialog — translation of UNRESTVIEWDLG from SCW.EXE.

Shows all stars where the player's garrison is experiencing loyalty stress
(loyalty < 0) or where a foreign garrison is present.  Mirrors the original
listbox format:

  "Star %d  loyalty:%d  foreign:%d units"
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL
from second_conflict.model.constants import EMPIRE_FACTION
from second_conflict.model.game_state import GameState
from second_conflict.engine.revolt import REVOLT_THRESHOLD

_ROW_H = 18


class UnrestDialog(BaseDialog):
    def __init__(self, screen: pygame.Surface, state: GameState,
                 player_faction: int):
        self._rows = _build_rows(state, player_faction)
        height = 80 + _ROW_H * (max(len(self._rows), 1) + 2) + 50
        super().__init__(screen, "Unrest Report", width=460, height=max(height, 180))
        self._scroll    = 0
        self._hover_ok  = False
        self._btn_ok    = None

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_ok = self._btn_ok and self._btn_ok.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self._btn_ok and self._btn_ok.collidepoint(event.pos):
                self.close(None)
            elif event.button == 4:
                self._scroll = max(0, self._scroll - 1)
            elif event.button == 5:
                self._scroll = min(max(0, len(self._rows) - 14), self._scroll + 1)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.close(None)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr  = self._content_rect()
        x, y = cr.x, cr.y

        if not self._rows:
            surface.blit(self._text("No unrest to report."), (x, y))
        else:
            visible = min(14, (cr.height - _ROW_H - 50) // _ROW_H)
            for row in self._rows[self._scroll: self._scroll + visible]:
                col = (255, 120, 60) if row['critical'] else TEXT_COL
                line = (f"Star {row['star_id']:2d}  "
                        f"loyalty:{row['loyalty']:+d}  "
                        f"foreign:{row['foreign']} ships")
                surface.blit(self._text(line, col), (x, y))
                y += _ROW_H

            if len(self._rows) > visible:
                note = self._text(
                    f"  {self._scroll+1}-{min(self._scroll+visible, len(self._rows))} "
                    f"of {len(self._rows)}",
                    (120, 120, 140)
                )
                surface.blit(note, (x, y))

        btn_y = self.rect.bottom - 38
        self._btn_ok = pygame.Rect(self.rect.centerx - 45, btn_y, 90, 28)
        self._draw_button(surface, self._btn_ok, "  OK  ", self._hover_ok)


def _build_rows(state: GameState, player_faction: int) -> list[dict]:
    rows = []
    for star in state.stars:
        factions = {g.owner_faction_id for g in star.garrison if g.ship_count > 0}
        if player_faction not in factions:
            continue
        # Find this player's garrison entry
        player_g = [g for g in star.garrison
                    if g.owner_faction_id == player_faction and g.ship_count > 0]
        if not player_g:
            continue
        loyalty = min(g.loyalty for g in player_g)
        if loyalty >= 0:
            continue  # no stress
        foreign = sum(
            g.ship_count for g in star.garrison
            if g.owner_faction_id != player_faction
            and g.owner_faction_id != EMPIRE_FACTION
            and g.ship_count > 0
        )
        rows.append({
            'star_id':  star.star_id,
            'loyalty':  loyalty,
            'foreign':  foreign,
            'critical': loyalty <= REVOLT_THRESHOLD + 1,
        })
    rows.sort(key=lambda r: r['loyalty'])
    return rows