"""About dialog — translation of ABOUT from SCW.EXE.

Shows the original SCWTIT.DLL title artwork if available, otherwise falls
back to a plain text credits screen.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL

_CREDITS = [
    "Original game by Jerry W. Galloway, 1991",
    "Published by Impressions Software",
    "",
    "Python/pygame recreation",
    "Mechanics faithfully translated from SCW.EXE",
    "via Ghidra 12.0 decompilation.",
]

_TITLE_W = 288
_TITLE_H = 360


class AboutDialog(BaseDialog):
    def __init__(self, screen: pygame.Surface):
        # Try to load the title artwork up front so we can size the dialog
        self._title_surf = None
        try:
            from second_conflict.assets import get_title_screen
            self._title_surf = get_title_screen()
        except Exception:
            pass

        if self._title_surf:
            w = _TITLE_W + 380   # image on left, credits on right
            h = _TITLE_H + 60    # room for title bar + OK button
        else:
            w, h = 520, 260

        super().__init__(screen, "About Second Conflict", width=w, height=h)
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

        if self._title_surf:
            # Left: title artwork
            img_rect = pygame.Rect(cr.x, cr.y, _TITLE_W, _TITLE_H)
            surface.blit(self._title_surf, img_rect)

            # Right: credits text
            tx = cr.x + _TITLE_W + 16
            ty = cr.y + 10
            surface.blit(self._font_title.render("Second Conflict", True, TITLE_COL),
                         (tx, ty))
            ty += 28
            for line in _CREDITS:
                surface.blit(self._font_body.render(line, True, TEXT_COL), (tx, ty))
                ty += 20
        else:
            # Fallback: text-only
            x, y = cr.x, cr.y
            surface.blit(self._font_title.render("Second Conflict", True, TITLE_COL),
                         (x, y))
            y += 24
            for line in _CREDITS:
                surface.blit(self._font_body.render(line, True, TEXT_COL), (x, y))
                y += 18

        btn_y = self.rect.bottom - 42
        self._btn_ok = pygame.Rect(self.rect.centerx - 45, btn_y, 90, 28)
        self._draw_button(surface, self._btn_ok, "  OK  ", self._hover_ok)