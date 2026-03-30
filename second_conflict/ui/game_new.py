"""New-game factory — builds a GameState from a NewGameDialog result.

Generates a random galaxy layout when no scenario file is specified.
"""
import math
import random
from second_conflict.model.constants import (
    EMPIRE_FACTION, PlanetType, MAX_TRANSIT_FLEETS,
)
from second_conflict.model.game_state import GameState, GameOptions
from second_conflict.model.player import Player
from second_conflict.model.star import Star, Planet
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

_HOME_GARRISON_WARSHIPS    = 20  # warships at each player's starting star
_HOME_GARRISON_TRANSPORTS  = 5   # starting transport ships (needed to dispatch troops)
_EMPIRE_WARSHIPS           = 5   # warships at Empire stars at game start
_STAR_COUNT             = 26


def build_new_game(options: GameOptions, names: list[str],
                   is_ai: list[bool] | None = None) -> GameState:
    state = GameState(options=options)
    if is_ai is None:
        is_ai = [False] * len(names)

    # Build players
    for i, name in enumerate(names):
        faction_id = i + 1
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
        star.warships    = _HOME_GARRISON_WARSHIPS
        star.transports  = _HOME_GARRISON_TRANSPORTS
        # Set all planets to be owned by this player
        for p in star.planets:
            p.owner_faction_id = player.faction_id

    # Remaining stars go to the Empire with a small warship garrison
    for star in stars:
        if star.owner_faction_id != EMPIRE_FACTION:
            continue
        star.warships = _EMPIRE_WARSHIPS

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
    rng = random.Random()
    map_size = options.map_param

    scale = 255 / map_size
    min_sep = 20

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

    while len(positions) < _STAR_COUNT:
        positions.append((rng.randint(0, map_size), rng.randint(0, map_size)))

    planet_pool = _PLANET_POOL[:]
    rng.shuffle(planet_pool)

    stars = []
    for i, (cx, cy) in enumerate(positions[:_STAR_COUNT]):
        px = min(255, int(cx * scale))
        py = min(255, int(cy * scale))
        pt = planet_pool[i % len(planet_pool)]
        resource    = rng.randint(3, 12)
        num_planets = rng.randint(1, 7)
        base_prod   = num_planets

        # Create planet TLV entries owned by Empire initially
        planets = []
        for _ in range(num_planets):
            recruit = rng.randint(2, 5)
            troops  = rng.randint(5, 25)
            planets.append(Planet(
                owner_faction_id=EMPIRE_FACTION,
                morale=1,
                recruit=recruit,
                troops=troops,
            ))

        stars.append(Star(
            star_id          = i,
            x                = px,
            y                = py,
            owner_faction_id = EMPIRE_FACTION,
            planet_type      = pt,
            resource         = resource,
            base_prod        = base_prod,
            planets          = planets,
        ))
    return stars


def _pick_home_stars(stars: list[Star], num_players: int) -> list[int]:
    """Spread home stars as evenly as possible around the map."""
    cx = sum(s.x for s in stars) / len(stars)
    cy = sum(s.y for s in stars) / len(stars)

    by_angle = sorted(
        range(len(stars)),
        key=lambda i: math.atan2(stars[i].y - cy, stars[i].x - cx)
    )
    step = max(1, len(by_angle) // num_players)
    chosen = [by_angle[i * step] for i in range(num_players)]

    seen: set[int] = set()
    result = []
    for idx in chosen:
        if idx not in seen:
            result.append(idx)
            seen.add(idx)
    for idx in range(len(stars)):
        if len(result) >= num_players:
            break
        if idx not in seen:
            result.append(idx)
            seen.add(idx)
    return result[:num_players]