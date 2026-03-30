from dataclasses import dataclass, field


@dataclass
class Player:
    slot: int               # 0-based slot index in file
    name: str               # max 8 chars
    faction_id: int         # byte value matching star garrison TLV owner byte
    is_human: bool = True
    is_active: bool = True  # False for inactive Empire placeholder slots

    # Player attributes (attrs[0..26] stored at record +9)
    active_flag: int = 0        # attrs[0]: 0=active, 101=Empire placeholder
    fleet_types_active: int = 6 # attrs[2]
    fleet_limit: int = 15       # attrs[3]
    budget: int = 100           # attrs[6]: starting_budget
    credits: int = 400          # attrs[7]: current credits/resources
    param8: int = 40            # attrs[8]
    empire_size: int = 0        # attrs[9]: territory metric
    production: int = 0         # attrs[10]: production rate
    fleet_count: int = 0        # attrs[11]
    strength: int = 0           # attrs[12]: combined fleet strength
    difficulty: int = 3         # attrs[13]: 3 or 5
    rating_a: int = 70          # attrs[15]
    rating_b: int = 70          # attrs[16]
    tech_level: int = 0         # attrs[25]: 0 or 1024
    game_param: int = 3         # attrs[26]

    def colour(self, palette):
        """Return display colour for this player from the given palette list."""
        if self.faction_id == 0x1A:
            from second_conflict.model.constants import EMPIRE_COLOUR
            return EMPIRE_COLOUR
        if 0 <= self.slot < len(palette):
            return palette[self.slot]
        from second_conflict.model.constants import NEUTRAL_COLOUR
        return NEUTRAL_COLOUR

    def __str__(self):
        return f"{self.name} (slot {self.slot}, faction 0x{self.faction_id:02x})"