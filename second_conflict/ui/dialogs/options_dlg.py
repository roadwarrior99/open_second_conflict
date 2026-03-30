"""Options view dialog — translation of OPTIONVIEWDLG from SCW.EXE.

Read-only display of the current game settings:
  - Turn number and equivalent years
  - Number of players / computer players
  - Fleet movement per turn (sim_steps)
  - Difficulty label
  - Empire Builds on/off
  - Random Events on/off
  - System Defenses on/off  (NOT_allowed / in_use — maps to state_flags)
  - Novice Mode on/off

Years = turns / sim_steps  (the original used turns / 3.0 per the format string
 "Number of turns: %d  (%.2f/years)")
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL, TITLE_COL
from second_conflict.model.game_state import GameState

_DIFFICULTY_NAMES = {0: "Novice", 1: "Easy", 2: "Standard", 3: "Hard", 4: "Expert"}
_ROW_H = 20


class OptionsDialog(BaseDialog):
    def __init__(self, screen: pygame.Surface, state: GameState):
        super().__init__(screen, "Game Options", width=400, height=340)
        self.state     = state
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
        x, y = cr.x, cr.y
        opts = self.state.options

        sim = max(1, opts.sim_steps)
        years = self.state.turn / sim

        rows = [
            ("Turn",           f"{self.state.turn}  ({years:.1f} years)"),
            ("Players",        str(opts.num_players)),
            ("Fleet movement", f"{opts.sim_steps} steps/turn"),
            ("Difficulty",     _DIFFICULTY_NAMES.get(opts.difficulty, str(opts.difficulty))),
            ("Map size",       str(opts.map_param)),
            ("Empire Builds",  "ON" if opts.empire_builds  else "OFF"),
            ("Random Events",  "ON" if opts.random_events  else "OFF"),
            ("Novice Mode",    "ON" if opts.novice_mode    else "OFF"),
        ]
        for label, value in rows:
            lbl_s = self._font_body.render(f"{label}:", True, (150, 150, 200))
            val_s = self._font_body.render(value,       True, TITLE_COL)
            surface.blit(lbl_s, (x, y))
            surface.blit(val_s, (x + 180, y))
            y += _ROW_H

        btn_y = self.rect.bottom - 40
        self._btn_ok = pygame.Rect(self.rect.centerx - 45, btn_y, 90, 28)
        self._draw_button(surface, self._btn_ok, "  OK  ", self._hover_ok)