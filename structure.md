# Second Conflict — Codebase Structure

A pygame recreation of the 1991 Windows 3.x turn-based space strategy game *Second Conflict* (`SCW.EXE`).
The binary file format and game logic have been reverse-engineered from the original executable using Ghidra.

---

## Directory Layout

```
patigona/
├── main.py                          Entry point — game loop, menu bar, UI wiring
├── requirements.txt                 Dependencies (pygame)
├── ghidra/                          Ghidra decompilation analysis notes
│
└── second_conflict/
    ├── model/                       Data structures (pure data, no logic)
    │   ├── game_state.py            GameState, GameOptions, EventEntry
    │   ├── star.py                  Star, Planet
    │   ├── player.py                Player
    │   ├── fleet.py                 FleetInTransit, EmpireOrder
    │   └── constants.py             All constants, enums, binary offsets
    │
    ├── engine/                      Turn-processing logic
    │   ├── turn_runner.py           Orchestrates the full turn sequence
    │   ├── fleet_transit.py         Fleet movement and arrival
    │   ├── combat.py                Orbital and ground combat resolution
    │   ├── production.py            Ship/troop production and planet upgrades
    │   ├── revolt.py                Loyalty decay and star revolts
    │   ├── events.py                Random events system
    │   └── distance.py             Star-to-star distance calculation
    │
    ├── ai/
    │   ├── player_ai.py             Computer player strategy
    │   └── empire_ai.py             Empire (neutral NPC) order processing
    │
    ├── io/
    │   └── scenario_parser.py       Binary .SCN/.SAV parse and write
    │
    ├── ui/
    │   ├── map_view.py              Galaxy map renderer and click handling
    │   ├── side_panel.py            Right-side player info + End Turn button
    │   ├── sys_info_panel.py        Bottom system detail strip
    │   ├── game_new.py              New-game factory (star generation)
    │   │
    │   └── dialogs/                 Modal dialog windows
    │       ├── base_dialog.py       BaseDialog parent class
    │       ├── new_game_dlg.py      New game setup
    │       ├── scenario_dlg.py      Scenario file picker
    │       ├── open_game_dlg.py     Save game file picker (with preview)
    │       ├── fleet_dlg.py         Fleet dispatch
    │       ├── fleet_view_dlg.py    View all in-transit fleets
    │       ├── planet_detail_dlg.py Single star's planets and troop detail
    │       ├── adm_view_dlg.py      Admin overview of all owned stars
    │       ├── ground_combat_dlg.py Bombard and invade UI
    │       ├── combat_anim.py       Animated orbital battle viewer
    │       ├── combat_pause_dlg.py  Pause between combat rounds
    │       ├── events_dlg.py        Scrollable event log
    │       ├── stats_dlg.py         Statistics (production, fleet counts)
    │       ├── score_dlg.py         Victory / defeat screen
    │       ├── unrest_dlg.py        Unrest / revolt status
    │       ├── revolt_view_dlg.py   Detailed revolt status
    │       ├── prod_limit_dlg.py    Production settings
    │       ├── reinf_view_dlg.py    Reinforcements view
    │       ├── scout_view_dlg.py    Scout reports
    │       ├── load_troops_dlg.py   Load troops onto transports
    │       ├── star_editor_dlg.py   Dev mode: edit any star's raw values
    │       ├── options_dlg.py       In-game options
    │       ├── message_dlg.py       Simple OK / Cancel dialog
    │       └── about_dlg.py         About screen
    │
    └── util/
        ├── rng.py                   GameRNG wrapper (matches original rand())
        └── name_gen.py              Random player name generator
```

---

## Key Classes

