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

        # Text-box editing: 'dest' or a star_attr string
        self._active_field: str = 'dest'
        self._edit_buf:     str = ''
        self._send_input_rects: dict[str, pygame.Rect] = {}
        self._dest_input_rect:  pygame.Rect | None = None

    # ------------------------------------------------------------------

    def _activate_field(self, field: str):
        """Switch the active text-input field, committing the previous one."""
        self._commit_field()
        self._active_field = field
        if field == 'dest':
            self._edit_buf = self._dest_str
        else:
            self._edit_buf = str(self._send.get(field, 0))

    def _commit_field(self):
        """Apply the current edit buffer to the active field."""
        if self._active_field == 'dest':
            self._dest_str = self._edit_buf
        else:
            try:
                val = int(self._edit_buf)
                self._send[self._active_field] = max(
                    0, min(val, self._avail.get(self._active_field, 0))
                )
            except ValueError:
                pass   # keep old value on bad input

    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_ok  = self._btn_ok_rect  and self._btn_ok_rect.collidepoint(event.pos)
            self._hover_can = self._btn_can_rect and self._btn_can_rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._btn_ok_rect and self._btn_ok_rect.collidepoint(pos):
                self._commit_field(); self._try_dispatch(); return
            if self._btn_can_rect and self._btn_can_rect.collidepoint(pos):
                self.close(None); return
            if self._dest_input_rect and self._dest_input_rect.collidepoint(pos):
                self._activate_field('dest'); return
            for key, r in self._send_input_rects.items():
                if r.collidepoint(pos):
                    self._activate_field(key); return
            for key, r in self._plus_rects.items():
                if r.collidepoint(pos):
                    self._commit_field()
                    self._apply_delta(key, +1); self._start_hold(key, +1)
                    if self._active_field == key:
                        self._edit_buf = str(self._send[key])
                    return
            for key, r in self._minus_rects.items():
                if r.collidepoint(pos):
                    self._commit_field()
                    self._apply_delta(key, -1); self._start_hold(key, -1)
                    if self._active_field == key:
                        self._edit_buf = str(self._send[key])
                    return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._commit_field(); self._try_dispatch()
            elif event.key == pygame.K_TAB:
                # cycle: dest → warships → transports → stealthships → missiles → dest
                order = ['dest'] + [sa for _, sa, _ in _SHIP_ROWS]
                idx = order.index(self._active_field) if self._active_field in order else 0
                self._activate_field(order[(idx + 1) % len(order)])
            elif event.key == pygame.K_BACKSPACE:
                self._edit_buf = self._edit_buf[:-1]
            elif event.unicode.isdigit():
                if self._active_field == 'dest' and len(self._edit_buf) < 3:
                    self._edit_buf += event.unicode
                elif self._active_field != 'dest' and len(self._edit_buf) < 6:
                    self._edit_buf += event.unicode

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
        dest_active = (self._active_field == 'dest')
        dest_display = (self._edit_buf if dest_active else self._dest_str) + "|"
        dest_box = pygame.Rect(x + 160, y, 60, 18)
        self._dest_input_rect = dest_box
        pygame.draw.rect(surface, (60, 60, 90) if dest_active else (40, 40, 60), dest_box)
        pygame.draw.rect(surface, (140, 140, 220) if dest_active else (100, 100, 160), dest_box, 1)
        surface.blit(self._text(dest_display), (dest_box.x + 3, dest_box.y + 1))
        if self._dest_error:
            surface.blit(self._text(self._dest_error, (220, 60, 60)), (x + 230, y))
        y += 26

        # Header
        surface.blit(self._text("Ship Type",  (160, 160, 200)), (x,           y))
        surface.blit(self._text("Available",  (160, 160, 200)), (x + 100,     y))
        surface.blit(self._text("Send",       (160, 160, 200)), (x + 190,     y))
        y += 18

        self._plus_rects.clear()
        self._minus_rects.clear()
        self._send_input_rects.clear()

        _DIM = (100, 100, 120)
        for label, star_attr, _ in _SHIP_ROWS:
            avail      = self._avail.get(star_attr, 0)
            send       = self._send.get(star_attr, 0)
            dim        = (avail <= 0)
            col        = _DIM if dim else TEXT_COL
            is_editing = (self._active_field == star_attr)

            surface.blit(self._text(label, col),      (x,       y))
            surface.blit(self._text(str(avail), col), (x + 100, y))

            # Send quantity box (always shown, editable when active)
            box_w  = 60
            box    = pygame.Rect(x + 190, y, box_w, 18)
            box_bg = (60, 70, 100) if is_editing else (35, 40, 65)
            box_bd = (140, 160, 230) if is_editing else (80, 90, 140)
            pygame.draw.rect(surface, box_bg, box)
            pygame.draw.rect(surface, box_bd, box, 1)
            display = (self._edit_buf + "|") if is_editing else str(send)
            surface.blit(self._text(display, (230, 240, 255) if is_editing else col),
                         (box.x + 4, box.y + 1))
            if not dim:
                self._send_input_rects[star_attr] = box

            # +/- buttons
            if not dim:
                hx = x + 260
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

        # Hint
        surface.blit(self._text("Click a Send box to type amount directly  (Tab to cycle)",
                                (90, 90, 110)), (x, y))

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