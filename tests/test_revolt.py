"""Tests for engine/revolt.py — loyalty decay and star revolts."""
import pytest
from second_conflict.engine import revolt
from second_conflict.model.constants import EMPIRE_FACTION
from second_conflict.model.star import Planet
from second_conflict.util import rng as rng_module
from tests.conftest import make_star, make_state, make_player


def _state(owner=1, planets=None, loyalty=0):
    if planets is None:
        planets = [Planet(owner_faction_id=owner, morale=1, recruit=3, troops=0)]
    star = make_star(star_id=0, owner=owner, planets=planets)
    star.loyalty = loyalty
    player = make_player(faction_id=owner)
    return make_state(stars=[star], players=[player])


class TestLoyaltyDecay:
    def test_loyalty_decreases_when_foreign_planet(self):
        planets = [Planet(owner_faction_id=2, morale=1, recruit=3, troops=50)]
        state = _state(owner=1, planets=planets, loyalty=0)
        revolt.process(state)
        assert state.stars[0].loyalty == -1

    def test_loyalty_recovers_when_all_friendly(self):
        state = _state(owner=1, loyalty=-3)
        revolt.process(state)
        assert state.stars[0].loyalty == -2

    def test_loyalty_does_not_increase_above_zero(self):
        state = _state(owner=1, loyalty=0)
        revolt.process(state)
        assert state.stars[0].loyalty == 0

    def test_empire_stars_not_processed(self):
        star = make_star(star_id=0, owner=EMPIRE_FACTION)
        star.loyalty = 0
        state = make_state(stars=[star])
        revolt.process(state)
        # Empire stars: loyalty unchanged
        assert star.loyalty == 0


class TestDiscontentEvent:
    def test_discontent_event_logged_when_loyalty_negative(self):
        planets = [Planet(owner_faction_id=2, morale=1, recruit=3, troops=50)]
        state = _state(owner=1, planets=planets, loyalty=-1)
        revolt.process(state)
        assert any('Discontent' in e.text for e in state.event_log)

    def test_no_discontent_event_when_loyalty_zero(self):
        state = _state(owner=1, loyalty=0)
        revolt.process(state)
        assert not any('Discontent' in e.text for e in state.event_log)


class TestRevoltTrigger:
    def setup_method(self):
        rng_module.seed(0)

    def test_revolt_at_threshold_changes_owner_to_empire(self):
        planets = [Planet(owner_faction_id=2, morale=1, recruit=3, troops=50)]
        state = _state(owner=1, planets=planets, loyalty=-10)
        revolt.process(state)
        assert state.stars[0].owner_faction_id == EMPIRE_FACTION

    def test_revolt_resets_planet_owners_to_empire(self):
        # Foreign planet → loyalty decays, then revolt fires
        planets = [Planet(owner_faction_id=2, morale=1, recruit=3, troops=10)]
        state = _state(owner=1, planets=planets, loyalty=-10)
        revolt.process(state)
        assert all(p.owner_faction_id == EMPIRE_FACTION for p in state.stars[0].planets)

    def test_revolt_resets_planet_morale(self):
        # Foreign planet → loyalty decays to -11 → revolt fires, resets morale
        planets = [Planet(owner_faction_id=2, morale=5, recruit=3, troops=10)]
        state = _state(owner=1, planets=planets, loyalty=-10)
        revolt.process(state)
        assert all(p.morale == 1 for p in state.stars[0].planets)

    def test_revolt_event_logged(self):
        planets = [Planet(owner_faction_id=2, morale=1, recruit=3, troops=50)]
        state = _state(owner=1, planets=planets, loyalty=-10)
        revolt.process(state)
        texts = [e.text for e in state.event_log]
        assert any('revolt' in t.lower() or 'throws off' in t for t in texts)

    def test_no_revolt_below_threshold(self):
        # Foreign planet with loyalty=-8: after decay → -9, still above threshold -10
        planets = [Planet(owner_faction_id=2, morale=1, recruit=3, troops=50)]
        state = _state(owner=1, planets=planets, loyalty=-8)
        revolt.process(state)
        assert state.stars[0].owner_faction_id == 1

    def test_loyalty_reset_after_revolt(self):
        planets = [Planet(owner_faction_id=2, morale=1, recruit=3, troops=50)]
        state = _state(owner=1, planets=planets, loyalty=-10)
        revolt.process(state)
        # Loyalty should be reset to a small random non-negative value
        assert state.stars[0].loyalty >= 0