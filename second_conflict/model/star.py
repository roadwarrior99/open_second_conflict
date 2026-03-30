from dataclasses import dataclass, field
from typing import List


@dataclass
class Planet:
    """One TLV entry (7 bytes) inside a star record — represents a single planet.

    Binary layout (corrected from Ghidra decompilation):
      [0]   owner_faction_id  — which faction controls this planet
      [1]   morale            — signed byte (loyalty/morale of garrison)
      [2]   recruit           — recruit rate (troops added per turn)
      [3-6] troops            — troop count (uint32, int16 in practice)
    """
    owner_faction_id: int
    morale: int = 1        # signed byte; 1 = neutral, higher = more loyal
    recruit: int = 3       # troops recruited per turn
    troops: int = 0        # current defending troops on this planet


@dataclass
class Star:
    """One 99-byte star record.

    Coordinate layout for most stars (1-25): byte[0]=id, [1]=x, [2]=y, [3]=owner.
    Star 0 is anomalous: coords at [9],[10].

    Ships (warships, transports, stealthships, missiles) belong to owner_faction_id
    and are stored at fixed offsets at the end of the record (+0x51, +0x53, +0x55, +0x61).

    Planets are the TLV entries at byte +11 (7 bytes each), one per planet.
    Each planet has its own owner, morale, recruit rate, and troop count.
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
                                   # also = planet capacity (number of planet slots)

    # Per-planet data (TLV entries, byte +11 onward)
    planets: List[Planet] = field(default_factory=list)

    # Ship counts at fixed offsets in the star record.
    # All ships belong to owner_faction_id.
    warships:     int = 0    # +0x51 = 81
    transports:   int = 0    # +0x53 = 83  (unloaded TranSports)
    stealthships: int = 0    # +0x55 = 85
    missiles:     int = 0    # +0x61 = 97

    # Troops delivered by transport fleets, waiting in orbit to invade planets.
    # Set by fleet_transit on arrival; consumed by manual Invade action.
    invasion_troops: int = 0

    # Loyalty/stability at the star level
    loyalty: int = 0

    # Turns held for DEAD-world terraforming countdown (separate from warships garrison)
    dead_counter: int = 0

    # Raw trailing bytes preserved for round-trip file fidelity
    _raw: bytes = field(default=b'', repr=False)

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def num_planets(self) -> int:
        """Number of planets in this system."""
        return len(self.planets)

    @property
    def troops(self) -> int:
        """Total enemy troops occupying planets not owned by this star's owner."""
        return sum(p.troops for p in self.planets
                   if p.owner_faction_id != self.owner_faction_id)

    @property
    def troop_faction(self) -> int:
        """Faction of the first occupying planet (0 if none)."""
        for p in self.planets:
            if p.owner_faction_id != self.owner_faction_id and p.troops > 0:
                return p.owner_faction_id
        return 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def owner_name(self, players) -> str:
        if self.owner_faction_id == 0x1A:
            return "Empire"
        for p in players:
            if p.faction_id == self.owner_faction_id:
                return p.name
        return f"0x{self.owner_faction_id:02x}"

    def total_ships(self) -> int:
        return self.warships + self.transports + self.stealthships + self.missiles

    def __str__(self):
        return (f"Star {self.star_id} ({self.x},{self.y}) "
                f"type={self.planet_type} owner=0x{self.owner_faction_id:02x} "
                f"W:{self.warships} T:{self.transports} S:{self.stealthships} M:{self.missiles} "
                f"planets:{self.num_planets}")