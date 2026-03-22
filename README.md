# Antihero System

> A dynamic NPC rivalry, memory, and hierarchy engine for Vice City-style open-world crime simulation games.

---

## What is the Antihero System?

The **Antihero System** is a Python prototype of a living, breathing criminal underworld engine. Inspired by the *Nemesis System* but tailored for small-scale open-world crime games, it gives every NPC a memory, a personality, and the ability to respond meaningfully to the player's actions — and to act independently when the player isn't watching.

Every gang lieutenant you beat remembers it. Kill a boss and watch the power vacuum collapse into chaos. Bribe a captain and his gang loses respect for him. Betray an ally and they may defect to your enemies. The world keeps moving whether you do anything or not.

---

## Architecture

```
antihero_system/
│
├── __init__.py        ← Public API surface (exports everything)
│
├── models.py          ← Core data models
│   ├── NPC            ← Crime figures with memory & relationships
│   ├── Gang           ← Criminal organisations with hierarchy
│   ├── District       ← City turf with businesses & heat
│   └── Event          ← Recorded interactions
│
├── generator.py       ← Procedural world generation
│   ├── generate_npc()
│   ├── generate_gang()
│   ├── generate_district()
│   └── generate_vice_city()
│
├── memory.py          ← Event logging & relationship tracking
│   └── MemoryManager
│
├── hierarchy.py       ← Promotions, power vacuums, gang wars
│   └── HierarchyManager
│
├── consequence.py     ← Events → world-state changes
│   └── ConsequenceEngine
│
├── dialogue.py        ← Procedural NPC dialogue (80s crime flavour)
│   └── DialogueGenerator
│
└── simulation.py      ← Main orchestrator
    └── AntiHeroEngine
```

```
Player Action
     │
     ▼
AntiHeroEngine.player_action()
     │
     ├─► MemoryManager.record_event()   → updates NPC memory & relationships
     │
     ├─► ConsequenceEngine.process_event()
     │       ├─ ASSASSINATION → HierarchyManager.fill_power_vacuum()
     │       ├─ BETRAYAL      → NPC may defect to rival gang
     │       ├─ TURF_WAR      → territory / heat level changes
     │       └─ ...
     │
     └─► DialogueGenerator  → contextual NPC reaction line
```

---

## Gangs & Districts

| Gang | Colour | Style |
|---|---|---|
| Diaz Cartel | Yellow | Latin crime lords in linen suits |
| Vercetti Gang | Cyan | Italian-American organised crime |
| Haitians | Red | Street-level gang, numbers & aggression |
| Cubans | Green | Tight-knit community organisation |
| Bikers | Magenta | Outlaw motorcycle club |

| District | Flavour |
|---|---|
| Ocean Beach | Tourist strip hiding a drug trade |
| Little Havana | Cuban stronghold |
| Little Haiti | Haitian territory |
| Downtown | Everyone wants it |
| Starfish Island | Mansions, money, and murder |
| Leaf Links | Golf course fronting a cartel |
| Vice Point | Nightclub strip |
| Washington Beach | Police HQ nearby — high heat |
| Prawn Island | Film studio, smugglers |
| Escobar International | Airport — customs are... flexible |

---

## How to Run

### Prerequisites

```bash
pip install -r requirements.txt
```

### Interactive CLI Demo

```bash
python main.py
```

You'll see a text menu letting you:

- View the world map and gang territories
- Browse gang hierarchies (boss → dealer)
- Profile any NPC (traits, history, relationship score)
- Attack, assassinate, bribe, ally, or intimidate NPCs
- Start turf wars
- Advance world time (autonomous NPC actions, gang wars)
- Review your rivalry history

### Run Tests

```bash
python -m pytest tests/test_antihero.py -v
```

---

## Example Gameplay Session

```
══════════════════════════════════════════════════════════
  ANTIHERO SYSTEM — VICE CITY
══════════════════════════════════════════════════════════
  World generated: 5 gangs, 21 NPCs, 10 districts.

  [1] View World Map
  [2] View Gang Hierarchies
  [3] View NPC Profile
  [4] Attack an NPC
  ...

  Choice: 4

══════════════════════════════════════════════════════════
  ACTION: ATTACK
══════════════════════════════════════════════════════════

  [  1] El Diablo            Enforcer     Diaz Cartel         Ocean Beach          😐 0
  [  2] Chainsaw             Captain      Vercetti Gang       Downtown             😐 0

  Select target for Attack: 1

  🗣  "Sleep with one eye open — 'cause I won't forget what you did."

  ─── Consequences ───
  ➤  El Diablo survived the encounter — scarred and furious, they vow to get even.

══════════════════════════════════════════════════════════
  ADVANCING TIME…
══════════════════════════════════════════════════════════
  ➤  GANG WAR: Haitians vs Cubans for Little Haiti!
       Winner: Haitians (power 34 vs 28)
       Little Haiti now controlled by Haitians.
       Casualties from Cubans: Razor.
  ➤  Power vacuum in Cubans! Stone Cold rises from Enforcer to Captain!
```

