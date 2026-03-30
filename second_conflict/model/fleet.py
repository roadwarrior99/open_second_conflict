from dataclasses import dataclass
from second_conflict.model.constants import FREE_SLOT


@dataclass
class FleetInTransit:
    """One 21-byte in-transit fleet record (section 3, 400 slots).

    Binary layout (corrected from Ghidra FUN_1088_0619 / combat strings):
      +0   owner_faction_id  (FREE_SLOT=0xFF means empty)
      +1   dest_star
      +2   turns_remaining   (int16 LE, decremented per sim sub-step)
      +4   flag_unknown
      +5   created_flag      (set to 1 on creation)
      +6   warships          (int16)
      +8   troop_ships       (int16) — TranSports loaded with troops for invasion
      +10  stealthships      (int16)
      +12  missiles          (int16)
      +14  scouts            (int16)
      +16  probes            (int16)
      +18  fleet_type_char   ('M'=Missile 2x, 'S'=Scout 1.5x, 'C'=combat, etc.)
      +19  src_star          (used for map rendering)
      +20  unknown
    """
    slot: int                   # index 0-399 in the transit array
    owner_faction_id: int       # faction byte; FREE_SLOT = 0xFF means empty
    dest_star: int              # destination star index 0-25
    turns_remaining: int        # int16; counts down to 0 = arrival
    fleet_type_char: str = 'C'  # determines speed bonus
    src_star: int = 0           # source star (byte +19, used for rendering)

    warships:     int = 0
    transports:   int = 0   # TranSport ship count in transit
    troop_ships:  int = 0   # troops loaded onto those transports
    stealthships: int = 0   # binary offset +10
    missiles:     int = 0
    scouts:       int = 0
    probes:       int = 0

    flag_unknown: int = 0
    created_flag: int = 1

    @property
    def is_free(self) -> bool:
        return self.owner_faction_id == FREE_SLOT

    def total_ships(self) -> int:
        return (self.warships + self.troop_ships + self.stealthships +
                self.missiles + self.scouts + self.probes)

    def __str__(self):
        return (f"Fleet slot={self.slot} owner=0x{self.owner_faction_id:02x} "
                f"dest={self.dest_star} turns={self.turns_remaining} "
                f"type={self.fleet_type_char} ships={self.total_ships()}")


@dataclass
class EmpireOrder:
    """One 21-byte empire order record (section 4, 26 slots, one per star).

    Controls what The Empire dispatches from each star.
    Fields partially decoded from FUN_1088_0376.
      +0   active  (non-zero = order pending)
      +1   dest_faction_byte
      +5   active_flag
      +6   warships   (int16)
      +8   garrison_max (int16)
      +10  reinforcement_count (int16)
      +12  field_12 (int16)
      +14  field_14 (int16)
      +16  field_16 (int16)
    """
    star_index: int
    active: int = 0             # byte +0; non-zero = order is pending
    dest_faction: int = 0       # byte +1
    active_flag: int = 0        # byte +5
    warships: int = 0           # int16 +6
    garrison_max: int = 0       # int16 +8
    reinforcements: int = 0     # int16 +10
    field_12: int = 0
    field_14: int = 0
    field_16: int = 0

    _raw: bytes = b''           # 21 raw bytes for round-trip fidelity

    @property
    def is_active(self) -> bool:
        return self.active != 0 and self.active_flag != 0xEF