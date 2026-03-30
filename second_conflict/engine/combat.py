"""Combat resolution.

Faithful translation of FUN_10b0_2f35 from SCW.EXE.

The original does three attrition rounds between the garrison owner and an
attacking faction.  Each round:
  - Attacker losses ≈ rand(5) + defender_warships / 3
  - Defender losses ≈ rand(5) + garrison_capacity / 20

After combat the winning faction takes ownership if the defender is eliminated.
"""
from dataclasses import dataclass
from second_conflict.model.constants import EMPIRE_FACTION, ShipType
from second_conflict.model.star import Star, GarrisonEntry
from second_conflict.model.game_state import GameState
from second_conflict.util.rng import rand


@dataclass
class CombatRecord:
    """Per-battle data captured for the COMBATWNDPROC animation."""
    star_id: int
    star_x: int
    star_y: int
    attacker_faction: int
    defender_faction: int
    atk_initial: int          # attacker warships before combat
    def_initial: int          # defender warships before combat
    rounds: list              # list of (atk_hit, def_hit) tuples — 0-3 entries
    atk_final: int            # attacker warships after combat
    def_final: int            # defender warships after combat
    winner_faction: int = -1  # set by _resolve_star after _update_owner


def resolve_all(state: GameState) -> list:
    """Resolve all pending combat stars.  Returns list of CombatRecord."""
    records = []
    for star_id in list(state.pending_combats):
        star = state.stars[star_id]
        records.extend(_resolve_star(star, state))
    state.pending_combats.clear()
    return records


def _resolve_star(star: Star, state: GameState) -> list:
    """Run one round of inter-faction combat at a star.

    We pit every non-owner faction against the current owner sequentially.
    The owner is the faction with the highest total warship count.
    Returns list of CombatRecord (one per attacker).
    """
    # Identify defender (highest warship count) and attackers
    faction_warships = {}
    for g in star.garrison:
        if g.ship_type == ShipType.WARSHIP and g.ship_count > 0:
            faction_warships[g.owner_faction_id] = (
                faction_warships.get(g.owner_faction_id, 0) + g.ship_count
            )

    if not faction_warships:
        return []

    # The star's current owner is always the defender; everyone else is an attacker.
    defender_faction = star.owner_faction_id
    attackers = [f for f in faction_warships if f != defender_faction]

    if not attackers:
        return []   # only the owner's ships present, no combat

    # If the defender has no warships they can't fight back — skip attrition and
    # let _update_owner hand the star to whoever arrived.
    if defender_faction not in faction_warships:
        _update_owner(star, state)
        return []

    records = []
    for attacker_faction in attackers:
        rec = _attrition(star, defender_faction, attacker_faction, state)
        _log_combat(star, defender_faction, attacker_faction, rec, state)
        records.append(rec)

    # Transfer ownership if defender eliminated
    _update_owner(star, state)

    # Fill in winner now that ownership is settled
    for rec in records:
        rec.winner_faction = star.owner_faction_id

    return records


def _attrition(star: Star, defender_faction: int, attacker_faction: int,
               state: GameState) -> 'CombatRecord':
    """Three-round attrition combat matching FUN_10b0_2f35.

    Returns a CombatRecord with per-round data (winner_faction filled later).
    """
    def_warships = sum(
        g.ship_count for g in star.garrison
        if g.owner_faction_id == defender_faction and g.ship_type == ShipType.WARSHIP
    )
    atk_warships = sum(
        g.ship_count for g in star.garrison
        if g.owner_faction_id == attacker_faction and g.ship_type == ShipType.WARSHIP
    )

    atk_initial = atk_warships
    def_initial = def_warships
    rounds = []

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
        rounds.append((atk_hit, def_hit))

    atk_losses = sum(r[0] for r in rounds)
    def_losses = sum(r[1] for r in rounds)

    # Apply losses to garrison entries
    _apply_losses(star, attacker_faction, ShipType.WARSHIP, atk_losses)
    _apply_losses(star, defender_faction, ShipType.WARSHIP, def_losses)

    return CombatRecord(
        star_id=star.star_id,
        star_x=star.x,
        star_y=star.y,
        attacker_faction=attacker_faction,
        defender_faction=defender_faction,
        atk_initial=atk_initial,
        def_initial=def_initial,
        rounds=rounds,
        atk_final=atk_warships,
        def_final=def_warships,
    )


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


def _log_combat(star: Star, defender: int, attacker: int, rec: 'CombatRecord',
                state: GameState):
    atk_losses = rec.atk_initial - rec.atk_final
    def_losses = rec.def_initial - rec.def_final
    text = (f"Combat at star {star.star_id}: "
            f"attacker 0x{attacker:02x} lost {atk_losses}, "
            f"defender 0x{defender:02x} lost {def_losses}")
    state.add_event('combat', attacker, text)
    state.add_event('combat', defender, text)