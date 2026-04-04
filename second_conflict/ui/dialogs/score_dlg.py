"""Score / end-game dialog — translation of SCOREVIEWDLG from SCW.EXE.

Shows the final ranking of all players (including Empire) sorted by score,
plus a winner announcement.  The original sorted by score descending.

Score is approximated as empire_size * 10 + fleet_count (the original used
a more complex morale × territory formula; we use what we have in the model).
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL
from second_conflict.model.constants import PLAYER_COLOURS, EMPIRE_FACTION, EMPIRE_COLOUR
from second_conflict.model.game_state import GameState

_ROW_H = 20


def _score(player) -> int:
    return player.empire_size * 10 + player.fleet_count


class ScoreDialog(BaseDialog):
    def __init__(self, screen: pygame.Surface, state: GameState):
        n = len(state.players) + 1   # +1 for Empire row
        height = 100 + _ROW_H * (n + 2) + 60
        super().__init__(screen, "Final Scores", width=440, height=max(height, 240))
        self.state     = state
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

        # Turn / game summary line
        summary = self._text(f"Game ended on turn {self.state.turn}", (160, 160, 200))
        surface.blit(summary, (x, y)); y += 20

        # Winner banner
        if self.state.winner_slot is not None:
            winner = self.state.players[self.state.winner_slot]
            banner = self._font_title.render(
                f"Winner: {winner.name}", True, (255, 220, 60)
            )
            surface.blit(banner, (x, y)); y += 24
        y += 4

        # Column headers
        headers = [("#", 0), ("Admiral", 20), ("Stars", 145), ("Fleet", 185),
                   ("Score", 225), ("Status", 270)]
        for hdr, cx in headers:
            surface.blit(self._font_body.render(hdr, True, (150, 150, 200)), (x + cx, y))
        y += _ROW_H
        pygame.draw.line(surface, (60, 60, 90), (x, y), (x + cr.width, y))
        y += 2

        # Rank players by score
        players = sorted(self.state.players, key=_score, reverse=True)

        for rank, player in enumerate(players, 1):
            pidx   = self.state.players.index(player)
            colour = PLAYER_COLOURS[pidx] if pidx < len(PLAYER_COLOURS) else TEXT_COL
            status = "Active" if player.is_active else "Eliminated"
            cols = [
                (str(rank),           0),
                (player.name[:14],    20),
                (str(player.empire_size), 145),
                (str(player.fleet_count), 185),
                (str(_score(player)), 225),
                (status,              270),
            ]
            for text, cx in cols:
                surface.blit(self._font_body.render(text, True, colour), (x + cx, y))
            y += _ROW_H

        btn_y = self.rect.bottom - 40
        self._btn_ok = pygame.Rect(self.rect.centerx - 45, btn_y, 90, 28)
        self._draw_button(surface, self._btn_ok, "  OK  ", self._hover_ok)