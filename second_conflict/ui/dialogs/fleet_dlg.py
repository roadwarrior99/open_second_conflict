"""Fleet dispatch dialog — translation of FLEETDLG from SCW.EXE.

Shows the ships at a selected star and lets the player choose:
  - Destination star (typed number)
  - How many ships of each type to send

Warships go as combat ships; transports are dispatched as troop ships
(loaded for invasion).  Result: dict with 'dest_star' and ship counts,
or None if cancelled.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL, TITLE_COL
from second_conflict.model.star import Star
from second_conflict.model.game_state import GameState

# (label, star_attr, fleet_attr) — what to show and what field to fill in fleet
_SHIP_ROWS = [
    ("WarShips",    "warships",     "warships"),
    ("TranSports",  "transports",   "troop_ships"),   # transports dispatch as troop ships
    ("StealthShps", "stealthships", "stealthships"),
    ("Missiles",    "missiles",     "missiles"),
]

_ROW_H  = 22
_COL_W  = 90
_BTN_H  = 28
_BTN_W  = 90


class FleetDialog(BaseDialog):
    """Dispatch a fleet from src_star_idx to a chosen destination."""

    def __init__(self, screen: pygame.Surface, state: GameState,
                 src_star_idx: int, player_faction: int):
        super().__init__(screen, "Dispatch Fleet", width=460, height=340)
        self.state          = state
        self.src_star_idx   = src_star_idx
        self.player_faction = player_faction
        self._star          = state.stars[src_star_idx]

        # Build available counts from star fields
        self._avail: dict[str, int] = {
            star_attr: getattr(self._star, star_attr, 0)
            for _, star_attr, _ in _SHIP_ROWS
        }
        self._send: dict[str, int] = {star_attr: 0 for _, star_attr, _ in _SHIP_ROWS}

        self._dest_str   = ""
        self._dest_error = ""
        self._hover_ok   = False
        self._hover_can  = False

        self._btn_ok_rect  = None
        self._btn_can_rect = None
        self._plus_rects:  dict[str, pygame.Rect] = {}
        self._minus_rects: dict[str, pygame.Rect] = {}

        self._held        = None
        self._hold_timer  = 0
        self._hold_accum  = 0
        self._INITIAL_DELAY   = 400
        self._REPEAT_INTERVAL = 60
        self._FAST_INTERVAL   = 20

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_ok  = self._btn_ok_rect  and self._btn_ok_rect.collidepoint(event.pos)
            self._hover_can = self._btn_can_rect and self._btn_can_rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._btn_ok_rect and self._btn_ok_rect.collidepoint(pos):
                self._try_dispatch(); return
            if self._btn_can_rect and self._btn_can_rect.collidepoint(pos):
                self.close(None); return
            for key, r in self._plus_rects.items():
                if r.collidepoint(pos):
                    self._apply_delta(key, +1); self._start_hold(key, +1); return
            for key, r in self._minus_rects.items():
                if r.collidepoint(pos):
                    self._apply_delta(key, -1); self._start_hold(key, -1); return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._try_dispatch()
            elif event.key == pygame.K_BACKSPACE:
                self._dest_str = self._dest_str[:-1]
            elif event.unicode.isdigit() and len(self._dest_str) < 3:
                self._dest_str += event.unicode

    def update(self, dt: int):
        if self._held is None:
            return
        key, delta = self._held
        self._hold_timer += dt
        if self._hold_timer < self._INITIAL_DELAY:
            return
        interval = self._FAST_INTERVAL if self._hold_timer > 1000 else self._REPEAT_INTERVAL
        self._hold_accum += dt
        while self._hold_accum >= interval:
            self._hold_accum -= interval
            self._apply_delta(key, delta)

    def _start_hold(self, key: str, delta: int):
        self._held = (key, delta); self._hold_timer = 0; self._hold_accum = 0

    def _apply_delta(self, key: str, delta: int):
        if delta > 0:
            self._send[key] = min(self._send[key] + 1, self._avail.get(key, 0))
        else:
            self._send[key] = max(0, self._send[key] - 1)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        surf = self._text(
            f"Star {self._star.star_id}  ({self._star.x},{self._star.y})  "
            f"Type:{self._star.planet_type}", TITLE_COL)
        surface.blit(surf, (x, y)); y += 20

        # Destination input
        surface.blit(self._text("Destination star #:"), (x, y))
        input_rect = pygame.Rect(x + 160, y, 60, 18)
        pygame.draw.rect(surface, (40, 40, 60), input_rect)
        pygame.draw.rect(surface, (100, 100, 160), input_rect, 1)
        surface.blit(self._text(self._dest_str + "|"), (input_rect.x + 3, input_rect.y + 1))
        if self._dest_error:
            surface.blit(self._text(self._dest_error, (220, 60, 60)), (x + 230, y))
        y += 26

        # Header
        for hi, h in enumerate(["Ship Type", "Available", "Send", "", ""]):
            surface.blit(self._text(h, (160, 160, 200)), (x + hi * _COL_W, y))
        y += 18

        self._plus_rects.clear()
        self._minus_rects.clear()

        _DIM = (100, 100, 120)
        for label, star_attr, _ in _SHIP_ROWS:
            avail = self._avail.get(star_attr, 0)
            send  = self._send.get(star_attr, 0)
            dim   = (avail <= 0)
            col   = _DIM if dim else TEXT_COL
            for ci, txt in enumerate([label, str(avail), str(send)]):
                surface.blit(self._text(txt, col), (x + ci * _COL_W, y))

            hx = x + 3 * _COL_W
            if not dim:
                minus_r = pygame.Rect(hx, y, 20, 18)
                self._minus_rects[star_attr] = minus_r
                self._draw_button(surface, minus_r, "-")
                plus_r = pygame.Rect(hx + 26, y, 20, 18)
                self._plus_rects[star_attr] = plus_r
                self._draw_button(surface, plus_r, "+")
            y += _ROW_H

        # Reminder when transports are selected
        if self._send.get('transports', 0) > 0:
            surface.blit(self._text("Troops loaded at Dispatch step", (160, 220, 160)),
                         (x, y)); y += 16

        btn_y = self.rect.bottom - _BTN_H - 10
        self._btn_ok_rect  = pygame.Rect(self.rect.x + 20,          btn_y, _BTN_W, _BTN_H)
        self._btn_can_rect = pygame.Rect(self.rect.right - _BTN_W - 20, btn_y, _BTN_W, _BTN_H)
        self._draw_button(surface, self._btn_ok_rect,  "Dispatch", self._hover_ok)
        self._draw_button(surface, self._btn_can_rect, "Cancel",   self._hover_can)

    def _try_dispatch(self):
        if not self._dest_str:
            self._dest_error = "Enter destination"; return
        dest = int(self._dest_str)
        if dest < 0 or dest >= len(self.state.stars):
            self._dest_error = f"No star {dest}"; return
        if dest == self.src_star_idx:
            self._dest_error = "Same star!"; return
        if sum(self._send.values()) == 0:
            self._dest_error = "No ships selected"; return
        self._dest_error = ""

        num_transports = self._send.get('transports', 0)
        troops_loaded  = 0

        if num_transports > 0:
            from second_conflict.ui.dialogs.load_troops_dlg import LoadTroopsDialog
            result = LoadTroopsDialog(self.screen, self._star,
                                      self.player_faction, num_transports).run()
            if result is None:
                return   # player cancelled loading
            troops_loaded = result
            # Deduct loaded troops from friendly planets (greedy: largest first)
            remaining = troops_loaded
            for planet in sorted(self._star.planets, key=lambda p: -p.troops):
                if planet.owner_faction_id != self.player_faction:
                    continue
                if remaining <= 0:
                    break
                take = min(planet.troops, remaining)
                planet.troops -= take
                remaining -= take

        self.close({
            'dest_star':    dest,
            'warships':     self._send.get('warships',     0),
            'transports':   num_transports,
            'troop_ships':  troops_loaded,
            'stealthships': self._send.get('stealthships', 0),
            'missiles':     self._send.get('missiles',     0),
        })