"""Tests for engine/production.py — ship production and troop recruitment."""
import pytest
from second_conflict.engine import production
from second_conflict.model.constants import EMPIRE_FACTION, PlanetType
from second_conflict.model.star import Planet
from second_conflict.util import rng as rng_module
from tests.conftest import make_star, make_state, make_player, make_options


def _state_one_star(planet_type='W', resource=3, base_prod=0, difficulty=1,
                    owner=1, warships=0, **star_kwargs):
    opts = make_options(difficulty=difficulty, empire_builds=False)
    star = make_star(star_id=0, owner=owner, planet_type=planet_type,
                     resource=resource, base_prod=base_prod,
                     warships=warships, **star_kwargs)
    player = make_player(faction_id=owner)
    return make_state(stars=[star], players=[player], options=opts)


class TestWarshipProduction:
    def test_produces_warships(self):
        state = _state_one_star(planet_type='W', resource=3, difficulty=1)
        production.process(state)
        # credits = (4-1)*3 + 0 = 9
        assert state.stars[0].warships == 9

    def test_higher_resource_more_warships(self):
        s1 = _state_one_star(resource=2, difficulty=1)
        s2 = _state_one_star(resource=5, difficulty=1)
        production.process(s1)
        production.process(s2)
        assert s1.stars[0].warships < s2.stars[0].warships

    def test_higher_difficulty_fewer_credits(self):
        s1 = _state_one_star(difficulty=0, resource=3)
        s2 = _state_one_star(difficulty=3, resource=3)
        production.process(s1)
        production.process(s2)
        assert s1.stars[0].warships > s2.stars[0].warships


class TestMissileProduction:
    def test_produces_missiles_half_credits(self):
        state = _state_one_star(planet_type='M', resource=4, difficulty=0)
        production.process(state)
        # credits = (4-0)*4 = 16; missiles = 16//2 = 8
        assert state.stars[0].missiles == 8


class TestTransportProduction:
    def test_produces_transports_third_credits(self):
        state = _state_one_star(planet_type='T', resource=3, difficulty=1)
        production.process(state)
        # credits = 3*3 = 9; transports = 9//3 = 3
        assert state.stars[0].transports == 3


class TestStealthProduction:
    def test_produces_stealthships(self):
        state = _state_one_star(planet_type='S', resource=3, difficulty=1)
        production.process(state)
        assert state.stars[0].stealthships == 3


class TestFactoryProduction:
    def test_upgrades_resource_when_credits_sufficient(self):
        state = _state_one_star(planet_type='F', resource=2, difficulty=0)
        # credits = 4*2 = 8; threshold = 3*2 = 6; 8 >= 6 → upgrade
        production.process(state)
        assert state.stars[0].resource == 3

    def test_no_upgrade_when_credits_insufficient(self):
        state = _state_one_star(planet_type='F', resource=10, difficulty=3)
        # credits = (4-3)*10 = 10; threshold = 3*10 = 30; 10 < 30 → no upgrade
        production.process(state)
        assert state.stars[0].resource == 10

    def test_produces_warships_at_base_rate(self):
        state = _state_one_star(planet_type='F', resource=2, difficulty=3)
        # credits = 1*2 = 2; threshold = 6; no upgrade; warships += resource-1 = 1
        production.process(state)
        assert state.stars[0].warships == 1


class TestDeadWorldTerraform:
    def test_increments_dead_counter(self):
        state = _state_one_star(planet_type='D', resource=1)
        production.process(state)
        assert state.stars[0].dead_counter == 1

    def test_converts_to_warship_after_10_turns(self):
        state = _state_one_star(planet_type='D', resource=1)
        state.stars[0].dead_counter = 9
        production.process(state)
        assert state.stars[0].planet_type == PlanetType.WARSHIP
        assert state.stars[0].dead_counter == 0

    def test_event_logged_on_conversion(self):
        state = _state_one_star(planet_type='D', resource=1)
        state.stars[0].dead_counter = 9
        production.process(state)
        assert any('terraformed' in e.text for e in state.event_log)


class TestOccupiedStarSkipped:
    def test_occupied_star_produces_nothing(self):
        planets = [Planet(owner_faction_id=2, morale=1, recruit=3, troops=50)]
        state = _state_one_star(planet_type='W', resource=5, planets=planets)
        production.process(state)
        assert state.stars[0].warships == 0


class TestEmpireStarSkipped:
    def test_empire_star_skipped_when_empire_builds_off(self):
        opts = make_options(empire_builds=False)
        star = make_star(star_id=0, owner=EMPIRE_FACTION, planet_type='W', resource=5)
        state = make_state(stars=[star], options=opts)
        production.process(state)
        assert star.warships == 0


class TestNoviceMode:
    def test_novice_gives_30000_credits(self):
        opts = make_options(novice_mode=True, difficulty=3)
        star = make_star(star_id=0, owner=1, planet_type='W', resource=1)
        player = make_player(faction_id=1)
        state = make_state(stars=[star], players=[player], options=opts)
        production.process(state)
        assert star.warships == 30000


class TestTroopRecruitment:
    def test_planets_gain_troops_each_turn(self):
        planets = [Planet(owner_faction_id=1, morale=1, recruit=5, troops=10)]
        state = _state_one_star(planets=planets)
        production.process(state)
        assert planets[0].troops == 15

    def test_troops_capped_at_10000(self):
        planets = [Planet(owner_faction_id=1, morale=1, recruit=100, troops=9990)]
        state = _state_one_star(planets=planets)
        production.process(state)
        assert planets[0].troops == 10000


class TestRecomputePlayerStats:
    def test_empire_size_equals_owned_stars(self):
        opts = make_options(difficulty=1)
        stars = [
            make_star(star_id=0, owner=1, planet_type='W', resource=3),
            make_star(star_id=1, x=20, y=0, owner=1, planet_type='W', resource=3),
            make_star(star_id=2, x=40, y=0, owner=2, planet_type='W', resource=3),
        ]
        players = [make_player(faction_id=1), make_player(slot=1, faction_id=2)]
        state = make_state(stars=stars, players=players, options=opts)
        production.process(state)
        assert players[0].empire_size == 2
        assert players[1].empire_size == 1

    def test_fleet_count_includes_all_ship_types(self):
        opts = make_options(difficulty=1)
        star = make_star(star_id=0, owner=1, planet_type='N', warships=5,
                         transports=2, stealthships=1)
        player = make_player(faction_id=1)
        state = make_state(stars=[star], players=[player], options=opts)
        production.process(state)
        assert player.fleet_count == 8