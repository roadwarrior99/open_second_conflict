"""Ground Combat dialog.

Opened when a star has occupied enemy planets or invasion troops in orbit.
Lets the player:
  - Bombard: use orbital warships to kill enemy planet troops (one action).
  - Invade:  land invasion_troops on enemy planets.

The dialog stays open so the player can bombard multiple times before
committing to an invasion.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL
from second_conflict.model.star import Star
from second_conflict.model.game_state import GameState
from second_conflict.engine import combat as combat_engine

_ROW_H    = 18
_HDR_COL  = (160, 160, 210)
_OCC_COL  = (220, 140,  40)
_FREE_COL = ( 80, 200,  80)
_ALT_COL  = ( 18,  22,  36)
_COLS     = [0, 70, 170, 270]   # Planet | Status | Troops | Notes


class GroundCombatDialog(BaseDialog):
    """Manual bombardment and planetary invasion for an occupied star."""

    def __init__(self, screen: pygame.Surface, star: Star,
                 player_faction: int, state: GameState):
        self._star           = star
        self._player_faction = player_faction
        self._state          = state
        self._message        = ""
        self._message_col    = TEXT_COL

        n = max(star.num_planets, 1)
        h = 80 + n * _ROW_H + 160
        super().__init__(screen, f"Ground Combat — Star {star.star_id}", width=500, height=h)

        self._hover_bombard = False
        self._hover_invade  = False
        self._hover_close   = False
        self._btn_bombard   = None
        self._btn_invade    = None
        self._btn_close     = None

    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_bombard = self._btn_bombard and self._btn_bombard.collidepoint(event.pos)
            self._hover_invade  = self._btn_invade  and self._btn_invade.collidepoint(event.pos)
            self._hover_close   = self._btn_close   and self._btn_close.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._btn_bombard and self._btn_bombard.collidepoint(pos):
                self._do_bombard()
            elif self._btn_invade and self._btn_invade.collidepoint(pos):
                self._do_invade()
            elif self._btn_close and self._btn_close.collidepoint(pos):
                self.close(None)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_b:
                self._do_bombard()
            elif event.key == pygame.K_i:
                self._do_invade()

    # ------------------------------------------------------------------

    def _do_bombard(self):
        if self._star.warships <= 0:
            self._message     = "No orbital warships to bombard with."
            self._message_col = (200, 80, 80)
            return
        if self._star.troops <= 0:
            self._message     = "No enemy troops to bombard."
            self._message_col = (200, 80, 80)
            return
        result = combat_engine.bombard(self._star, self._player_faction, self._state)
        freed  = result['planets_freed']
        killed = result['troops_killed']
        if freed:
            self._message     = f"Bombardment freed planet(s) {freed}!  {killed} troops killed."
            self._message_col = _FREE_COL
        else:
            self._message     = f"Bombardment killed {killed} troops."
            self._message_col = TEXT_COL

    def _do_invade(self):
        if self._star.invasion_troops <= 0:
            self._message     = "No invasion troops in orbit."
            self._message_col = (200, 80, 80)
            return
        if self._star.troops <= 0:
            self._message     = "No occupied planets to invade."
            self._message_col = (200, 80, 80)
            return
        result = combat_engine.invade(self._star, self._player_faction, self._state)
        taken  = result['planets_taken']
        used   = result['troops_used']
        left   = result['troops_remaining']
        if taken:
            self._message     = f"{taken} planet(s) taken!  Used {used} troops, {left} remain."
            self._message_col = _FREE_COL
        else:
            self._message     = f"Invasion repelled!  Used {used} troops, {left} remain."
            self._message_col = _OCC_COL

    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y

        # Summary line
        surface.blit(self._text(
            f"Orbital warships: {self._star.warships}    "
            f"Invasion troops: {self._star.invasion_troops}",
            TITLE_COL), (x, y)); y += 22

        # Planet table header
        for ci, h in enumerate(["Planet", "Owner", "Troops", "Status"]):
            surface.blit(self._text(h, _HDR_COL), (x + _COLS[ci], y))
        y += _ROW_H

        for pi, planet in enumerate(self._star.planets):
            occupied = (planet.owner_faction_id != self._player_faction)
            row_rect = pygame.Rect(cr.x, y, cr.width, _ROW_H)
            if pi % 2 == 1:
                pygame.draw.rect(surface, _ALT_COL, row_rect)

            owner = self._state.player_for_faction(planet.owner_faction_id)
            if owner:
                oname = owner.name[:8]
            elif planet.owner_faction_id == 0x1A:
                oname = "Empire"
            else:
                oname = f"0x{planet.owner_faction_id:02x}"

            status     = "Occupied" if occupied else "Clear"
            status_col = _OCC_COL   if occupied else _FREE_COL
            troops_str = str(planet.troops) if planet.troops > 0 else "—"

            surface.blit(self._text(f"Planet {pi + 1}"),          (x + _COLS[0], y))
            surface.blit(self._text(oname),                        (x + _COLS[1], y))
            surface.blit(self._text(troops_str, status_col),       (x + _COLS[2], y))
            surface.blit(self._text(status, status_col),           (x + _COLS[3], y))
            y += _ROW_H

        y += 6

        # Last action message
        if self._message:
            surface.blit(self._text(self._message, self._message_col), (x, y))
        y += _ROW_H + 4

        # Buttons
        can_bombard = self._star.warships > 0 and self._star.troops > 0
        can_invade  = self._star.invasion_troops > 0 and self._star.troops > 0

        btn_y = self.rect.bottom - 40
        bx = x
        self._btn_bombard = pygame.Rect(bx, btn_y, 110, 28)
        self._btn_invade  = pygame.Rect(bx + 120, btn_y, 100, 28)
        self._btn_close   = pygame.Rect(self.rect.right - 100, btn_y, 80, 28)

        self._draw_button(surface, self._btn_bombard,
                          "[B]ombard" if can_bombard else "Bombard",
                          self._hover_bombard and can_bombard)
        self._draw_button(surface, self._btn_invade,
                          "[I]nvade" if can_invade else "Invade",
                          self._hover_invade and can_invade)
        self._draw_button(surface, self._btn_close, "Close", self._hover_close)

        # Hint
        hint = "B=Bombard (warships)   I=Invade (troops in orbit)"
        surface.blit(self._text(hint, (100, 100, 130)),
                     (x, self.rect.bottom - 64))