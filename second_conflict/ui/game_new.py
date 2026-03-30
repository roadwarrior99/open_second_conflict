"""New-game factory — builds a GameState from a NewGameDialog result.

Generates a random galaxy layout when no scenario file is specified.
"""
import math
import random
from second_conflict.model.constants import (
    EMPIRE_FACTION, PLAYER_COLOURS, PlanetType, ShipType, MAX_TRANSIT_FLEETS,
)
from second_conflict.model.game_state import GameState, GameOptions
from second_conflict.model.player import Player
from second_conflict.model.star import Star, GarrisonEntry
from second_conflict.model.fleet import FleetInTransit, EmpireOrder
from second_conflict.util.rng import rand as grnd

# Planet type distribution (excluding NEUTRAL placeholder)
_PLANET_POOL = (
    [PlanetType.WARSHIP]   * 8 +
    [PlanetType.MISSILE]   * 3 +
    [PlanetType.TRANSPORT] * 3 +
    [PlanetType.STEALTH]   * 2 +
    [PlanetType.FACTORY]   * 3 +
    [PlanetType.POPULATION]* 2 +
    [PlanetType.DEAD]      * 2 +
    [PlanetType.NEUTRAL]   * 3
)

_HOME_GARRISON_WARSHIPS = 20   # ships at each player's starting star
_EMPIRE_GARRISON        = 5    # ships at Empire stars at game start
_STAR_COUNT             = 26


def build_new_game(options: GameOptions, names: list[str],
                   is_ai: list[bool] | None = None) -> GameState:
    state = GameState(options=options)
    if is_ai is None:
        is_ai = [False] * len(names)

    # Build players
    for i, name in enumerate(names):
        faction_id = i + 1   # faction IDs 1-based
        p = Player(
            slot       = i,
            faction_id = faction_id,
            name       = name[:9],
            is_human   = not is_ai[i],
            is_active  = True,
            credits    = 100,
        )
        state.players.append(p)
    state.faction_ids = [p.faction_id for p in state.players]

    # Generate stars
    stars = _generate_stars(options)
    state.stars = stars

    # Assign home stars to players
    home_indices = _pick_home_stars(stars, options.num_players)
    for player, home_idx in zip(state.players, home_indices):
        star = stars[home_idx]
        star.owner_faction_id = player.faction_id
        star.planet_type = PlanetType.WARSHIP
        star.resource = 10
        # Starting garrison
        star.garrison.append(GarrisonEntry(
            owner_faction_id=player.faction_id,
            ship_type=int(ShipType.WARSHIP),
            ship_count=_HOME_GARRISON_WARSHIPS,
        ))

    # Remaining stars go to the Empire with a small garrison
    for i, star in enumerate(stars):
        if star.owner_faction_id != EMPIRE_FACTION:
            continue
        star.garrison.append(GarrisonEntry(
            owner_faction_id=EMPIRE_FACTION,
            ship_type=int(ShipType.WARSHIP),
            ship_count=_EMPIRE_GARRISON,
        ))

    # Initialise empty fleet transit slots
    for i in range(MAX_TRANSIT_FLEETS):
        state.fleets_in_transit.append(FleetInTransit(
            slot=i, owner_faction_id=0xFF, dest_star=0, turns_remaining=0
        ))

    # Initialise empire orders
    for i in range(_STAR_COUNT):
        state.empire_orders.append(EmpireOrder(star_index=i))

    # Compute initial player stats
    from second_conflict.engine.production import _recompute_player_stats
    _recompute_player_stats(state)

    return state


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _generate_stars(options: GameOptions) -> list[Star]:
    """Place _STAR_COUNT stars with random positions, avoiding overlap."""
    rng = random.Random()   # independent RNG for layout (not the game RNG)
    map_size = options.map_param   # 150 or 200

    # Scale to 0-255 byte range
    scale = 255 / map_size
    min_sep = 20   # minimum pixel distance between stars

    positions: list[tuple[int, int]] = []
    attempts = 0
    while len(positions) < _STAR_COUNT and attempts < 10000:
        cx = rng.randint(10, map_size - 10)
        cy = rng.randint(10, map_size - 10)
        too_close = any(
            math.hypot(cx - px, cy - py) < min_sep
            for px, py in positions
        )
        if not too_close:
            positions.append((cx, cy))
        attempts += 1

    # Pad if we couldn't place enough
    while len(positions) < _STAR_COUNT:
        positions.append((rng.randint(0, map_size), rng.randint(0, map_size)))

    planet_pool = _PLANET_POOL[:]
    rng.shuffle(planet_pool)

    stars = []
    for i, (cx, cy) in enumerate(positions[:_STAR_COUNT]):
        px = min(255, int(cx * scale))
        py = min(255, int(cy * scale))
        pt = planet_pool[i % len(planet_pool)]
        resource = rng.randint(3, 12)
        stars.append(Star(
            star_id          = i,
            x                = px,
            y                = py,
            owner_faction_id = EMPIRE_FACTION,
            planet_type      = pt,
            resource         = resource,
            base_prod        = resource,
        ))
    return stars


def _pick_home_stars(stars: list[Star], num_players: int) -> list[int]:
    """Spread home stars as evenly as possible around the map."""
    # Simple approach: spread by angle from the centre
    import math
    cx = sum(s.x for s in stars) / len(stars)
    cy = sum(s.y for s in stars) / len(stars)

    # Sort stars by angle
    by_angle = sorted(
        range(len(stars)),
        key=lambda i: math.atan2(stars[i].y - cy, stars[i].x - cx)
    )
    # Pick evenly spaced indices
    step = max(1, len(by_angle) // num_players)
    chosen = [by_angle[i * step] for i in range(num_players)]
    # Ensure unique (shouldn't be an issue with 26 stars and ≤10 players)
    seen: set[int] = set()
    result = []
    for idx in chosen:
        if idx not in seen:
            result.append(idx)
            seen.add(idx)
    # Fallback if somehow short
    for idx in range(len(stars)):
        if len(result) >= num_players:
            break
        if idx not in seen:
            result.append(idx)
            seen.add(idx)
    return result[:num_players]