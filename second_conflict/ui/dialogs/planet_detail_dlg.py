"""Planet Detail dialog.

Shows the individual planets within a single star system — their index,
troop count, and occupation status.  Opened from the Planet Administration
overview when a star row is selected.
"""
import pygame
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL
from second_conflict.model.star import Star
from second_conflict.model.game_state import GameState

_ROW_H   = 22
_HDR_COL = (160, 160, 210)
_ALT_COL = (18, 22, 36)
_OCC_COL = (220, 140,  40)   # orange — occupied
_FREE_COL = (80, 200,  80)   # green  — clear

_COLS = [0, 80, 200, 290]   # Planet# | Status | Troops | Action
_GARN_COL = (80, 160, 80)    # garrison button colour
_GARN_HOV = (110, 200, 110)


class PlanetDetailDialog(BaseDialog):
    """Per-system planet list with occupation detail."""

    def __init__(self, screen: pygame.Surface, star: Star, state: GameState):
        self.star  = star
        self.state = state
        n = star.num_planets
        h = 80 + n * _ROW_H + 130
        super().__init__(screen, f"Star {star.star_id} — Planets", width=500, height=h)
        self._btn_close_rect  = None
        self._hover_close     = False
        # Garrison controls
        player = state.current_player()
        self._player_faction  = player.faction_id if player else -1
        self._garrison_amount = max(1, star.invasion_troops)
        self._inc_garn_rect: pygame.Rect | None = None
        self._dec_garn_rect: pygame.Rect | None = None
        self._garrison_rects: dict[int, pygame.Rect] = {}
        self._hover_garrison: int | None = None
        self._garrison_msg    = ""

    # ------------------------------------------------------------------

    def _do_garrison(self, planet_idx: int):
        planet = self.star.planets[planet_idx]
        if planet.owner_faction_id != self._player_faction:
            self._garrison_msg = "Can only garrison own planets."
            return
        available = self.star.invasion_troops
        if available <= 0:
            self._garrison_msg = "No troops in orbit."
            return
        amount = min(self._garrison_amount, available)
        planet.troops          += amount
        self.star.invasion_troops -= amount
        # Keep garrison_amount valid
        self._garrison_amount = max(1, min(self._garrison_amount, self.star.invasion_troops)) \
            if self.star.invasion_troops > 0 else 1
        self._garrison_msg = (f"Garrisoned {amount} troops on Planet {planet_idx + 1}. "
                              f"{self.star.invasion_troops} remain in orbit.")

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            self._hover_close = bool(self._btn_close_rect and
                                     self._btn_close_rect.collidepoint(event.pos))
            self._hover_garrison = None
            for pi, r in self._garrison_rects.items():
                if r.collidepoint(event.pos):
                    self._hover_garrison = pi
                    break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._btn_close_rect and self._btn_close_rect.collidepoint(pos):
                self.close(None)
                return
            if self._inc_garn_rect and self._inc_garn_rect.collidepoint(pos):
                self._garrison_amount = min(self._garrison_amount + 1,
                                            max(1, self.star.invasion_troops))
                return
            if self._dec_garn_rect and self._dec_garn_rect.collidepoint(pos):
                self._garrison_amount = max(1, self._garrison_amount - 1)
                return
            for pi, r in self._garrison_rects.items():
                if r.collidepoint(pos):
                    self._do_garrison(pi)
                    return

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr = self._content_rect()
        x, y = cr.x, cr.y
        star = self.star

        # System summary
        owner_name = star.owner_name(self.state.players)
        total_troops = star.troops
        surface.blit(self._text(
            f"Owner: {owner_name}   Type: {star.planet_type}   "
            f"Resource: {star.resource}", TITLE_COL), (x, y))
        y += _ROW_H

        if total_troops > 0:
            occ_name = next(
                (p.name for p in self.state.players
                 if p.faction_id == star.troop_faction),
                f"0x{star.troop_faction:02x}"
            )
            surface.blit(self._text(
                f"OCCUPIED by {occ_name} — {total_troops} troops total",
                _OCC_COL), (x, y))
        else:
            surface.blit(self._text("All planets clear.", _FREE_COL), (x, y))
        y += _ROW_H + 4

        # Column headers
        for ci, hdr in enumerate(["Planet", "Status", "Troops", "Action"]):
            surface.blit(self._text(hdr, _HDR_COL), (x + _COLS[ci], y))
        y += _ROW_H

        self._garrison_rects.clear()
        self._inc_garn_rect = None
        self._dec_garn_rect = None

        n = star.num_planets
        for pi in range(n):
            planet   = star.planets[pi] if pi < len(star.planets) else None
            troops   = planet.troops if planet is not None else 0
            is_own   = (planet is not None and
                        planet.owner_faction_id == self._player_faction)
            occupied = (planet is not None and
                        planet.owner_faction_id != self._player_faction and
                        troops > 0)
            enemy_held = (planet is not None and
                          planet.owner_faction_id != self._player_faction)

            row_rect = pygame.Rect(cr.x, y, cr.width, _ROW_H)
            if pi % 2 == 1:
                pygame.draw.rect(surface, _ALT_COL, row_rect)

            if is_own:
                status     = "Own"
                status_col = _FREE_COL
            elif enemy_held:
                status     = "Occupied"
                status_col = _OCC_COL
            else:
                status     = "Clear"
                status_col = _FREE_COL

            troops_str = str(troops) if troops > 0 else "—"

            surface.blit(self._text(f"Planet {pi + 1}"),       (x + _COLS[0], y))
            surface.blit(self._text(status, status_col),        (x + _COLS[1], y))
            surface.blit(self._text(troops_str, status_col),    (x + _COLS[2], y))

            # Action column
            ax = x + _COLS[3]
            if is_own and star.invasion_troops > 0:
                can_garrison = True
                hover = (self._hover_garrison == pi)
                bg    = _GARN_HOV if hover else _GARN_COL
                btn   = pygame.Rect(ax, y, 90, _ROW_H - 2)
                pygame.draw.rect(surface, bg, btn, border_radius=2)
                surface.blit(self._text("Garrison", (0, 0, 0)), (ax + 6, y + 1))
                self._garrison_rects[pi] = btn
            elif enemy_held:
                surface.blit(self._text("Bombard/Invade", (160, 160, 160)), (ax, y))

            y += _ROW_H

        y += 6

        # Garrison controls — shown when troops are in orbit
        if star.invasion_troops > 0:
            surface.blit(self._text(
                f"Troops in orbit: {star.invasion_troops}", (160, 200, 255)), (x, y))
            ax = x + 200
            surface.blit(self._text("Garrison amount:", TEXT_COL), (ax, y))
            self._dec_garn_rect = pygame.Rect(ax + 130, y, 20, 17)
            self._inc_garn_rect = pygame.Rect(ax + 160, y, 20, 17)
            pygame.draw.rect(surface, (50, 60, 100), self._dec_garn_rect, border_radius=2)
            pygame.draw.rect(surface, (50, 60, 100), self._inc_garn_rect, border_radius=2)
            surface.blit(self._text("−"), (self._dec_garn_rect.x + 4, y))
            surface.blit(self._text("+"), (self._inc_garn_rect.x + 4, y))
            amt = max(1, min(self._garrison_amount, star.invasion_troops))
            surface.blit(self._text(str(amt), TITLE_COL),
                         (ax + 145 - self._font_body.size(str(amt))[0] // 2, y))
            y += _ROW_H
        else:
            self._inc_garn_rect = None
            self._dec_garn_rect = None
            y += _ROW_H

        # Garrison feedback message
        if self._garrison_msg:
            surface.blit(self._text(self._garrison_msg, (140, 210, 140)), (x, y))
        y += _ROW_H

        btn_y = self.rect.bottom - 38
        self._btn_close_rect = pygame.Rect(self.rect.centerx - 40, btn_y, 80, 26)
        self._draw_button(surface, self._btn_close_rect, "Close", self._hover_close)