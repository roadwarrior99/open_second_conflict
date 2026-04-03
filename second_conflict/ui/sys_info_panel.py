"""System / planet info panel — translation of SYSLINEWNDPROC + PLTLINEWNDPROC.

Renders as a horizontal strip below the galaxy map.  Two sections:

  LEFT — Star details (SYSLINEWNDPROC):
    Star id, coords, owner, resource, base_prod, current planet type.
    Eight clickable production-type buttons (F P W S T N M D).
    Clicking a button changes that star's planet_type (own stars only).
    In novice mode only W / T / F / N are selectable.

  RIGHT — Garrison breakdown (PLTLINEWNDPROC):
    Faction-by-faction garrison list with ship types and counts.

When no star is selected, a plain status bar shows current player and turn.

Faithfully translated from:
  SYSLINEWNDPROC @ 1010:0000
  PLTLINEWNDPROC @ 1010:10e6
"""
import pygame
from second_conflict.model.constants import (
    PLAYER_COLOURS, EMPIRE_COLOUR, NEUTRAL_COLOUR, EMPIRE_FACTION,
    PlanetType,
)
from second_conflict.model.game_state import GameState

# Production-type button order from PRODLIMITDLG switch (indices 0-7):
#   0=F  1=P  2=W  3=S  4=T  5=N  6=M  7=D
_PROD_TYPES = [
    PlanetType.FACTORY,    # 0
    PlanetType.POPULATION, # 1
    PlanetType.WARSHIP,    # 2
    PlanetType.STEALTH,    # 3
    PlanetType.TRANSPORT,  # 4
    PlanetType.NEUTRAL,    # 5
    PlanetType.MISSILE,    # 6
    PlanetType.DEAD,       # 7
]

_TYPE_LABELS = {
    PlanetType.WARSHIP:    "WarShip",
    PlanetType.MISSILE:    "Missile",
    PlanetType.TRANSPORT:  "TranSport",
    PlanetType.STEALTH:    "Stealth",
    PlanetType.FACTORY:    "Factory",
    PlanetType.POPULATION: "Pop",
    PlanetType.DEAD:       "Dead",
    PlanetType.NEUTRAL:    "Neutral",
}

_TYPE_TOOLTIPS = {
    PlanetType.WARSHIP:    "WarShip — 1 WarShip per credit",
    PlanetType.MISSILE:    "Missile — 1 Missile per 2 credits",
    PlanetType.TRANSPORT:  "TranSport — 1 TranSport per 3 credits",
    PlanetType.STEALTH:    "Stealth — 1 StealthShip per 3 credits; used for scout missions",
    PlanetType.FACTORY:    "Factory — resource grows each turn; also builds WarShips",
    PlanetType.POPULATION: "Population — grows up to 10 pop; each unit = 1 WarShip/turn",
    PlanetType.DEAD:       "Dead — terraforms into WarShip world after 10 turns",
    PlanetType.NEUTRAL:    "Neutral — no production",
}

_TOOLTIP_BG   = (30, 34, 52)
_TOOLTIP_FG   = (220, 220, 240)
_TOOLTIP_BORDER = (90, 100, 160)

# In novice mode only W/T/F/N are valid selections
_NOVICE_ALLOWED = {PlanetType.WARSHIP, PlanetType.TRANSPORT,
                   PlanetType.FACTORY,  PlanetType.NEUTRAL}

_BTN_W  = 30
_BTN_H  = 22
_BTN_GAP = 3

_BG      = (12, 14, 22)
_BORDER  = (50, 55, 80)
_LABEL   = (130, 130, 160)
_VALUE   = (210, 210, 210)
_BTN_NRM = (35, 45, 75)
_BTN_SEL = (60, 120, 60)
_BTN_HOV = (55, 70, 110)
_BTN_DIS = (28, 32, 45)
_BTN_TXT = (200, 200, 220)
_BTN_DIS_TXT = (70, 70, 90)
_FONT_SIZE = 12


