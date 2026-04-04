"""Fleet-in-transit processing.

Faithful translation of FUN_1088_0619 from SCW.EXE.

Each game turn runs sim_steps sub-steps.  In each sub-step every active
transit slot has its turns_remaining decremented:
  - Normal fleet:  -1
  - Missile ('M'): -2  (extra -1 every sub-step)
  - Scout   ('S'): -1 on even sub-steps, -2 on odd sub-steps (≈1.5×)
When turns_remaining < 1 the fleet is delivered to its destination star.
"""
from second_conflict.model.constants import FREE_SLOT, FLEET_TYPE_MISSILE, FLEET_TYPE_SCOUT
from second_conflict.model.fleet import FleetInTransit
from second_conflict.model.game_state import GameState
logger = __import__('logging').getLogger(__name__)

def process(state: GameState) -> list:
    """Run all sim_steps sub-steps for one game turn.

    Returns a list of CombatRecord objects for any battles that fired on arrival.
    """
    combat_records = []
    sim_steps = state.options.sim_steps

    for sub_step in range(sim_steps):
        for fleet in state.fleets_in_transit:
            if fleet.owner_faction_id == FREE_SLOT:
                continue

            fleet.turns_remaining -= 1

            if fleet.fleet_type_char == FLEET_TYPE_MISSILE:
                fleet.turns_remaining -= 1
            elif fleet.fleet_type_char == FLEET_TYPE_SCOUT and (sub_step % 2 != 0):
                fleet.turns_remaining -= 1

            if fleet.turns_remaining < 1:
                star = state.stars[fleet.dest_star]
                rec = _deliver_fleet(fleet, star, state)
                if rec is not None:
                    combat_records.append(rec)

    return combat_records


def _deliver_fleet(fleet: FleetInTransit, star, state: GameState):
    """Deliver an arriving fleet to its destination star.

    Returns a CombatRecord if battle occurred, else None.
    """
    from second_conflict.engine import combat

    is_friendly = (fleet.owner_faction_id == star.owner_faction_id)
    rec = None

    if is_friendly:
        # Reinforce: add ships directly to star
        star.warships     += fleet.warships
        star.transports   += fleet.transports
        star.stealthships += fleet.stealthships
        star.missiles     += fleet.missiles
        # Troops arrive in orbit — held as invasion_troops for manual ground combat.
        # If no planets are occupied they reinforce the first friendly planet instead.
        if fleet.troop_ships > 0:
            if star.troops > 0:
                star.invasion_troops += fleet.troop_ships
            else:
                deposited = False
                for planet in star.planets:
                    if planet.owner_faction_id == fleet.owner_faction_id:
                        planet.troops += fleet.troop_ships
                        deposited = True
                        break
                if not deposited:
                    star.invasion_troops += fleet.troop_ships
    else:
        # Enemy arrival: orbital combat only.  Troops held in orbit for
        # manual invasion — the player uses the Ground Combat dialog.
        rec = combat.resolve_arrival(fleet, star, state)
        # Ships only land if the attacker now controls the star
        if star.owner_faction_id == fleet.owner_faction_id:
            star.transports += fleet.transports
            star.missiles   += fleet.missiles
            if fleet.troop_ships > 0:
                star.invasion_troops += fleet.troop_ships
        # Repelled: send surviving ships back to the source star over time
        elif fleet.warships > 0 or fleet.stealthships > 0:
            from second_conflict.engine.distance import travel_time
            src  = state.stars[fleet.src_star]
            dest = state.stars[fleet.dest_star]
            fleet.src_star, fleet.dest_star = fleet.dest_star, fleet.src_star
            fleet.turns_remaining = travel_time(
                dest, src, state.options.sim_steps, state.options.map_param
            )
            fleet.missiles    = 0   # already expended
            return rec

    # Free the transit slot (friendly arrival, attacker destroyed, or captured)
    fleet.owner_faction_id = FREE_SLOT
    fleet.turns_remaining  = 0
    fleet.warships     = 0
    fleet.transports   = 0
    fleet.troop_ships  = 0
    fleet.stealthships = 0
    fleet.missiles     = 0
    fleet.scouts       = 0
    fleet.probes       = 0
    return rec


def recall_fleet(state: GameState, fleet: FleetInTransit) -> bool:
    """Reverse a fleet's direction mid-transit.

    Swaps src/dest and sets turns_remaining to the turns already spent,
    so the fleet returns home in the same time it has been travelling.
    Returns False if the fleet cannot be recalled (missiles, already arrived).
    """
    from second_conflict.engine.distance import travel_time

    if fleet.fleet_type_char == FLEET_TYPE_MISSILE:
        return False   # missiles cannot be recalled

    src  = state.stars[fleet.src_star]
    dest = state.stars[fleet.dest_star]
    total = travel_time(src, dest, state.options.sim_steps, state.options.map_param)
    turns_spent = total - fleet.turns_remaining

    fleet.src_star, fleet.dest_star = fleet.dest_star, fleet.src_star
    fleet.turns_remaining = max(1, turns_spent)
    return True


def dispatch_fleet(state: GameState, src_star_idx: int, dest_star_idx: int,
                   owner_faction: int, warships: int = 0,
                   transports: int = 0, troop_ships: int = 0,
                   stealthships: int = 0, missiles: int = 0,
                   scouts: int = 0, probes: int = 0,
                   fleet_type_char: str = 'C') -> bool:
    """Create a new in-transit fleet record.

    ``transports``  — number of TranSport ships consumed from src.transports.
    ``troop_ships`` — troops loaded onto those transports (stored in fleet for
                      combat; may differ from transports × 10 if fewer troops
                      were available at embarkation).

    Deducts ships from the source star.  Returns True if a free slot was found
    and the fleet was dispatched.
    """
    from second_conflict.engine.distance import travel_time

    free_slot = next(
        (f for f in state.fleets_in_transit if f.owner_faction_id == FREE_SLOT),
        None
    )
    if free_slot is None:
        return False

    src_star  = state.stars[src_star_idx]
    dest_star = state.stars[dest_star_idx]
    turns = travel_time(src_star, dest_star, state.options.sim_steps, state.options.map_param)
    logger.debug(f"Fleet from star {src_star.star_id} owner {src_star.owner_name(state.players)}"
                 f" to {dest_star.star_id} owner {dest_star.owner_name(state.players)} in {turns} turns")
    # Clamp to available
    warships     = max(0, min(warships,     src_star.warships))
    transports   = max(0, min(transports,   src_star.transports))
    stealthships = max(0, min(stealthships, src_star.stealthships))
    missiles     = max(0, min(missiles,     src_star.missiles))
    troop_ships  = max(0, troop_ships)   # already deducted from planets by caller
    logger.debug(f"Fleet: {warships} warships, {transports} transports, {stealthships} stealth"
                 f", {missiles} missiles, {troop_ships} troops")
    # Deduct ships from source star
    src_star.warships     -= warships
    src_star.transports   -= transports
    src_star.stealthships -= stealthships
    src_star.missiles     -= missiles

    free_slot.owner_faction_id = owner_faction
    free_slot.dest_star        = dest_star_idx
    free_slot.src_star         = src_star_idx
    free_slot.turns_remaining  = turns
    free_slot.fleet_type_char  = fleet_type_char
    free_slot.warships         = warships
    free_slot.transports       = transports
    free_slot.troop_ships      = troop_ships
    free_slot.stealthships     = stealthships
    free_slot.missiles         = missiles
    free_slot.scouts           = scouts
    free_slot.probes           = probes
    free_slot.created_flag     = 1

    return True