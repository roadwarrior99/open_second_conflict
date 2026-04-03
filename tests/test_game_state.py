"""Tests for model/game_state.py — GameState helpers and EventEntry."""
import pytest
from second_conflict.model.constants import EMPIRE_FACTION
from second_conflict.model.game_state import GameState, GameOptions, EventEntry
from tests.conftest import make_player, make_star, make_state


class TestGameStateLookup:
    def test_player_for_faction_found(self):
        state = make_state(players=[make_player(faction_id=5)])
        assert state.player_for_faction(5) is not None

    def test_player_for_faction_missing_returns_none(self):
        state = make_state(players=[make_player(faction_id=5)])
        assert state.player_for_faction(99) is None

    def test_stars_owned_by(self):
        stars = [
            make_star(star_id=0, x=0,  y=0, owner=1),
            make_star(star_id=1, x=10, y=0, owner=2),
            make_star(star_id=2, x=20, y=0, owner=1),
        ]
        state = make_state(stars=stars)
        owned = state.stars_owned_by(1)
        assert len(owned) == 2
        assert all(s.owner_faction_id == 1 for s in owned)

    def test_active_players_excludes_inactive(self):
        p1 = make_player(slot=0, faction_id=1, is_active=True)
        p2 = make_player(slot=1, faction_id=2, is_active=False)
        state = make_state(players=[p1, p2])
        assert len(state.active_players()) == 1

    def test_human_players(self):
        p1 = make_player(slot=0, faction_id=1, is_human=True)
        p2 = make_player(slot=1, faction_id=2, is_human=False, is_active=True)
        state = make_state(players=[p1, p2])
        assert len(state.human_players()) == 1
        assert state.human_players()[0].faction_id == 1

    def test_current_player_wraps(self):
        p1 = make_player(slot=0, faction_id=1)
        state = make_state(players=[p1])
        state.current_player_slot = 5  # well past the list length
        assert state.current_player() is p1


class TestEventLog:
    def test_add_event_appends(self):
        state = make_state()
        state.add_event('combat', 1, 'Battle at star 0')
        assert len(state.event_log) == 1

    def test_add_event_fields(self):
        state = make_state()
        state.turn = 7
        state.add_event('revolt', 2, 'Discontent at star 3')
        e = state.event_log[0]
        assert e.category == 'revolt'
        assert e.player_faction == 2
        assert e.text == 'Discontent at star 3'
        assert e.turn == 7

    def test_events_for_faction_returns_own_and_empire(self):
        state = make_state()
        state.add_event('combat', 1, 'msg1')
        state.add_event('combat', 2, 'msg2')
        state.add_event('revolt', EMPIRE_FACTION, 'empire msg')
        events = state.events_for_faction(1)
        texts = [e.text for e in events]
        assert 'msg1' in texts
        assert 'empire msg' in texts
        assert 'msg2' not in texts