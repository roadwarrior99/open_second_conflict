"""Full turn sequence orchestrator.

Turn phases (derived from FUN_1088_xxxx call order in SCW.EXE):
  1. Increment turn counter
  2. Process fleet-in-transit movement (all sim_steps sub-steps)
  3. Resolve all pending combat (legacy; most combat now fires on arrival)
  4. Process production at all stars (ships + troop recruitment)
  5. Process revolt / loyalty changes
  6. Fire random events (if enabled)
  7. Bombardment of occupied planets by orbital warships
  8. Run Empire AI orders
  9. Run computer player AI
 10. Check victory conditions
"""
from second_conflict.model.game_state import GameState
from second_conflict.model.constants import EMPIRE_FACTION
from second_conflict.engine import fleet_transit, combat, production, revolt, events


def run_turn(state: GameState):
    """Execute a full end-of-turn processing cycle.

    Called once when the human player (or the last human player in hotseat)
    clicks 'End Turn'.  Mutates state in-place.

    Returns a list of EventEntry objects generated this turn so the UI can
    display them.
    """
    log_start = len(state.event_log)

    state.turn += 1

    # Phase 1: move fleets, deliver arrivals (combat fires on arrival)
    combat_records = fleet_transit.process(state)

    # Phase 2: resolve any stale pending combat (normally empty)
    combat_records += combat.resolve_all(state)

    # Phase 3: production at all stars (ships + troop recruitment)
    production.process(state)

    # Phase 4: revolt / loyalty
    revolt.process(state)

    # Phase 5: random events
    if state.options.random_events:
        events.process(state)

    # Phase 6: Empire AI
    _run_empire_ai(state)

    # Phase 7: computer player AI (non-human active players)
    _run_computer_players(state)

    # Phase 9: victory check
    _check_victory(state)

    return state.event_log[log_start:], combat_records


def _run_empire_ai(state: GameState):
    """Dispatch Empire orders for this turn (FUN_1088_0376 equivalent)."""
    try:
        from second_conflict.ai.empire_ai import process as empire_process
        empire_process(state)
    except ImportError:
        pass


def _run_computer_players(state: GameState):
    """Run AI for all non-human active players."""
    try:
        from second_conflict.ai.player_ai import process as ai_process
        for player in state.active_players():
            if not player.is_human:
                ai_process(player, state)
    except ImportError:
        pass


def _check_victory(state: GameState):
    """Determine if the game is over.

    Victory conditions (from SCOREVIEWDLG):
      - Only one active player remains → that player wins.
      - All human players eliminated → Empire wins (score screen).
    """
    if state.game_over:
        return

    active = state.active_players()
    if not active:
        state.game_over = True
        state.winner_slot = None
        return

    # Eliminate players who have no stars and no fleets
    for player in list(active):
        owns_star = any(s.owner_faction_id == player.faction_id for s in state.stars)
        has_fleet = any(
            f.owner_faction_id == player.faction_id
            for f in state.fleets_in_transit
        )
        if not owns_star and not has_fleet:
            player.is_active = False
            state.add_event(
                'event', player.faction_id,
                f"{player.name} has been eliminated!"
            )

    active = state.active_players()
    if len(active) == 1:
        state.game_over = True
        state.winner_slot = state.players.index(active[0])
        state.add_event(
            'event', active[0].faction_id,
            f"{active[0].name} has conquered the galaxy!"
        )
    elif len(active) == 0:
        state.game_over = True
        state.winner_slot = None
    elif not state.human_players():
        state.game_over = True
        state.winner_slot = None
        state.add_event('event', 0, "All human players have been eliminated.")