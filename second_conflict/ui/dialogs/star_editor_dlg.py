"""Star Editor dialog — developer mode only.

Allows direct editing of all star fields and per-planet data.
Opened from the system info panel when dev_mode is enabled.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL, TITLE_COL
from second_conflict.model.game_state import GameState

_ROW_H      = 22
_LBL_W      = 150
_VAL_W      = 150
_FIELD_BG   = (30, 35, 55)
_FIELD_SEL  = (50, 65, 110)
_FIELD_FG   = (220, 220, 255)
_INACTIVE_FG = (160, 160, 185)
_SEC_COL    = (140, 160, 200)


class StarEditorDialog(BaseDialog):
    def __init__(self, screen: pygame.Surface, star, state: GameState):
        self._star  = star
        self._state = state
        num_p = len(star.planets)
        # 10 star fields + 2 per planet + section headers/gaps + title + buttons
        content_rows = 10 + num_p * 2 + (1 if num_p else 0)
        height = 36 + content_rows * _ROW_H + 16 + 40
        height = max(height, 260)
        super().__init__(screen, f"Edit Star {star.star_id} [DEV]",
                         width=380, height=height)
        self._active       = None   # index into _fields
        self._buf          = ""
        self._fields       = []
        self._field_rects  = []
        self._btn_ok       = None
        self._btn_cancel   = None
        self._hover_ok     = False
        self._hover_cancel = False
        self._build_fields()

    # ------------------------------------------------------------------

    def _build_fields(self):
        s = self._star
        # Each entry: (label, getter, setter, kind)
        # kind: 'int' | 'hex' | 'str'
        self._fields = [
            ("WarShips",
             lambda: s.warships,
             lambda v: setattr(s, 'warships', v),
             'int'),
            ("TranSports",
             lambda: s.transports,
             lambda v: setattr(s, 'transports', v),
             'int'),
            ("StealthShips",
             lambda: s.stealthships,
             lambda v: setattr(s, 'stealthships', v),
             'int'),
            ("Missiles",
             lambda: s.missiles,
             lambda v: setattr(s, 'missiles', v),
             'int'),
            ("Inv.Troops",
             lambda: s.invasion_troops,
             lambda v: setattr(s, 'invasion_troops', v),
             'int'),
            ("Resource",
             lambda: s.resource,
             lambda v: setattr(s, 'resource', v),
             'int'),
            ("Base Prod",
             lambda: s.base_prod,
             lambda v: setattr(s, 'base_prod', v),
             'int'),
            ("Loyalty",
             lambda: s.loyalty,
             lambda v: setattr(s, 'loyalty', v),
             'int'),
            ("Owner (hex)",
             lambda: f"{s.owner_faction_id:02x}",
             lambda v: setattr(s, 'owner_faction_id', int(v.strip(), 16)),
             'hex'),
            ("Planet Type",
             lambda: s.planet_type,
             lambda v: setattr(s, 'planet_type', v.strip()[:1].upper() if v.strip() else s.planet_type),
             'str'),
        ]
        for i in range(len(s.planets)):
            pi = i
            self._fields.append((
                f"Planet {i} Owner (hex)",
                lambda pi=pi: f"{s.planets[pi].owner_faction_id:02x}",
                lambda v, pi=pi: setattr(s.planets[pi], 'owner_faction_id', int(v.strip(), 16)),
                'hex',
            ))
            self._fields.append((
                f"Planet {i} Troops",
                lambda pi=pi: s.planets[pi].troops,
                lambda v, pi=pi: setattr(s.planets[pi], 'troops', v),
                'int',
            ))

    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            self._hover_ok     = bool(self._btn_ok     and self._btn_ok.collidepoint(event.pos))
            self._hover_cancel = bool(self._btn_cancel and self._btn_cancel.collidepoint(event.pos))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_ok and self._btn_ok.collidepoint(event.pos):
                self._commit_active()
                self.close(True)
                return
            if self._btn_cancel and self._btn_cancel.collidepoint(event.pos):
                self.close(None)
                return
            for i, r in enumerate(self._field_rects):
                if r and r.collidepoint(event.pos):
                    self._commit_active()
                    self._active = i
                    self._buf = str(self._fields[i][1]())
                    return

        if event.type == pygame.KEYDOWN:
            if self._active is not None:
                if event.key == pygame.K_RETURN:
                    self._commit_active()
                    self._active = None
                    self._buf = ""
                elif event.key == pygame.K_TAB:
                    self._commit_active()
                    self._active = (self._active + 1) % len(self._fields)
                    self._buf = str(self._fields[self._active][1]())
                elif event.key == pygame.K_ESCAPE:
                    self._active = None
                    self._buf = ""
                elif event.key == pygame.K_BACKSPACE:
                    self._buf = self._buf[:-1]
                elif event.unicode and event.unicode.isprintable():
                    self._buf += event.unicode
            else:
                if event.key == pygame.K_RETURN:
                    self.close(True)

    def _commit_active(self):
        if self._active is None or self._active >= len(self._fields):
            return
        _, getter, setter, kind = self._fields[self._active]
        try:
            if kind == 'int':
                setter(int(self._buf))
            else:
                setter(self._buf)
        except (ValueError, IndexError):
            pass  # invalid input — keep old value

    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr  = self._content_rect()
        x   = cr.x
        y   = cr.y
        self._field_rects = []

        num_star_fields = 10

        for i, (label, getter, setter, kind) in enumerate(self._fields):
            # Section header before planet fields
            if i == num_star_fields and self._star.planets:
                surface.blit(
                    self._font_body.render("Planets", True, _SEC_COL),
                    (x, y),
                )
                y += _ROW_H

            is_active = (self._active == i)

            lbl_s = self._font_body.render(f"{label}:", True, TEXT_COL)
            surface.blit(lbl_s, (x, y + 3))

            vr = pygame.Rect(x + _LBL_W, y, _VAL_W, _ROW_H - 2)
            pygame.draw.rect(surface, _FIELD_SEL if is_active else _FIELD_BG, vr)
            pygame.draw.rect(surface, (80, 90, 140), vr, 1)

            display = (self._buf + "|") if is_active else str(getter())
            col = _FIELD_FG if is_active else _INACTIVE_FG
            val_s = self._font_body.render(display, True, col)
            surface.blit(val_s, (vr.x + 4, y + 3))

            self._field_rects.append(vr)
            y += _ROW_H

        btn_y = self.rect.bottom - 38
        cx    = self.rect.centerx
        self._btn_ok     = pygame.Rect(cx - 100, btn_y, 80, 26)
        self._btn_cancel = pygame.Rect(cx + 20,  btn_y, 80, 26)
        self._draw_button(surface, self._btn_ok,     "  OK  ",   self._hover_ok)
        self._draw_button(surface, self._btn_cancel, " Cancel ", self._hover_cancel)