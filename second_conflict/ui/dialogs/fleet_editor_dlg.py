"""Dev-mode fleet editor dialog.

Lets a developer directly edit any field of a FleetInTransit record.
Accessible from the Fleet View dialog when dev_mode is enabled.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL, TITLE_COL
from second_conflict.model.fleet import FleetInTransit
from second_conflict.model.game_state import GameState

_ROW_H    = 22
_LABEL_W  = 130
_VAL_W    = 120
_HDR_COL  = (150, 150, 200)
_SEL_COL  = (40, 80, 40)
_AMB_COL  = (200, 160,  60)   # amber — dev mode accent


class FleetEditorDialog(BaseDialog):
    def __init__(self, screen: pygame.Surface, fleet: FleetInTransit,
                 state: GameState):
        super().__init__(screen, f"Edit Fleet (slot {fleet.slot})",
                         width=400, height=380)
        self._fleet = fleet
        self._state = state

        self._fields = self._build_fields()
        self._active: int | None = None   # index of currently edited field
        self._buf:    str        = ''

        self._btn_ok  = None
        self._btn_can = None
        self._hover_ok  = False
        self._hover_can = False

    # ------------------------------------------------------------------

    def _build_fields(self):
        """Return list of (label, getter, setter, kind) tuples.

        kind is 'int' for numeric fields or 'char' for single-character fields.
        """
        f = self._fleet
        return [
            ("dest_star",      lambda: f.dest_star,
             lambda v: setattr(f, 'dest_star', v),      'int'),
            ("src_star",       lambda: f.src_star,
             lambda v: setattr(f, 'src_star', v),       'int'),
            ("turns_remaining",lambda: f.turns_remaining,
             lambda v: setattr(f, 'turns_remaining', v),'int'),
            ("warships",       lambda: f.warships,
             lambda v: setattr(f, 'warships', v),       'int'),
            ("transports",     lambda: f.transports,
             lambda v: setattr(f, 'transports', v),     'int'),
            ("troop_ships",    lambda: f.troop_ships,
             lambda v: setattr(f, 'troop_ships', v),    'int'),
            ("stealthships",   lambda: f.stealthships,
             lambda v: setattr(f, 'stealthships', v),   'int'),
            ("missiles",       lambda: f.missiles,
             lambda v: setattr(f, 'missiles', v),       'int'),
            ("scouts",         lambda: f.scouts,
             lambda v: setattr(f, 'scouts', v),         'int'),
            ("fleet_type_char",lambda: f.fleet_type_char,
             lambda v: setattr(f, 'fleet_type_char', v),'char'),
        ]

    # ------------------------------------------------------------------

    def _activate(self, idx: int):
        self._commit()
        self._active = idx
        self._buf = str(self._fields[idx][1]())

    def _commit(self):
        if self._active is None:
            return
        _, getter, setter, kind = self._fields[self._active]
        try:
            if kind == 'char':
                if self._buf:
                    setter(self._buf[0].upper())
            else:
                setter(int(self._buf))
        except (ValueError, IndexError):
            pass
        self._active = None
        self._buf    = ''

    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            self._hover_ok  = bool(self._btn_ok  and self._btn_ok.collidepoint(event.pos))
            self._hover_can = bool(self._btn_can and self._btn_can.collidepoint(event.pos))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._btn_ok  and self._btn_ok.collidepoint(pos):
                self._commit(); self.close(True); return
            if self._btn_can and self._btn_can.collidepoint(pos):
                self.close(None); return
            cr = self._content_rect()
            for i, _ in enumerate(self._fields):
                row_y = cr.y + _ROW_H + i * _ROW_H   # +_ROW_H to skip the header row
                val_rect = pygame.Rect(cr.x + _LABEL_W, row_y, _VAL_W, _ROW_H - 2)
                if val_rect.collidepoint(pos):
                    self._activate(i)
                    return
            # Click outside any field — commit
            self._commit()

        if event.type == pygame.KEYDOWN:
            if self._active is not None:
                if event.key == pygame.K_RETURN:
                    self._commit()
                elif event.key == pygame.K_TAB:
                    self._commit()
                    self._activate((self._active + 1) % len(self._fields))
                elif event.key == pygame.K_ESCAPE:
                    self._active = None; self._buf = ''
                elif event.key == pygame.K_BACKSPACE:
                    self._buf = self._buf[:-1]
                else:
                    ch = event.unicode
                    if ch and (ch.isdigit() or ch == '-' or
                               (self._fields[self._active][3] == 'char' and ch.isalpha())):
                        self._buf += ch
            else:
                if event.key == pygame.K_RETURN:
                    self._commit(); self.close(True)

    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        # Column headers
        surface.blit(self._font_body.render("Field",  True, _HDR_COL), (x,             y))
        surface.blit(self._font_body.render("Value",  True, _HDR_COL), (x + _LABEL_W,  y))
        pygame.draw.line(surface, (60, 60, 90),
                         (x, y + _ROW_H - 4), (x + _LABEL_W + _VAL_W, y + _ROW_H - 4))
        y += _ROW_H

        for i, (label, getter, _, _kind) in enumerate(self._fields):
            row_y    = y + i * _ROW_H
            val_rect = pygame.Rect(x + _LABEL_W, row_y, _VAL_W, _ROW_H - 2)

            is_active = (i == self._active)
            if is_active:
                pygame.draw.rect(surface, _SEL_COL, val_rect)

            surface.blit(self._font_body.render(label, True, _AMB_COL), (x, row_y + 2))

            display = (self._buf + '|') if is_active else str(getter())
            col     = TEXT_COL if not is_active else (180, 255, 180)
            surface.blit(self._font_body.render(display, True, col),
                         (x + _LABEL_W + 4, row_y + 2))

        # Buttons
        btn_y = self.rect.bottom - 38
        self._btn_ok  = pygame.Rect(self.rect.centerx - 100, btn_y, 80, 28)
        self._btn_can = pygame.Rect(self.rect.centerx + 20,  btn_y, 80, 28)
        self._draw_button(surface, self._btn_ok,  "Apply", self._hover_ok)
        self._draw_button(surface, self._btn_can, "Cancel", self._hover_can)