| Class | File | Role |
|---|---|---|
| `GameState` | model/game_state.py | Central state container; passed everywhere |
| `GameOptions` | model/game_state.py | Immutable game configuration (difficulty, flags) |
| `EventEntry` | model/game_state.py | One entry in the event log |
| `Star` | model/star.py | One star system (26 total) |
| `Planet` | model/star.py | One planet within a star system |
| `Player` | model/player.py | Human or AI player |
| `FleetInTransit` | model/fleet.py | Fleet moving between stars (one of 400 slots) |
| `EmpireOrder` | model/fleet.py | Empire AI standing order (one per star) |
| `MapView` | ui/map_view.py | Galaxy map renderer and input handler |
| `SidePanel` | ui/side_panel.py | Right panel: player list, credits, End Turn |
| `SysInfoPanel` | ui/sys_info_panel.py | Bottom panel: selected star detail |
| `BaseDialog` | ui/dialogs/base_dialog.py | Modal dialog base class |
| `CombatRecord` | engine/combat.py | Data captured for combat animation |

---

## Screen Layout

```
+----------- Menu bar (26 px) --------------------------------+
| File   View   Game                                          |
+----------- Map View (800 × 684) ----------+-- Side Panel --+
|                                            |  (300 × 710)  |
|   Galaxy map                               |  Player list  |
|   Stars as coloured circles                |  Credits      |
|   Fleet transit lines                      |  [End Turn]   |
|   Selection highlight                      |               |
+----------- Sys Info Panel (800 × 110) ----+---------------+
|  Selected star: owner, ships, planets, garrison, buttons    |
+-------------------------------------------------------------+
```

---

## Data Model

### GameState

The single source of truth. Always passed as a parameter — never a global.

```
GameState
  .options       GameOptions   — difficulty, flags, map params
  .stars         List[Star]    — all 26 star systems
  .players       List[Player]  — all 26 player slots (most inactive)
  .fleets_in_transit  List[FleetInTransit]  — up to 400 active fleets
  .empire_orders List[EmpireOrder]          — 26 Empire standing orders
  .faction_ids   List[int]     — maps slot index → faction_id
  .turn          int           — current turn number
  .current_player_slot  int    — hotseat index into human_players()
  .event_log     List[EventEntry]
  .pending_combats  List[int]  — star indices needing combat resolution
```

Key methods: `active_players()`, `human_players()`, `current_player()`,
`player_for_faction(fid)`, `stars_owned_by(fid)`, `add_event()`, `events_for_faction(fid)`.

### Star

```
Star
  .star_id       int           — 0–25
  .x, .y         int           — map coordinates
  .owner_faction_id  int       — faction that controls this star
  .planet_type   str           — single char: W M T S F P D N (see below)
  .resource      int           — production multiplier
  .base_prod     int           — bonus credits per turn
  .planets       List[Planet]  — each planet tracks owner/morale/troops
  .warships, .transports, .stealthships, .missiles  int
  .invasion_troops  int        — troops in orbit, not yet on any planet
  .loyalty       int           — signed; <0 = discontent; <=-10 = revolt
  .dead_counter  int           — countdown for Terraform (D) → Warship (W) conversion
```

Planet types and what they produce:

| Char | Name | Produces |
|------|------|----------|
| W | Warship | 1 warship per credit |
| M | Missile | 1 missile per 2 credits |
| T | Transport | 1 transport per 3 credits |
| S | Stealth | 1 stealthship per 3 credits |
| F | Factory | accumulates credits; upgrades resource multiplier |
| P | Population | grows new planets; each costs `pop_count × 10` credits |
| D | Terraform | counts down 10 turns, then converts to Warship world |
| N | None | no production |

### Player

```
Player
  .slot          int   — index 0–25
  .faction_id    int   — unique faction identifier (1–25; Empire = 0x1A)
  .name          str
  .is_human      bool
  .is_active     bool
  .credits       int   — production credits this turn
  .empire_size   int   — number of stars owned
  .production    int   — total credits per turn
  .fleet_count   int
  .strength      int
```

### FleetInTransit

```
FleetInTransit
  .slot              int   — index into the 400-slot array
  .owner_faction_id  int   — FREE_SLOT (0xFF) if empty
  .dest_star         int   — destination star index
  .src_star          int   — source star index
  .turns_remaining   int   — decrements each sub-step; 0 = arrive
  .fleet_type_char   str   — 'C' combat (1×), 'M' missile (2×), 'S' scout (1.5×)
  .warships, .transports, .troop_ships, .stealthships, .missiles, .scouts, .probes  int
```

