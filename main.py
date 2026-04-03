"""Second Conflict — pygame recreation entry point.

Usage:
    python main.py [path/to/scenario.scn]

Layout
------
  +------------------+--------+
  |  Menu bar (top, MENU_H px)                           |
  +------------------+--------+
  |                  |        |
  |   Galaxy Map     | Side   |
  |   (MAP_W px)     | Panel  |
  |                  |        |
  +------------------+--------+
  |  System Info Strip (full width, SYS_H px)            |
  +------------------------------------------------------+

Menu bar
--------
  File:  New Game (Ctrl+N) | Open (Ctrl+O) | Save (Ctrl+S) | Quit
  View:  Fleets (F2) | Production (F3) | Unrest (F4) | Stats (F1) | Options (F5)
  Game:  End Turn (Enter) | Score (F6) | About
"""
import sys
import os
import pygame
import argparse
import logging

# Layout constants
SCREEN_W = 1100
SCREEN_H = 760
MENU_H   = 26
MAP_W    = 800
PANEL_W  = SCREEN_W - MAP_W
SYS_H    = 110         # system-info strip below map
MAP_H    = SCREEN_H - MENU_H - SYS_H
FPS      = 30
TITLE    = "Open Second Conflict"

BG_COLOUR   = (8, 8, 16)
MENU_BG     = (18, 22, 36)
MENU_FG     = (200, 200, 220)
MENU_SEL_BG = (50, 70, 130)
MENU_HOV_BG = (35, 45, 80)


# ---------------------------------------------------------------------------
# Menu bar
# ---------------------------------------------------------------------------

class MenuItem:
    def __init__(self, label: str, key: int | None = None, mod: int = 0):
        self.label = label
        self.key   = key    # pygame.K_* shortcut
        self.mod   = mod    # pygame.KMOD_CTRL etc.

class Menu:
    def __init__(self, title: str, items: list[MenuItem]):
        self.title = title
        self.items = items
        self.rect: pygame.Rect | None = None

