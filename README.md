# Second Conflict

A Python/pygame recreation of *Second Conflict* (1991, Windows 3.x) by Jerry W. Galloway.

Game mechanics are faithfully translated from the original `SCW.EXE` binary via Ghidra decompilation. File format compatibility with the original `.scn` scenario files is a stretch goal.

---

## Requirements

- Python 3.11+
- pygame 2.x

```bash
python -m venv .venv
source .venv/bin/activate
pip install pygame
```

---

## Running

```bash
# Start with the New Game wizard
python main.py

# Load an original scenario file
python main.py second-conflict/somefile.scn
```

---

## Controls

| Input | Action |
|---|---|
| Left-click star | Select star |
| Right-click star / double-click star | Open fleet dispatch dialog |
| End Turn button | Process the turn |
| F1 | Statistics table |
| Ctrl+N | New game |
| Ctrl+O | Open scenario file |
| Escape | Close dialog |

---

## Project Structure

```
main.py                         Entry point and main game loop
second_conflict/
  model/
    constants.py                Ship types, planet types, file offsets, colours
    player.py                   Player dataclass (27 attributes from decompilation)
    star.py                     Star and GarrisonEntry dataclasses
    fleet.py                    FleetInTransit and EmpireOrder (21-byte records)
    game_state.py               GameState, GameOptions, EventEntry
  io/
    scenario_parser.py          Load original .scn / .sav files into GameState
  util/
    rng.py                      RNG wrapper matching FUN_1000_1f75 from SCW.EXE
  engine/
    distance.py                 Star distance and travel time calculations
    fleet_transit.py            Fleet movement (FUN_1088_0619): sim sub-steps,
                                speed multipliers, arrival and combat queuing
    combat.py                   3-round attrition combat (FUN_10b0_2f35)
    production.py               End-of-turn production by planet type (FUN_1088_13d8)
    revolt.py                   Loyalty decay and revolt (FUN_1088_1c9e)
    events.py                   10 random event types (FUN_1088_07a7)
    turn_runner.py              Full turn sequence orchestrator
  ai/
    empire_ai.py                Empire neutral AI (FUN_1088_0376)
    player_ai.py                Computer player AI (threat / attack heuristics)
  ui/
    map_view.py                 Galaxy map: stars, fleet lines, click detection
    side_panel.py               Player stats strip and End Turn button
    game_new.py                 New-game factory: random galaxy layout
    dialogs/
      base_dialog.py            Modal dialog base class
      fleet_dlg.py              Fleet dispatch dialog (FLEETDLG)
      events_dlg.py             Turn dispatches / news ticker
      new_game_dlg.py           New Game wizard (NEWGAMEDLG1/2/3)
      stats_dlg.py              Statistics table (STATSVIEWDLG)
```

---

## Game Mechanics

All mechanics are translated from the Ghidra decompilation of `SCW.EXE` (275 456 bytes, Windows 3.x NE executable).

### Turn sequence

1. Fleet movement — each fleet's `turns_remaining` is decremented across `sim_steps` sub-steps per turn (6 for 10-player games, 5 for 2-player)
2. Combat resolution — 3-round attrition at any star with multiple factions
3. Production — credits formula: `(4 − difficulty) × resource + base_prod`
4. Revolt / loyalty — loyalty decays when foreign factions share a star; revolt fires at threshold −3
5. Random events — 10 event types, probability-gated by difficulty
6. AI — Empire neutral faction and computer player orders

### Ship types

| Type | Code | Production cost |
|---|---|---|
| WarShip | W | 1 credit |
| StealthShip | S | — |
| TranSport | T | 3 credits |
| Missile | M | 2 credits |
| Scout | S | 3 credits |
| Privateer | P | — |
| Probe | B | — |

### Fleet speeds

| Fleet type | Speed |
|---|---|
| Combat / Transport | 1× |
| Missile | 2× (−2 per sub-step) |
| Scout | 1.5× (−2 on odd sub-steps) |

### Planet types

| Char | Type | Effect |
|---|---|---|
| W | WarShip world | Produces 1 WarShip per credit |
| M | Missile world | 1 Missile per 2 credits |
| T | Transport world | 1 TranSport per 3 credits |
| S | Scout world | 1 Scout per 3 credits |
| F | Factory | Resource grows each turn; also produces WarShips |
| P | Population | Population grows up to 10; each unit produces 1 WarShip/turn |
| D | Dead world | Terraforms into a WarShip world after 10 turns of ownership |
| N | Neutral | No production |

---

## Reverse Engineering Notes

The original binary was analysed with **Ghidra 12.0** (headless export via `analyzeHeadless`). Key functions:

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

The Ghidra project lives in `ghidra/`. The headless export (`decomp_scw.txt`, 538 functions, 25 826 lines) is at `second-conflict/decomp_scw.txt`.

### Save file layout

| Section | Offset | Size | Contents |
|---|---|---|---|
| Header | 0 | 18 | Version, player count, star count, sim_steps, difficulty |
| Star records | 18 | 2574 | 26 × 99 bytes |
| Fleet transit | 2592 | 8400 | 400 × 21 bytes |
| Empire orders | 10992 | 546 | 26 × 21 bytes |
| Unknown A | 11538 | 2860 | |
| Unknown B | 14398 | 2704 | |
| Unknown C | 17102 | 40 | |
| Player records | 17142 | 1638 | 26 × 63 bytes; name at +0, attrs at +9 |
| Game state | 18780 | 20 | Faction IDs |
| Scenario meta | 18800 | 140 | |