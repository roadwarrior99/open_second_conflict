"""Revolt and loyalty processing.

Faithful translation of FUN_1088_1c9e from SCW.EXE.

Each turn, for every star with player-owned garrison entries:
  - Loyalty decays if a foreign faction is present.
  - When loyalty < -3, the planet revolts: ownership changes.
  - Discontent messages are logged when loyalty approaches the threshold.
"""
from second_conflict.model.constants import EMPIRE_FACTION
from second_conflict.model.game_state import GameState
from second_conflict.util.rng import rand


REVOLT_THRESHOLD = -3
LOYALTY_DECAY_RATE = 1     # loyalty decrements by this each turn under stress
LOYALTY_RECOVER_RATE = 1   # loyalty recovers by this each turn when stable


def process(state: GameState):
    for star in state.stars:
        _process_star(star, state)


def _process_star(star, state: GameState):
    factions = {g.owner_faction_id for g in star.garrison if g.ship_count > 0}
    if not factions:
        return

    # Only process if there is at least one non-Empire player faction
    player_factions = [f for f in factions if f != EMPIRE_FACTION]
    if not player_factions:
        return

    for g in star.garrison:
        if g.owner_faction_id == EMPIRE_FACTION:
            continue
        if g.ship_count <= 0:
            continue

        # Multiple factions at same star causes loyalty stress
        foreign_present = any(
            f != g.owner_faction_id for f in factions if f != EMPIRE_FACTION
        )
        if foreign_present:
            g.loyalty -= LOYALTY_DECAY_RATE
        else:
            # Loyal star: loyalty recovers toward 0
            if g.loyalty < 0:
                g.loyalty += LOYALTY_RECOVER_RATE

        # Check discontent threshold
        if g.loyalty < 0 and g.loyalty > REVOLT_THRESHOLD:
            player = state.player_for_faction(g.owner_faction_id)
            pname = player.name if player else f"0x{g.owner_faction_id:02x}"
            state.add_event(
                'revolt', g.owner_faction_id,
                f"Discontent builds at star {star.star_id} ({pname} garrison)"
            )

        # Revolt fires when loyalty drops too low
        if g.loyalty <= REVOLT_THRESHOLD:
            _trigger_revolt(star, g.owner_faction_id, state)
            return   # star ownership changed, stop processing this star


def _trigger_revolt(star, revolting_faction: int, state: GameState):
    """Transfer star ownership and log the revolt event."""
    old_owner = star.owner_faction_id
    player = state.player_for_faction(old_owner)
    pname = player.name if player else f"0x{old_owner:02x}"

    # Star reverts to Empire (or to the opposing faction if one is present)
    factions = {g.owner_faction_id for g in star.garrison
                if g.ship_count > 0 and g.owner_faction_id != revolting_faction}
    if factions:
        new_owner = max(factions, key=lambda f: sum(
            g.ship_count for g in star.garrison
            if g.owner_faction_id == f
        ))
    else:
        new_owner = EMPIRE_FACTION

    star.owner_faction_id = new_owner

    # Reset loyalty with a small random boost
    for g in star.garrison:
        if g.owner_faction_id == revolting_faction:
            g.loyalty = rand(3)

    new_name = "The Empire" if new_owner == EMPIRE_FACTION else (
        state.player_for_faction(new_owner).name
        if state.player_for_faction(new_owner) else f"0x{new_owner:02x}"
    )
    state.add_event(
        'revolt', revolting_faction,
        f"Star {star.star_id} throws off {pname}'s garrison!  Now held by {new_name}."
    )
    state.add_event(
        'revolt', new_owner,
        f"Star {star.star_id} revolts from {pname} — now under {new_name}."
    )