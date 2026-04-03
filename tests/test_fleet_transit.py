"""Tests for engine/fleet_transit.py — fleet movement, dispatch, recall, delivery."""
import pytest
from second_conflict.engine.fleet_transit import (
    dispatch_fleet, recall_fleet, process as transit_process,
)
from second_conflict.model.constants import FREE_SLOT, FLEET_TYPE_MISSILE, FLEET_TYPE_SCOUT
from second_conflict.model.fleet import FleetInTransit
from second_conflict.util import rng as rng_module
from tests.conftest import make_star, make_state, make_player, make_fleet, make_free_fleet, make_options


def _two_star_state(src_warships=50, dest_warships=0, dest_owner=1,
                    distance=20, fleet_slots=10):
    opts = make_options(sim_steps=5, map_param=150)
    src  = make_star(star_id=0, x=0,        y=0, owner=1, warships=src_warships)
    dest = make_star(star_id=1, x=distance, y=0, owner=dest_owner,
                     warships=dest_warships)
    fleets = [make_free_fleet(i) for i in range(fleet_slots)]
    player = make_player(faction_id=1)
    return make_state(stars=[src, dest], players=[player], fleets=fleets, options=opts)


# ---------------------------------------------------------------------------
# dispatch_fleet
# ---------------------------------------------------------------------------

class TestDispatchFleet:
    def test_returns_true_when_slot_available(self):
        state = _two_star_state()
        ok = dispatch_fleet(state, src_star_idx=0, dest_star_idx=1,
                            owner_faction=1, warships=10)
        assert ok is True

    def test_returns_false_when_no_free_slot(self):
        opts = make_options()
        src  = make_star(star_id=0, x=0, y=0, owner=1, warships=50)
        dest = make_star(star_id=1, x=20, y=0, owner=1)
        # All fleet slots occupied
        fleets = [make_fleet(i, owner=1, dest=1, src=0, turns=5) for i in range(5)]
        state = make_state(stars=[src, dest], fleets=fleets, options=opts)
        ok = dispatch_fleet(state, 0, 1, owner_faction=1, warships=5)
        assert ok is False

    def test_deducts_ships_from_source(self):
        state = _two_star_state(src_warships=50)
        dispatch_fleet(state, 0, 1, owner_faction=1, warships=20)
        assert state.stars[0].warships == 30

    def test_clamped_to_available_ships(self):
        state = _two_star_state(src_warships=5)
        dispatch_fleet(state, 0, 1, owner_faction=1, warships=100)
        assert state.stars[0].warships == 0

    def test_fleet_slot_populated(self):
        state = _two_star_state()
        dispatch_fleet(state, 0, 1, owner_faction=1, warships=10)
        active = [f for f in state.fleets_in_transit if not f.is_free]
        assert len(active) == 1
        assert active[0].warships == 10
        assert active[0].dest_star == 1
        assert active[0].owner_faction_id == 1

    def test_fleet_type_stored(self):
        state = _two_star_state()
        dispatch_fleet(state, 0, 1, owner_faction=1, warships=5,
                       fleet_type_char='M')
        active = [f for f in state.fleets_in_transit if not f.is_free]
        assert active[0].fleet_type_char == 'M'

    def test_turns_remaining_positive(self):
        state = _two_star_state(distance=30)
        dispatch_fleet(state, 0, 1, owner_faction=1, warships=5)
        active = [f for f in state.fleets_in_transit if not f.is_free]
        assert active[0].turns_remaining >= 1


# ---------------------------------------------------------------------------
# recall_fleet
# ---------------------------------------------------------------------------

class TestRecallFleet:
    def test_recall_swaps_src_and_dest(self):
        state = _two_star_state()
        dispatch_fleet(state, 0, 1, owner_faction=1, warships=10)
        fleet = next(f for f in state.fleets_in_transit if not f.is_free)
        recall_fleet(state, fleet)
        assert fleet.dest_star == 0
        assert fleet.src_star == 1

    def test_recall_sets_positive_turns(self):
        state = _two_star_state(distance=40)
        dispatch_fleet(state, 0, 1, owner_faction=1, warships=10)
        fleet = next(f for f in state.fleets_in_transit if not f.is_free)
        # Simulate some travel
        fleet.turns_remaining -= 10
        recall_fleet(state, fleet)
        assert fleet.turns_remaining >= 1

    def test_missile_cannot_be_recalled(self):
        state = _two_star_state()
        dispatch_fleet(state, 0, 1, owner_faction=1, missiles=5,
                       fleet_type_char=FLEET_TYPE_MISSILE)
        fleet = next(f for f in state.fleets_in_transit if not f.is_free)
        result = recall_fleet(state, fleet)
        assert result is False


