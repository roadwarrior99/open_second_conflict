"""Load troops dialog — LOADTRPDLG translation.

Shown from FleetDialog when the player dispatches TranSports.
Displays the friendly-owned planet troops at the source star and lets
the player choose how many to embark (up to transport capacity).

Capacity: each TranSport carries up to 10 troops.
Returns the troop count to embark, or None if cancelled.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL
from second_conflict.model.star import Star

_MAX_PER_TRANSPORT = 10

_OCC_COL  = (220, 140,  40)
_FREE_COL = (120, 200, 120)
_HDR_COL  = (160, 160, 210)
_ALT_COL  = (18,  22,  36)


class LoadTroopsDialog(BaseDialog):
    """Let the player load planet troops onto transport ships."""

    def __init__(self, screen: pygame.Surface, star: Star,
                 faction_id: int, num_transports: int):
        self._star          = star
        self._faction_id    = faction_id
        self._num_transports = num_transports
        self._capacity      = num_transports * _MAX_PER_TRANSPORT

        # Collect (planet_index, troops) for friendly planets
        self._planet_troops: list[tuple[int, int]] = [
            (pi, p.troops)
            for pi, p in enumerate(star.planets)
            if p.owner_faction_id == faction_id and p.troops > 0
        ]
        self._available = sum(t for _, t in self._planet_troops)
        self._max_load  = min(self._available, self._capacity)
        self._load      = self._max_load   # default: full load

        # Hold-to-repeat
        self._held           = None
        self._hold_timer     = 0
        self._hold_accum     = 0
        self._INITIAL_DELAY   = 400
        self._REPEAT_INTERVAL = 60
        self._FAST_INTERVAL   = 20

        h = max(280, 140 + max(1, len(self._planet_troops)) * 18 + 60)
        super().__init__(screen, "Load Troops", width=400, height=h)
        self._hover_ok  = False
        self._hover_can = False
        self._btn_ok    = None
        self._btn_can   = None
        self._btn_plus  = None
        self._btn_minus = None

    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_ok  = self._btn_ok  and self._btn_ok.collidepoint(event.pos)
            self._hover_can = self._btn_can and self._btn_can.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._btn_ok  and self._btn_ok.collidepoint(pos):
                self.close(self._load); return
            if self._btn_can and self._btn_can.collidepoint(pos):
                self.close(None); return
            if self._btn_plus  and self._btn_plus.collidepoint(pos):
                self._adjust(+1); self._start_hold(+1); return
            if self._btn_minus and self._btn_minus.collidepoint(pos):
                self._adjust(-1); self._start_hold(-1); return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._adjust(+1)
            elif event.key == pygame.K_DOWN:
                self._adjust(-1)
            elif event.key == pygame.K_RETURN:
                self.close(self._load)
            elif event.key == pygame.K_ESCAPE:
                self.close(None)

    def update(self, dt: int):
        if self._held is None:
            return
        self._hold_timer += dt
        if self._hold_timer < self._INITIAL_DELAY:
            return
        interval = self._FAST_INTERVAL if self._hold_timer > 1000 else self._REPEAT_INTERVAL
        self._hold_accum += dt
        while self._hold_accum >= interval:
            self._hold_accum -= interval
            self._adjust(self._held)

    def _start_hold(self, delta: int):
        self._held = delta; self._hold_timer = 0; self._hold_accum = 0

    def _adjust(self, delta: int):
        self._load = max(0, min(self._max_load, self._load + delta))

    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        # Summary line
        surface.blit(self._text(
            f"Transports: {self._num_transports}   "
            f"Capacity: {self._capacity}   "
            f"Available troops: {self._available}",
            TITLE_COL), (x, y)); y += 22

        # Per-planet breakdown
        if not self._planet_troops:
            surface.blit(self._text("No friendly troops at this star.", _OCC_COL), (x, y))
            y += 18
        else:
            surface.blit(self._text("Planet", _HDR_COL),  (x,      y))
            surface.blit(self._text("Troops", _HDR_COL),  (x + 80, y))
            y += 16
            for ri, (pi, t) in enumerate(self._planet_troops):
                row = pygame.Rect(cr.x, y, cr.width, 16)
                if ri % 2 == 1:
                    pygame.draw.rect(surface, _ALT_COL, row)
                surface.blit(self._text(f"Planet {pi + 1}"),  (x,      y))
                surface.blit(self._text(str(t), _FREE_COL),   (x + 80, y))
                y += 16

        y += 6

        # Troop selector
        surface.blit(self._text("Troops to embark:"), (x, y))
        n_surf = self._font_title.render(str(self._load), True, TITLE_COL)
        surface.blit(n_surf, (x + 180, y)); y += 26

        self._btn_minus = pygame.Rect(x,      y, 36, 26)
        self._btn_plus  = pygame.Rect(x + 44, y, 36, 26)
        self._draw_button(surface, self._btn_minus, " - ")
        self._draw_button(surface, self._btn_plus,  " + ")

        if self._max_load > 0:
            pct = self._load / self._max_load * 100
            surface.blit(self._text(f"  {pct:.0f}% of maximum", (160, 200, 160)),
                         (x + 88, y))
        y += 34

        if self._available < self._capacity:
            surface.blit(self._text(
                f"Note: only {self._available} troops available "
                f"(capacity {self._capacity})", (200, 160, 80)),
                (x, y))

        btn_y = self.rect.bottom - 40
        self._btn_ok  = pygame.Rect(self.rect.centerx - 100, btn_y, 90, 28)
        self._btn_can = pygame.Rect(self.rect.centerx + 10,  btn_y, 90, 28)
        self._draw_button(surface, self._btn_ok,  "Embark",  self._hover_ok)
        self._draw_button(surface, self._btn_can, "Cancel",  self._hover_can)