---

## Game Loop

```
main()
  pygame.init()
  Create MapView, SidePanel, SysInfoPanel, MenuBar
  Wire callbacks (on_star_click, on_end_turn, menu actions)

  while running:
    for event in pygame.event.get():
      menu_bar.handle_event(event)
      map_view.handle_event(event)
      side_panel.handle_event(event)
      sys_panel.handle_event(event)

    map_view.draw(screen)
    side_panel.draw(screen)
    sys_panel.draw(screen)
    menu_bar.draw(screen)
    pygame.display.flip()
    clock.tick(30)
```

---

## Turn Sequence

Triggered by `on_end_turn()` → `_do_end_turn()` → `run_turn(state)`:

1. `state.turn += 1`
2. **Fleet transit** — each fleet moves `sim_steps` sub-steps; arrivals trigger orbital combat
3. **Resolve pending combat** — any combat queued from arrivals
4. **Production** — all stars produce ships and recruit troops
5. **Revolt** — occupied stars lose loyalty; at -10 star reverts to Empire
6. **Random events** — if enabled, each human player may receive an event
7. **Empire AI** — process Empire orders
8. **Computer player AI** — each non-human active player takes its turn
9. **Victory check** — if one faction controls all stars, game ends

After `run_turn()` returns:
- Show `CombatAnimation` for each combat record
- Show `EventsDialog` if there are new events for the current player
- Show `ScoreDialog` if game is over
- Advance hotseat to the next human player

---

## Turn Processing Pipeline (engine/)

### fleet_transit.py

Runs `sim_steps` (typically 5) sub-steps per turn.
Each sub-step decrements `turns_remaining` for every fleet:
- Fleet type `'C'`: -1 per sub-step (base speed)
- Fleet type `'M'`: -2 per sub-step (missiles, 2× speed)
- Fleet type `'S'`: -1 on even, -2 on odd sub-steps (scouts, ≈1.5× speed)

On arrival (`turns_remaining < 1`):
- **Friendly star**: merge ships into star; troops placed in orbit (`invasion_troops`) or deposited to first friendly planet
- **Enemy star**: orbital combat fires immediately

### combat.py

**Orbital combat** (automatic on enemy fleet arrival):
1. Phase 0 — Missile barrage (simultaneous): missiles kill warships/stealthships 1-for-1 on both sides
2. Phase 1 — Three attrition rounds: random losses scaled by total ship counts
3. Surviving ships distributed proportionally between warships and stealthships
4. If defender eliminated: attacker captures the star (planets remain under their current owners until ground combat)
5. If attacker eliminated or both sides survive: attacker repelled, fleet returns to source

**Ground combat** (manual, via `GroundCombatDialog`):
- `bombard()`: costs 1 orbital warship, kills 2 planet troops; also reduces `star.resource` by 1
- `invade()`: uses `invasion_troops` to assault planets; morale affects casualty exchange rate

### production.py

For each star:
```
credits = (4 - difficulty) * resource + base_prod
```
Ships produced based on `planet_type` (see table above).
Each planet recruits `planet.recruit` troops per turn (capped at 10 000).
Player stats (`empire_size`, `production`, `fleet_count`, `strength`) recomputed from live star data.

### revolt.py

For each star per turn:
- If any planet has a foreign owner: `loyalty -= 1`
- Else if `loyalty < 0`: `loyalty += 1`
- At `loyalty < 0`: player receives a "Discontent" event
- At `loyalty <= -10`: star reverts to Empire; all planets reset to Empire ownership

### events.py

Each turn, each human player with at least one star rolls for a random event.
Ten possible event types: Imperial missile strike, independence movement, tech breakthrough,
muon cloud (fleet damage), reinforcements, espionage, pirate raid, diplomatic overture,
resource discovery, plague.

---

## AI

### player_ai.py — Computer player

Runs once per turn for each non-human active player:

