"""Empire AI — faithful translation of FUN_1088_0376 from SCW.EXE.

The Empire is the neutral adversary faction (faction_id = EMPIRE_FACTION = 0x1A).
It owns stars and produces ships, then each turn it:
  1. For each Empire star, pick the nearest non-Empire star as a target.
  2. If enough WarShips are stockpiled (>= some threshold), dispatch a fleet.
  3. The dispatch uses the pre-computed empire_orders records loaded from the
     save file; if those aren't set we fall back to a simple heuristic.

The original FUN_1088_0376 loops over the 26 EmpireOrder slots and calls
the fleet-dispatch routine for non-empty orders.  We replicate that here.
"""
from second_conflict.model.constants import EMPIRE_FACTION
from second_conflict.model.game_state import GameState
from second_conflict.engine.fleet_transit import dispatch_fleet
from second_conflict.engine.distance import star_distance
from second_conflict.util.rng import rand

# Minimum warships before the Empire bothers to attack
_ATTACK_THRESHOLD = 8


def process(state: GameState):
    """Execute all pending Empire orders, then generate new attacks.

    Each EmpireOrder record (one per star) describes a pending attack order
    loaded from the save file.  The order is active if order.active != 0.
    dest_faction tells us which player faction the Empire is targeting; we
    find the nearest star owned by that faction and dispatch toward it.
    """
    for order in state.empire_orders:
        if not order.is_active:
            continue
        if order.warships <= 0:
            continue
        # Find the star this order is anchored to
        star_idx = order.star_index
        if star_idx < 0 or star_idx >= len(state.stars):
            continue
        src_star = state.stars[star_idx]
        if src_star.owner_faction_id != EMPIRE_FACTION:
            continue
        avail = _available_warships(src_star, EMPIRE_FACTION)
        if avail < _ATTACK_THRESHOLD:
            continue
        # Find nearest star of target faction (or any non-Empire star)
        target_idx = _find_target_for_faction(star_idx, order.dest_faction, state)
        if target_idx is None:
            continue
        dispatch_fleet(
            state, star_idx, target_idx, EMPIRE_FACTION,
            warships=min(order.warships, avail // 2),
        )

    # Generate new opportunistic attacks for Empire stars with no pending order
    _generate_opportunistic_attacks(state)


def _generate_opportunistic_attacks(state: GameState):
    """Simple heuristic: each Empire star attacks the nearest non-Empire star
    if it has enough ships and no fleet is already en route from it."""
    empire_stars = [i for i, s in enumerate(state.stars)
                    if s.owner_faction_id == EMPIRE_FACTION]

    for src_idx in empire_stars:
        src = state.stars[src_idx]
        warships = _available_warships(src, EMPIRE_FACTION)
        if warships < _ATTACK_THRESHOLD:
            continue

        # Check if a fleet is already in transit from this star
        already_dispatched = any(
            f.owner_faction_id == EMPIRE_FACTION and f.src_star == src_idx
            for f in state.fleets_in_transit
        )
        if already_dispatched:
            continue

        target_idx = _pick_target(src_idx, state)
        if target_idx is None:
            continue

        # Attack with half the available warships (keep some for defence)
        send = max(1, warships // 2 + rand(warships // 4 + 1))
        dispatch_fleet(
            state, src_idx, target_idx, EMPIRE_FACTION,
            warships=send,
        )


def _pick_target(src_idx: int, state: GameState) -> int | None:
    """Return the index of the nearest star not owned by the Empire."""
    src = state.stars[src_idx]
    best_idx = None
    best_dist = float('inf')
    for i, s in enumerate(state.stars):
        if s.owner_faction_id == EMPIRE_FACTION:
            continue
        d = star_distance(src, s)
        if d < best_dist:
            best_dist = d
            best_idx = i
    return best_idx


def _find_target_for_faction(src_idx: int, target_faction: int,
                              state: GameState) -> int | None:
    """Return the nearest star owned by target_faction (or any non-Empire star)."""
    src = state.stars[src_idx]
    best_idx = None
    best_dist = float('inf')
    for i, s in enumerate(state.stars):
        if s.owner_faction_id == EMPIRE_FACTION:
            continue
        if target_faction and s.owner_faction_id != target_faction:
            continue
        d = star_distance(src, s)
        if d < best_dist:
            best_dist = d
            best_idx = i
    # Fallback: any non-Empire star
    if best_idx is None:
        return _pick_target(src_idx, state)
    return best_idx


def _available_warships(star, faction_id: int) -> int:
    # Ships belong to the star owner; Empire only calls this for its own stars
    return star.warships if star.owner_faction_id == faction_id else 0