class MenuBar:
    """Simple pull-down menu bar."""

    def __init__(self, rect: pygame.Rect):
        self.rect      = rect
        self._font     = None
        self._open_idx: int | None = None   # which top-level menu is open
        self._hover_item: tuple[int, int] | None = None
        self._callbacks: dict[str, callable] = {}
        self._menus: list[Menu] = []

    def setup(self, menus: list[Menu]):
        self._menus = menus

    def register(self, label: str, cb: callable):
        self._callbacks[label] = cb

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True if the menu consumed the event."""
        if self._font is None:
            self._font = pygame.font.SysFont('monospace', 13)

        if event.type == pygame.KEYDOWN:
            for menu in self._menus:
                for item in menu.items:
                    if (item.key and event.key == item.key and
                            (item.mod == 0 or event.mod & item.mod)):
                        self._fire(item.label)
                        return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            # Click on top-level title
            for i, menu in enumerate(self._menus):
                if menu.rect and menu.rect.collidepoint(pos):
                    self._open_idx = None if self._open_idx == i else i
                    return True
            # Click on dropdown item
            if self._open_idx is not None:
                for j, item in enumerate(self._menus[self._open_idx].items):
                    r = self._item_rect(self._open_idx, j)
                    if r and r.collidepoint(pos):
                        self._fire(item.label)
                        self._open_idx = None
                        return True
            # Click elsewhere closes menu
            self._open_idx = None

        if event.type == pygame.MOUSEMOTION:
            pos = event.pos
            self._hover_item = None
            if self._open_idx is not None:
                for j, item in enumerate(self._menus[self._open_idx].items):
                    r = self._item_rect(self._open_idx, j)
                    if r and r.collidepoint(pos):
                        self._hover_item = (self._open_idx, j)

        return False

    def draw(self, surface: pygame.Surface):
        if self._font is None:
            self._font = pygame.font.SysFont('monospace', 13)

        surface.fill(MENU_BG, self.rect)
        pygame.draw.line(surface, (40, 45, 70),
                         (self.rect.x, self.rect.bottom - 1),
                         (self.rect.right, self.rect.bottom - 1))

        x = self.rect.x + 6
        for i, menu in enumerate(self._menus):
            lbl  = self._font.render(menu.title, True, MENU_FG)
            w    = lbl.get_width() + 16
            rect = pygame.Rect(x, self.rect.y, w, self.rect.height)
            menu.rect = rect
            if i == self._open_idx:
                pygame.draw.rect(surface, MENU_SEL_BG, rect)
            surface.blit(lbl, (x + 8, self.rect.y + (self.rect.height - lbl.get_height()) // 2))
            x += w

        # Draw open dropdown
        if self._open_idx is not None:
            menu = self._menus[self._open_idx]
            dw   = 200
            dx   = menu.rect.x
            dy   = self.rect.bottom
            dh   = len(menu.items) * 22 + 4
            drop = pygame.Rect(dx, dy, dw, dh)
            pygame.draw.rect(surface, MENU_BG, drop)
            pygame.draw.rect(surface, (60, 70, 120), drop, 1)
            for j, item in enumerate(menu.items):
                r = self._item_rect(self._open_idx, j)
                if r:
                    if self._hover_item == (self._open_idx, j):
                        pygame.draw.rect(surface, MENU_HOV_BG, r)
                    lbl = self._font.render(item.label, True, MENU_FG)
                    surface.blit(lbl, (r.x + 8, r.y + 4))
                    # Keyboard shortcut hint
                    if item.key:
                        hint = self._shortcut_text(item)
                        hs   = self._font.render(hint, True, (120, 120, 160))
                        surface.blit(hs, (r.right - hs.get_width() - 8, r.y + 4))

    def _item_rect(self, menu_idx: int, item_idx: int) -> pygame.Rect | None:
        menu = self._menus[menu_idx]
        if not menu.rect:
            return None
        dw = 200
        return pygame.Rect(
            menu.rect.x,
            self.rect.bottom + 2 + item_idx * 22,
            dw, 22
        )

    def _fire(self, label: str):
        cb = self._callbacks.get(label)
        if cb:
            cb()

    def _shortcut_text(self, item: MenuItem) -> str:
        name = pygame.key.name(item.key).upper()
        if item.mod & pygame.KMOD_CTRL:
            return f"Ctrl+{name}"
        return f"F{item.key - pygame.K_F1 + 1}" if pygame.K_F1 <= item.key <= pygame.K_F12 else name


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(save_file: str, debug: bool = False):
    logger = logging.getLogger()
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock  = pygame.time.Clock()

    # Start with a file from argv, or an empty state (user picks from menu)
    if len(sys.argv) > 1 and os.path.isfile(save_file):
        state = _load_file(save_file)
        state.options.dev_mode = debug
    else:
        from second_conflict.model.game_state import GameState, GameOptions
        state = GameState(options=GameOptions(dev_mode=debug))

    from second_conflict.ui.map_view    import MapView
    from second_conflict.ui.side_panel  import SidePanel
    from second_conflict.ui.sys_info_panel import SysInfoPanel

    menu_rect  = pygame.Rect(0,            0,      SCREEN_W, MENU_H)
    map_rect   = pygame.Rect(0,            MENU_H, MAP_W,    MAP_H)
    panel_rect = pygame.Rect(MAP_W,        MENU_H, PANEL_W,  MAP_H + SYS_H)
    sys_rect   = pygame.Rect(0,            MENU_H + MAP_H, MAP_W, SYS_H)

    map_view   = MapView(map_rect, state)
    side_panel = SidePanel(panel_rect, state)
    sys_panel  = SysInfoPanel(sys_rect, state)
    menu_bar   = MenuBar(menu_rect)

    # Wire End Turn
    def on_end_turn():
        nonlocal state
        if not state.stars:
            return
        state = _do_end_turn(screen, state, map_view, side_panel, sys_panel)

    def on_star_click(star_idx: int, second_click: bool):
        if second_click:
            _open_fleet_dialog(screen, state, star_idx)

    map_view.set_star_click_callback(on_star_click)
    side_panel.set_end_turn_callback(on_end_turn)
    sys_panel.set_type_change_callback(
        lambda star_idx, pt: None   # state already mutated; map redraws next frame
    )
    sys_panel.set_ground_combat_callback(
        lambda star_idx: _open_ground_combat(screen, state, star_idx)
    )
    sys_panel.set_edit_star_callback(
        lambda star_idx: _open_star_editor(screen, state, star_idx)
    )

    # Build menus
    menu_bar.setup([
        Menu("File", [
            MenuItem("New Game",       pygame.K_n, pygame.KMOD_CTRL),
            MenuItem("Scenario...",    pygame.K_l, pygame.KMOD_CTRL),
            MenuItem("Open...",        pygame.K_o, pygame.KMOD_CTRL),
            MenuItem("Save...",        pygame.K_s, pygame.KMOD_CTRL),
            MenuItem("Quit",           pygame.K_q, pygame.KMOD_CTRL),
        ]),
        Menu("View", [
            MenuItem("Fleets",          pygame.K_F2),
            MenuItem("Production",      pygame.K_F3),
            MenuItem("Unrest",          pygame.K_F4),
            MenuItem("Statistics",      pygame.K_F1),
            MenuItem("Options",         pygame.K_F5),
            MenuItem("Planets",         pygame.K_F7),
            MenuItem("Scout Report",    pygame.K_F8),
            MenuItem("Reinforcements",  pygame.K_F9),
            MenuItem("Revolt",          pygame.K_F10),
        ]),
        Menu("Game", [
            MenuItem("End Turn",  pygame.K_RETURN),
            MenuItem("Score",     pygame.K_F6),
            MenuItem("About",     pygame.K_F12),
        ]),
    ])

    def _set_state(new_state):
        nonlocal state
        state = new_state
        map_view.set_state(state)
        side_panel.set_state(state)
        sys_panel.set_state(state)

    menu_bar.register("New Game",    lambda: _new_game_action(screen, _set_state))
    menu_bar.register("Scenario...", lambda: _scenario_action(screen, _set_state))
    menu_bar.register("Open...",     lambda: _open_action(screen, _set_state))
    menu_bar.register("Save...",    lambda: _save_action(screen, state))
    menu_bar.register("Quit",       lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)))
    menu_bar.register("Fleets",         lambda: _show_fleets(screen, state, map_view))
    menu_bar.register("Production",     lambda: _show_production(screen, state))
    menu_bar.register("Unrest",         lambda: _show_unrest(screen, state))
    menu_bar.register("Statistics",     lambda: _show_stats(screen, state))
    menu_bar.register("Options",        lambda: _show_options(screen, state))
    menu_bar.register("Planets",        lambda: _show_planets(screen, state, map_view.selected_star))
    menu_bar.register("Scout Report",   lambda: _show_scout_report(screen, state))
    menu_bar.register("Reinforcements", lambda: _show_reinforcements(screen, state))
    menu_bar.register("Revolt",         lambda: _show_revolt(screen, state))
    menu_bar.register("End Turn",   on_end_turn)
    menu_bar.register("Score",      lambda: _show_score(screen, state))
    menu_bar.register("About",      lambda: _show_about(screen))

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if menu_bar.handle_event(event):
                continue

            map_view.handle_event(event)
            side_panel.handle_event(event)
            sys_panel.handle_event(event, map_view.selected_star)

        screen.fill(BG_COLOUR)
        map_view.draw(screen)
        side_panel.draw(screen, map_view.selected_star)
        sys_panel.draw(screen, map_view.selected_star)
        menu_bar.draw(screen)

        if not state.stars:
            _draw_no_game(screen)

        if state.game_over:
            _draw_game_over(screen, state)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


# ---------------------------------------------------------------------------
# Turn processing
# ---------------------------------------------------------------------------

def _do_end_turn(screen, state, map_view, side_panel, sys_panel):
    from second_conflict.engine.turn_runner import run_turn
    from second_conflict.ui.dialogs.events_dlg import EventsDialog

    # Capture the acting player's faction before run_turn can eliminate them
    current = state.current_player()
    faction = current.faction_id if current else 0

    new_events, combat_records = run_turn(state)

    if combat_records:
        from second_conflict.ui.dialogs.combat_anim import CombatAnimation
        for rec in combat_records:
            if rec.attacker_faction == faction or rec.defender_faction == faction:
                CombatAnimation(screen, rec, state).run()

    # Show event log for this player (if option enabled)
    if state.options.show_events_log:
        player_events = [e for e in new_events
                         if e.player_faction == faction or e.category in ('combat', 'event')]
        if player_events:
            dlg = EventsDialog(screen, player_events)
            dlg.run()

    # Show score dialog if game over
    if state.game_over:
        from second_conflict.ui.dialogs.score_dlg import ScoreDialog
        ScoreDialog(screen, state).run()

    # Advance to next human player in hotseat
    active_humans = state.human_players()
    if active_humans:
        current_idx = state.current_player_slot % len(active_humans)
        state.current_player_slot = (current_idx + 1) % len(active_humans)

    map_view.select_star(None)
    side_panel.set_state(state)
    sys_panel.set_state(state)
    return state


# ---------------------------------------------------------------------------
# Menu actions
# ---------------------------------------------------------------------------

def _new_game_action(screen, set_state_cb):
    s = _new_game(screen)
    if s:
        set_state_cb(s)

def _scenario_action(screen, set_state_cb):
    from second_conflict.ui.dialogs.scenario_dlg import ScenarioDialog
    from second_conflict.io.scenario_parser import parse_file
    path = ScenarioDialog(screen).run()
    if not path:
        return
    try:
        set_state_cb(parse_file(path))
    except Exception as e:
        print(f"Scenario load error: {e}")

def _open_action(screen, set_state_cb):
    s = _load_game(screen)
    if s:
        set_state_cb(s)

def _save_action(screen, state):
    path = _simple_input_dialog(screen, "Save to file:", "savegame.sav")
    if not path:
        return
    # In dev mode, allow overriding the turn number stored in the file
    save_turn = state.turn
    if state.options.dev_mode:
        turn_str = _simple_input_dialog(screen, "Turn number to save:",
                                        str(state.turn))
        if not turn_str:
            return
        try:
            save_turn = int(turn_str)
        except ValueError:
            pass
    old_turn = state.turn
    state.turn = save_turn
    try:
        from second_conflict.io.scenario_parser import write_file
        write_file(state, path)
    except Exception as e:
        print(f"Save error: {e}")
    finally:
        state.turn = old_turn

def _show_fleets(screen, state, map_view):
    current = state.current_player()
    if not current:
        return
    from second_conflict.ui.dialogs.fleet_view_dlg import FleetViewDialog
    result = FleetViewDialog(screen, state, current.faction_id).run()
    if result is not None:   # result = dest_star to jump to
        map_view.select_star(result)

def _show_production(screen, state):
    current = state.current_player()
    if not current:
        return
    from second_conflict.ui.dialogs.prod_limit_dlg import ProdLimitDialog
    ProdLimitDialog(screen, state, current.faction_id).run()

def _show_unrest(screen, state):
    current = state.current_player()
    if not current:
        return
    from second_conflict.ui.dialogs.unrest_dlg import UnrestDialog
    UnrestDialog(screen, state, current.faction_id).run()

def _show_stats(screen, state):
    from second_conflict.ui.dialogs.stats_dlg import StatsDialog
    StatsDialog(screen, state).run()

def _show_options(screen, state):
    from second_conflict.ui.dialogs.options_dlg import OptionsDialog
    OptionsDialog(screen, state).run()

def _show_score(screen, state):
    from second_conflict.ui.dialogs.score_dlg import ScoreDialog
    ScoreDialog(screen, state).run()

def _show_about(screen):
    from second_conflict.ui.dialogs.about_dlg import AboutDialog
    AboutDialog(screen).run()

def _show_planets(screen, state, selected_star_idx=None):
    if not state.stars:
        return
    # If a star is selected on the map, jump straight to its planet detail
    if selected_star_idx is not None and 0 <= selected_star_idx < len(state.stars):
        star = state.stars[selected_star_idx]
        from second_conflict.ui.dialogs.planet_detail_dlg import PlanetDetailDialog
        PlanetDetailDialog(screen, star, state).run()
        return
    # Otherwise show the owned-star overview
    current = state.current_player()
    if not current:
        return
    from second_conflict.ui.dialogs.adm_view_dlg import AdminViewDialog
    AdminViewDialog(screen, state, current.faction_id).run()

def _show_scout_report(screen, state):
    current = state.current_player()
    if not current:
        return
    from second_conflict.ui.dialogs.scout_view_dlg import ScoutViewDialog
    ScoutViewDialog(screen, state, current.faction_id).run()

def _show_reinforcements(screen, state):
    current = state.current_player()
    if not current:
        return
    from second_conflict.ui.dialogs.reinf_view_dlg import ReinfViewDialog
    ReinfViewDialog(screen, state, current.faction_id).run()

def _show_revolt(screen, state):
    current = state.current_player()
    if not current:
        return
    from second_conflict.ui.dialogs.revolt_view_dlg import RevoltViewDialog
    RevoltViewDialog(screen, state, current.faction_id).run()


# ---------------------------------------------------------------------------
# Ground combat
# ---------------------------------------------------------------------------

def _open_ground_combat(screen, state, star_idx: int):
    current = state.current_player()
    if current is None:
        return
    star = state.stars[star_idx]
    if star.owner_faction_id != current.faction_id:
        return
    from second_conflict.ui.dialogs.ground_combat_dlg import GroundCombatDialog
    GroundCombatDialog(screen, star, current.faction_id, state).run()


def _open_star_editor(screen, state, star_idx: int):
    if star_idx < 0 or star_idx >= len(state.stars):
        return
    from second_conflict.ui.dialogs.star_editor_dlg import StarEditorDialog
    StarEditorDialog(screen, state.stars[star_idx], state).run()


# ---------------------------------------------------------------------------
# Fleet dispatch
# ---------------------------------------------------------------------------

def _open_fleet_dialog(screen, state, star_idx: int):
    current = state.current_player()
    if current is None:
        return
    from second_conflict.ui.dialogs.fleet_dlg import FleetDialog
    from second_conflict.engine.fleet_transit import dispatch_fleet
    dlg = FleetDialog(screen, state, star_idx, current.faction_id)
    result = dlg.run()
    if result:
        dispatch_fleet(
            state, star_idx, result['dest_star'],
            current.faction_id,
            warships     = result.get('warships',     0),
            transports   = result.get('transports',   0),
            troop_ships  = result.get('troop_ships',  0),
            stealthships = result.get('stealthships', 0),
            missiles     = result.get('missiles',     0),
        )


# ---------------------------------------------------------------------------
# Load / new game helpers
# ---------------------------------------------------------------------------

def _new_game(screen: pygame.Surface):
    from second_conflict.ui.dialogs.new_game_dlg import NewGameDialog
    from second_conflict.ui.game_new import build_new_game
    dlg = NewGameDialog(screen)
    result = dlg.run()
    if result is None:
        return None
    return build_new_game(result['options'], result['names'], result.get('is_ai'))

def _load_game(screen: pygame.Surface):
    try:
        from second_conflict.ui.dialogs.open_game_dlg import OpenGameDialog
        path = OpenGameDialog(screen).run()
        if path and os.path.isfile(path):
            return _load_file(path)
    except Exception as e:
        print(f"Load error: {e}")
    return None

def _load_file(path: str):
    from second_conflict.io.scenario_parser import parse_file
    return parse_file(path)


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

def _draw_no_game(screen: pygame.Surface):
    font_big  = pygame.font.SysFont('monospace', 28, bold=True)
    font_sub  = pygame.font.SysFont('monospace', 14)
    cx, cy = screen.get_width() // 2, screen.get_height() // 2
    title = font_big.render("Second Conflict", True, (180, 200, 255))
    sub1  = font_sub.render("File > New Game       — random galaxy", True, (160, 160, 180))
    sub2  = font_sub.render("File > Scenario...    — load SCWSCEN.*", True, (160, 160, 180))
    sub3  = font_sub.render("File > Open...        — load saved game", True, (160, 160, 180))
    screen.blit(title, (cx - title.get_width() // 2, cy - 60))
    screen.blit(sub1,  (cx - sub1.get_width()  // 2, cy - 10))
    screen.blit(sub2,  (cx - sub2.get_width()  // 2, cy + 12))
    screen.blit(sub3,  (cx - sub3.get_width()  // 2, cy + 34))

def _draw_game_over(screen: pygame.Surface, state):
    font = pygame.font.SysFont('monospace', 32, bold=True)
    msg  = (f"{state.players[state.winner_slot].name} wins!"
            if state.winner_slot is not None else "Game Over")
    surf = font.render(msg, True, (255, 220, 60))
    x = screen.get_width()  // 2 - surf.get_width()  // 2
    y = screen.get_height() // 2 - surf.get_height() // 2
    screen.blit(surf, (x, y))

def _simple_input_dialog(screen: pygame.Surface, prompt: str, default: str) -> str:
    font  = pygame.font.SysFont('monospace', 14)
    clock = pygame.time.Clock()
    text  = default
    w, h  = 500, 80
    rect  = pygame.Rect((screen.get_width()-w)//2, (screen.get_height()-h)//2, w, h)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return ""
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return text
                elif event.key == pygame.K_ESCAPE:
                    return ""
                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                elif event.unicode:
                    text += event.unicode
        pygame.draw.rect(screen, (20, 20, 35), rect)
        pygame.draw.rect(screen, (80, 80, 150), rect, 2)
        screen.blit(font.render(prompt,     True, (180, 180, 220)), (rect.x+10, rect.y+10))
        screen.blit(font.render(text + "|", True, (255, 255, 255)), (rect.x+10, rect.y+36))
        pygame.display.flip()
        clock.tick(30)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Second Conflict')
    parser.add_argument('--save', metavar='save', help='Load scenario/save from file')
    parser.add_argument('--dev-mode', action='store_true', help='Enable dev mode')
    parser.add_argument('--loglevel', default='INFO', help='Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL')
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.loglevel))
    main(save_file=args.save, debug=args.dev_mode)