class SysInfoPanel:
    def __init__(self, rect: pygame.Rect, state: GameState):
        self.rect  = rect
        self.state = state
        self._font = None
        self._btn_rects: list[pygame.Rect] = []   # 8 production-type button rects
        self._hover_btn: int | None = None
        self._on_type_change = None   # callback(star_idx, new_planet_type)
        self._on_ground_combat = None  # callback(star_idx) → opens GroundCombatDialog
        self._on_edit_star = None     # callback(star_idx) → opens StarEditorDialog
        self._gc_btn_rect: pygame.Rect | None = None
        self._edit_btn_rect: pygame.Rect | None = None
        self._hover_gc   = False
        self._hover_edit = False

    def set_state(self, state: GameState):
        self.state = state

    def set_type_change_callback(self, cb):
        """cb(star_idx: int, new_planet_type: str) → None"""
        self._on_type_change = cb

    def set_ground_combat_callback(self, cb):
        """cb(star_idx: int) → None  — opens Ground Combat dialog for that star."""
        self._on_ground_combat = cb

    def set_edit_star_callback(self, cb):
        """cb(star_idx: int) → None  — opens Star Editor dialog (dev mode)."""
        self._on_edit_star = cb

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event,
                     selected_star_idx: int | None = None):
        if selected_star_idx is None:
            return
        if selected_star_idx >= len(self.state.stars):
            return

        star = self.state.stars[selected_star_idx]

        # Dev-mode Edit Star button — works on any star regardless of ownership
        if self.state.options.dev_mode:
            if event.type == pygame.MOUSEMOTION:
                self._hover_edit = (self._edit_btn_rect is not None and
                                    self._edit_btn_rect.collidepoint(event.pos))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._edit_btn_rect and self._edit_btn_rect.collidepoint(event.pos):
                    if self._on_edit_star:
                        self._on_edit_star(selected_star_idx)
                    return

        current_player = self.state.current_player()
        if current_player is None:
            return
        if star.owner_faction_id != current_player.faction_id:
            return   # can only change own stars

        novice = self.state.options.novice_mode

        if event.type == pygame.MOUSEMOTION:
            self._hover_btn = None
            self._hover_gc  = (self._gc_btn_rect is not None and
                               self._gc_btn_rect.collidepoint(event.pos))
            if self.rect.collidepoint(event.pos):
                for i, r in enumerate(self._btn_rects):
                    if r.collidepoint(event.pos):
                        pt = _PROD_TYPES[i]
                        if novice and pt not in _NOVICE_ALLOWED:
                            break
                        self._hover_btn = i
                        break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._gc_btn_rect and self._gc_btn_rect.collidepoint(event.pos):
                if self._on_ground_combat:
                    self._on_ground_combat(selected_star_idx)
                return
            for i, r in enumerate(self._btn_rects):
                if r.collidepoint(event.pos):
                    pt = _PROD_TYPES[i]
                    if novice and pt not in _NOVICE_ALLOWED:
                        return
                    star.planet_type = pt
                    if self._on_type_change:
                        self._on_type_change(selected_star_idx, pt)
                    return

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, selected_star_idx: int | None = None):
        if self._font is None:
            self._font = pygame.font.SysFont('monospace', _FONT_SIZE)

        surface.fill(_BG, self.rect)
        pygame.draw.line(surface, _BORDER,
                         (self.rect.x, self.rect.y),
                         (self.rect.right, self.rect.y))

        self._btn_rects = []

        if selected_star_idx is None or selected_star_idx >= len(self.state.stars):
            self._draw_status_bar(surface)
            return

        star = self.state.stars[selected_star_idx]
        current_player = self.state.current_player()
        is_own = (current_player is not None and
                  star.owner_faction_id == current_player.faction_id)

        self._draw_star_info(surface, star, is_own)
        self._draw_garrison(surface, star, is_own)

        # Tooltip — drawn last so it renders on top of everything
        if self._hover_btn is not None and self._hover_btn < len(self._btn_rects):
            pt = _PROD_TYPES[self._hover_btn]
            self._draw_tooltip(surface, self._btn_rects[self._hover_btn], pt)

    # ------------------------------------------------------------------

    def _draw_status_bar(self, surface: pygame.Surface):
        x = self.rect.x + 8
        y = self.rect.y + (self.rect.height - _FONT_SIZE) // 2
        player = self.state.current_player()
        if player:
            pidx   = self.state.players.index(player)
            colour = PLAYER_COLOURS[pidx] if pidx < len(PLAYER_COLOURS) else (180, 180, 180)
            pygame.draw.rect(surface, colour, (x, y, 10, 10))
            line = (f"  {player.name}   "
                    f"Turn {self.state.turn}   "
                    f"Stars: {player.empire_size}   "
                    f"Credits: {player.credits}   "
                    f"Fleet: {player.fleet_count}")
            surface.blit(self._font.render(line, True, _VALUE), (x + 14, y))
        else:
            surface.blit(self._font.render("No active player", True, _LABEL), (x, y))

    def _draw_star_info(self, surface: pygame.Surface, star, is_own: bool):
        x = self.rect.x + 8
        y = self.rect.y + 5
        novice = self.state.options.novice_mode

        owner_player = self.state.player_for_faction(star.owner_faction_id)
        owner_name = (
            "Empire" if star.owner_faction_id == EMPIRE_FACTION
            else (owner_player.name[:8] if owner_player else f"?{star.owner_faction_id:02x}")
        )
        type_name = _TYPE_LABELS.get(star.planet_type, star.planet_type)
        info = (f"Star {star.star_id}  ({star.x},{star.y})  "
                f"Res:{star.resource}  "
                f"Owner:{owner_name}  "
                f"Type:{type_name}")
        surface.blit(self._font.render(info, True, _VALUE), (x, y))

        # Production type buttons (only drawn/active for own stars)
        bx = x
        by = y + _FONT_SIZE + 4
        for i, pt in enumerate(_PROD_TYPES):
            disabled = (novice and pt not in _NOVICE_ALLOWED) or not is_own
            selected = (star.planet_type == pt)
            hover    = (self._hover_btn == i and not disabled)

            if disabled:
                bg = _BTN_DIS
            elif selected:
                bg = _BTN_SEL
            elif hover:
                bg = _BTN_HOV
            else:
                bg = _BTN_NRM

            btn_rect = pygame.Rect(bx, by, _BTN_W, _BTN_H)
            self._btn_rects.append(btn_rect)
            pygame.draw.rect(surface, bg, btn_rect, border_radius=3)
            pygame.draw.rect(surface, _BORDER, btn_rect, 1, border_radius=3)

            txt_col = _BTN_DIS_TXT if disabled else _BTN_TXT
            lbl = self._font.render(pt, True, txt_col)
            surface.blit(lbl, (bx + (_BTN_W - lbl.get_width()) // 2,
                                by  + (_BTN_H - lbl.get_height()) // 2))
            bx += _BTN_W + _BTN_GAP

        self._gc_btn_rect = None   # reset; set in _draw_garrison
        if is_own:
            hint = self._font.render("Click to select production type", True, _LABEL)
            surface.blit(hint, (bx + 8, by + (_BTN_H - hint.get_height()) // 2))

    def _draw_garrison(self, surface: pygame.Surface, star, is_own: bool = False):
        """Right-hand section: ship and planet summary (PLTLINEWNDPROC)."""
        rx = self.rect.centerx + 8
        y  = self.rect.y + 5

        # Ship counts
        ships = [
            ("WarShips",    star.warships),
            ("TranSports",  star.transports),
            ("StealthShps", star.stealthships),
            ("Missiles",    star.missiles),
        ]
        has_ships = any(c > 0 for _, c in ships)
        if not has_ships:
            surface.blit(self._font.render("No ships", True, _LABEL), (rx, y))
            y += _FONT_SIZE + 3
        else:
            for name, count in ships:
                if count > 0:
                    line = f"{name:<12} ×{count}"
                    surface.blit(self._font.render(line, True, _VALUE), (rx, y))
                    y += _FONT_SIZE + 3

        # Invasion troops in orbit
        if star.invasion_troops > 0:
            line = f"{'Inv.Troops':<12} ×{star.invasion_troops}"
            surface.blit(self._font.render(line, True, (180, 220, 255)), (rx, y))
            y += _FONT_SIZE + 3

        # Ground Combat button — placed here so it renders after (on top of) ship text
        has_enemy_planets = any(p.owner_faction_id != star.owner_faction_id
                                for p in star.planets)
        needs_gc = is_own and (has_enemy_planets or star.invasion_troops > 0)
        if needs_gc:
            occupied_count = sum(1 for p in star.planets
                                 if p.owner_faction_id != star.owner_faction_id)
            parts = []
            if star.invasion_troops > 0:
                parts.append(f"{star.invasion_troops} troops")
            if occupied_count > 0:
                parts.append(f"{occupied_count} occupied")
            gc_label = "Ground Combat" + (f" ({', '.join(parts)})" if parts else "")
            gc_w = 8 * len(gc_label) + 16
            gc_rect = pygame.Rect(rx, y, gc_w, _BTN_H)
            bg = _BTN_HOV if self._hover_gc else (90, 50, 30)
            pygame.draw.rect(surface, bg, gc_rect, border_radius=3)
            pygame.draw.rect(surface, (160, 100, 60), gc_rect, 1, border_radius=3)
            lbl = self._font.render(gc_label, True, (255, 200, 120))
            surface.blit(lbl, (gc_rect.x + 6, gc_rect.y + (_BTN_H - lbl.get_height()) // 2))
            self._gc_btn_rect = gc_rect

        # Dev-mode Edit Star button — any star, any owner
        self._edit_btn_rect = None
        if self.state.options.dev_mode:
            edit_label = f"[DEV] Edit Star {star.star_id}"
            edit_w = 8 * len(edit_label) + 16
            edit_rect = pygame.Rect(rx, y, edit_w, _BTN_H)
            bg = (80, 60, 20) if self._hover_edit else (55, 40, 15)
            pygame.draw.rect(surface, bg, edit_rect, border_radius=3)
            pygame.draw.rect(surface, (160, 140, 60), edit_rect, 1, border_radius=3)
            lbl = self._font.render(edit_label, True, (255, 230, 100))
            surface.blit(lbl, (edit_rect.x + 6, edit_rect.y + (_BTN_H - lbl.get_height()) // 2))
            self._edit_btn_rect = edit_rect

    def _draw_tooltip(self, surface: pygame.Surface,
                      anchor: pygame.Rect, planet_type: str):
        """Render a small tooltip above the hovered production button."""
        text = _TYPE_TOOLTIPS.get(planet_type, planet_type)
        lbl  = self._font.render(text, True, _TOOLTIP_FG)
        pad  = 5
        tw   = lbl.get_width()  + pad * 2
        th   = lbl.get_height() + pad * 2

        # Position above the button; clamp so it doesn't leave the screen
        tx = anchor.centerx - tw // 2
        ty = anchor.top - th - 3
        sw = surface.get_width()
        tx = max(0, min(tx, sw - tw))
        # If above panel top, flip below the button instead
        if ty < 0:
            ty = anchor.bottom + 3

        tip_rect = pygame.Rect(tx, ty, tw, th)
        pygame.draw.rect(surface, _TOOLTIP_BG, tip_rect, border_radius=3)
        pygame.draw.rect(surface, _TOOLTIP_BORDER, tip_rect, 1, border_radius=3)
        surface.blit(lbl, (tx + pad, ty + pad))