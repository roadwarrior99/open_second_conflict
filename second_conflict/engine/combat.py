"""Combat resolution.

Two-phase combat matching the original SCW.EXE:

  Phase 1 — Orbital battle: arriving warships fight the star's defending warships.
             Three attrition rounds (FUN_10b0_2f35). If the attacker eliminates
             the defender, the star changes hands.  Planets stay under their
             current owners — they must be cleared by manual ground combat.

  Phase 2 — Ground combat (manual, player-initiated):
             Bombard: orbital warships kill enemy planet troops each action.
             Invade:  invasion troops (star.invasion_troops) fight planet by planet.

fleet.troop_ships stores the actual troop count loaded at embarkation.
"""
from dataclasses import dataclass, field
from second_conflict.model.constants import EMPIRE_FACTION
from second_conflict.model.game_state import GameState
from second_conflict.model.star import Star
from second_conflict.util.rng import rand
import logging
from math import floor
logger = logging.getLogger(__name__)

_BOMBARD_RATE = 2   # troops killed per warship per bombardment action


def _faction_name(faction_id: int, state: GameState) -> str:
    """Return a human-readable name for a faction (player name or 'The Empire')."""
    if faction_id == EMPIRE_FACTION:
        return "The Empire"
    p = state.player_for_faction(faction_id)
    return p.name if p else f"Faction {faction_id:02x}"


@dataclass
class CombatRecord:
    """Per-battle data captured for the COMBATWNDPROC animation."""
    star_id: int
    star_x: int
    star_y: int
    attacker_faction: int
    defender_faction: int
    atk_initial: int
    def_initial: int
    rounds: list = field(default_factory=list)
    atk_final: int = 0
    def_final: int = 0
    winner_faction: int = -1
    planets_taken: int = 0


def resolve_all(state: GameState) -> list:
    """Resolve any stale pending combat.  Returns list of CombatRecord."""
    records = []
    for star_id in list(state.pending_combats):
        star = state.stars[star_id]
        rec = _resolve_star(star, state)
        if rec:
            records.append(rec)
    state.pending_combats.clear()
    return records


def resolve_arrival(fleet, star: Star, state: GameState):
    """Resolve orbital combat when an arriving fleet reaches a star.

    Troop ships are NOT auto-landed — the player must manually invoke
    bombard() and invade() from the Ground Combat dialog.
    Returns a CombatRecord, or None for friendly arrivals.
    """
    if fleet.owner_faction_id == star.owner_faction_id:
        return None

    return _orbital_combat(fleet, star, state)


def _resolve_star(star: Star, state: GameState):
    return None


# ---------------------------------------------------------------------------
# Orbital combat
# ---------------------------------------------------------------------------

