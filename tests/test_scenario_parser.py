"""Tests for io/scenario_parser.py — binary save/load round-trip."""
import struct
import pytest
from second_conflict.io.scenario_parser import write_bytes, parse_bytes
from second_conflict.model.constants import (
    EMPIRE_FACTION, FREE_SLOT, OFFSET_HEADER,
    STAR_COUNT, MAX_TRANSIT_FLEETS, PLAYER_SLOTS,
    OFFSET_SCENARIO_META, SIZE_SCENARIO_META,
)
from second_conflict.model.game_state import GameState, GameOptions
from second_conflict.model.star import Star, Planet
from second_conflict.model.player import Player
from second_conflict.model.fleet import FleetInTransit, EmpireOrder
from tests.conftest import make_star, make_player, make_free_fleet, make_options


def _minimal_state(turn=1, difficulty=1) -> GameState:
    """Build a minimal valid GameState that can be round-tripped."""
    opts = make_options(difficulty=difficulty, num_players=2)
    opts.is_savegame = True
    opts.sim_steps = 5
    opts.map_param = 150
    opts.version = 0x0300
    opts.star_count = STAR_COUNT

    stars = []
    for i in range(STAR_COUNT):
        owner = 1 if i < 2 else EMPIRE_FACTION
        planets = [Planet(owner_faction_id=owner, morale=1, recruit=3, troops=0)]
        stars.append(Star(
            star_id=i, x=i * 5, y=i * 3,
            owner_faction_id=owner,
            planet_type='W', resource=3, base_prod=0,
            planets=planets,
        ))

    players = []
    faction_ids = []
    for i in range(PLAYER_SLOTS):
        fid = i + 1 if i < 10 else EMPIRE_FACTION
        active = i < 2
        p = Player(slot=i, name=f"P{i}", faction_id=fid,
                   is_human=(i == 0), is_active=active,
                   active_flag=0 if active else 101)
        players.append(p)
        if i < 10:
            faction_ids.append(fid)

    fleets = [FleetInTransit(slot=i, owner_faction_id=FREE_SLOT,
                             dest_star=0, turns_remaining=0)
              for i in range(MAX_TRANSIT_FLEETS)]

    orders = [EmpireOrder(star_index=i) for i in range(STAR_COUNT)]

    state = GameState(
        options=opts,
        turn=turn,
        stars=stars,
        players=players,
        fleets_in_transit=fleets,
        empire_orders=orders,
        faction_ids=faction_ids,
    )
    return state


class TestRoundTrip:
    def test_basic_round_trip(self):
        state = _minimal_state(turn=42)
        data = write_bytes(state)
        restored = parse_bytes(data)
        assert restored is not None

    def test_turn_number_persisted(self):
        for turn in (1, 10, 100, 500, 65535):
            state = _minimal_state(turn=turn)
            data = write_bytes(state)
            restored = parse_bytes(data)
            assert restored.turn == turn, f"turn={turn} not preserved"

    def test_turn_zero_in_original_file_defaults_to_1(self):
        state = _minimal_state(turn=1)
        data = bytearray(write_bytes(state))
        # Zero out the turn bytes (header offset 11-12)
        struct.pack_into('<H', data, OFFSET_HEADER + 11, 0)
        restored = parse_bytes(bytes(data))
        assert restored.turn == 1

    def test_star_count(self):
        state = _minimal_state()
        data = write_bytes(state)
        restored = parse_bytes(data)
        assert len(restored.stars) == STAR_COUNT

    def test_star_owner_preserved(self):
        state = _minimal_state()
        state.stars[0].owner_faction_id = 1
        data = write_bytes(state)
        restored = parse_bytes(data)
        assert restored.stars[0].owner_faction_id == 1

    def test_star_warships_preserved(self):
        state = _minimal_state()
        state.stars[0].warships = 123
        data = write_bytes(state)
        restored = parse_bytes(data)
        assert restored.stars[0].warships == 123

    def test_star_resource_preserved(self):
        state = _minimal_state()
        state.stars[2].resource = 7
        data = write_bytes(state)
        restored = parse_bytes(data)
        assert restored.stars[2].resource == 7

    def test_player_name_preserved(self):
        state = _minimal_state()
        state.players[0].name = "Zara"
        data = write_bytes(state)
        restored = parse_bytes(data)
        assert restored.players[0].name == "Zara"

    def test_difficulty_preserved(self):
        state = _minimal_state(difficulty=3)
        data = write_bytes(state)
        restored = parse_bytes(data)
        assert restored.options.difficulty == 3

    def test_planet_troops_preserved(self):
        state = _minimal_state()
        state.stars[0].planets[0].troops = 999
        data = write_bytes(state)
        restored = parse_bytes(data)
        assert restored.stars[0].planets[0].troops == 999

    def test_invasion_troops_preserved(self):
        state = _minimal_state()
        state.stars[0].invasion_troops = 250
        data = write_bytes(state)
        restored = parse_bytes(data)
        assert restored.stars[0].invasion_troops == 250

    def test_fleet_in_transit_preserved(self):
        state = _minimal_state()
        fleet = state.fleets_in_transit[0]
        fleet.owner_faction_id = 1
        fleet.dest_star = 3
        fleet.src_star = 0
        fleet.turns_remaining = 12
        fleet.warships = 55
        fleet.fleet_type_char = 'C'
        data = write_bytes(state)
        restored = parse_bytes(data)
        rf = restored.fleets_in_transit[0]
        assert rf.owner_faction_id == 1
        assert rf.dest_star == 3
        assert rf.warships == 55
        assert rf.turns_remaining == 12

    def test_loyalty_preserved(self):
        state = _minimal_state()
        state.stars[0].loyalty = -5
        data = write_bytes(state)
        restored = parse_bytes(data)
        assert restored.stars[0].loyalty == -5

    def test_output_size_is_fixed(self):
        state = _minimal_state()
        data = write_bytes(state)
        expected = OFFSET_SCENARIO_META + SIZE_SCENARIO_META
        assert len(data) == expected


class TestParseHeader:
    def test_version_written_and_read(self):
        state = _minimal_state()
        state.options.version = 0x0300
        data = write_bytes(state)
        restored = parse_bytes(data)
        assert restored.options.version == 0x0300

    def test_sim_steps_preserved(self):
        state = _minimal_state()
        state.options.sim_steps = 7
        data = write_bytes(state)
        restored = parse_bytes(data)
        assert restored.options.sim_steps == 7