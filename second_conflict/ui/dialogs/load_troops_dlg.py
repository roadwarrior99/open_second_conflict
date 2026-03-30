"""Load troops dialog — translation of LOADTRPDLG from SCW.EXE.

When a TranSport fleet is being dispatched, this dialog lets the player
choose how many 'troops' (WarShips loaded as cargo) to put aboard each
transport.  In the original, transports carry a fixed number of troops.

The original LOADTRPDLG is invoked from FLEETDLG when transports are in the
fleet.  Here it is a standalone modal that returns the troop count or None.

Capacity: each transport carries up to 10 troops.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL

_MAX_PER_TRANSPORT = 10


class LoadTroopsDialog(BaseDialog):
    def __init__(self, screen: pygame.Surface,
                 num_transports: int, available_warships: int):
        super().__init__(screen, "Load Troops", width=360, height=220)
        self._num_transports   = num_transports
        self._available        = min(available_warships,
                                     num_transports * _MAX_PER_TRANSPORT)
        self._troops           = 0
        self._hover_ok         = False
        self._hover_can        = False
        self._btn_ok           = None
        self._btn_can          = None
        self._btn_plus         = None
        self._btn_minus        = None

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_ok  = self._btn_ok  and self._btn_ok.collidepoint(event.pos)
            self._hover_can = self._btn_can and self._btn_can.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._btn_ok  and self._btn_ok.collidepoint(pos):
                self.close(self._troops)
            if self._btn_can and self._btn_can.collidepoint(pos):
                self.close(None)
            if self._btn_plus  and self._btn_plus.collidepoint(pos):
                self._troops = min(self._available, self._troops + 1)
            if self._btn_minus and self._btn_minus.collidepoint(pos):
                self._troops = max(0, self._troops - 1)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._troops = min(self._available, self._troops + 1)
            elif event.key == pygame.K_DOWN:
                self._troops = max(0, self._troops - 1)
            elif event.key == pygame.K_RETURN:
                self.close(self._troops)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        surface.blit(self._text(
            f"Transports: {self._num_transports}   Capacity: {self._available}"
        ), (x, y)); y += 22

        surface.blit(self._text("Troops to load:"), (x, y))
        troops_surf = self._font_title.render(str(self._troops), True, TITLE_COL)
        surface.blit(troops_surf, (x + 160, y)); y += 26

        # +/- buttons
        self._btn_minus = pygame.Rect(x,       y, 40, 28)
        self._btn_plus  = pygame.Rect(x + 50,  y, 40, 28)
        self._draw_button(surface, self._btn_minus, "  -  ")
        self._draw_button(surface, self._btn_plus,  "  +  ")
        y += 36

        capacity_pct = (self._troops / max(1, self._available)) * 100
        surface.blit(self._text(f"Loading: {capacity_pct:.0f}%",
                                 (160, 200, 160)), (x, y))

        btn_y = self.rect.bottom - 40
        self._btn_ok  = pygame.Rect(self.rect.centerx - 100, btn_y, 90, 28)
        self._btn_can = pygame.Rect(self.rect.centerx + 10,  btn_y, 90, 28)
        self._draw_button(surface, self._btn_ok,  "Load",   self._hover_ok)
        self._draw_button(surface, self._btn_can, "Cancel", self._hover_can)