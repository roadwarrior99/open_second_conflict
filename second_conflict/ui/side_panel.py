"""Side panel — player stats strip and End Turn button.

Renders on the right side of the screen:
  - Current player name + colour swatch
  - Turn number
  - Stats: empire_size, production, fleet_count, credits
  - Selected star info (if any)
  - "End Turn" button
"""
import pygame
from second_conflict.model.constants import PLAYER_COLOURS, EMPIRE_COLOUR, EMPIRE_FACTION
from second_conflict.model.game_state import GameState

PANEL_BG   = (20, 20, 30)
TEXT_COL   = (210, 210, 210)
LABEL_COL  = (140, 140, 160)
BTN_NORMAL = (50, 90, 160)
BTN_HOVER  = (80, 130, 210)
BTN_TEXT   = (255, 255, 255)
DIVIDER    = (60, 60, 80)

_FONT_TITLE_SIZE = 16
_FONT_BODY_SIZE  = 13
_BTN_H           = 36
_BTN_MARGIN      = 14
_LOG_LINE_H      = 14   # px per wrapped line in the event log

# Per-category text colours for the event log
_CAT_COL = {
    'combat':   (220,  80,  80),
    'revolt':   (220, 150,  50),
    'scout':    ( 80, 200, 220),
    'reinforce':( 80, 200, 120),
    'event':    (200, 200,  80),
}


