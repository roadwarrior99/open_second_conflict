"""Production limit dialog — translation of PRODLIMITDLG from SCW.EXE.

Shows each star owned by the current player, its planet type, and how many
ships it produces per turn given the current difficulty setting.

The original PRODLIMITDLG used a listbox with entries formatted as:
  "Star %d  [type_name]  [production]"

It is read-only (the player cannot change planet types here; that is the
scenario editor). Dismiss with OK.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TEXT_COL, TITLE_COL
from second_conflict.model.constants import PlanetType, ShipType, EMPIRE_FACTION
from second_conflict.model.game_state import GameState

_ROW_H = 18

_TYPE_LABELS = {
    PlanetType.WARSHIP:    "WarShip",
    PlanetType.MISSILE:    "Missile",
    PlanetType.TRANSPORT:  "TranSport",
    PlanetType.SCOUT:      "Scout",
    PlanetType.FACTORY:    "Factory",
    PlanetType.POPULATION: "Population",
    PlanetType.DEAD:       "Dead",
    PlanetType.NEUTRAL:    "Neutral",
}

_PROD_COST = {
    PlanetType.WARSHIP:    1,
    PlanetType.MISSILE:    2,
    PlanetType.TRANSPORT:  3,
    PlanetType.SCOUT:      3,
}


def _production_per_turn(star, difficulty: int) -> int:
    """Credits produced this turn."""
    return max(0, (4 - difficulty) * star.resource + star.base_prod)


def _ships_per_turn(star, difficulty: int) -> int:
    """Ships produced per turn given planet type and difficulty."""
    pt = star.planet_type
    credits = _production_per_turn(star, difficulty)
    cost = _PROD_COST.get(pt, 0)
    if cost == 0:
        return 0
    return credits // cost


class ProdLimitDialog(BaseDialog):
    def __init__(self, screen: pygame.Surface, state: GameState,
                 player_faction: int):
        my_stars = [s for s in state.stars if s.owner_faction_id == player_faction]
        height = 80 + _ROW_H * (len(my_stars) + 2) + 50
        super().__init__(screen, "Production Summary", width=460, height=max(height, 200))
        self.state          = state
        self.player_faction = player_faction
        self._my_stars      = my_stars
        self._scroll        = 0
        self._hover_ok      = False
        self._btn_ok        = None

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_ok = self._btn_ok and self._btn_ok.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self._btn_ok and self._btn_ok.collidepoint(event.pos):
                self.close(None)
            elif event.button == 4:
                self._scroll = max(0, self._scroll - 1)
            elif event.button == 5:
                max_scroll = max(0, len(self._my_stars) - 15)
                self._scroll = min(self._scroll + 1, max_scroll)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.close(None)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y
        diff = self.state.options.difficulty

        # Column headers
        hdrs = [("Star",  0), ("Type",  50), ("Res", 140), ("Credits", 170), ("Ships/Turn", 230)]
        for hdr, cx in hdrs:
            surface.blit(self._font_body.render(hdr, True, (150, 150, 200)), (x + cx, y))
        y += _ROW_H
        pygame.draw.line(surface, (60, 60, 90), (x, y), (x + cr.width, y))
        y += 2

        if not self._my_stars:
            surface.blit(self._text("No stars owned."), (x, y))
        else:
            visible = min(15, (cr.height - _ROW_H * 2 - 50) // _ROW_H)
            for star in self._my_stars[self._scroll: self._scroll + visible]:
                type_lbl = _TYPE_LABELS.get(star.planet_type, star.planet_type)
                credits  = _production_per_turn(star, diff)
                ships    = _ships_per_turn(star, diff)
                ships_str = str(ships) if ships > 0 else "—"

                cols = [
                    (f"{star.star_id:2d}", 0),
                    (type_lbl[:10], 50),
                    (str(star.resource), 140),
                    (str(credits), 170),
                    (ships_str, 230),
                ]
                for text, cx in cols:
                    surface.blit(self._text(text), (x + cx, y))
                y += _ROW_H

        # Total ships this turn
        total_credits = sum(_production_per_turn(s, diff) for s in self._my_stars)
        total_ships   = sum(_ships_per_turn(s, diff)     for s in self._my_stars)
        pygame.draw.line(surface, (60, 60, 90), (x, y), (x + cr.width, y))
        y += 4
        surface.blit(self._text(f"Total credits: {total_credits}   Total ships: {total_ships}",
                                 TITLE_COL), (x, y))

        # OK button
        btn_y = self.rect.bottom - 38
        self._btn_ok = pygame.Rect(self.rect.centerx - 45, btn_y, 90, 28)
        self._draw_button(surface, self._btn_ok, "  OK  ", self._hover_ok)