# ---------------------------------------------------------------------------
# Fleet transit process — movement and arrival
# ---------------------------------------------------------------------------

class TestTransitProcess:
    def setup_method(self):
        rng_module.seed(0)

    def test_turns_remaining_decrements(self):
        state = _two_star_state()
        dispatch_fleet(state, 0, 1, owner_faction=1, warships=5)
        fleet = next(f for f in state.fleets_in_transit if not f.is_free)
        before = fleet.turns_remaining
        transit_process(state)
        # After one call fleet has moved one full turn (sim_steps sub-steps)
        assert fleet.turns_remaining < before or fleet.is_free

    def test_friendly_fleet_merges_on_arrival(self):
        opts = make_options(sim_steps=5, map_param=150)
        src  = make_star(star_id=0, x=0, y=0, owner=1, warships=50)
        dest = make_star(star_id=1, x=1, y=0, owner=1, warships=0)
        fleets = [make_free_fleet(i) for i in range(10)]
        state = make_state(stars=[src, dest], fleets=fleets, options=opts)
        dispatch_fleet(state, 0, 1, owner_faction=1, warships=10)
        fleet = next(f for f in state.fleets_in_transit if not f.is_free)
        # Force immediate arrival
        fleet.turns_remaining = 1
        transit_process(state)
        assert dest.warships == 10

    def test_fleet_slot_freed_after_arrival(self):
        opts = make_options(sim_steps=5)
        src  = make_star(star_id=0, x=0, y=0, owner=1, warships=50)
        dest = make_star(star_id=1, x=1, y=0, owner=1, warships=0)
        fleets = [make_free_fleet(i) for i in range(5)]
        state = make_state(stars=[src, dest], fleets=fleets, options=opts)
        dispatch_fleet(state, 0, 1, owner_faction=1, warships=10)
        fleet = next(f for f in state.fleets_in_transit if not f.is_free)
        fleet.turns_remaining = 1
        transit_process(state)
        assert fleet.is_free

    def test_missile_fleet_moves_twice_as_fast(self):
        """Missile fleet turns_remaining should drop by 2*sim_steps per turn."""
        opts = make_options(sim_steps=5)
        src  = make_star(star_id=0, x=0, y=0, owner=1, warships=0, missiles=10)
        dest = make_star(star_id=1, x=50, y=0, owner=1)
        fleets = [make_free_fleet(i) for i in range(5)]
        state = make_state(stars=[src, dest], fleets=fleets, options=opts)
        dispatch_fleet(state, 0, 1, owner_faction=1, missiles=5,
                       fleet_type_char=FLEET_TYPE_MISSILE)
        fleet = next(f for f in state.fleets_in_transit if not f.is_free)
        before = fleet.turns_remaining
        transit_process(state)
        if not fleet.is_free:
            # Should have decremented by 2*sim_steps = 10
            assert before - fleet.turns_remaining == 10

    def test_enemy_arrival_triggers_combat(self):
        opts = make_options(sim_steps=5)
        src  = make_star(star_id=0, x=0, y=0, owner=1, warships=50)
        dest = make_star(star_id=1, x=1, y=0, owner=2, warships=5)
        fleets = [make_free_fleet(i) for i in range(5)]
        player1 = make_player(slot=0, faction_id=1)
        player2 = make_player(slot=1, faction_id=2)
        state = make_state(stars=[src, dest], players=[player1, player2],
                           fleets=fleets, options=opts)
        dispatch_fleet(state, 0, 1, owner_faction=1, warships=50)
        fleet = next(f for f in state.fleets_in_transit if not f.is_free)
        fleet.turns_remaining = 1
        records = transit_process(state)
        assert len(records) > 0

    def test_troop_delivery_to_friendly_empty_planet(self):
        opts = make_options(sim_steps=5)
        src  = make_star(star_id=0, x=0, y=0, owner=1, transports=5)
        dest = make_star(star_id=1, x=1, y=0, owner=1)
        dest.planets[0].troops = 0
        fleets = [make_free_fleet(i) for i in range(5)]
        state = make_state(stars=[src, dest], fleets=fleets, options=opts)
        dispatch_fleet(state, 0, 1, owner_faction=1, transports=5, troop_ships=50)
        fleet = next(f for f in state.fleets_in_transit if not f.is_free)
        fleet.turns_remaining = 1
        transit_process(state)
        # Troops should go to the planet (no enemy occupation)
        assert dest.planets[0].troops == 50 or dest.invasion_troops == 50