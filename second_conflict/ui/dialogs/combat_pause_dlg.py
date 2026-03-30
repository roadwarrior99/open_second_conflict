"""Combat Pause dialog — COMBATPAUSEDLG translation.

Simple two-button dialog shown between combat rounds:
  Continue (returns True) — watch next round
  Skip     (returns False) — skip remaining animation

Original button IDs: 0x2e6 = Continue, 0x2e7 = Skip/Quit
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL


class CombatPauseDialog(BaseDialog):
    """COMBATPAUSEDLG — pause between battle rounds."""

    def __init__(self, screen: pygame.Surface, round_num: int, total_rounds: int):
        super().__init__(screen, "Combat Pause", width=280, height=130)
        self.round_num    = round_num
        self.total_rounds = total_rounds
        self._btn_cont  = None
        self._btn_skip  = None
        self._hover_cont = False
        self._hover_skip = False

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            self._hover_cont = self._btn_cont and self._btn_cont.collidepoint(event.pos)
            self._hover_skip = self._btn_skip and self._btn_skip.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_cont and self._btn_cont.collidepoint(event.pos):
                self.close(True)
            elif self._btn_skip and self._btn_skip.collidepoint(event.pos):
                self.close(False)

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.close(True)
            elif event.key == pygame.K_s:
                self.close(False)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        msg = f"Round {self.round_num} of {self.total_rounds} complete."
        surface.blit(self._text(msg, TITLE_COL), (x, y))
        y += 22
        surface.blit(self._text("Continue to next round?", TEXT_COL), (x, y))

        btn_y = self.rect.bottom - 42
        mid   = self.rect.centerx
        self._btn_cont = pygame.Rect(mid - 110, btn_y, 100, 26)
        self._btn_skip = pygame.Rect(mid +  10, btn_y, 100, 26)
        self._draw_button(surface, self._btn_cont, "Continue", self._hover_cont)
        self._draw_button(surface, self._btn_skip, "Skip All", self._hover_skip)