# Second Conflict

A Python/pygame recreation of *Second Conflict* (1991, Windows 3.x) by Jerry W. Galloway.

Game mechanics are faithfully translated from the original `SCW.EXE` binary via Ghidra decompilation. The binary save file format (`.scn` / `.sav`) is fully compatible with the original game.

---

## Requirements

- Python 3.11+
- pygame 2.x

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Running

```bash
# Start with the New Game wizard
python main.py

# Load an existing save or scenario file
python main.py mysave.sav
python main.py second-conflict/SCWSCEN.1
```

---

## Controls

| Input | Action |
|---|---|
| Left-click star | Select star |
| Right-click star / double-click | Open fleet dispatch dialog |
| Enter / End Turn button | Process the turn |
| F1 | Statistics table |
| Ctrl+N | New game |
| Ctrl+O | Open save game |
| Ctrl+S | Save game |
| Escape | Close dialog |

---

## Gameplay

Second Conflict is a turn-based 4X space strategy game for up to 10 players (human or AI) sharing one screen. Each player starts with one home star and must expand across 26 star systems, defeating rival factions and The Empire.

### Turn sequence

1. **Fleet movement** — fleets travel across `sim_steps` sub-steps; arrivals at enemy stars trigger orbital combat automatically
2. **Combat resolution** — three-round attrition at contested stars
3. **Production** — each star produces ships or grows based on its planet type
4. **Revolt** — occupied stars lose loyalty each turn and revert to Empire at the threshold
5. **Random events** — 10 event types including reinforcements, espionage, resource discoveries, and pirate raids (can be disabled)
6. **AI turns** — Empire neutral faction and computer players act

### Planet types

| Char | Name | Effect |
|---|---|---|
| W | WarShip world | 1 WarShip per production credit |
| M | Missile world | 1 Missile per 2 credits |
| T | Transport world | 1 TranSport per 3 credits |
| S | StealthShip world | 1 StealthShip per 3 credits |
| F | Factory | Upgrades resource multiplier; also produces WarShips |
| P | Population | Grows up to 10 planets; each funds extra production |
| D | Terraform | Counts down 10 turns, then converts to a WarShip world |
| N | Neutral | No production |

### Ship types and fleet speeds

| Ship | Production cost | Transit speed |
|---|---|---|
| WarShip | 1 credit | 1× |
| StealthShip | 3 credits | 1× |
| TranSport | 3 credits | 1× |
| Missile | 2 credits | 2× (arrives in half the turns) |
| Scout | — | 1.5× |

### Production formula

```
credits = (4 − difficulty) × resource + base_prod
```

Higher `resource` values and lower difficulty produce more credits per turn. Novice mode gives player stars a flat 30 000 credits per turn.

### Ground combat

After capturing a star orbitally, planets remain under their original owners. Use the **Ground Combat** dialog to:
- **Bombard** — spend one orbital warship to kill troops and reduce the star's resource value
- **Invade** — commit invasion troops (delivered by TranSports) to take planets by force

### Revolt

Stars with foreign-occupied planets lose 1 loyalty per turn. At −10 the star reverts to Empire control and all planets are reset. Clear occupying troops to stop the decay.

---

## Project Structure

```
main.py                         Entry point and main game loop
tests/                          Unit tests (pytest)
second_conflict/
  model/
    constants.py                Ship types, planet types, file offsets, colours
    player.py                   Player dataclass
    star.py                     Star and Planet dataclasses
    fleet.py                    FleetInTransit and EmpireOrder (21-byte records)
    game_state.py               GameState, GameOptions, EventEntry
  io/
    scenario_parser.py          Load and write .scn / .sav binary files
  util/
    rng.py                      RNG wrapper matching FUN_1000_1f75 from SCW.EXE
    name_gen.py                 Random player name generator
  engine/
    distance.py                 Star distance and travel time calculations
    fleet_transit.py            Fleet movement (FUN_1088_0619)
    combat.py                   Orbital and ground combat (FUN_10b0_2f35)
    production.py               End-of-turn production (FUN_1088_13d8)
    revolt.py                   Loyalty decay and revolt (FUN_1088_1c9e)
    events.py                   10 random event types (FUN_1088_07a7)
    turn_runner.py              Full turn sequence orchestrator
  ai/
    empire_ai.py                Empire neutral AI (FUN_1088_0376)
    player_ai.py                Computer player AI
  ui/
    map_view.py                 Galaxy map: stars, fleet lines, click detection
    side_panel.py               Player stats strip and End Turn button
    sys_info_panel.py           Bottom panel: selected star detail and actions
    game_new.py                 New-game factory: random galaxy layout
    dialogs/
      base_dialog.py            Modal dialog base class
      new_game_dlg.py           New Game wizard
      open_game_dlg.py          Open save game (file list with preview)
      fleet_dlg.py              Fleet dispatch dialog
      fleet_view_dlg.py         View all in-transit fleets
      planet_detail_dlg.py      Star detail: planets, troops, garrison
      adm_view_dlg.py           Admin overview of all owned stars
      ground_combat_dlg.py      Bombard and invade UI
      combat_anim.py            Animated orbital battle viewer
      events_dlg.py             Turn dispatches / news ticker
      stats_dlg.py              Statistics table
      score_dlg.py              Victory / defeat screen
      star_editor_dlg.py        Dev mode: edit any star's raw values
```

For a deeper architectural walkthrough, see [structure.md](structure.md).

---

## Testing

```bash
pip install pytest
python -m pytest tests/ -v
```

110 unit tests covering combat, production, revolt, fleet transit, game state, distance calculations, and binary save/load round-trips.

---

## Reverse Engineering Notes

The original binary was analysed with **Ghidra 12.0**. Key functions:

| Function | Description |
|---|---|
| `FUN_1070_013f` | Save-file loader — confirms 10-section layout |
| `FUN_1070_0000` | Save-file writer |
| `FUN_1088_0619` | Fleet-in-transit processing (speed multipliers) |
| `FUN_10b0_2f35` | Combat resolution (3-round attrition) |
| `FUN_1088_13d8` | Production processing |
| `FUN_1088_1c9e` | Revolt / loyalty processing |
| `FUN_1088_07a7` | Random events (10 types) |
| `FUN_1088_0376` | Empire AI order dispatch |
| `FUN_1000_1f75` | RNG — `rand(n)` returns `[0, n−1]` |

The Ghidra project lives in `ghidra/`. The headless export is at `second-conflict/decomp_scw.txt` (538 functions, 25 826 lines).

### Save file layout

| Section | Offset | Size | Contents |
|---|---|---|---|
| Header | 0 | 18 | num_players, mode_flag, map_param, difficulty, **turn** (bytes 11–12), version |
| Star records | 18 | 2 574 | 26 × 99 bytes |
| Fleet transit | 2 592 | 8 400 | 400 × 21 bytes |
| Empire orders | 10 992 | 546 | 26 × 21 bytes |
| Unknown A | 11 538 | 2 860 | Preserved verbatim |
| Unknown B | 14 398 | 2 704 | Preserved verbatim |
| Unknown C | 17 102 | 40 | Preserved verbatim |
| Player records | 17 142 | 1 638 | 26 × 63 bytes; name at +0, attrs at +9 |
| Game state | 18 780 | 20 | Faction IDs (10 × uint16) |
| Scenario meta | 18 800 | 140 | Preserved verbatim |

> **Header bytes 11–12** store the current turn number (uint16 LE) — a Python extension not present in original SCW files. Original files have zero here, which the parser maps to turn 1.