def _orbital_combat(fleet, star: Star, state: GameState) -> CombatRecord:
    """Three-round attrition between arriving ships and star's ships.

    Phase 0 — Missile barrage (before attrition rounds):
      Attacker missiles kill defender ships 1-for-1 (warships first, then stealth).
      Defender missiles kill attacker ships 1-for-1 (warships first, then stealth).
      Both barrages resolve simultaneously; missiles are expended regardless.

    Phase 1 — Three attrition rounds with remaining warships/stealthships.
    Losses are distributed proportionally across each ship type.
    """
    # --- Phase 0: missile barrage ---
    atk_ws = fleet.warships
    atk_ss = fleet.stealthships
    def_ws = star.warships
    def_ss = star.stealthships

    atk_missiles = fleet.missiles
    def_missiles = star.missiles

    # Attacker missiles hit defender (warships first)
    if atk_missiles > 0:
        kill = min(atk_missiles, def_ws)
        def_ws -= kill
        remainder = atk_missiles - kill
        kill2 = min(remainder, def_ss)
        def_ss -= kill2

    # Defender missiles hit attacker (warships first) — simultaneous
    if def_missiles > 0:
        kill = min(def_missiles, atk_ws)
        atk_ws -= kill
        remainder = def_missiles - kill
        kill2 = min(remainder, atk_ss)
        atk_ss -= kill2

    # Missiles expended
    fleet.missiles = 0
    star.missiles  = 0

    # --- Phase 1: attrition rounds ---
    atk    = atk_ws + atk_ss
    def_   = def_ws + def_ss

    atk_init = atk
    def_init = def_

    rounds = []
    for _ in range(3):
        if atk <= 0 or def_ <= 0:
            break
        atk_hit = rand(5) + def_ // 3
        atk_hit = min(atk_hit, atk)
        def_hit = rand(5) + atk // 3
        def_hit = min(def_hit, def_)
        atk  = max(0, atk  - atk_hit)
        def_ = max(0, def_ - def_hit)
        rounds.append((atk_hit, def_hit))

    # Distribute surviving ships proportionally back to each type
    # (baseline is post-barrage counts, which may already differ from fleet/star originals)
    if atk_init > 0:
        r = atk / atk_init
        fleet.warships     = round(atk_ws * r)
        fleet.stealthships = round(atk_ss * r)
    else:
        fleet.warships = fleet.stealthships = 0

    if def_init > 0:
        r = def_ / def_init
        star.warships     = round(def_ws * r)
        star.stealthships = round(def_ss * r)
    else:
        star.warships = star.stealthships = 0
    # Note: star.missiles already zeroed in barrage phase above

    rec = CombatRecord(
        star_id=star.star_id,
        star_x=star.x,
        star_y=star.y,
        attacker_faction=fleet.owner_faction_id,
        defender_faction=star.owner_faction_id,
        atk_initial=atk_init,
        def_initial=def_init,
        rounds=rounds,
        atk_final=atk,
        def_final=def_,
    )

    atk_losses = atk_init - atk
    def_losses = def_init - def_
    state.add_event('combat', fleet.owner_faction_id,
                    f"Combat at star {star.star_id}: attacker lost {atk_losses}, "
                    f"defender lost {def_losses}")
    state.add_event('combat', star.owner_faction_id,
                    f"Combat at star {star.star_id}: attacker lost {atk_losses}, "
                    f"defender lost {def_losses}")

    if def_ == 0:
        # Defender eliminated — attacker takes the star
        old_owner = star.owner_faction_id
        star.owner_faction_id  = fleet.owner_faction_id
        star.loyalty = 0   # reset revolt timer on capture
        # Surviving attacker ships land at the star
        star.warships     += fleet.warships
        star.stealthships += fleet.stealthships
        fleet.warships = fleet.stealthships = 0
        rec.winner_faction = fleet.owner_faction_id
        state.add_event('combat', fleet.owner_faction_id,
                        f"Star {star.star_id} captured from {_faction_name(old_owner, state)}! "
                        f"Use Ground Combat to clear occupied planets.")
    elif atk == 0:
        # Attacker destroyed: defender holds
        rec.winner_faction = star.owner_faction_id
    else:
        # Both sides survived: attacker repelled — ships return to source star
        # (fleet.warships / stealthships left at post-combat values;
        #  _deliver_fleet will transfer them back to fleet.src_star)
        rec.winner_faction = star.owner_faction_id

    return rec


# ---------------------------------------------------------------------------
# Ground combat — called manually from GroundCombatDialog
# ---------------------------------------------------------------------------

