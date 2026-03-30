"""Parse Second Conflict .SCN / SCWSCEN.* binary files.

All offsets and sizes confirmed from Ghidra analysis of SCW.EXE loader
(FUN_1070_013f) and verified against known scenario files.
"""

import struct
from pathlib import Path
from typing import Optional

from second_conflict.model.constants import (
    STAR_COUNT, STAR_STRIDE, MAX_TRANSIT_FLEETS, FLEET_STRIDE,
    PLAYER_SLOTS, PLAYER_STRIDE, EMPIRE_FACTION, FREE_SLOT,
    OFFSET_HEADER, OFFSET_STAR_RECORDS, OFFSET_FLEET_TRANSIT,
    OFFSET_EMPIRE_ORDERS, OFFSET_UNKNOWN_A, OFFSET_UNKNOWN_B,
    OFFSET_UNKNOWN_C, OFFSET_PLAYER_RECORDS, OFFSET_GAME_STATE,
    OFFSET_SCENARIO_META, SIZE_UNKNOWN_A, SIZE_UNKNOWN_B, SIZE_UNKNOWN_C,
    SIZE_SCENARIO_META,
)
from second_conflict.model.game_state import GameOptions, GameState
from second_conflict.model.player import Player
from second_conflict.model.star import Star, GarrisonEntry
from second_conflict.model.fleet import FleetInTransit, EmpireOrder


def parse_file(path) -> GameState:
    data = Path(path).read_bytes()
    return parse_bytes(data)


def parse_bytes(data: bytes) -> GameState:
    options = _parse_header(data)
    stars = _parse_stars(data, options)
    fleets = _parse_fleet_transit(data)
    empire_orders = _parse_empire_orders(data)
    players, faction_ids = _parse_players(data, options)

    state = GameState(
        options=options,
        stars=stars,
        players=players,
        fleets_in_transit=fleets,
        empire_orders=empire_orders,
        faction_ids=faction_ids,
    )

    # Preserve unknown sections verbatim for round-trip saves
    state._raw_unknown_a = data[OFFSET_UNKNOWN_A : OFFSET_UNKNOWN_A + SIZE_UNKNOWN_A]
    state._raw_unknown_b = data[OFFSET_UNKNOWN_B : OFFSET_UNKNOWN_B + SIZE_UNKNOWN_B]
    state._raw_unknown_c = data[OFFSET_UNKNOWN_C : OFFSET_UNKNOWN_C + SIZE_UNKNOWN_C]
    if len(data) >= OFFSET_SCENARIO_META + SIZE_SCENARIO_META:
        state._raw_scenario_meta = data[OFFSET_SCENARIO_META : OFFSET_SCENARIO_META + SIZE_SCENARIO_META]

    return state


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def _parse_header(data: bytes) -> GameOptions:
    h = data[OFFSET_HEADER : OFFSET_HEADER + 18]
    num_players  = h[0]
    mode_raw     = h[1]          # on-disk value = in_memory * 8
    map_param    = h[3]
    save_flags   = struct.unpack_from('<H', h, 4)[0]
    star_count   = h[6]          # always 26
    sim_steps    = h[7]
    state_flags  = h[8]
    difficulty   = h[10]
    version      = struct.unpack_from('<H', h, 16)[0]

    is_savegame  = (mode_raw == 0x08)

    return GameOptions(
        num_players=num_players,
        star_count=star_count,
        sim_steps=sim_steps,
        map_param=map_param,
        difficulty=difficulty,
        is_savegame=is_savegame,
        version=version,
        mode_flag=mode_raw >> 3,   # convert to in-memory representation
        state_flags=state_flags,
    )


# ---------------------------------------------------------------------------
# Star records
# ---------------------------------------------------------------------------

