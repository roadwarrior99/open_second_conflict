"""Battle animation dialog — translation of COMBATWNDPROC from SCW.EXE.

The original renders scattered 5×7 ship-dot sprites in attacker (left) and
defender (right) halves.  Casualties cycle through three colour phases
(live → red → yellow → removed) for each of the three attrition rounds.

If missiles were involved a missile-barrage phase plays first, showing
projectile streaks flying across the divide and the resulting casualties.
"""
import pygame
import random
from second_conflict.ui.dialogs.base_dialog import BaseDialog, TITLE_COL, TEXT_COL
from second_conflict.model.constants import PLAYER_COLOURS, EMPIRE_FACTION

DOT_W      = 6
DOT_H      = 8
TOTAL_DOTS = 60   # total dots split proportionally between both sides

_COLOR_RED    = (220,  40,  40)
_COLOR_YEL    = (220, 200,  40)
_COLOR_MISSILE= (255, 220,  80)   # projectile streak colour

_DOT_SCALE  = 2   # scale factor for ship-dot sprites
_MAX_STREAKS = 8  # max visible missile streaks per salvo


class _Dot:
    __slots__ = ('x', 'y', 'is_attacker', 'state')

    def __init__(self, x, y, is_attacker):
        self.x = x
        self.y = y
        self.is_attacker = is_attacker
        self.state = 'alive'   # 'alive' | 'red' | 'dead'


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
        self._missile_casualties: tuple[list, list] = ([], [])

        # Missile streak data: list of (x1,y1, x2,y2, is_attacker)
        self._streaks: list[tuple[int,int,int,int,bool]] = []

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
        rec = self.record
        if rec.atk_missiles_fired > 0 or rec.def_missiles_fired > 0:
            phases.append(('missile_fly',   700))
            phases.append(('missile_hit',   450))
            phases.append(('missile_clear', 300))
        for r in range(len(rec.rounds)):
            phases.append((f'r{r}_red',    500))
            phases.append((f'r{r}_yellow', 350))
            phases.append((f'r{r}_clear',  300))
        phases.append(('result', 0))
        return phases

    def _setup_dots(self):
        cr   = self._content_rect()
        ba_x = cr.x
        ba_y = cr.y + 36
        ba_w = cr.width
        ba_h = 140

        half_w = ba_w // 2 - 8
        mid_x  = ba_x + ba_w // 2

        rec = self.record

        # Base dot split on pre-barrage totals when missiles were involved,
        # otherwise fall back to post-barrage (backward-compatible).
        atk_total = rec.atk_ships_total if rec.atk_ships_total > 0 else rec.atk_initial
        def_total = rec.def_ships_total if rec.def_ships_total > 0 else rec.def_initial
        grand     = atk_total + def_total
        if grand > 0:
            atk_n = max(1, min(TOTAL_DOTS - 1, round(TOTAL_DOTS * atk_total / grand)))
            def_n = max(1, TOTAL_DOTS - atk_n)
        else:
            atk_n = def_n = 1

        if self._dot_sprite:
            dw = self._dot_sprite.get_width()
            dh = self._dot_sprite.get_height()
        else:
            dw, dh = DOT_W, DOT_H

        atk_area = pygame.Rect(ba_x + 4,      ba_y + 4, half_w - 8, ba_h - 8)
        def_area = pygame.Rect(mid_x + 4,     ba_y + 4, half_w - 8, ba_h - 8)

        for _ in range(atk_n):
            x = random.randint(atk_area.x, max(atk_area.x, atk_area.right  - dw))
            y = random.randint(atk_area.y, max(atk_area.y, atk_area.bottom - dh))
            self._dots.append(_Dot(x, y, True))

        for _ in range(def_n):
            x = random.randint(def_area.x, max(def_area.x, def_area.right  - dw))
            y = random.randint(def_area.y, max(def_area.y, def_area.bottom - dh))
            self._dots.append(_Dot(x, y, False))

        atk_dots = [d for d in self._dots if d.is_attacker]
        def_dots = [d for d in self._dots if not d.is_attacker]

        # Pre-compute missile casualties (proportional to kill counts)
        if atk_total > 0 and rec.missile_atk_killed > 0:
            n = round(rec.missile_atk_killed * atk_n / atk_total)
            m_atk_dying = atk_dots[:n]
            atk_dots    = atk_dots[n:]
        else:
            m_atk_dying = []

        if def_total > 0 and rec.missile_def_killed > 0:
            n = round(rec.missile_def_killed * def_n / def_total)
            m_def_dying = def_dots[:n]
            def_dots    = def_dots[n:]
        else:
            m_def_dying = []

        self._missile_casualties = (m_atk_dying, m_def_dying)

        # Pre-compute attrition casualties from the remaining live dots
        atk_alive = list(atk_dots)
        def_alive = list(def_dots)
        atk_post  = rec.atk_initial
        def_post  = rec.def_initial
        for atk_hit, def_hit in rec.rounds:
            a_n = round(atk_hit * len(atk_alive) / atk_post) if atk_post > 0 else 0
            d_n = round(def_hit * len(def_alive) / def_post) if def_post > 0 else 0
            self._casualties.append((list(atk_alive[:a_n]), list(def_alive[:d_n])))
            atk_alive = atk_alive[a_n:]
            def_alive = def_alive[d_n:]
            atk_post  = max(1, atk_post - atk_hit)
            def_post  = max(1, def_post - def_hit)

        # Generate missile streak start/end positions for the fly animation
        n_atk_streaks = min(_MAX_STREAKS, rec.atk_missiles_fired)
        n_def_streaks = min(_MAX_STREAKS, rec.def_missiles_fired)
        for _ in range(n_atk_streaks):
            sx = random.randint(atk_area.x, atk_area.right)
            sy = random.randint(atk_area.y, atk_area.bottom)
            ex = random.randint(def_area.x, def_area.right)
            ey = random.randint(def_area.y, def_area.bottom)
            self._streaks.append((sx, sy, ex, ey, True))
        for _ in range(n_def_streaks):
            sx = random.randint(def_area.x, def_area.right)
            sy = random.randint(def_area.y, def_area.bottom)
            ex = random.randint(atk_area.x, atk_area.right)
            ey = random.randint(atk_area.y, atk_area.bottom)
            self._streaks.append((sx, sy, ex, ey, False))

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

        if phase_name == 'missile_hit':
            for d in self._missile_casualties[0] + self._missile_casualties[1]:
                d.state = 'red'

        elif phase_name == 'missile_clear':
            for d in self._missile_casualties[0] + self._missile_casualties[1]:
                d.state = 'dead'

        elif phase_name.endswith('_red'):
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
        surface.blit(self._text(f"Attacker: {atk_name}", atk_color), (cr.x + 4, cr.y + 18))
        surface.blit(self._text(f"Defender: {def_name}", def_color), (mid_x + 4, cr.y + 18))

        # Battle area
        ba_y = cr.y + 36
        ba_h = 140
        ba_rect = pygame.Rect(cr.x, ba_y, cr.width, ba_h)
        pygame.draw.rect(surface, (10, 12, 20), ba_rect)
        pygame.draw.rect(surface, (40, 50, 80), ba_rect, 1)
        pygame.draw.line(surface, (40, 50, 80), (mid_x, ba_y), (mid_x, ba_y + ba_h))

        phase_name, phase_dur = self._phases[self._phase_idx]

        # ---- Missile streak animation ----
        if phase_name == 'missile_fly' and self._streaks and phase_dur > 0:
            t = min(1.0, self._phase_timer / phase_dur)
            for sx, sy, ex, ey, is_atk in self._streaks:
                cx = int(sx + (ex - sx) * t)
                cy = int(sy + (ey - sy) * t)
                # Draw a short trailing line behind the projectile
                tail_t = max(0.0, t - 0.15)
                tx = int(sx + (ex - sx) * tail_t)
                ty = int(sy + (ey - sy) * tail_t)
                col = atk_color if is_atk else def_color
                pygame.draw.line(surface, col,         (tx, ty), (cx, cy), 1)
                pygame.draw.circle(surface, _COLOR_MISSILE, (cx, cy), 2)

        # ---- Ship dots ----
        if self._dot_sprite:
            dw = self._dot_sprite.get_width()
            dh = self._dot_sprite.get_height()
        else:
            dw, dh = DOT_W, DOT_H

        for dot in self._dots:
            if dot.state == 'dead':
                continue
            if dot.state in ('red', 'yellow'):
                color = _COLOR_RED if dot.state == 'red' else _COLOR_YEL
                pygame.draw.rect(surface, color, (dot.x, dot.y, dw, dh))
            elif self._dot_sprite:
                tinted  = self._dot_sprite.copy()
                color   = atk_color if dot.is_attacker else def_color
                overlay = pygame.Surface((dw, dh))
                overlay.fill(color)
                tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
                tinted.set_colorkey((0, 0, 0))
                surface.blit(tinted, (dot.x, dot.y))
            else:
                color = atk_color if dot.is_attacker else def_color
                pygame.draw.rect(surface, color, (dot.x, dot.y, dw, dh))

        # ---- Info rows below battle area ----
        stats_y = ba_y + ba_h + 8

        # Missile summary (shown during and after missile phases)
        missile_phases = ('missile_fly', 'missile_hit', 'missile_clear')
        if phase_name in missile_phases or (
            rec.atk_missiles_fired > 0 or rec.def_missiles_fired > 0
        ):
            if rec.atk_missiles_fired > 0 or rec.def_missiles_fired > 0:
                msl_text = (
                    f"Missiles:  Atk fired {rec.atk_missiles_fired} "
                    f"(killed {rec.missile_def_killed})   "
                    f"Def fired {rec.def_missiles_fired} "
                    f"(killed {rec.missile_atk_killed})"
                )
                col = _COLOR_MISSILE if phase_name in missile_phases else (160, 140, 80)
                surface.blit(self._text(msl_text, col), (cr.x, stats_y))
                stats_y += 18

        # Attrition stats
        atk_losses = rec.atk_initial - rec.atk_final
        def_losses = rec.def_initial - rec.def_final
        stats = (f"WarShips: "
                 f"Attacker {rec.atk_initial} → {rec.atk_final}  (lost {atk_losses}) "
                 f"Defender {rec.def_initial} → {rec.def_final}  (lost {def_losses})")
        surface.blit(self._text(stats), (cr.x, stats_y))

        # Phase label (missile barrage or round counter)
        if phase_name in missile_phases:
            lbl = self._text("— Missile Barrage —", _COLOR_MISSILE)
            surface.blit(lbl, (cr.right - lbl.get_width(), stats_y + 18))
        elif phase_name not in ('result', 'scatter'):
            rnum = int(phase_name[1]) + 1
            lbl  = self._text(f"Round {rnum} of {len(rec.rounds)}", (140, 140, 180))
            surface.blit(lbl, (cr.right - lbl.get_width(), stats_y + 18))

        # Outcome text
        if phase_name == 'result':
            winner = self._faction_name(rec.winner_faction)
            rs = self._title_text(f"{winner} controls Star {rec.star_id}", (255, 220, 60))
            surface.blit(rs, (cr.x + (cr.width - rs.get_width()) // 2, stats_y + 20))
            hint = self._text("Click or press any key to continue", (100, 100, 140))
            surface.blit(hint, (cr.x + (cr.width - hint.get_width()) // 2, stats_y + 42))

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