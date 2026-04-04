"""Revolt and loyalty processing.

Each turn, for every star:
  - If the star has occupied enemy planets, morale on those planets decays.
  - If a friendly planet's morale is low (stress from occupation), it may revolt.
  - Star-level loyalty tracks overall stability.
"""
from second_conflict.model.constants import EMPIRE_FACTION
from second_conflict.model.game_state import GameState
from second_conflict.util.rng import rand

logger = __import__('logging').getLogger(__name__)
REVOLT_THRESHOLD   = -10
LOYALTY_DECAY_RATE =  1
LOYALTY_RECOVER    =  1


def process(state: GameState):
    for star in state.stars:
        _process_star(star, state)


def _process_star(star, state: GameState):
    if star.owner_faction_id == EMPIRE_FACTION:
        return

    has_foreign = any(
        p.owner_faction_id != star.owner_faction_id
        for p in star.planets
    )

    if has_foreign:
        star.loyalty -= LOYALTY_DECAY_RATE
    else:
        if star.loyalty < 0:
            star.loyalty += LOYALTY_RECOVER

    if star.loyalty < 0 and star.loyalty > REVOLT_THRESHOLD:
        player = state.player_for_faction(star.owner_faction_id)
        pname = player.name if player else f"0x{star.owner_faction_id:02x}"
        state.add_event(
            'revolt', star.owner_faction_id,
            f"Discontent at star {star.star_id} ({pname})"
        )

    if star.loyalty <= REVOLT_THRESHOLD:
        _trigger_revolt(star, state)


def _trigger_revolt(star, state: GameState):
    """Star reverts to prior owner control; reset loyalty."""
    logger.debug(f"Star {star.star_id} reverts to prior owner control")
    old_owner = star.owner_faction_id
    player = state.player_for_faction(old_owner)
    pname = player.name if player else f"0x{old_owner:02x}"

    new_owner = 0
    #find owner of planets that isn't star owner.
    for planet in star.planets:
        if planet.owner_faction_id != old_owner:
            new_owner = planet.owner_faction_id
            logger.debug(f"Star {star.star_id} reverts to owner {new_owner}")
            break
    star.owner_faction_id = new_owner
    star.loyalty = rand(3)
    # Reset planet ownership to new_owner
    for p in star.planets:
        p.owner_faction_id = new_owner
        p.morale = 1

    state.add_event(
        'revolt', old_owner,
        f"Star {star.star_id} throws off {pname}'s control! Now held by {state.player_for_faction(new_owner).name}."
    )