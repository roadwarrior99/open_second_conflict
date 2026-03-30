from dataclasses import dataclass, field
from typing import List, Optional

from second_conflict.model.constants import EMPIRE_FACTION


@dataclass
class GameOptions:
    num_players: int = 2
    star_count: int = 26
    sim_steps: int = 5          # header[7]: simulation sub-steps per game turn
    map_param: int = 150        # 150 or 200
    difficulty: int = 1         # header[10]: 0-3; affects production formula
    random_events: bool = True
    novice_mode: bool = False   # production = 30000 when True (training wheels)
    empire_builds: bool = True  # Empire-owned stars also produce
    show_events_log: bool = True  # show dispatch/event log dialog after each turn
    is_savegame: bool = False
    version: int = 0x0300
    mode_flag: int = 0          # in-memory mode flag (raw_on_disk = mode * 8)
    state_flags: int = 0        # header[8] bitmask


@dataclass
class EventEntry:
    """A single news-ticker message generated during turn processing."""
    category: str           # 'scout' | 'reinforce' | 'revolt' | 'event' | 'combat'
    player_faction: int     # which player this message is addressed to
    text: str
    turn: int = 0


@dataclass
class GameState:
    options: GameOptions
    turn: int = 1
    current_player_slot: int = 0

    stars: List = field(default_factory=list)             # List[Star]
    players: List = field(default_factory=list)           # List[Player]
    fleets_in_transit: List = field(default_factory=list) # List[FleetInTransit]
    empire_orders: List = field(default_factory=list)     # List[EmpireOrder]
    faction_ids: List[int] = field(default_factory=list)  # 10 uint16 from game_state section

    event_log: List[EventEntry] = field(default_factory=list)
    pending_combats: List[int] = field(default_factory=list)  # star indices needing combat

    game_over: bool = False
    winner_slot: Optional[int] = None

    # Raw bytes for the three unknown sections — preserved for file round-trips
    _raw_unknown_a: bytes = field(default=b'', repr=False)
    _raw_unknown_b: bytes = field(default=b'', repr=False)
    _raw_unknown_c: bytes = field(default=b'', repr=False)
    _raw_scenario_meta: bytes = field(default=b'', repr=False)

    def active_players(self):
        return [p for p in self.players if p.is_active]

    def human_players(self):
        return [p for p in self.players if p.is_active and p.is_human]

    def current_player(self):
        active = self.active_players()
        if active:
            return active[self.current_player_slot % len(active)]
        return None

    def player_for_faction(self, faction_id: int):
        for p in self.players:
            if p.faction_id == faction_id:
                return p
        return None

    def stars_owned_by(self, faction_id: int):
        return [s for s in self.stars if s.owner_faction_id == faction_id]

    def add_event(self, category: str, player_faction: int, text: str):
        self.event_log.append(EventEntry(
            category=category,
            player_faction=player_faction,
            text=text,
            turn=self.turn,
        ))

    def events_for_faction(self, faction_id: int, min_difficulty: int = 0):
        return [e for e in self.event_log
                if e.player_faction == faction_id or e.player_faction == EMPIRE_FACTION]