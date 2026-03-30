"""About dialog — translation of ABOUT from SCW.EXE."""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL

_LINES = [
    "Second Conflict",
    "Original game by Jerry W. Galloway, 1991",
    "",
    "Python/pygame recreation",
    "Mechanics faithfully translated from SCW.EXE",
    "via Ghidra decompilation.",
    "",
    "Press OK to close.",
]


class AboutDialog(BaseDialog):
    def __init__(self, screen: pygame.Surface):
        super().__init__(screen, "About Second Conflict", width=400, height=240)
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
        for i, line in enumerate(_LINES):
            col = TITLE_COL if i == 0 else TEXT_COL
            surface.blit(self._font_body.render(line, True, col), (x, y))
            y += 18

        btn_y = self.rect.bottom - 40
        self._btn_ok = pygame.Rect(self.rect.centerx - 45, btn_y, 90, 28)
        self._draw_button(surface, self._btn_ok, "  OK  ", self._hover_ok)