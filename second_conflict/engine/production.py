"""End-of-turn production processing.

Faithful translation of FUN_1088_13d8 from SCW.EXE.

For each star the engine:
  1. Computes this turn's production credits.
  2. Converts credits into ships (warships/transports/stealthships/missiles)
     stored at fixed offsets in the star record.
  3. For Population ('P') worlds: grows new planets (TLV entries) each with
     a starting troop count and recruit rate.
  4. Recruits troops on existing planets (each planet gains planet.recruit
     troops per turn, capped at a maximum).
"""
from second_conflict.model.constants import EMPIRE_FACTION, PlanetType
from second_conflict.model.game_state import GameState
from second_conflict.model.star import Planet
from second_conflict.util.rng import rand

# Maximum troops that can be on any single planet
_MAX_PLANET_TROOPS = 10000

# Production formula: credits_this_turn = (4 - difficulty) * resource + base_prod
# (from PRODLIMITDLG and FUN_1088_13d8 in Ghidra decompilation)


def process(state: GameState):
    difficulty = state.options.difficulty
    novice     = state.options.novice_mode
    emp_builds = state.options.empire_builds

    for star in state.stars:
        is_player_owned = star.owner_faction_id != EMPIRE_FACTION
        if not (is_player_owned or emp_builds):
            continue

        # Occupied planets don't produce — enemy troops must be cleared first
        if star.troops > 0:
            continue

        # Production credits for this turn.
        # Novice mode gives player stars unlimited credits to help new players.
        # Empire always uses the normal formula.
        if novice and is_player_owned:
            credits = 30000
        else:
            credits = max(0, (4 - difficulty) * star.resource + star.base_prod)

        _produce(star, credits, state)

        # Troop recruitment: each planet gains troops each turn
        _recruit_troops(star)

    _recompute_player_stats(state)


def _produce(star, credits: int, state: GameState):
    pt = star.planet_type

    if pt == PlanetType.WARSHIP:
        star.warships += credits

    elif pt == PlanetType.MISSILE:
        star.missiles += credits // 2

    elif pt == PlanetType.TRANSPORT:
        star.transports += credits // 3

    elif pt == PlanetType.STEALTH:
        star.stealthships += credits // 3

    elif pt == PlanetType.FACTORY:
        # Factory upgrades resource when credits >= 3 * resource
        threshold = max(1, 3 * star.resource)
        if credits >= threshold:
            star.resource += 1
            state.add_event(
                'reinforce', star.owner_faction_id,
                f"Factory at star {star.star_id} upgraded (resource now {star.resource})"
            )
        # Factories also produce warships at base rate
        star.warships += max(0, star.resource - 1)

    elif pt == PlanetType.POPULATION:
        # Population world: grows new planets (TLV entries) each seeded with troops.
        # Each growth event costs pop_count * 10 credits, up to 10 planets max.
        pop_count = star.num_planets
        while pop_count < 10 and credits >= pop_count * 10:
            credits -= pop_count * 10
            pop_count += 1
            # New planet owned by this star's owner
            recruit_rate = max(1, star.base_prod + 2)
            starting_troops = rand(20) + 20   # 20–39 troops at founding
            new_planet = Planet(
                owner_faction_id=star.owner_faction_id,
                morale=max(1, star.base_prod),
                recruit=recruit_rate,
                troops=starting_troops,
            )
            star.planets.append(new_planet)
            state.add_event(
                'reinforce', star.owner_faction_id,
                f"Population at star {star.star_id} grows to {pop_count} planets "
                f"({starting_troops} troops, recruit {recruit_rate}/turn)"
            )

    elif pt == PlanetType.DEAD:
        # Dead world: count turns held, convert after 10
        star.dead_counter += 1
        if star.dead_counter >= 10:
            star.planet_type = PlanetType.WARSHIP
            star.dead_counter = 0
            state.add_event(
                'reinforce', star.owner_faction_id,
                f"Dead star {star.star_id} terraformed into a WarShip world"
            )

    elif pt == PlanetType.NEUTRAL:
        pass


def _recruit_troops(star):
    """Each planet recruits troops each turn up to the maximum."""
    for planet in star.planets:
        if planet.troops < _MAX_PLANET_TROOPS:
            planet.troops = min(_MAX_PLANET_TROOPS, planet.troops + planet.recruit)


def _recompute_player_stats(state: GameState):
    """Recompute empire_size, production, fleet_count, strength from live star data."""
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
        owner.empire_size += 1
        owner.production  += max(0, (4 - state.options.difficulty) * star.resource + star.base_prod)
        total_ships = star.warships + star.transports + star.stealthships + star.missiles
        owner.fleet_count += total_ships
        owner.strength    += total_ships