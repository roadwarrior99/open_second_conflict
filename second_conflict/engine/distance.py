"""Fleet travel distance and time calculations."""
import math


def star_distance(star_a, star_b) -> float:
    """Euclidean distance between two stars in map coordinate units."""
    dx = star_a.x - star_b.x
    dy = star_a.y - star_b.y
    return math.sqrt(dx * dx + dy * dy)


def travel_time(star_a, star_b, sim_steps: int, map_param: int = 150) -> int:
    """Number of sim sub-steps for a normal fleet to travel from star_a to star_b.

    The original game's transit counter counts down at 1 per sub-step for
    normal fleets (Missiles count down 2x, Scouts 1.5x).

    We scale the Euclidean distance by a factor derived from map_param so that
    the 150-unit map produces transit times consistent with the original game.
    The exact formula is not decompiled, but empirically distances up to ~70
    map units correspond to ~6-8 turns at sim_steps=5.
    """
    dist = star_distance(star_a, star_b)
    # Scale factor: map_param controls the playfield size.
    # Approximate: each unit of distance ≈ 0.5 sim sub-steps at map_param=150.
    scale = map_param / 300.0
    raw_steps = dist * scale * sim_steps
    return max(1, int(round(raw_steps)))


def missile_travel_time(star_a, star_b, sim_steps: int, map_param: int = 150) -> int:
    """Missiles travel at 2× speed (turns_remaining decrements by 2 per step)."""
    return max(1, travel_time(star_a, star_b, sim_steps, map_param) // 2)


def scout_travel_time(star_a, star_b, sim_steps: int, map_param: int = 150) -> int:
    """Scouts travel at 1.5× speed (extra decrement on odd sub-steps)."""
    base = travel_time(star_a, star_b, sim_steps, map_param)
    return max(1, int(base * 2 / 3))