from dataclasses import dataclass, field
from typing import List


@dataclass
class GarrisonEntry:
    """One 7-byte TLV fleet entry stored inside a star record.

    On disk layout: [owner_faction_id] [0x01 marker] [ship_type] [count uint32 LE]
    In-memory we also carry combat-state fields from the surrounding star bytes.
    """
    owner_faction_id: int   # faction byte (0x1a = Empire, others = player faction)
    ship_type: int          # 1-7 matching ShipType enum
    ship_count: int         # number of ships

    # Per-TLV state bytes that sit adjacent in the star record
    loyalty: int = 0        # signed byte: garrison loyalty (positive = loyal)
    unrest: int = 0         # unsigned byte
    strength: int = 0       # int16: garrison combat strength at this star

    def is_empire(self) -> bool:
        return self.owner_faction_id == 0x1A


@dataclass
class Star:
    """One 99-byte star record.

    Coordinate layout for most stars (1-25): byte[0]=id, [1]=x, [2]=y, [3]=owner.
    Star 0 is anomalous: coords at [9],[10].
    """
    star_id: int                   # 0-based, 0-25
    x: int                         # map x coordinate
    y: int                         # map y coordinate
    owner_faction_id: int          # primary owner faction byte
    secondary_faction: int = 0x1A  # byte[4], often Empire

    # Byte[9] in the star record
    planet_type: str = 'N'         # char: W/F/M/N/P/S/T/D

    # Production fields derived from star record internals
    resource: int = 1              # star_record[6]: production rate multiplier
    base_prod: int = 0             # star_record[5]: signed base production bonus

    # Garrison TLV entries (variable count, up to ~12)
    garrison: List[GarrisonEntry] = field(default_factory=list)

    # Production accumulators (int16 at various offsets in the star record)
    prod_warships: int = 0         # offset +0x51=81
    prod_transports: int = 0       # offset +0x53=83
    prod_stealth: int = 0          # offset +0x55=85  StealthShip count
    prod_stealthships: int = 0     # offset +0x57=87 (also fleet_strength aggregator)
    prod_population: int = 0       # offset +0x59=89
    prod_missiles: int = 0         # offset +0x61=97

    # Stability
    loyalty: int = 0               # base loyalty (signed; negative = unrest)
    flags: int = 0                 # bitmask flags byte

    # Raw trailing bytes preserved for round-trip file fidelity
    _raw: bytes = field(default=b'', repr=False)

    def owner_name(self, players) -> str:
        if self.owner_faction_id == 0x1A:
            return "Empire"
        for p in players:
            if p.faction_id == self.owner_faction_id:
                return p.name
        return f"0x{self.owner_faction_id:02x}"

    def garrison_for_faction(self, faction_id: int) -> List[GarrisonEntry]:
        return [g for g in self.garrison if g.owner_faction_id == faction_id]

    def total_ships_for_faction(self, faction_id: int) -> int:
        return sum(g.ship_count for g in self.garrison_for_faction(faction_id))

    def factions_present(self):
        return list({g.owner_faction_id for g in self.garrison})

    def __str__(self):
        return f"Star {self.star_id} ({self.x},{self.y}) type={self.planet_type} owner=0x{self.owner_faction_id:02x}"