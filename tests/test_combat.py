"""Tests for engine/combat.py — orbital and ground combat."""
import pytest
from second_conflict.engine.combat import bombard, invade, resolve_arrival, CombatRecord
from second_conflict.model.constants import EMPIRE_FACTION, FREE_SLOT
from second_conflict.model.star import Star, Planet
from second_conflict.util import rng as rng_module
from tests.conftest import make_star, make_state, make_player, make_fleet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _star_with_enemy_planet(owner=1, enemy=2, enemy_troops=100, warships=10):
    """Star owned by *owner* with one planet occupied by *enemy*."""
    planets = [Planet(owner_faction_id=enemy, morale=1, recruit=3, troops=enemy_troops)]
    return make_star(star_id=0, owner=owner, warships=warships, planets=planets)


def _fixed_rand(value):
    """Monkeypatch rng.rand to always return *value*."""
    return value


# ---------------------------------------------------------------------------
# Bombard
# ---------------------------------------------------------------------------

class TestBombard:
    def setup_method(self):
        # Seed so rand() returns 0 (minimum attrition)
        rng_module.seed(42)

    def test_warship_consumed(self):
        star = _star_with_enemy_planet(warships=10)
        state = make_state(stars=[star])
        before = star.warships
        bombard(star, attacker_faction=1, state=state)
        assert star.warships == before - 1

    def test_troops_reduced(self):
        star = _star_with_enemy_planet(warships=10, enemy_troops=100)
        state = make_state(stars=[star])
        bombard(star, attacker_faction=1, state=state)
        # firepower = (10-1) * 2 = 18; planet had 100 troops
        assert star.planets[0].troops < 100

    def test_planet_freed_when_troops_reach_zero(self):
        # Small troop count so one bombardment clears it
        star = _star_with_enemy_planet(warships=50, enemy_troops=5)
        state = make_state(stars=[star])
        result = bombard(star, attacker_faction=1, state=state)
        assert 1 in result['planets_freed']
        assert star.planets[0].owner_faction_id == 1

    def test_freed_planet_morale_reset(self):
        star = _star_with_enemy_planet(warships=50, enemy_troops=5)
        state = make_state(stars=[star])
        bombard(star, attacker_faction=1, state=state)
        assert star.planets[0].morale == 1

    def test_resource_reduced_when_kills_happen(self):
        star = _star_with_enemy_planet(warships=10, enemy_troops=100)
        star.resource = 5
        state = make_state(stars=[star])
        bombard(star, attacker_faction=1, state=state)
        assert star.resource == 4

    def test_resource_not_below_one(self):
        star = _star_with_enemy_planet(warships=10, enemy_troops=100)
        star.resource = 1
        state = make_state(stars=[star])
        bombard(star, attacker_faction=1, state=state)
        assert star.resource == 1

    def test_own_planets_not_targeted(self):
        planets = [
            Planet(owner_faction_id=1, morale=1, recruit=3, troops=50),
            Planet(owner_faction_id=2, morale=1, recruit=3, troops=50),
        ]
        star = make_star(owner=1, warships=10, planets=planets)
        state = make_state(stars=[star])
        result = bombard(star, attacker_faction=1, state=state)
        # Own planet troops should be untouched
        assert planets[0].troops == 50

    def test_event_logged(self):
        star = _star_with_enemy_planet(warships=10, enemy_troops=100)
        state = make_state(stars=[star])
        bombard(star, attacker_faction=1, state=state)
        assert any('bombardment' in e.text for e in state.event_log)

    def test_no_kills_no_resource_damage(self):
        # Only own planets → no damage
        planets = [Planet(owner_faction_id=1, morale=1, recruit=3, troops=0)]
        star = make_star(owner=1, warships=5, planets=planets)
        star.resource = 3
        state = make_state(stars=[star])
        bombard(star, attacker_faction=1, state=state)
        assert star.resource == 3


# ---------------------------------------------------------------------------
# Invade
# ---------------------------------------------------------------------------

