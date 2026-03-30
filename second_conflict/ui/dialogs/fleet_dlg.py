"""Fleet dispatch dialog — translation of FLEETDLG from SCW.EXE.

Shows the garrison at a selected star and lets the player choose:
  - Destination star (typed number or clicked on map — here we use a text input)
  - How many ships of each type to send

Result: dict with keys 'dest_star', 'ship_counts' or None if cancelled.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL, TITLE_COL
from second_conflict.model.star import Star
from second_conflict.model.constants import ShipType, SHIP_NAMES
from second_conflict.model.game_state import GameState

_SHIP_ORDER = [
    ShipType.WARSHIP,
    ShipType.STEALTHSHIP,
    ShipType.TRANSPORT,
    ShipType.MISSILE,
    ShipType.SCOUT,
    ShipType.PROBE,
]

_ROW_H  = 22
_COL_W  = 80
_BTN_H  = 28
_BTN_W  = 90


class FleetDialog(BaseDialog):
    """Dispatch a fleet from src_star_idx to a chosen destination."""

    def __init__(self, screen: pygame.Surface, state: GameState,
                 src_star_idx: int, player_faction: int):
        super().__init__(screen, "Dispatch Fleet", width=460, height=360)
        self.state          = state
        self.src_star_idx   = src_star_idx
        self.player_faction = player_faction
        self._star          = state.stars[src_star_idx]

        # Build garrison rows: {ship_type: (available, to_send)}
        avail = {}
        for g in self._star.garrison:
            if g.owner_faction_id == player_faction and g.ship_count > 0:
                avail[g.ship_type] = avail.get(g.ship_type, 0) + g.ship_count
        self._avail: dict[int, int] = avail
        self._send:  dict[int, int] = {st: 0 for st in _SHIP_ORDER if st in avail}

        # Destination input
        self._dest_str   = ""
        self._dest_error = ""
        self._hover_ok   = False
        self._hover_can  = False

        # Compute button rects (set in draw)
        self._btn_ok_rect  = None
        self._btn_can_rect = None
        self._plus_rects:  dict[int, pygame.Rect] = {}
        self._minus_rects: dict[int, pygame.Rect] = {}

        # Hold-repeat state: (ship_type, delta) while a +/- button is held
        self._held:         tuple[int, int] | None = None  # (ship_type, +1 or -1)
        self._hold_timer:   int = 0   # ms since button pressed
        self._hold_accum:   int = 0   # ms since last repeat tick
        _INITIAL_DELAY      = 400     # ms before repeat starts
        _REPEAT_INTERVAL    = 60      # ms between repeat ticks (speeds up after 1 s)
        _FAST_INTERVAL      = 20      # ms between ticks after 1 s of holding
        self._INITIAL_DELAY  = _INITIAL_DELAY
        self._REPEAT_INTERVAL = _REPEAT_INTERVAL
        self._FAST_INTERVAL   = _FAST_INTERVAL

    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_ok  = self._btn_ok_rect  and self._btn_ok_rect.collidepoint(event.pos)
            self._hover_can = self._btn_can_rect and self._btn_can_rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._btn_ok_rect and self._btn_ok_rect.collidepoint(pos):
                self._try_dispatch()
                return
            if self._btn_can_rect and self._btn_can_rect.collidepoint(pos):
                self.close(None)
                return
            for st, r in self._plus_rects.items():
                if r.collidepoint(pos):
                    self._apply_delta(st, +1)
                    self._start_hold(st, +1)
                    return
            for st, r in self._minus_rects.items():
                if r.collidepoint(pos):
                    self._apply_delta(st, -1)
                    self._start_hold(st, -1)
                    return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._try_dispatch()
            elif event.key == pygame.K_BACKSPACE:
                self._dest_str = self._dest_str[:-1]
            elif event.unicode.isdigit():
                if len(self._dest_str) < 3:
                    self._dest_str += event.unicode

    def update(self, dt: int):
        if self._held is None:
            return
        st, delta = self._held
        self._hold_timer += dt
        if self._hold_timer < self._INITIAL_DELAY:
            return
        # Choose repeat interval: fast after 1 second of holding
        interval = (self._FAST_INTERVAL
                    if self._hold_timer > 1000
                    else self._REPEAT_INTERVAL)
        self._hold_accum += dt
        while self._hold_accum >= interval:
            self._hold_accum -= interval
            self._apply_delta(st, delta)

    def _start_hold(self, ship_type: int, delta: int):
        self._held       = (ship_type, delta)
        self._hold_timer = 0
        self._hold_accum = 0

    def _apply_delta(self, ship_type: int, delta: int):
        if delta > 0:
            self._send[ship_type] = min(
                self._send[ship_type] + 1, self._avail.get(ship_type, 0)
            )
        else:
            self._send[ship_type] = max(0, self._send[ship_type] - 1)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr  = self._content_rect()
        x, y = cr.x, cr.y

        # Source info
        surf = self._text(
            f"Star {self._star.star_id}  ({self._star.x},{self._star.y})  "
            f"Type:{self._star.planet_type}",
            TITLE_COL
        )
        surface.blit(surf, (x, y)); y += 20

        # Destination input row
        dest_lbl = self._text("Destination star #:")
        surface.blit(dest_lbl, (x, y))
        # Input box
        input_rect = pygame.Rect(x + 160, y, 60, 18)
        pygame.draw.rect(surface, (40, 40, 60), input_rect)
        pygame.draw.rect(surface, (100, 100, 160), input_rect, 1)
        inp_surf = self._text(self._dest_str + "|")
        surface.blit(inp_surf, (input_rect.x + 3, input_rect.y + 1))
        if self._dest_error:
            err = self._text(self._dest_error, (220, 60, 60))
            surface.blit(err, (x + 230, y))
        y += 26

        # Header row
        headers = ["Ship Type", "Available", "Send", "", ""]
        hx = x
        for h in headers:
            s = self._text(h, (160, 160, 200))
            surface.blit(s, (hx, y))
            hx += _COL_W
        y += 18

        self._plus_rects.clear()
        self._minus_rects.clear()

        for st in _SHIP_ORDER:
            if st not in self._avail:
                continue
            cols = [
                SHIP_NAMES.get(st, f"Type{st}"),
                str(self._avail.get(st, 0)),
                str(self._send.get(st, 0)),
            ]
            hx = x
            for col in cols:
                surface.blit(self._text(col), (hx, y))
                hx += _COL_W

            # Minus button
            minus_r = pygame.Rect(hx, y, 20, 18)
            self._minus_rects[st] = minus_r
            self._draw_button(surface, minus_r, "-")
            hx += 26

            # Plus button
            plus_r = pygame.Rect(hx, y, 20, 18)
            self._plus_rects[st] = plus_r
            self._draw_button(surface, plus_r, "+")

            y += _ROW_H

        y += 6

        # OK / Cancel buttons
        btn_y = self.rect.bottom - _BTN_H - 10
        self._btn_ok_rect  = pygame.Rect(self.rect.x + 20, btn_y, _BTN_W, _BTN_H)
        self._btn_can_rect = pygame.Rect(self.rect.right - _BTN_W - 20, btn_y, _BTN_W, _BTN_H)
        self._draw_button(surface, self._btn_ok_rect,  "Dispatch", self._hover_ok)
        self._draw_button(surface, self._btn_can_rect, "Cancel",   self._hover_can)

    # ------------------------------------------------------------------

    def _try_dispatch(self):
        if not self._dest_str:
            self._dest_error = "Enter destination"
            return
        dest = int(self._dest_str)
        if dest < 0 or dest >= len(self.state.stars):
            self._dest_error = f"No star {dest}"
            return
        if dest == self.src_star_idx:
            self._dest_error = "Same star!"
            return
        total = sum(self._send.values())
        if total == 0:
            self._dest_error = "No ships selected"
            return
        self._dest_error = ""
        self.close({
            'dest_star':   dest,
            'ship_counts': {st: n for st, n in self._send.items() if n > 0},
        })