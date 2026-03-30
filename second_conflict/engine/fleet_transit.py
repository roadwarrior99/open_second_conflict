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
from second_conflict.engine import combat


def process(state: GameState) -> list:
    """Run all sim_steps sub-steps for one game turn.

    Returns a list of (fleet, star) tuples for fleets that arrived this turn,
    so the caller can schedule combat checks and event messages.
    """
    arrivals = []
    sim_steps = state.options.sim_steps

    for sub_step in range(sim_steps):
        for fleet in state.fleets_in_transit:
            if fleet.owner_faction_id == FREE_SLOT:
                continue

            # Decrement turns counter
            fleet.turns_remaining -= 1

            # Missiles travel at 2× speed
            if fleet.fleet_type_char == FLEET_TYPE_MISSILE:
                fleet.turns_remaining -= 1

            # Scouts travel at 1.5×: extra -1 on odd sub-steps
            elif fleet.fleet_type_char == FLEET_TYPE_SCOUT and (sub_step % 2 != 0):
                fleet.turns_remaining -= 1

            # Deliver arrived fleets
            if fleet.turns_remaining < 1:
                star = state.stars[fleet.dest_star]
                arrivals.append((fleet, star))
                _deliver_fleet(fleet, star, state)

    return arrivals


def _deliver_fleet(fleet: FleetInTransit, star, state: GameState):
    """Merge an arriving fleet into the star's garrison and mark slot free."""
    from second_conflict.model.star import GarrisonEntry
    from second_conflict.model.constants import ShipType

    ship_map = [
        (ShipType.WARSHIP,     fleet.warships),
        (ShipType.STEALTHSHIP, fleet.stealthships),
        (ShipType.TRANSPORT,   fleet.transports),
        (ShipType.MISSILE,     fleet.missiles),
        (ShipType.SCOUT,       fleet.scouts),
        (ShipType.PROBE,       fleet.probes),
    ]

    for ship_type, count in ship_map:
        if count <= 0:
            continue
        # Merge into existing garrison entry if one exists for this faction+type
        existing = next(
            (g for g in star.garrison
             if g.owner_faction_id == fleet.owner_faction_id and g.ship_type == ship_type),
            None
        )
        if existing:
            existing.ship_count += count
        else:
            star.garrison.append(GarrisonEntry(
                owner_faction_id=fleet.owner_faction_id,
                ship_type=int(ship_type),
                ship_count=count,
            ))

    # If multiple factions are now present, flag the star for combat
    factions = {g.owner_faction_id for g in star.garrison if g.ship_count > 0}
    if len(factions) > 1 and star.star_id not in state.pending_combats:
        state.pending_combats.append(star.star_id)

    # Free the transit slot
    fleet.owner_faction_id = FREE_SLOT
    fleet.turns_remaining  = 0


def dispatch_fleet(state: GameState, src_star_idx: int, dest_star_idx: int,
                   owner_faction: int, ship_counts: dict,
                   fleet_type_char: str = 'C') -> bool:
    """Create a new in-transit fleet record.

    ship_counts: dict mapping ShipType -> count
    Returns True if a free slot was found and the fleet was dispatched.
    """
    from second_conflict.model.constants import ShipType
    from second_conflict.engine.distance import travel_time

    free_slot = next(
        (f for f in state.fleets_in_transit if f.owner_faction_id == FREE_SLOT),
        None
    )
    if free_slot is None:
        return False  # No free transit slots (max 400 active)

    src  = state.stars[src_star_idx]
    dest = state.stars[dest_star_idx]
    turns = travel_time(src, dest, state.options.sim_steps, state.options.map_param)

    free_slot.owner_faction_id = owner_faction
    free_slot.dest_star        = dest_star_idx
    free_slot.src_star         = src_star_idx
    free_slot.turns_remaining  = turns
    free_slot.fleet_type_char  = fleet_type_char
    free_slot.warships         = ship_counts.get(ShipType.WARSHIP,     0)
    free_slot.stealthships     = ship_counts.get(ShipType.STEALTHSHIP, 0)
    free_slot.transports       = ship_counts.get(ShipType.TRANSPORT,   0)
    free_slot.missiles         = ship_counts.get(ShipType.MISSILE,     0)
    free_slot.scouts           = ship_counts.get(ShipType.SCOUT,       0)
    free_slot.probes           = ship_counts.get(ShipType.PROBE,       0)
    free_slot.created_flag     = 1

    # Remove dispatched ships from source star garrison
    for ship_type, count in ship_counts.items():
        if count <= 0:
            continue
        for g in src.garrison:
            if g.owner_faction_id == owner_faction and g.ship_type == int(ship_type):
                g.ship_count = max(0, g.ship_count - count)

    return True