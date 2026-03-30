"""Second Conflict — pygame recreation entry point.

Usage:
    python main.py [path/to/scenario.scn]

If a scenario path is given it is loaded; otherwise a New Game dialog is shown.
"""
import sys
import os
import pygame

SCREEN_W  = 1100
SCREEN_H  = 720
MAP_W     = 800
PANEL_W   = SCREEN_W - MAP_W
FPS       = 30
TITLE     = "Second Conflict"

BG_COLOUR = (8, 8, 16)


def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock  = pygame.time.Clock()

    state = _load_or_new_game(screen)
    if state is None:
        pygame.quit()
        return

    from second_conflict.ui.map_view  import MapView
    from second_conflict.ui.side_panel import SidePanel

    map_rect   = pygame.Rect(0,     0, MAP_W,   SCREEN_H)
    panel_rect = pygame.Rect(MAP_W, 0, PANEL_W, SCREEN_H)

    map_view  = MapView(map_rect, state)
    side_panel = SidePanel(panel_rect, state)

    def on_end_turn():
        _do_end_turn(screen, state, map_view, side_panel)

    def on_star_click(star_idx: int, second_click: bool):
        if second_click:
            _open_fleet_dialog(screen, state, star_idx)

    map_view.set_star_click_callback(on_star_click)
    side_panel.set_end_turn_callback(on_end_turn)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Menu shortcuts
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F1:
                    _show_stats(screen, state)
                if event.key == pygame.K_n and (event.mod & pygame.KMOD_CTRL):
                    new_state = _new_game(screen)
                    if new_state:
                        state = new_state
                        map_view.set_state(state)
                        side_panel.set_state(state)
                if event.key == pygame.K_o and (event.mod & pygame.KMOD_CTRL):
                    loaded = _load_game(screen)
                    if loaded:
                        state = loaded
                        map_view.set_state(state)
                        side_panel.set_state(state)

            map_view.handle_event(event)
            side_panel.handle_event(event)

        screen.fill(BG_COLOUR)
        map_view.draw(screen)
        side_panel.draw(screen, map_view.selected_star)

        # Game-over overlay
        if state.game_over:
            _draw_game_over(screen, state)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


# ---------------------------------------------------------------------------
# Turn processing
# ---------------------------------------------------------------------------

def _do_end_turn(screen, state, map_view, side_panel):
    from second_conflict.engine.turn_runner import run_turn
    from second_conflict.ui.dialogs.events_dlg import EventsDialog

    new_events = run_turn(state)

    # Show events dialog for the current (now previous) player
    current = state.current_player()
    if current:
        faction = current.faction_id
    else:
        faction = 0
    player_events = [e for e in new_events
                     if e.player_faction == faction or e.category == 'combat']
    if player_events:
        dlg = EventsDialog(screen, player_events)
        dlg.run()

    # Advance to next human player in hotseat
    active_humans = state.human_players()
    if active_humans:
        current_idx = state.current_player_slot % len(active_humans)
        state.current_player_slot = (current_idx + 1) % len(active_humans)

    map_view.select_star(None)


# ---------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------

def _load_or_new_game(screen: pygame.Surface):
    """Show splash/menu and return a GameState or None."""
    # If scenario path given on command line, load it
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        return _load_file(sys.argv[1])
    # Otherwise show the new-game dialog immediately
    return _new_game(screen)


def _new_game(screen: pygame.Surface):
    from second_conflict.ui.dialogs.new_game_dlg import NewGameDialog
    from second_conflict.ui.game_new import build_new_game
    dlg = NewGameDialog(screen)
    result = dlg.run()
    if result is None:
        return None
    return build_new_game(result['options'], result['names'])


def _load_game(screen: pygame.Surface):
    """Simple file-path prompt (Ctrl+O).  Uses a basic text-input dialog."""
    try:
        path = _simple_input_dialog(screen, "Open scenario file:", "")
        if path and os.path.isfile(path):
            return _load_file(path)
    except Exception as e:
        print(f"Load error: {e}")
    return None


def _load_file(path: str):
    from second_conflict.io.scenario_parser import parse_file
    return parse_file(path)


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
            state,
            star_idx,
            result['dest_star'],
            current.faction_id,
            result['ship_counts'],
        )


def _show_stats(screen, state):
    from second_conflict.ui.dialogs.stats_dlg import StatsDialog
    dlg = StatsDialog(screen, state)
    dlg.run()


def _draw_game_over(screen: pygame.Surface, state):
    font = pygame.font.SysFont('monospace', 32, bold=True)
    if state.winner_slot is not None:
        w = state.players[state.winner_slot]
        msg = f"{w.name} wins!"
    else:
        msg = "Game Over"
    surf = font.render(msg, True, (255, 220, 60))
    x = screen.get_width()  // 2 - surf.get_width()  // 2
    y = screen.get_height() // 2 - surf.get_height() // 2
    screen.blit(surf, (x, y))


def _simple_input_dialog(screen: pygame.Surface, prompt: str, default: str) -> str:
    """Minimal blocking text-input box for file paths."""
    font  = pygame.font.SysFont('monospace', 14)
    clock = pygame.time.Clock()
    text  = default
    w, h  = 500, 80
    rect  = pygame.Rect((screen.get_width()-w)//2, (screen.get_height()-h)//2, w, h)
    running = True
    while running:
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
                else:
                    text += event.unicode
        pygame.draw.rect(screen, (20, 20, 35), rect)
        pygame.draw.rect(screen, (80, 80, 150), rect, 2)
        p_surf = font.render(prompt, True, (180, 180, 220))
        t_surf = font.render(text + "|", True, (255, 255, 255))
        screen.blit(p_surf, (rect.x + 10, rect.y + 10))
        screen.blit(t_surf, (rect.x + 10, rect.y + 36))
        pygame.display.flip()
        clock.tick(30)
    return ""


if __name__ == '__main__':
    main()