1. **Ground combat phase** — for each owned star with enemy-occupied planets:
   - Bombard repeatedly (up to 10 rounds) while warships > 0 and enemy troops remain
   - Then invade with any `invasion_troops`

2. **Fleet dispatch phase** — for each owned star with surplus warships:
   - Skip if a fleet is already in transit from this star
   - Skip if `warships <= MIN_GARRISON` (3)
   - Target selection: nearest enemy player star preferred; nearest Empire star as fallback
   - Attack a **player** star only if we have ≥ 2× the defender's warships AND ≥ 4 ships total
   - Always leave ≥ 3 warships at the source star

### empire_ai.py — Empire NPC

Processes Empire standing orders each turn. The Empire owns uncontested stars at game start and uses `EmpireOrder` records to dispatch fleets and garrison stars.

---

## Save / Load

**File format**: Binary, fixed size, 10 sections — reverse-engineered from `SCW.EXE`.

| # | Section | Offset | Size |
|---|---------|--------|------|
| 1 | Header | 0 | 18 B |
| 2 | Star records | 18 | 2 574 B (26 × 99) |
| 3 | Fleet transit | 2 592 | 8 400 B (400 × 21) |
| 4 | Empire orders | 10 992 | 546 B (26 × 21) |
| 5 | Unknown A | 11 538 | 2 860 B |
| 6 | Unknown B | 14 398 | 2 704 B |
| 7 | Unknown C | 17 102 | 40 B |
| 8 | Player records | 17 142 | 1 638 B (26 × 63) |
| 9 | Game state | 18 780 | 20 B |
| 10 | Scenario meta | 18 800 | 140 B |

Header byte layout:

```
[0]     num_players
[1]     mode_flag  (0x08 on disk = save game)
[3]     map_param
[4-5]   state_flags  (uint16 LE)
[6]     star_count   (always 26)
[7]     sim_steps
[8]     state_flags  (byte)
[10]    difficulty
[11-12] turn         (uint16 LE) — Python extension; 0 in original SCW files
[16-17] version      (uint16 LE)
```

Unknown sections (5–7) are preserved verbatim for round-trip fidelity with original files.

**API**:
```python
from second_conflict.io.scenario_parser import parse_file, write_file

state = parse_file("mysave.sav")   # → GameState
write_file(state, "mysave.sav")
```

---

## Dialog System

All dialogs inherit from `BaseDialog` and are **modal** — `dialog.run()` blocks the main loop until closed, then returns a result value.

```python
class BaseDialog:
    def run(self) -> Any:
        """Block until closed; return self._result."""

    def close(self, result):
        """Set result and stop the loop."""

    # Subclasses override:
    def handle_event(self, event): ...   # input
    def update(self, dt: int): ...       # animation (dt in ms)
    def draw(self, surface): ...         # rendering
```

Within `draw()`, use `self._content_rect()` for the usable area inside the border/title,
and `self._draw_button()`, `self._text()`, `self._title_text()` for common elements.

Typical usage in `main.py`:
```python
result = FleetDialog(screen, state, star_idx, faction_id).run()
if result:
    dispatch_fleet(state, *result)
```

---

## Data Flow Summary

```
User clicks "New Game"
  → NewGameDialog.run()
  → build_new_game(options, names, is_ai)
       Generate 26 stars, assign home stars, initialise fleets/orders
  → GameState returned; UI views updated

User double-clicks a star
  → FleetDialog.run()  — choose destination and ship counts
  → dispatch_fleet()   — deduct from star, create FleetInTransit slot

User clicks "End Turn"
  → run_turn(state)
       fleet_transit → combat → production → revolt → events → AI
  → Show CombatAnimation dialogs
  → Show EventsDialog
  → Check victory → ScoreDialog
  → Advance hotseat player; redraw screen

User clicks "Save"
  → dev mode: prompt for turn number override
  → write_file(state, path)

User clicks "Open"
  → OpenGameDialog.run()  — shows file list + preview
  → parse_file(path) → GameState; UI views updated
```