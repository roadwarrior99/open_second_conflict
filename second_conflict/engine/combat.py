"""Combat resolution.

Faithful translation of FUN_10b0_2f35 from SCW.EXE.

The original does three attrition rounds between the garrison owner and an
attacking faction.  Each round:
  - Attacker losses ≈ rand(5) + defender_warships / 3
  - Defender losses ≈ rand(5) + garrison_capacity / 20

After combat the winning faction takes ownership if the defender is eliminated.
"""
from second_conflict.model.constants import EMPIRE_FACTION, ShipType
from second_conflict.model.star import Star, GarrisonEntry
from second_conflict.model.game_state import GameState
from second_conflict.util.rng import rand


def resolve_all(state: GameState):
    """Resolve all pending combat stars."""
    for star_id in list(state.pending_combats):
        star = state.stars[star_id]
        _resolve_star(star, state)
    state.pending_combats.clear()


def _resolve_star(star: Star, state: GameState):
    """Run one round of inter-faction combat at a star.

    We pit every non-owner faction against the current owner sequentially.
    The owner is the faction with the highest total warship count.
    """
    # Identify defender (highest warship count) and attackers
    faction_warships = {}
    for g in star.garrison:
        if g.ship_type == ShipType.WARSHIP and g.ship_count > 0:
            faction_warships[g.owner_faction_id] = (
                faction_warships.get(g.owner_faction_id, 0) + g.ship_count
            )

    if not faction_warships:
        return

    defender_faction = max(faction_warships, key=faction_warships.get)
    attackers = [f for f in faction_warships if f != defender_faction]

    for attacker_faction in attackers:
        result = _attrition(star, defender_faction, attacker_faction, state)
        _log_combat(star, defender_faction, attacker_faction, result, state)

    # Transfer ownership if defender eliminated
    _update_owner(star, state)


def _attrition(star: Star, defender_faction: int, attacker_faction: int,
               state: GameState) -> dict:
    """Three-round attrition combat matching FUN_10b0_2f35.

    Returns a dict with total losses on each side.
    """
    def_warships = sum(
        g.ship_count for g in star.garrison
        if g.owner_faction_id == defender_faction and g.ship_type == ShipType.WARSHIP
    )
    atk_warships = sum(
        g.ship_count for g in star.garrison
        if g.owner_faction_id == attacker_faction and g.ship_type == ShipType.WARSHIP
    )

    def_losses = 0
    atk_losses = 0

    for _ in range(3):   # three attrition rounds
        if atk_warships < 2 or def_warships < 2:
            break

        # Attacker casualties from defender fire
        atk_hit = rand(5) + def_warships // 3
        atk_hit = min(atk_hit, atk_warships - 1)

        # Defender casualties from attacker fire
        def_hit = rand(5) + atk_warships // 3
        def_hit = min(def_hit, def_warships - 1)

        atk_warships = max(0, atk_warships - atk_hit)
        def_warships = max(0, def_warships - def_hit)
        atk_losses  += atk_hit
        def_losses  += def_hit

    # Apply losses to garrison entries
    _apply_losses(star, attacker_faction, ShipType.WARSHIP, atk_losses)
    _apply_losses(star, defender_faction, ShipType.WARSHIP, def_losses)

    return {'attacker_losses': atk_losses, 'defender_losses': def_losses}


def _apply_losses(star: Star, faction: int, ship_type: int, losses: int):
    for g in star.garrison:
        if g.owner_faction_id == faction and g.ship_type == int(ship_type):
            g.ship_count = max(0, g.ship_count - losses)


def _update_owner(star: Star, state: GameState):
    """Set star owner to the faction with the highest remaining warship count."""
    faction_totals = {}
    for g in star.garrison:
        if g.ship_count > 0:
            faction_totals[g.owner_faction_id] = (
                faction_totals.get(g.owner_faction_id, 0) + g.ship_count
            )

    # Remove zero-ship entries
    star.garrison = [g for g in star.garrison if g.ship_count > 0]

    if not faction_totals:
        star.owner_faction_id = EMPIRE_FACTION
        return

    new_owner = max(faction_totals, key=faction_totals.get)
    if new_owner != star.owner_faction_id:
        old_owner = star.owner_faction_id
        star.owner_faction_id = new_owner
        state.add_event(
            'combat',
            new_owner,
            f"Star {star.star_id} ({star.x},{star.y}) captured from 0x{old_owner:02x}",
        )


def _log_combat(star: Star, defender: int, attacker: int, result: dict,
                state: GameState):
    text = (f"Combat at star {star.star_id}: "
            f"attacker 0x{attacker:02x} lost {result['attacker_losses']}, "
            f"defender 0x{defender:02x} lost {result['defender_losses']}")
    state.add_event('combat', attacker, text)
    state.add_event('combat', defender, text)