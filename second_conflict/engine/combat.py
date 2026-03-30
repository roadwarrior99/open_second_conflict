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

_BOMBARD_RATE = 2   # troops killed per warship per bombardment action


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
    """Three-round attrition between arriving warships and star's warships."""
    atk = fleet.warships
    def_ = star.warships
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
        atk = max(0, atk - atk_hit)
        def_ = max(0, def_ - def_hit)
        rounds.append((atk_hit, def_hit))

    fleet.warships = atk
    star.warships  = def_

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

    if def_ == 0 and atk > 0:
        old_owner = star.owner_faction_id
        star.owner_faction_id = fleet.owner_faction_id
        star.loyalty = 0   # reset revolt timer on capture
        # Surviving attacker warships land at the star
        star.warships += fleet.warships
        fleet.warships = 0
        rec.winner_faction = fleet.owner_faction_id
        state.add_event('combat', fleet.owner_faction_id,
                        f"Star {star.star_id} captured from 0x{old_owner:02x}! "
                        f"Use Ground Combat to clear occupied planets.")
    elif atk == 0:
        # Attacker destroyed: defender holds
        rec.winner_faction = star.owner_faction_id
    else:
        # Both sides survived: attacker repelled, remaining ships lost
        fleet.warships = 0
        rec.winner_faction = star.owner_faction_id

    return rec


# ---------------------------------------------------------------------------
# Ground combat — called manually from GroundCombatDialog
# ---------------------------------------------------------------------------

def bombard(star: Star, attacker_faction: int, state: GameState) -> dict:
    """One bombardment round: orbital warships kill enemy planet troops.

    Returns a summary dict: {'firepower': int, 'troops_killed': int, 'planets_freed': list}
    """
    firepower = star.warships * _BOMBARD_RATE
    remaining = firepower
    killed_total = 0
    freed = []

    for pi, planet in enumerate(star.planets):
        if remaining <= 0:
            break
        if planet.owner_faction_id == attacker_faction:
            continue
        if planet.troops <= 0:
            continue
        killed = min(planet.troops, remaining)
        planet.troops -= killed
        remaining    -= killed
        killed_total += killed
        if planet.troops == 0:
            planet.owner_faction_id = attacker_faction
            planet.morale = 1
            freed.append(pi + 1)

    if freed:
        state.add_event('combat', attacker_faction,
                        f"Star {star.star_id}: bombardment freed planet(s) {freed}!")
    elif killed_total:
        state.add_event('combat', attacker_faction,
                        f"Star {star.star_id}: bombardment killed {killed_total} troops.")

    return {'firepower': firepower, 'troops_killed': killed_total, 'planets_freed': freed}


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
                            f"Star {star.star_id} planet taken from 0x{old_owner:02x}!")
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