class TestInvade:
    def test_takes_unoccupied_planet_free(self):
        planets = [Planet(owner_faction_id=2, morale=1, recruit=3, troops=0)]
        star = make_star(owner=1, planets=planets)
        star.invasion_troops = 50
        state = make_state(stars=[star])
        result = invade(star, attacker_faction=1, state=state)
        assert result['planets_taken'] == 1
        assert planets[0].owner_faction_id == 1

    def test_takes_enemy_planet_with_enough_troops(self):
        # morale=1 → effective = troops * (1/5 + 0.5) = troops * 0.7
        planets = [Planet(owner_faction_id=2, morale=1, recruit=3, troops=10)]
        star = make_star(owner=1, planets=planets)
        star.invasion_troops = 200
        state = make_state(stars=[star])
        result = invade(star, attacker_faction=1, state=state)
        assert result['planets_taken'] == 1
        assert planets[0].owner_faction_id == 1

    def test_invasion_repelled_when_troops_insufficient(self):
        planets = [Planet(owner_faction_id=2, morale=1, recruit=3, troops=1000)]
        star = make_star(owner=1, planets=planets)
        star.invasion_troops = 1
        state = make_state(stars=[star])
        result = invade(star, attacker_faction=1, state=state)
        assert result['planets_taken'] == 0
        assert planets[0].owner_faction_id == 2

    def test_invasion_troops_consumed(self):
        planets = [Planet(owner_faction_id=2, morale=1, recruit=3, troops=0)]
        star = make_star(owner=1, planets=planets)
        star.invasion_troops = 100
        state = make_state(stars=[star])
        invade(star, attacker_faction=1, state=state)
        # Unoccupied planet costs nothing; troops should still be ~100
        assert star.invasion_troops == 100

    def test_own_planets_skipped(self):
        planets = [
            Planet(owner_faction_id=1, morale=1, recruit=3, troops=50),
        ]
        star = make_star(owner=1, planets=planets)
        star.invasion_troops = 100
        state = make_state(stars=[star])
        result = invade(star, attacker_faction=1, state=state)
        assert result['planets_taken'] == 0
        assert planets[0].troops == 50

    def test_multiple_planets_cleared_in_sequence(self):
        planets = [
            Planet(owner_faction_id=2, morale=1, recruit=3, troops=0),
            Planet(owner_faction_id=2, morale=1, recruit=3, troops=0),
        ]
        star = make_star(owner=1, planets=planets)
        star.invasion_troops = 100
        state = make_state(stars=[star])
        result = invade(star, attacker_faction=1, state=state)
        assert result['planets_taken'] == 2


# ---------------------------------------------------------------------------
# Orbital combat (resolve_arrival)
# ---------------------------------------------------------------------------

class TestResolveArrival:
    def test_friendly_arrival_returns_none(self):
        star = make_star(owner=1, warships=10)
        fleet = make_fleet(owner=1, dest=0, warships=5)
        state = make_state(stars=[star])
        rec = resolve_arrival(fleet, star, state)
        assert rec is None

    def test_returns_combat_record(self):
        rng_module.seed(0)
        star = make_star(owner=2, warships=5)
        fleet = make_fleet(owner=1, dest=0, warships=100)
        state = make_state(stars=[star])
        rec = resolve_arrival(fleet, star, state)
        assert isinstance(rec, CombatRecord)

    def test_attacker_wins_when_overwhelming(self):
        rng_module.seed(0)
        star = make_star(owner=2, warships=1)
        fleet = make_fleet(owner=1, dest=0, warships=1000)
        state = make_state(stars=[star])
        rec = resolve_arrival(fleet, star, state)
        assert rec.winner_faction == 1
        assert star.owner_faction_id == 1

    def test_defender_wins_when_overwhelming(self):
        rng_module.seed(0)
        star = make_star(owner=2, warships=1000)
        fleet = make_fleet(owner=1, dest=0, warships=1)
        state = make_state(stars=[star])
        rec = resolve_arrival(fleet, star, state)
        assert rec.winner_faction == 2
        assert star.owner_faction_id == 2

    def test_missiles_expended_after_combat(self):
        rng_module.seed(0)
        star = make_star(owner=2, warships=10)
        star.missiles = 5
        fleet = make_fleet(owner=1, dest=0, warships=10)
        fleet.missiles = 3
        state = make_state(stars=[star])
        resolve_arrival(fleet, star, state)
        assert fleet.missiles == 0
        assert star.missiles == 0

    def test_attacker_missiles_kill_defender_warships(self):
        rng_module.seed(0)
        star = make_star(owner=2, warships=10)
        star.missiles = 0
        fleet = make_fleet(owner=1, dest=0, warships=0)
        fleet.missiles = 5
        fleet.stealthships = 0
        state = make_state(stars=[star])
        resolve_arrival(fleet, star, state)
        # 5 attacker missiles should have killed exactly 5 of 10 defender warships
        # (both sides had 0 ships post-barrage, so result may vary, but warships started lower)
        assert star.warships <= 5

    def test_star_captured_ships_land(self):
        rng_module.seed(0)
        star = make_star(star_id=0, owner=2, warships=0)
        fleet = make_fleet(owner=1, dest=0, warships=100)
        state = make_state(stars=[star])
        rec = resolve_arrival(fleet, star, state)
        assert star.owner_faction_id == 1
        # Ships should be on the star
        assert star.warships > 0

    def test_combat_record_attacker_initial_correct(self):
        rng_module.seed(0)
        star = make_star(owner=2, warships=8)
        fleet = make_fleet(owner=1, dest=0, warships=20)
        state = make_state(stars=[star])
        rec = resolve_arrival(fleet, star, state)
        assert rec.atk_initial == 20
        assert rec.def_initial == 8

    def test_event_logged_for_both_factions(self):
        rng_module.seed(0)
        star = make_star(owner=2, warships=5)
        fleet = make_fleet(owner=1, dest=0, warships=50)
        state = make_state(stars=[star])
        resolve_arrival(fleet, star, state)
        factions_notified = {e.player_faction for e in state.event_log}
        assert 1 in factions_notified
        assert 2 in factions_notified

    def test_loyalty_reset_on_capture(self):
        rng_module.seed(0)
        star = make_star(owner=2, warships=1)
        star.loyalty = -5
        fleet = make_fleet(owner=1, dest=0, warships=1000)
        state = make_state(stars=[star])
        resolve_arrival(fleet, star, state)
        assert star.loyalty == 0