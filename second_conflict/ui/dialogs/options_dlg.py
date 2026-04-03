"""Options dialog — translation of OPTIONVIEWDLG from SCW.EXE.

Displays current game settings; toggleable options can be changed in-game.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL, TITLE_COL
from second_conflict.model.game_state import GameState

_DIFFICULTY_NAMES = {0: "Novice", 1: "Easy", 2: "Standard", 3: "Hard", 4: "Expert"}
_ROW_H = 22
_HDR_COL = (150, 150, 200)


class OptionsDialog(BaseDialog):
    def __init__(self, screen: pygame.Surface, state: GameState):
        super().__init__(screen, "Game Options", width=400, height=392)
        self.state     = state
        self._hover_ok = False
        self._btn_ok   = None
        # rects for clickable toggles
        self._toggle_rects: dict[str, pygame.Rect] = {}

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_ok = self._btn_ok and self._btn_ok.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_ok and self._btn_ok.collidepoint(event.pos):
                self.close(None)
                return
            for key, rect in self._toggle_rects.items():
                if rect.collidepoint(event.pos):
                    self._toggle(key)
                    return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.close(None)

    def _toggle(self, key: str):
        opts = self.state.options
        if key == 'random_events':
            opts.random_events  = not opts.random_events
        elif key == 'empire_builds':
            opts.empire_builds  = not opts.empire_builds
        elif key == 'novice_mode':
            opts.novice_mode    = not opts.novice_mode
        elif key == 'show_events_log':
            opts.show_events_log = not opts.show_events_log
        elif key == 'dev_mode':
            opts.dev_mode = not opts.dev_mode

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y
        opts = self.state.options
        self._toggle_rects.clear()

        sim   = max(1, opts.sim_steps)
        years = self.state.turn / sim

        # ---- read-only info rows ----
        info_rows = [
            ("Turn",           f"{self.state.turn}  ({years:.1f} years)"),
            ("Players",        str(opts.num_players)),
            ("Fleet movement", f"{opts.sim_steps} steps/turn"),
            ("Difficulty",     _DIFFICULTY_NAMES.get(opts.difficulty, str(opts.difficulty))),
            ("Map size",       str(opts.map_param)),
        ]
        for label, value in info_rows:
            lbl_s = self._font_body.render(f"{label}:", True, _HDR_COL)
            val_s = self._font_body.render(value,        True, TITLE_COL)
            surface.blit(lbl_s, (x, y))
            surface.blit(val_s, (x + 180, y))
            y += _ROW_H

        y += 6
        surface.blit(self._font_body.render("Toggles", True, _HDR_COL), (x, y))
        y += _ROW_H

        # ---- toggleable options ----
        toggles = [
            ('random_events',  "Random Events",   opts.random_events),
            ('empire_builds',  "Empire Builds",   opts.empire_builds),
            ('novice_mode',    "Novice Mode",      opts.novice_mode),
            ('show_events_log',"Show Event Log",   opts.show_events_log),
            ('dev_mode',       "Developer Mode",   opts.dev_mode),
        ]
        for key, label, val in toggles:
            box = pygame.Rect(x, y, 20, 18)
            pygame.draw.rect(surface, (40, 40, 65), box)
            pygame.draw.rect(surface, (100, 100, 160), box, 1)
            if val:
                surface.blit(self._font_body.render("X", True, (120, 210, 120)),
                             (box.x + 4, box.y + 1))
            col = TITLE_COL if val else (120, 120, 140)
            surface.blit(self._font_body.render(f"  {label}", True, col),
                         (x + 26, y))
            # extend clickable area across the label
            hit = pygame.Rect(x, y, 220, 20)
            self._toggle_rects[key] = hit
            y += _ROW_H

        btn_y = self.rect.bottom - 40
        self._btn_ok = pygame.Rect(self.rect.centerx - 45, btn_y, 90, 28)
        self._draw_button(surface, self._btn_ok, "  OK  ", self._hover_ok)