def bombard(star: Star, attacker_faction: int, state: GameState) -> dict:
    """One bombardment round: orbital warships kill enemy planet troops.

    Returns a summary dict: {'firepower': int, 'troops_killed': int, 'planets_freed': list}
    """
    logger.debug(f"Bombard system {star.star_id} with {star.warships} warships")
    firepower = star.warships * _BOMBARD_RATE
    logger.debug(f"Firepower: {firepower}")
    attacker_remaining = firepower
    killed_total = 0
    freed = []

    collateral_damage_message = ""
    for pi, planet in enumerate(star.planets):
        if attacker_remaining <= 0:
            break
        if planet.owner_faction_id == attacker_faction:
            continue
        if planet.troops <= 0:
            continue
        logger.debug(f"Bombarding planet {pi + 1} with {attacker_remaining} attack power")
        killed = min(planet.troops, attacker_remaining)
        planet.troops -= killed
        attacker_remaining    -= killed
        killed_total += killed
        lost_ships = 0
        lost_ships += floor(((killed / 3) * rand(100)/100))
        star.warships -= lost_ships
        logger.debug(f"Planet {pi + 1}: killed {killed} troops, and we lost {lost_ships}"
                     f" warships with {attacker_remaining} warships remaining. ")

        state.add_event('combat', attacker_faction, f"While bombarding planet {pi + 1}, we lost {lost_ships} warships! ")
        if planet.troops == 0:
            planet.owner_faction_id = attacker_faction
            planet.morale = 1
            freed.append(pi + 1)

        # Bombardment damages the star's industrial output

        if killed_total > 0 and star.resource > 1:
            #Lets add a chance of a bombardment destroying production
            damage_factory_hit = rand( 100 )
            logger.debug(f"Bombardment factory hit roll: {damage_factory_hit}")
            if damage_factory_hit < 30:
                star.resource -= 1
                logger.debug("Factory destroyed! Resource reduced to 1.")
                collateral_damage_message = f"Star {star.star_id}: bombardment destroyed factory! Resource reduced to {star.resource}."
                state.add_event('combat', attacker_faction, collateral_damage_message)
            if damage_factory_hit <= 5:
                #distory the planet
                nuked_planet = pi
                star.blow_up_planet(nuked_planet)
                logger.debug(f"Planet {nuked_planet + 1} destroyed! Number of planet reduced to {star.num_planets}.")
                collateral_damage_message = f"Star {star.star_id}: bombardment destroyed planet {nuked_planet + 1}! Number of planet reduced to {star.num_planets}."
                state.add_event('combat', attacker_faction, collateral_damage_message)

    if freed:
        state.add_event('combat', attacker_faction,
                        f"Star {star.star_id}: bombardment freed planet(s) {freed}! "
                        f"Resource reduced to {star.resource}.")
    elif killed_total:
        state.add_event('combat', attacker_faction,
                        f"Star {star.star_id}: bombardment killed {killed_total} troops. "
                        f"Resource reduced to {star.resource}.")

    return {'firepower': firepower, 'troops_killed': killed_total, 'planets_freed': freed,
            'collateral_msg': collateral_damage_message}


def invade(star: Star, attacker_faction: int, state: GameState) -> dict:
    """Use star.invasion_troops to assault enemy-occupied planets.

    Attacks planets one by one until troops run out or all cleared.
    Returns a summary dict: {'troops_used': int, 'troops_remaining': int, 'planets_taken': int}
    """
    attacking = star.invasion_troops
    initial   = attacking
    taken     = 0

    for planet in star.planets:
        if attacking <= 0:
            break
        if planet.owner_faction_id == attacker_faction:
            continue
        if planet.troops <= 0:
            # Unoccupied — take it for free
            planet.owner_faction_id = attacker_faction
            taken += 1
            continue

        effective = max(1, int(planet.troops * (planet.morale / 5 + 0.5)))

        if attacking > effective:
            attacking -= effective
            old_owner = planet.owner_faction_id
            planet.owner_faction_id = attacker_faction
            planet.troops = 0
            planet.morale = 1
            taken += 1
            state.add_event('combat', attacker_faction,
                            f"Star {star.star_id} planet taken from {_faction_name(old_owner, state)}!")
        else:
            planet.troops = max(0, planet.troops - attacking // 2)
            state.add_event('combat', star.owner_faction_id,
                            f"Star {star.star_id}: invasion repelled! "
                            f"{planet.troops} troops remain.")
            attacking = 0

    star.invasion_troops = attacking
    return {
        'troops_used':      initial - attacking,
        'troops_remaining': attacking,
        'planets_taken':    taken,
    }