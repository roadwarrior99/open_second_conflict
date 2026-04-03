"""Stats / score dialog — translation of STATSVIEWDLG from SCW.EXE.

Shows a ranking table of all active players sorted by empire_size.
Columns: Rank, Name, Stars, Production, Fleet, Credits
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL, TITLE_COL
from second_conflict.model.game_state import GameState
from second_conflict.model.constants import PLAYER_COLOURS, EMPIRE_FACTION

_ROW_H  = 20
_COL_XS = [0, 30, 120, 200, 280, 360]   # column x offsets relative to content_rect.x
_HEADERS = ["#", "Name", "Stars", "Prod", "Fleet", "Credits"]


class StatsDialog(BaseDialog):
    def __init__(self, screen: pygame.Surface, state: GameState):
        players = [p for p in state.players if p.is_active]
        height = 80 + (_ROW_H * (len(players) + 2)) + 50
        super().__init__(screen, "Statistics", width=420, height=max(height, 200))
        self.state    = state
        self._hover_ok = False
        self._btn_ok   = None

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_ok = self._btn_ok and self._btn_ok.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_ok and self._btn_ok.collidepoint(event.pos):
                self.close(None)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.close(None)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        # Header row
        for col, hdr in zip(_COL_XS, _HEADERS):
            s = self._font_body.render(hdr, True, (160, 160, 200))
            surface.blit(s, (x + col, y))
        y += _ROW_H

        pygame.draw.line(surface, (60, 60, 90),
                         (x, y), (x + cr.width, y))
        y += 4

        # Sort players by empire_size descending
        players = sorted(
            [p for p in self.state.players if p.is_active],
            key=lambda p: p.empire_size,
            reverse=True,
        )
        for rank, player in enumerate(players, 1):
            pidx = self.state.players.index(player)
            colour = PLAYER_COLOURS[pidx] if pidx < len(PLAYER_COLOURS) else TEXT_COL
            display_name = ("The Empire" if player.faction_id == EMPIRE_FACTION
                            else player.name[:9])
            cols = [
                str(rank),
                display_name,
                str(player.empire_size),
                str(player.production),
                str(player.fleet_count),
                str(player.credits),
            ]
            for col, text in zip(_COL_XS, cols):
                s = self._font_body.render(text, True, colour)
                surface.blit(s, (x + col, y))
            y += _ROW_H

        # Turn info
        y += 8
        turn_s = self._text(f"Turn {self.state.turn}", (120, 120, 140))
        surface.blit(turn_s, (x, y))

        # OK button
        btn_y = self.rect.bottom - 40
        self._btn_ok = pygame.Rect(self.rect.centerx - 45, btn_y, 90, 28)
        self._draw_button(surface, self._btn_ok, "  OK  ", self._hover_ok)