def _wrap_text(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
    """Word-wrap *text* to fit within *max_w* pixels. Returns list of lines."""
    words  = text.split()
    lines  = []
    current = ''
    for word in words:
        candidate = (current + ' ' + word).strip()
        if font.size(candidate)[0] <= max_w:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or ['']


class SidePanel:
    def __init__(self, rect: pygame.Rect, state: GameState):
        self.rect  = rect
        self.state = state
        self._font_title = None
        self._font_body  = None
        self._font_log   = None
        self._btn_rect: pygame.Rect | None = None
        self._log_rect:  pygame.Rect | None = None
        self._on_end_turn = None
        self._hovering_btn = False
        self._log_scroll   = 0   # number of lines scrolled from top

    def set_state(self, state: GameState):
        self.state = state
        self._log_scroll = 0

    def set_end_turn_callback(self, cb):
        self._on_end_turn = cb

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEMOTION:
            self._hovering_btn = (
                self._btn_rect is not None and
                self._btn_rect.collidepoint(event.pos)
            )
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_rect and self._btn_rect.collidepoint(event.pos):
                if self._on_end_turn:
                    self._on_end_turn()
        # Mouse-wheel scroll inside the event log area
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL):
            over_log = self._log_rect and self._log_rect.collidepoint(
                event.pos if event.type == pygame.MOUSEBUTTONDOWN else
                pygame.mouse.get_pos()
            )
            if over_log:
                if event.type == pygame.MOUSEWHEEL:
                    self._log_scroll = max(0, self._log_scroll - event.y)
                elif event.button == 4:
                    self._log_scroll = max(0, self._log_scroll - 1)
                elif event.button == 5:
                    self._log_scroll += 1

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, selected_star_idx: int | None = None):
        if self._font_title is None:
            self._font_title = pygame.font.SysFont('monospace', _FONT_TITLE_SIZE, bold=True)
            self._font_body  = pygame.font.SysFont('monospace', _FONT_BODY_SIZE)
            self._font_log   = pygame.font.SysFont('monospace', 11)

        surface.fill(PANEL_BG, self.rect)

        x = self.rect.x + 10
        y = self.rect.y + 10
        w = self.rect.width - 20

        # Current player
        player = self.state.current_player()
        if player:
            idx = self.state.players.index(player)
            colour = PLAYER_COLOURS[idx] if idx < len(PLAYER_COLOURS) else (180, 180, 180)
            pygame.draw.rect(surface, colour, (x, y, 14, 14))
            name_surf = self._font_title.render(player.name, True, TEXT_COL)
            surface.blit(name_surf, (x + 18, y))
            y += 22

        # Turn counter
        turn_surf = self._font_body.render(f"Turn {self.state.turn}", True, LABEL_COL)
        surface.blit(turn_surf, (x, y))
        y += 20

        # Divider
        pygame.draw.line(surface, DIVIDER, (x, y), (x + w, y))
        y += 8

        # Player stats
        if player:
            stats = [
                ("Stars",      player.empire_size),
                ("Production", player.production),
                ("Fleets",     player.fleet_count),
                ("Credits",    player.credits),
            ]
            for label, val in stats:
                lbl = self._font_body.render(f"{label}:", True, LABEL_COL)
                val_s = self._font_body.render(str(val), True, TEXT_COL)
                surface.blit(lbl, (x, y))
                surface.blit(val_s, (x + w - val_s.get_width(), y))
                y += 18

        y += 8
        pygame.draw.line(surface, DIVIDER, (x, y), (x + w, y))
        y += 8

        # Selected star info
        if selected_star_idx is not None and selected_star_idx < len(self.state.stars):
            star = self.state.stars[selected_star_idx]
            owner = self.state.player_for_faction(star.owner_faction_id)
            owner_name = (
                "The Empire" if star.owner_faction_id == EMPIRE_FACTION
                else (owner.name if owner else f"0x{star.owner_faction_id:02x}")
            )
            star_lines = [
                f"Star {star.star_id}  ({star.x},{star.y})",
                f"Type: {star.planet_type}   Res: {star.resource}",
                f"Owner: {owner_name}",
            ]
            # Ship summary
            if star.warships:     star_lines.append(f"  WarShips:    {star.warships}")
            if star.transports:   star_lines.append(f"  TranSports:  {star.transports}")
            if star.stealthships: star_lines.append(f"  StealthShps: {star.stealthships}")
            if star.missiles:     star_lines.append(f"  Missiles:    {star.missiles}")
            # Occupation
            occupied = sum(1 for p in star.planets
                           if p.owner_faction_id != star.owner_faction_id and p.troops > 0)
            if occupied:
                star_lines.append(f"  Occupied: {occupied} planet(s)")

            hdr = self._font_body.render("Selected Star", True, LABEL_COL)
            surface.blit(hdr, (x, y))
            y += 18
            for line in star_lines:
                surf = self._font_body.render(line, True, TEXT_COL)
                surface.blit(surf, (x, y))
                y += 16

        # ---- Event log ----
        btn_y    = self.rect.bottom - _BTN_H - _BTN_MARGIN
        log_top  = y + 6
        log_h    = btn_y - log_top - 8
        self._log_rect = pygame.Rect(x, log_top, w, log_h)

        if log_h > _LOG_LINE_H * 2:
            self._draw_event_log(surface, x, log_top, w, log_h)

        # "End Turn" button pinned to bottom
        self._btn_rect = pygame.Rect(x, btn_y, w, _BTN_H)
        btn_col = BTN_HOVER if self._hovering_btn else BTN_NORMAL
        pygame.draw.rect(surface, btn_col, self._btn_rect, border_radius=4)
        btn_label = self._font_title.render("End Turn", True, BTN_TEXT)
        bx = self._btn_rect.centerx - btn_label.get_width() // 2
        by = self._btn_rect.centery - btn_label.get_height() // 2
        surface.blit(btn_label, (bx, by))

    # ------------------------------------------------------------------
    # Event log helpers
    # ------------------------------------------------------------------

    def _draw_event_log(self, surface: pygame.Surface,
                        x: int, y: int, w: int, h: int):
        font = self._font_log

        # Header
        hdr = self._font_body.render("Events", True, LABEL_COL)
        surface.blit(hdr, (x, y))
        y  += 16
        h  -= 16
        pygame.draw.line(surface, DIVIDER, (x, y), (x + w, y))
        y  += 4
        h  -= 4

        # Build wrapped lines for the current player's events, newest-first
        player  = self.state.current_player()
        faction = player.faction_id if player else -1
        events  = list(reversed(self.state.events_for_faction(faction)))

        lines: list[tuple[str, tuple]] = []   # (text, colour)
        for ev in events:
            colour = _CAT_COL.get(ev.category, TEXT_COL)
            prefix = f"T{ev.turn} "
            wrapped = _wrap_text(ev.text, font, w - 4)
            for i, segment in enumerate(wrapped):
                lines.append((prefix + segment if i == 0 else "    " + segment, colour))

        # Clamp scroll
        visible  = h // _LOG_LINE_H
        max_scroll = max(0, len(lines) - visible)
        self._log_scroll = min(self._log_scroll, max_scroll)

        # Clip drawing to the log area so text never bleeds outside
        clip_rect = pygame.Rect(x, y, w, h)
        old_clip  = surface.get_clip()
        surface.set_clip(clip_rect)

        ry = y
        for line, colour in lines[self._log_scroll : self._log_scroll + visible + 1]:
            surf = font.render(line, True, colour)
            surface.blit(surf, (x + 2, ry))
            ry += _LOG_LINE_H

        surface.set_clip(old_clip)

        # Scroll-bar if content overflows
        if len(lines) > visible:
            bar_x    = x + w - 3
            bar_h    = max(12, h * visible // len(lines))
            bar_y    = y + (h - bar_h) * self._log_scroll // max(1, max_scroll)
            pygame.draw.rect(surface, DIVIDER,   (bar_x, y, 3, h))
            pygame.draw.rect(surface, LABEL_COL, (bar_x, bar_y, 3, bar_h))