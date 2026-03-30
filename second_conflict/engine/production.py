"""End-of-turn production processing.

Faithful translation of FUN_1088_13d8 from SCW.EXE.

For each star the engine:
  1. Computes this turn's production credits.
  2. Converts credits into ships according to planet_type.
  3. Handles Factory ('F') and Population ('P') special cases.
  4. Updates player aggregate stats.
"""
from second_conflict.model.constants import (
    EMPIRE_FACTION, PlanetType, ShipType,
)
from second_conflict.model.game_state import GameState
from second_conflict.model.star import GarrisonEntry
from second_conflict.util.rng import rand


# Production formula: credits_this_turn = (4 - difficulty) * resource + base_prod
# (from PRODLIMITDLG and FUN_1088_13d8 in Ghidra decompilation)

def process(state: GameState):
    difficulty = state.options.difficulty
    novice     = state.options.novice_mode
    emp_builds = state.options.empire_builds

    for star in state.stars:
        # Determine if this star produces
        is_player_owned = star.owner_faction_id != EMPIRE_FACTION
        if not (is_player_owned or emp_builds):
            continue

        # Production credits for this turn
        if novice or star.owner_faction_id == EMPIRE_FACTION:
            credits = 30000   # unlimited in novice / Empire mode
        else:
            credits = max(0, (4 - difficulty) * star.resource + star.base_prod)

        _produce(star, credits, state)

    _recompute_player_stats(state)


def _produce(star, credits: int, state: GameState):
    pt = star.planet_type

    if pt == PlanetType.WARSHIP:
        # Each credit → 1 WarShip
        count = credits
        star.prod_warships += count
        _add_garrison(star, star.owner_faction_id, ShipType.WARSHIP, count, state)

    elif pt == PlanetType.MISSILE:
        # Every 2 credits → 1 Missile
        count = credits // 2
        _add_garrison(star, star.owner_faction_id, ShipType.MISSILE, count, state)

    elif pt == PlanetType.TRANSPORT:
        # Every 3 credits → 1 TranSport
        count = credits // 3
        star.prod_transports += count
        _add_garrison(star, star.owner_faction_id, ShipType.TRANSPORT, count, state)

    elif pt == PlanetType.STEALTH:
        # Every 3 credits → 1 StealthShip (used for scout missions)
        count = credits // 3
        star.prod_stealth += count
        _add_garrison(star, star.owner_faction_id, ShipType.STEALTHSHIP, count, state)

    elif pt == PlanetType.FACTORY:
        # Factory: accumulates resource multiplier when enough credits
        # When credits >= 3 * resource, increase resource by 1.
        # Also produces WarShips from resource base.
        threshold = max(1, 3 * star.resource)
        if credits >= threshold:
            star.resource += 1
            state.add_event(
                'reinforce', star.owner_faction_id,
                f"Factory at star {star.star_id} upgraded (resource now {star.resource})"
            )
        # Factories also produce warships at base rate
        base_count = max(0, star.resource - 1)
        _add_garrison(star, star.owner_faction_id, ShipType.WARSHIP, base_count, state)

    elif pt == PlanetType.POPULATION:
        # Population world: grows population counter; each pop unit adds warships
        # Population grows when credits >= pop_count * 10, max pop = 10
        if star.prod_population < 10 and credits >= star.prod_population * 10:
            star.prod_population += 1
            state.add_event(
                'reinforce', star.owner_faction_id,
                f"Population at star {star.star_id} grows to {star.prod_population}"
            )
        # Population produces warships proportional to pop
        count = star.prod_population
        _add_garrison(star, star.owner_faction_id, ShipType.WARSHIP, count, state)

    elif pt == PlanetType.DEAD:
        # Dead world: transitions to Warship world once conditions are met.
        # Condition: owner has held star for enough turns (prod_warships acts as counter)
        star.prod_warships += 1
        if star.prod_warships >= 10:
            star.planet_type = PlanetType.WARSHIP
            star.prod_warships = 0
            state.add_event(
                'reinforce', star.owner_faction_id,
                f"Dead star {star.star_id} has been terraformed into a WarShip world"
            )

    elif pt == PlanetType.NEUTRAL:
        pass   # No production


def _add_garrison(star, owner_faction: int, ship_type: ShipType, count: int, state):
    if count <= 0:
        return
    existing = next(
        (g for g in star.garrison
         if g.owner_faction_id == owner_faction and g.ship_type == int(ship_type)),
        None
    )
    if existing:
        existing.ship_count += count
    else:
        star.garrison.append(GarrisonEntry(
            owner_faction_id=owner_faction,
            ship_type=int(ship_type),
            ship_count=count,
        ))


def _recompute_player_stats(state: GameState):
    """Recompute empire_size, production, fleet_count, strength from live star data."""
    from second_conflict.model.constants import PLAYER_COLOURS

    # Reset all active players
    for p in state.players:
        if p.is_active:
            p.empire_size  = 0
            p.production   = 0
            p.fleet_count  = 0
            p.strength     = 0

    for star in state.stars:
        owner = state.player_for_faction(star.owner_faction_id)
        if owner is None or not owner.is_active:
            continue
        owner.empire_size  += 1
        owner.production   += max(0, (4 - state.options.difficulty) * star.resource + star.base_prod)
        for g in star.garrison:
            if g.owner_faction_id == owner.faction_id:
                owner.fleet_count += g.ship_count
                owner.strength    += g.ship_count   # simplified strength metric