---

## System Components

### `models.py` — Data Models

All models are Python `@dataclass` objects — serialisable, composable, no hidden state.

**NPC**
- Unique ID + procedurally generated name + street alias
- `Rank` enum: Boss → Underboss → Captain → Enforcer → Dealer
- Traits, strengths, weaknesses, appearance (all randomised)
- `relationships` dict: NPC ID → score (−100 to +100)
- `memory`: list of Event IDs this NPC remembers

**Event**
- `EventType`: DEFEAT, VICTORY, BETRAYAL, ALLIANCE, INTIMIDATION, ESCAPE, TURF_WAR, ASSASSINATION, BRIBE
- Timestamp, description, outcome
- `player_involved` flag

**Gang**
- Members list, ordered hierarchy, territory, rivals, allies
- `power_level()` computed from living member ranks

**District**
- `controlling_gang`, `heat_level` (0–100), businesses

### `generator.py` — Procedural Generation

Themed name pools for Latin, Italian, Haitian, Cuban, and Biker characters. Randomised trait/strength/weakness assignment. `generate_vice_city()` bootstraps a complete world in one call.

### `memory.py` — MemoryManager

Central event store. Every `record_event()` call:
1. Stores the full `Event` object
2. Appends the event ID to every involved NPC's memory list
3. Adjusts each NPC's player-relationship score by the event-type delta

Query methods: `get_npc_history()`, `get_player_history()`, `get_rivalry_score()`, `get_relationship_summary()`.

### `hierarchy.py` — HierarchyManager

- `promote_npc()` / `demote_npc()` — manual rank changes
- `fill_power_vacuum()` — automatically promotes the best-ranked successor when a leader dies; if no internal candidate exists, a rival gang makes its move
- `gang_war()` — power-based combat simulation with randomness; territory changes hands, casualties taken from the losing side
- `get_hierarchy_display()` — ASCII tree of the full gang structure

### `consequence.py` — ConsequenceEngine

Translates events into concrete world changes:

| Event | Consequence |
|---|---|
| ASSASSINATION | Power vacuum + ally relationship penalties |
| DEFEAT | NPC survives scarred, may queue for revenge |
| BETRAYAL | NPC may defect to rival gang |
| ALLIANCE | Relationship boost, crew goodwill |
| TURF_WAR | Territory + heat changes |
| BRIBE | Temporary trust but NPC loses gang respect |
| INTIMIDATION | Cowardly NPCs back down; brave ones escalate |

`update_world_state()` runs one autonomous tick: random gang wars, promotions for loyal NPCs.

### `dialogue.py` — DialogueGenerator

Template-driven, Vice City-flavoured dialogue with NPC-specific substitution:
- `generate_greeting()` — mood-based: hostile / neutral / allied / respected
- `generate_threat()` — references past events
- `generate_taunt()` — victory gloating + city flavour line
- `generate_respect()` — acknowledgement of player's rep
- `generate_betrayal_reaction()` — emotional explosion

### `simulation.py` — AntiHeroEngine

The single entry point for game integration:

```python
from antihero_system import AntiHeroEngine

engine = AntiHeroEngine()

# Player attacks an NPC
result = engine.player_action("attack", npc_id)
print(result["dialogue"])
print(result["consequences"])

# World advances one tick
updates = engine.advance_time()

# Query world state
state = engine.get_world_state()
rivals = engine.get_active_rivals()
allies = engine.get_potential_allies()
```

---

## How to Integrate Into Your Own Game

1. Install the package (copy the `antihero_system/` folder into your project).
2. Instantiate `AntiHeroEngine()` at game startup.
3. Call `engine.player_action(action_type, npc_id)` whenever the player does something to an NPC.
4. Call `engine.advance_time()` each in-game hour / day / tick.
5. Use `engine.get_npc_dialogue(npc_id, "greeting")` to fetch lines for NPC encounters.
6. Read `engine.get_active_rivals()` to drive enemy AI spawns.
7. Read `engine.get_world_state()` to update your minimap.

All data is plain Python dataclasses — serialise to JSON for save games with `dataclasses.asdict()`.

---

## Design Principles

1. **Everything is data-driven** — NPCs, gangs, events are serialisable dataclasses
2. **Memory is the core** — every interaction is logged and influences future behaviour
3. **Emergent storytelling** — the system creates narratives, not scripted events
4. **NPC autonomy** — NPCs act on their own even without player involvement
5. **Vice City flavour** — 80s Miami crime aesthetic in names, dialogue, and world design
6. **Modular and reusable** — each subsystem can be used independently
7. **Well-documented** — full docstrings, type hints throughout

---

## License

MIT — use freely in your own projects. Credits appreciated but not required.

---

## Credits

Inspired by the *Nemesis System* (Middle-earth: Shadow of Mordor / Shadow of War, Warner Bros. Games).
Vice City world design inspired by Rockstar Games' *Grand Theft Auto: Vice City*.
Built entirely with Python stdlib + `colorama` for terminal colour support.