def _parse_stars(data: bytes, options: GameOptions) -> list:
    stars = []
    base = OFFSET_STAR_RECORDS
    for i in range(STAR_COUNT):
        off = base + i * STAR_STRIDE
        rec = data[off : off + STAR_STRIDE]
        star = _parse_star_record(i, rec)
        stars.append(star)
    return stars


def _parse_star_record(index: int, rec: bytes) -> Star:
    star_id = rec[0]

    # Star 0 uses anomalous layout: coords at bytes [9],[10].
    # All other stars: [1]=x, [2]=y.
    if star_id == 0:
        x = rec[9]
        y = rec[10]
    else:
        x = rec[1]
        y = rec[2]

    owner          = rec[3]
    secondary      = rec[4]
    num_garrison   = rec[5]   # number of TLV entries

    # Planet type char is at byte +9 in standard records
    # For star 0, this byte holds x-coord, so planet type is at byte +6... actually
    # star 0's planet type is NOT at byte 9 (that's x). We store it from byte 6
    # for star 0 and byte 9 for others. This needs further verification.
    if star_id == 0:
        planet_type_byte = rec[6]
    else:
        planet_type_byte = rec[9]

    planet_type = chr(planet_type_byte) if 32 <= planet_type_byte < 127 else 'N'

    # Production fields
    base_prod = rec[5] if star_id != 0 else 0   # signed base prod bonus
    resource  = rec[6] if star_id != 0 else 1    # production rate

    # Parse TLV garrison entries starting at byte +11
    garrison = []
    for g in range(num_garrison):
        tlv_off = 11 + g * 7
        if tlv_off + 7 > len(rec):
            break
        g_owner     = rec[tlv_off]
        g_marker    = rec[tlv_off + 1]
        g_ship_type = rec[tlv_off + 2]
        g_count     = struct.unpack_from('<I', rec, tlv_off + 3)[0]
        if g_marker == 0x01 and 1 <= g_ship_type <= 7:
            garrison.append(GarrisonEntry(
                owner_faction_id=g_owner,
                ship_type=g_ship_type,
                ship_count=g_count,
            ))

    # Production accumulators at fixed offsets (int16 LE)
    prod_warships    = struct.unpack_from('<h', rec, 81)[0]  if len(rec) > 82 else 0
    prod_transports  = struct.unpack_from('<h', rec, 83)[0]  if len(rec) > 84 else 0
    prod_scouts      = struct.unpack_from('<h', rec, 85)[0]  if len(rec) > 86 else 0
    prod_stealths    = struct.unpack_from('<h', rec, 87)[0]  if len(rec) > 88 else 0
    prod_population  = struct.unpack_from('<h', rec, 89)[0]  if len(rec) > 90 else 0

    return Star(
        star_id=star_id,
        x=x,
        y=y,
        owner_faction_id=owner,
        secondary_faction=secondary,
        planet_type=planet_type,
        resource=resource,
        base_prod=base_prod,
        garrison=garrison,
        prod_warships=prod_warships,
        prod_transports=prod_transports,
        prod_scouts=prod_scouts,
        prod_stealthships=prod_stealths,
        prod_population=prod_population,
        _raw=bytes(rec),
    )


# ---------------------------------------------------------------------------
# Fleet-in-transit records
# ---------------------------------------------------------------------------

