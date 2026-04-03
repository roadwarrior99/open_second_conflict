"""Battle animation dialog — translation of COMBATWNDPROC from SCW.EXE.

The original renders scattered 5×7 ship-dot sprites in attacker (left) and
defender (right) halves.  Casualties cycle through three colour phases
(live → red → yellow → removed) for each of the three attrition rounds.
"""
import pygame
import random
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL
from second_conflict.model.constants import PLAYER_COLOURS, EMPIRE_FACTION

DOT_W      = 6
DOT_H      = 8
TOTAL_DOTS = 60   # total dots split proportionally between both sides

_COLOR_RED  = (220,  40,  40)
_COLOR_YEL  = (220, 200,  40)
_COLOR_DEAD = ( 45,  45,  55)   # "dark" — briefly visible then hidden

_DOT_SCALE  = 2   # scale factor for ship-dot sprites


class _Dot:
    __slots__ = ('x', 'y', 'is_attacker', 'state')

    def __init__(self, x, y, is_attacker):
        self.x = x
        self.y = y
        self.is_attacker = is_attacker
        self.state = 'alive'   # 'alive' | 'red' | 'yellow' | 'dead'


class CombatAnimation(BaseDialog):
    """Shows the COMBATWNDPROC battle animation for one CombatRecord."""

    def __init__(self, screen: pygame.Surface, record, state):
        super().__init__(screen, "Battle", width=580, height=330)
        self.record = record
        self.state  = state

        self._phases = self._build_phases()
        self._phase_idx   = 0
        self._phase_timer = 0

        self._dots: list[_Dot] = []
        self._casualties: list[tuple[list, list]] = []

        # Try to load the original ship-dot sprite from SCW.EXE
        self._dot_sprite: pygame.Surface | None = None
        try:
            from second_conflict.assets import get_ship_dot
            self._dot_sprite = get_ship_dot(_DOT_SCALE)
        except Exception:
            pass

        self._setup_dots()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _build_phases(self):
        phases = [('scatter', 600)]
        for r in range(len(self.record.rounds)):
            phases.append((f'r{r}_red',    500))
            phases.append((f'r{r}_yellow', 350))
            phases.append((f'r{r}_clear',  300))
        phases.append(('result', 0))
        return phases

    def _setup_dots(self):
        cr = self._content_rect()
        ba_x = cr.x
        ba_y = cr.y + 36    # leave room for faction labels
        ba_w = cr.width
        ba_h = 140

        half_w = ba_w // 2 - 8

        atk_init = self.record.atk_initial
        def_init = self.record.def_initial
        total    = atk_init + def_init
        if total > 0:
            atk_n = max(1, min(TOTAL_DOTS - 1,
                               round(TOTAL_DOTS * atk_init / total)))
            def_n = max(1, TOTAL_DOTS - atk_n)
        else:
            atk_n = def_n = 1

        # Use sprite dimensions if available, else fallback constants
        if self._dot_sprite:
            dw = self._dot_sprite.get_width()
            dh = self._dot_sprite.get_height()
        else:
            dw, dh = DOT_W, DOT_H

        atk_area = pygame.Rect(ba_x + 4,            ba_y + 4, half_w - 8, ba_h - 8)
        def_area = pygame.Rect(ba_x + ba_w // 2 + 4, ba_y + 4, half_w - 8, ba_h - 8)

        for _ in range(atk_n):
            x = random.randint(atk_area.x, max(atk_area.x, atk_area.right  - dw))
            y = random.randint(atk_area.y, max(atk_area.y, atk_area.bottom - dh))
            self._dots.append(_Dot(x, y, True))

        for _ in range(def_n):
            x = random.randint(def_area.x, max(def_area.x, def_area.right  - dw))
            y = random.randint(def_area.y, max(def_area.y, def_area.bottom - dh))
            self._dots.append(_Dot(x, y, False))

        # Pre-compute which displayed dots die each round, scaled proportionally.
        atk_alive = [d for d in self._dots if d.is_attacker]
        def_alive = [d for d in self._dots if not d.is_attacker]

        for atk_hit, def_hit in self.record.rounds:
            if self.record.atk_initial > 0:
                a_dying_n = round(atk_hit * atk_n / self.record.atk_initial)
            else:
                a_dying_n = 0
            if self.record.def_initial > 0:
                d_dying_n = round(def_hit * def_n / self.record.def_initial)
            else:
                d_dying_n = 0

            a_dying = atk_alive[:a_dying_n]
            d_dying = def_alive[:d_dying_n]
            atk_alive = atk_alive[a_dying_n:]
            def_alive = def_alive[d_dying_n:]
            self._casualties.append((list(a_dying), list(d_dying)))

    # ------------------------------------------------------------------
    # Event / update
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        super().handle_event(event)
        phase_name, _ = self._phases[self._phase_idx]
        if phase_name == 'result':
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                self.close(None)

    def update(self, dt: int):
        phase_name, phase_dur = self._phases[self._phase_idx]
        if phase_dur == 0:
            return
        self._phase_timer += dt
        if self._phase_timer >= phase_dur:
            self._phase_timer = 0
            self._advance_phase()

    def _advance_phase(self):
        self._phase_idx = min(self._phase_idx + 1, len(self._phases) - 1)
        self._apply_phase_effect()

    def _apply_phase_effect(self):
        phase_name, _ = self._phases[self._phase_idx]

        if phase_name.endswith('_red'):
            rnum = int(phase_name[1])
            if rnum < len(self._casualties):
                for d in self._casualties[rnum][0] + self._casualties[rnum][1]:
                    d.state = 'red'

        elif phase_name.endswith('_yellow'):
            rnum = int(phase_name[1])
            if rnum < len(self._casualties):
                for d in self._casualties[rnum][0] + self._casualties[rnum][1]:
                    d.state = 'yellow'

        elif phase_name.endswith('_clear'):
            rnum = int(phase_name[1])
            if rnum < len(self._casualties):
                for d in self._casualties[rnum][0] + self._casualties[rnum][1]:
                    d.state = 'dead'

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        cr  = self._content_rect()
        rec = self.record

        atk_name  = self._faction_name(rec.attacker_faction)
        def_name  = self._faction_name(rec.defender_faction)
        atk_color = self._faction_color(rec.attacker_faction)
        def_color = self._faction_color(rec.defender_faction)

        # Location subtitle
        loc = f"Star {rec.star_id}  ({rec.star_x},{rec.star_y})"
        surface.blit(self._text(loc, (160, 160, 200)), (cr.x, cr.y))

        # Faction name labels
        mid_x = cr.x + cr.width // 2
        atk_lbl = self._text(f"Attacker: {atk_name}", atk_color)
        def_lbl = self._text(f"Defender: {def_name}", def_color)
        surface.blit(atk_lbl, (cr.x + 4, cr.y + 18))
        surface.blit(def_lbl, (mid_x + 4, cr.y + 18))

        # Battle area background + dividing line
        ba_y = cr.y + 36
        ba_h = 140
        ba_rect = pygame.Rect(cr.x, ba_y, cr.width, ba_h)
        pygame.draw.rect(surface, (10, 12, 20), ba_rect)
        pygame.draw.rect(surface, (40, 50, 80), ba_rect, 1)
        pygame.draw.line(surface, (40, 50, 80),
                         (mid_x, ba_y), (mid_x, ba_y + ba_h))

        # Ship dots
        if self._dot_sprite:
            dw = self._dot_sprite.get_width()
            dh = self._dot_sprite.get_height()
        else:
            dw, dh = DOT_W, DOT_H

        for dot in self._dots:
            if dot.state == 'dead':
                continue
            if dot.state in ('red', 'yellow'):
                # Phase colours: draw plain rect so the flash is obvious
                color = _COLOR_RED if dot.state == 'red' else _COLOR_YEL
                pygame.draw.rect(surface, color, (dot.x, dot.y, dw, dh))
            elif self._dot_sprite:
                # Alive: tint the sprite to faction colour
                tinted = self._dot_sprite.copy()
                color  = atk_color if dot.is_attacker else def_color
                overlay = pygame.Surface((dw, dh))
                overlay.fill(color)
                tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
                tinted.set_colorkey((0, 0, 0))
                surface.blit(tinted, (dot.x, dot.y))
            else:
                color = atk_color if dot.is_attacker else def_color
                pygame.draw.rect(surface, color, (dot.x, dot.y, dw, dh))

        # Stats row
        stats_y = ba_y + ba_h + 8
        atk_losses = rec.atk_initial - rec.atk_final
        def_losses = rec.def_initial - rec.def_final
        stats = (f"WarShips:  "
                 f"Attacker {rec.atk_initial} → {rec.atk_final}  "
                 f"(lost {atk_losses})     "
                 f"Defender {rec.def_initial} → {rec.def_final}  "
                 f"(lost {def_losses})")
        surface.blit(self._text(stats), (cr.x, stats_y))

        # Round counter
        phase_name, _ = self._phases[self._phase_idx]
        if phase_name != 'result' and phase_name != 'scatter':
            rnum = int(phase_name[1]) + 1
            round_s = self._text(f"Round {rnum} of {len(rec.rounds)}", (140, 140, 180))
            surface.blit(round_s, (cr.right - round_s.get_width(), stats_y))

        # Outcome text (result phase only)
        if phase_name == 'result':
            winner = self._faction_name(rec.winner_faction)
            result_text = f"{winner} controls Star {rec.star_id}"
            rs = self._title_text(result_text, (255, 220, 60))
            surface.blit(rs, (cr.x + (cr.width - rs.get_width()) // 2,
                               stats_y + 20))
            hint = self._text("Click or press any key to continue",
                              (100, 100, 140))
            surface.blit(hint, (cr.x + (cr.width - hint.get_width()) // 2,
                                stats_y + 42))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _faction_name(self, fid: int) -> str:
        if fid == EMPIRE_FACTION:
            return "Empire"
        p = self.state.player_for_faction(fid)
        return p.name if p else f"Faction {fid:02x}"

    def _faction_color(self, fid: int) -> tuple:
        p = self.state.player_for_faction(fid)
        if p:
            idx = self.state.players.index(p)
            if idx < len(PLAYER_COLOURS):
                return PLAYER_COLOURS[idx]
        return (180, 180, 180)