"""New Game dialog — translation of NEWGAMEDLG1/2/3 from SCW.EXE.

Three-step wizard:
  1. Number of players (2-10), map size, difficulty
  2. Player names
  3. Options (random events, novice mode, empire builds)

Returns a GameOptions + list of player names, or None if cancelled.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL, TITLE_COL
from second_conflict.model.game_state import GameOptions

_BTN_W = 100
_BTN_H = 30
_ROW_H = 28


class NewGameDialog(BaseDialog):
    """Wizard-style new game setup."""

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen, "New Game", width=440, height=360)
        self._page        = 0     # 0=settings, 1=names, 2=options
        self._num_players = 4
        self._difficulty  = 1     # 0-3
        self._map_param   = 150   # 150 or 200
        self._random_events = True
        self._novice_mode   = False
        self._empire_builds = True
        self._names         = [f"Player {i+1}" for i in range(10)]
        self._is_ai         = [False] * 10   # per-player AI flag
        self._editing_name: int | None = None
        self._hover_next    = False
        self._hover_back    = False
        self._hover_cancel  = False
        self._btn_next:   pygame.Rect | None = None
        self._btn_back:   pygame.Rect | None = None
        self._btn_cancel: pygame.Rect | None = None
        # +/- button rects for page 0 numeric fields
        self._inc_rects: dict[str, pygame.Rect] = {}
        self._dec_rects: dict[str, pygame.Rect] = {}
        self._ai_rects:  dict[int, pygame.Rect] = {}

    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_next   = self._btn_next   and self._btn_next.collidepoint(event.pos)
            self._hover_back   = self._btn_back   and self._btn_back.collidepoint(event.pos)
            self._hover_cancel = self._btn_cancel and self._btn_cancel.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._btn_cancel and self._btn_cancel.collidepoint(pos):
                self.close(None)
                return
            if self._btn_next and self._btn_next.collidepoint(pos):
                self._advance()
                return
            if self._btn_back and self._btn_back.collidepoint(pos):
                self._page = max(0, self._page - 1)
                return

            # Page-specific clicks
            if self._page == 0:
                self._handle_page0_click(pos)
            elif self._page == 1:
                self._handle_page1_click(pos)
            elif self._page == 2:
                self._handle_page2_click(pos)

        if event.type == pygame.KEYDOWN and self._page == 1 and self._editing_name is not None:
            i = self._editing_name
            if event.key == pygame.K_RETURN:
                self._editing_name = None
            elif event.key == pygame.K_BACKSPACE:
                self._names[i] = self._names[i][:-1]
            elif event.unicode and len(self._names[i]) < 9:
                self._names[i] += event.unicode

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()

        if self._page == 0:
            self._draw_page0(surface, cr)
        elif self._page == 1:
            self._draw_page1(surface, cr)
        elif self._page == 2:
            self._draw_page2(surface, cr)

        # Navigation buttons
        btn_y = self.rect.bottom - _BTN_H - 12
        self._btn_cancel = pygame.Rect(self.rect.x + 10, btn_y, _BTN_W, _BTN_H)
        self._draw_button(surface, self._btn_cancel, "Cancel", self._hover_cancel)

        if self._page > 0:
            self._btn_back = pygame.Rect(
                self.rect.centerx - _BTN_W - 5, btn_y, _BTN_W, _BTN_H
            )
            self._draw_button(surface, self._btn_back, "< Back", self._hover_back)
        else:
            self._btn_back = None

        next_label = "Finish" if self._page == 2 else "Next >"
        self._btn_next = pygame.Rect(
            self.rect.centerx + 5, btn_y, _BTN_W, _BTN_H
        )
        self._draw_button(surface, self._btn_next, next_label, self._hover_next)

    # ------------------------------------------------------------------
    # Page renderers
    # ------------------------------------------------------------------

    def _draw_page0(self, surface, cr):
        x, y = cr.x, cr.y
        surface.blit(self._title_text("Game Settings"), (x, y)); y += 24

        self._inc_rects.clear()
        self._dec_rects.clear()

        rows = [
            ("Players",    "num_players", self._num_players,  2,  10),
            ("Difficulty", "difficulty",  self._difficulty,   0,   3),
            ("Map size",   "map_param",   self._map_param,  150, 200),
        ]
        for label, key, val, lo, hi in rows:
            surface.blit(self._text(f"{label}:"), (x, y))
            val_s = self._text(str(val), TITLE_COL)
            surface.blit(val_s, (x + 180, y))
            dec_r = pygame.Rect(x + 220, y, 22, 18)
            inc_r = pygame.Rect(x + 248, y, 22, 18)
            self._dec_rects[key] = dec_r
            self._inc_rects[key] = inc_r
            self._draw_button(surface, dec_r, "-")
            self._draw_button(surface, inc_r, "+")
            y += _ROW_H

        # Map param note
        note = self._text("(150=medium, 200=large)", (120, 120, 140))
        surface.blit(note, (x, y)); y += 20

    def _draw_page1(self, surface, cr):
        x, y = cr.x, cr.y
        surface.blit(self._title_text("Player Names"), (x, y)); y += 16

        # Column headers
        surface.blit(self._text("Name", (160, 160, 210)), (x + 40, y))
        surface.blit(self._text("AI?",  (160, 160, 210)), (x + 210, y))
        y += 18

        self._ai_rects.clear()
        for i in range(self._num_players):
            lbl = self._text(f"P{i+1}:")
            surface.blit(lbl, (x, y))
            name = self._names[i]
            editing = (self._editing_name == i)
            box_col = (60, 60, 90) if editing else (35, 35, 55)
            box = pygame.Rect(x + 40, y, 160, 18)
            pygame.draw.rect(surface, box_col, box)
            pygame.draw.rect(surface, (100, 100, 160), box, 1)
            n_surf = self._text((name + "|") if editing else name)
            surface.blit(n_surf, (box.x + 3, box.y + 1))
            self._dec_rects[f'name_{i}'] = box

            # AI toggle checkbox
            ai_box = pygame.Rect(x + 210, y, 20, 18)
            check_col = (50, 50, 80)
            pygame.draw.rect(surface, check_col, ai_box)
            pygame.draw.rect(surface, (100, 100, 160), ai_box, 1)
            if self._is_ai[i]:
                surface.blit(self._text("X", (120, 200, 120)), (ai_box.x + 4, ai_box.y + 1))
            self._ai_rects[i] = ai_box

            # "AI" label when toggled
            if self._is_ai[i]:
                surface.blit(self._text("(AI)", (120, 200, 120)), (x + 236, y))

            y += _ROW_H

    def _draw_page2(self, surface, cr):
        x, y = cr.x, cr.y
        surface.blit(self._title_text("Options"), (x, y)); y += 24

        toggles = [
            ("Random Events",  "random_events",  self._random_events),
            ("Novice Mode",    "novice_mode",     self._novice_mode),
            ("Empire Builds",  "empire_builds",   self._empire_builds),
        ]
        for label, key, val in toggles:
            check = "[X]" if val else "[ ]"
            toggle_surf = self._text(f"{check}  {label}")
            box = pygame.Rect(x, y, 220, 18)
            surface.blit(toggle_surf, (x, y))
            self._dec_rects[f'toggle_{key}'] = box
            y += _ROW_H

    # ------------------------------------------------------------------
    # Click handlers
    # ------------------------------------------------------------------

    def _handle_page0_click(self, pos):
        step_map = {
            'num_players': (2, 10, 1, '_num_players'),
            'difficulty':  (0,  3, 1, '_difficulty'),
            'map_param':   (150, 200, 50, '_map_param'),
        }
        for key, (lo, hi, step, attr) in step_map.items():
            if key in self._inc_rects and self._inc_rects[key].collidepoint(pos):
                setattr(self, attr, min(hi, getattr(self, attr) + step))
            if key in self._dec_rects and self._dec_rects[key].collidepoint(pos):
                setattr(self, attr, max(lo, getattr(self, attr) - step))

    def _handle_page1_click(self, pos):
        for i in range(self._num_players):
            if i in self._ai_rects and self._ai_rects[i].collidepoint(pos):
                self._is_ai[i] = not self._is_ai[i]
                self._editing_name = None
                return
            key = f'name_{i}'
            if key in self._dec_rects and self._dec_rects[key].collidepoint(pos):
                self._editing_name = i
                return
        self._editing_name = None

    def _handle_page2_click(self, pos):
        toggle_map = {
            'toggle_random_events': '_random_events',
            'toggle_novice_mode':   '_novice_mode',
            'toggle_empire_builds': '_empire_builds',
        }
        for key, attr in toggle_map.items():
            if key in self._dec_rects and self._dec_rects[key].collidepoint(pos):
                setattr(self, attr, not getattr(self, attr))

    # ------------------------------------------------------------------

    def _advance(self):
        if self._page < 2:
            self._page += 1
        else:
            # Build result
            from second_conflict.model.game_state import GameOptions
            opts = GameOptions(
                num_players   = self._num_players,
                difficulty    = self._difficulty,
                map_param     = self._map_param,
                random_events = self._random_events,
                novice_mode   = self._novice_mode,
                empire_builds = self._empire_builds,
            )
            self.close({
                'options': opts,
                'names':   self._names[:self._num_players],
                'is_ai':   self._is_ai[:self._num_players],
            })