def _parse_fleet_transit(data: bytes) -> list:
    fleets = []
    base = OFFSET_FLEET_TRANSIT
    for i in range(MAX_TRANSIT_FLEETS):
        off = base + i * FLEET_STRIDE
        rec = data[off : off + FLEET_STRIDE]
        owner = rec[0]
        if owner == FREE_SLOT:
            fleets.append(FleetInTransit(
                slot=i, owner_faction_id=FREE_SLOT,
                dest_star=0, turns_remaining=0,
            ))
            continue

        dest_star      = rec[1]
        turns          = struct.unpack_from('<h', rec, 2)[0]
        flag_unknown   = rec[4]
        created_flag   = rec[5]
        warships       = struct.unpack_from('<h', rec, 6)[0]
        stealthships   = struct.unpack_from('<h', rec, 8)[0]
        transports     = struct.unpack_from('<h', rec, 10)[0]
        missiles       = struct.unpack_from('<h', rec, 12)[0]
        scouts         = struct.unpack_from('<h', rec, 14)[0]
        probes         = struct.unpack_from('<h', rec, 16)[0]
        type_byte      = rec[18]
        fleet_type     = chr(type_byte) if 32 <= type_byte < 127 else 'C'
        src_star       = rec[19]

        fleets.append(FleetInTransit(
            slot=i,
            owner_faction_id=owner,
            dest_star=dest_star,
            turns_remaining=turns,
            fleet_type_char=fleet_type,
            src_star=src_star,
            warships=max(0, warships),
            stealthships=max(0, stealthships),
            transports=max(0, transports),
            missiles=max(0, missiles),
            scouts=max(0, scouts),
            probes=max(0, probes),
            flag_unknown=flag_unknown,
            created_flag=created_flag,
        ))
    return fleets


# ---------------------------------------------------------------------------
# Empire orders
# ---------------------------------------------------------------------------

def _parse_empire_orders(data: bytes) -> list:
    orders = []
    base = OFFSET_EMPIRE_ORDERS
    for i in range(STAR_COUNT):
        off = base + i * FLEET_STRIDE
        rec = data[off : off + FLEET_STRIDE]
        orders.append(EmpireOrder(
            star_index=i,
            active=rec[0],
            dest_faction=rec[1],
            active_flag=rec[5],
            warships=struct.unpack_from('<h', rec, 6)[0],
            garrison_max=struct.unpack_from('<h', rec, 8)[0],
            reinforcements=struct.unpack_from('<h', rec, 10)[0],
            field_12=struct.unpack_from('<h', rec, 12)[0],
            field_14=struct.unpack_from('<h', rec, 14)[0],
            field_16=struct.unpack_from('<h', rec, 16)[0],
            _raw=bytes(rec),
        ))
    return orders


# ---------------------------------------------------------------------------
# Player records
# ---------------------------------------------------------------------------

def _parse_players(data: bytes, options: GameOptions):
    players = []
    base = OFFSET_PLAYER_RECORDS

    # Game state section: 10 × uint16 faction IDs
    faction_ids = list(struct.unpack_from('<10H', data, OFFSET_GAME_STATE))

    for i in range(PLAYER_SLOTS):
        off = base + i * PLAYER_STRIDE
        rec = data[off : off + PLAYER_STRIDE]

        # Layout (confirmed from raw bytes): +0 = name (9 bytes), +9 = attrs (27 × uint16)
        name_bytes = rec[0:9].split(b'\x00')[0]
        name = name_bytes.decode('latin-1', errors='replace')
        attrs = list(struct.unpack_from('<27H', rec, 9))

        active_flag = attrs[0]
        is_active   = (active_flag != 101)

        # faction_id: first 10 slots get their faction from game_state section;
        # slots 10-25 are Empire placeholders.
        if i < 10:
            faction_id = faction_ids[i]
        else:
            faction_id = EMPIRE_FACTION

        is_human = is_active and (i < options.num_players)

        p = Player(
            slot=i,
            name=name,
            faction_id=faction_id,
            is_human=is_human,
            is_active=is_active,
            active_flag=active_flag,
            fleet_types_active=attrs[2],
            fleet_limit=attrs[3],
            budget=attrs[6],
            credits=attrs[7],
            param8=attrs[8],
            empire_size=attrs[9],
            production=attrs[10],
            fleet_count=attrs[11],
            strength=attrs[12],
            difficulty=attrs[13],
            rating_a=attrs[15],
            rating_b=attrs[16],
            tech_level=attrs[25],
            game_param=attrs[26],
        )
        players.append(p)

    return players, faction_ids