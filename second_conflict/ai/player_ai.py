"""Computer player AI.

Approximates the non-human player logic from SCW.EXE.

Strategy (inferred from decompilation patterns):
  1. Assess threats: for each owned star, check if any adjacent enemy star
     has more WarShips than the garrison.
  2. Reinforce threatened stars first by pulling ships from safe stars.
  3. Attack the weakest reachable enemy star if we have an overwhelming force.
  4. Expand into unowned (Empire) stars when no threats exist.

This is a heuristic AI — the original used a scored priority table per star
that we approximate here.
"""
from second_conflict.model.constants import EMPIRE_FACTION, ShipType
from second_conflict.model.game_state import GameState
from second_conflict.engine.fleet_transit import dispatch_fleet
from second_conflict.engine.distance import star_distance
from second_conflict.util.rng import rand

_ATTACK_RATIO   = 2.0   # attack only if we have 2× defender's warships
_MIN_GARRISON   = 3     # always leave at least this many ships defending


def process(player, state: GameState):
    """Run one turn of AI for a single computer player."""
    my_stars = state.stars_owned_by(player.faction_id)
    if not my_stars:
        return

    for i, src in enumerate(state.stars):
        if src.owner_faction_id != player.faction_id:
            continue
        src_idx = state.stars.index(src)

        available = _available_warships(src, player.faction_id)
        if available <= _MIN_GARRISON:
            continue

        # Already has a fleet in transit from this star?
        if _has_outgoing_fleet(src_idx, player.faction_id, state):
            continue

        target_idx = _pick_target(src_idx, player.faction_id, state)
        if target_idx is None:
            continue

        target = state.stars[target_idx]
        target_ships = _total_warships_at(target)

        send = available - _MIN_GARRISON
        if target.owner_faction_id == EMPIRE_FACTION:
            # Expand into empty/Empire territory more aggressively
            if send >= 1:
                dispatch_fleet(
                    state, src_idx, target_idx, player.faction_id,
                    {ShipType.WARSHIP: send},
                )
        else:
            # Only attack a player star if we have a numerical advantage
            if send >= target_ships * _ATTACK_RATIO and send >= 4:
                dispatch_fleet(
                    state, src_idx, target_idx, player.faction_id,
                    {ShipType.WARSHIP: send},
                )


def _pick_target(src_idx: int, faction_id: int, state: GameState) -> int | None:
    """Prioritise: (1) nearest enemy player star, (2) nearest Empire star."""
    src = state.stars[src_idx]
    best_player_idx = None
    best_player_dist = float('inf')
    best_empire_idx = None
    best_empire_dist = float('inf')

    for i, s in enumerate(state.stars):
        if s.owner_faction_id == faction_id:
            continue
        d = star_distance(src, s)
        if s.owner_faction_id != EMPIRE_FACTION:
            if d < best_player_dist:
                best_player_dist = d
                best_player_idx = i
        else:
            if d < best_empire_dist:
                best_empire_dist = d
                best_empire_idx = i

    # Prefer to attack players; fall back to Empire expansion
    return best_player_idx if best_player_idx is not None else best_empire_idx


def _available_warships(star, faction_id: int) -> int:
    return sum(
        g.ship_count for g in star.garrison
        if g.owner_faction_id == faction_id and g.ship_type == ShipType.WARSHIP
    )


def _total_warships_at(star) -> int:
    return sum(
        g.ship_count for g in star.garrison
        if g.ship_type == ShipType.WARSHIP
    )


def _has_outgoing_fleet(src_idx: int, faction_id: int, state: GameState) -> bool:
    return any(
        f.owner_faction_id == faction_id and f.src_star == src_idx
        for f in state.fleets_in_transit
    )