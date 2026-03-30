from enum import IntEnum

STAR_COUNT = 26
MAX_TRANSIT_FLEETS = 400
STAR_STRIDE = 99
FLEET_STRIDE = 21
PLAYER_STRIDE = 63
PLAYER_SLOTS = 26
EMPIRE_FACTION = 0x1A  # 26 — The Empire (neutral AI)
FREE_SLOT = 0xFF       # marks empty fleet-in-transit slot

# File layout offsets (confirmed from Ghidra loader FUN_1070_013f)
OFFSET_HEADER        = 0
OFFSET_STAR_RECORDS  = 18
OFFSET_FLEET_TRANSIT = 2592
OFFSET_EMPIRE_ORDERS = 10992
OFFSET_UNKNOWN_A     = 11538
OFFSET_UNKNOWN_B     = 14398
OFFSET_UNKNOWN_C     = 17102
OFFSET_PLAYER_RECORDS = 17142
OFFSET_GAME_STATE    = 18780
OFFSET_SCENARIO_META = 18800

SIZE_HEADER          = 18
SIZE_FLEET_TRANSIT   = MAX_TRANSIT_FLEETS * FLEET_STRIDE   # 8400
SIZE_EMPIRE_ORDERS   = STAR_COUNT * FLEET_STRIDE           # 546
SIZE_UNKNOWN_A       = 0xB2C   # 2860
SIZE_UNKNOWN_B       = 0xA90   # 2704
SIZE_UNKNOWN_C       = 0x28    # 40
SIZE_PLAYER_RECORDS  = PLAYER_SLOTS * PLAYER_STRIDE        # 1638
SIZE_GAME_STATE      = 0x14    # 20
SIZE_SCENARIO_META   = 0x8C    # 140


class ShipType(IntEnum):
    WARSHIP      = 1
    STEALTHSHIP  = 2
    TRANSPORT    = 3
    MISSILE      = 4
    SCOUT        = 5
    PRIVATEER    = 6
    PROBE        = 7


SHIP_NAMES = {
    ShipType.WARSHIP:     "WarShip",
    ShipType.STEALTHSHIP: "StealthShip",
    ShipType.TRANSPORT:   "TranSport",
    ShipType.MISSILE:     "Missile",
    ShipType.SCOUT:       "Scout",
    ShipType.PRIVATEER:   "Privateer",
    ShipType.PROBE:       "Probe",
}


class PlanetType:
    """Planet type chars stored at star_record[+9].
    Determines what is produced and at what cost.
    """
    WARSHIP    = 'W'   # builds WarShips
    MISSILE    = 'M'   # builds Missiles  (cost 2 production credits)
    TRANSPORT  = 'T'   # builds TranSports (cost 3)
    STEALTH    = 'S'   # builds StealthShips (cost 3); used for scout missions
    FACTORY    = 'F'   # factory: accumulates credits, can grow resource value
    POPULATION = 'P'   # population world: grows pop units up to 10
    DEAD       = 'D'   # dead world: transitions to 'W' when conditions met
    NEUTRAL    = 'N'   # neutral placeholder (no production)


# Production cost per ship type (production credits required)
PRODUCTION_COST = {
    PlanetType.WARSHIP:    1,
    PlanetType.MISSILE:    2,
    PlanetType.TRANSPORT:  3,
    PlanetType.STEALTH:    3,
}

# Fleet type chars used in in-transit records (+18)
FLEET_TYPE_COMBAT    = 'C'
FLEET_TYPE_MISSILE   = 'M'   # travels 2x speed
FLEET_TYPE_SCOUT     = 'S'   # travels 1.5x speed
FLEET_TYPE_TRANSPORT = 'T'
FLEET_TYPE_PRIVATEER = 'P'

# Mode flag values (raw on-disk = in_memory * 8)
MODE_FRESH_SCENARIO  = 0   # in-memory
MODE_SCENARIO        = 1   # in-memory (written as 0x08 on disk)
MODE_IN_PROGRESS     = 1   # in-memory for savegames (disk byte = 0x08)

# Player colours (one per slot 0-9)
PLAYER_COLOURS = [
    (  0, 120, 220),   # 0 blue
    (220,  40,  40),   # 1 red
    ( 40, 180,  40),   # 2 green
    (220, 160,   0),   # 3 yellow
    (180,  40, 220),   # 4 purple
    (  0, 200, 200),   # 5 cyan
    (220, 120,   0),   # 6 orange
    (160, 200,  40),   # 7 lime
    (200,  40, 120),   # 8 pink
    ( 80,  80, 200),   # 9 indigo
]
EMPIRE_COLOUR  = (200, 160,  40)   # gold
NEUTRAL_COLOUR = ( 80,  80,  80)