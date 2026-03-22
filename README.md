# 🌴 Antihero System

**A dynamic NPC rivalry, memory, and hierarchy engine for Vice City-style open-world crime simulation games.**

Inspired by the *Nemesis System* (Shadow of Mordor), the Antihero System is a Python prototype that simulates living, breathing criminal underworld characters who *remember you*, *grow stronger*, *seek revenge*, and *fight each other* — even when you're not watching.

---

## ✨ Features

- **Procedural NPC generation** — Unique crime figures with names, nicknames, ranks, traits, strengths, weaknesses, and appearance
- **Persistent memory** — Every encounter is logged; NPCs remember defeats, betrayals, alliances, and bribes
- **Dynamic gang hierarchies** — Kill a boss, watch the power vacuum unfold in real time
- **Consequence engine** — Events cascade into world changes: gang wars, defections, turf takeovers
- **Autonomous NPCs** — Gang wars, promotions, and schemes happen even without the player
- **80s crime-movie dialogue** — Procedurally generated Vice City-flavored NPC reactions
- **Interactive CLI demo** — Full text-based game loop to experience the system in action

---

## 🏗 Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      AntiHeroEngine                            │
│              (antihero_system/simulation.py)                   │
│                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │  Generator  │  │   Memory    │  │  Hierarchy  │           │
│  │generator.py │  │  memory.py  │  │hierarchy.py │           │
│  │             │  │             │  │             │           │
│  │generate_npc │  │record_event │  │promote_npc  │           │
│  │generate_gang│  │get_history  │  │fill_vacuum  │           │
│  │generate_vc  │  │rival_score  │  │gang_war     │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
│                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ Consequence │  │  Dialogue   │  │   Models    │           │
│  │consequence  │  │ dialogue.py │  │  models.py  │           │
│  │             │  │             │  │             │           │
│  │process_event│  │gen_greeting │  │  NPC        │           │
│  │check_revenge│  │gen_threat   │  │  Gang       │           │
│  │update_world │  │gen_taunt    │  │  Event      │           │
│  └─────────────┘  └─────────────┘  │  District   │           │
│                                     └─────────────┘           │
└────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

| Module | Purpose |
|---|---|
| `models.py` | Core dataclasses: `NPC`, `Gang`, `District`, `Event`, `Rank`, `EventType` |
| `generator.py` | Procedural world generation with Vice City themed name pools |
| `memory.py` | `MemoryManager` — logs events, tracks NPC memories, calculates rivalry scores |
| `hierarchy.py` | `HierarchyManager` — promotions, demotions, power vacuums, gang wars |
| `consequence.py` | `ConsequenceEngine` — translates events into cascading world changes |
| `dialogue.py` | `DialogueGenerator` — 80s crime-movie style NPC dialogue generation |
| `simulation.py` | `AntiHeroEngine` — top-level orchestrator tying all systems together |

---

## 🚀 Quick Start

### Requirements

- Python 3.10+
- `colorama` (optional, for terminal colors)

```bash
pip install -r requirements.txt
```

### Run the Interactive Demo

```bash
python main.py
```

### Run the Tests

```bash
python -m pytest tests/test_antihero.py -v
```

---

## 🎮 Example Gameplay Session

```
🌴 ANTIHERO SYSTEM — VICE CITY
   A Dynamic NPC Rivalry Engine

Generating Vice City world...
✓ World generated: 5 gangs, 72 NPCs, 10 districts

─────────────────────────────────────────
  MAIN MENU
─────────────────────────────────────────
  1. View World Map & Gang Power
  2. Browse NPC Profiles & Hierarchies
  3. Attack an NPC
  ...

╔══════════════════════════════════════════╗
║          VICE CITY — TURF MAP            ║
╠══════════════════════════════════════════╣
║  Ocean Beach       [Vercetti Gang    ]   ║
║                    Heat: ██         22%  ║

[ATTACK] Miguel Diaz 'El Toro'

  Miguel Diaz: "I've been waiting for this moment, you snake."

  ⟹ World Consequences:
    • Miguel Diaz survived. They'll come back scarred and angrier.
    • 'El Toro' is now actively plotting revenge against you.

⚠  Miguel Diaz ('El Toro', Diaz Cartel) is hunting you down!
```

---

## 🌆 Vice City World

### Gangs

| Gang | Color | Home Territory |
|---|---|---|
| **Diaz Cartel** | 🔴 Red | Starfish Island, Prawn Island |
| **Vercetti Gang** | 🔵 Blue | Ocean Beach, Washington Beach |
| **Haitians** | 🟡 Yellow | Little Haiti |
| **Cubans** | 🟢 Green | Little Havana |
| **Bikers** | 🩵 Cyan | Vice Point, Leaf Links |

### Districts

Ocean Beach · Washington Beach · Little Havana · Little Haiti · Downtown · Starfish Island · Prawn Island · Vice Point · Leaf Links · Escobar International

### NPC Ranks (highest → lowest)

`Boss` → `Underboss` → `Captain` → `Enforcer` → `Dealer`

---

## 🔌 Integration Guide

The Antihero System is designed to be dropped into any Python game engine.

### Minimal Usage

```python
from antihero_system import AntiHeroEngine

# Initialize the world
engine = AntiHeroEngine()

# Player attacks an NPC
npc_id = engine.get_living_npcs()[0].npc_id
result = engine.player_action("attack", npc_id)

print(result["dialogue"])       # NPC's reaction
print(result["consequences"])   # World changes

# Advance simulation time
events = engine.advance_time()

# Query world state
state = engine.get_world_state()
```

### Custom Events

```python
from antihero_system import Event, EventType

event = Event(
    event_type=EventType.BETRAYAL,
    description="Player sold out Rodriguez to the police.",
    outcome="Rodriguez arrested and furious",
    involved_npcs=[rodriguez.npc_id],
    player_involved=True,
)
engine.consequence.process_event(event)
```

---

## 🎯 Design Principles

1. **Everything is data-driven** — NPCs, gangs, events are serializable dataclasses
2. **Memory is the core** — Every interaction is logged and influences future behavior
3. **Emergent storytelling** — The system creates narratives, not scripted events
4. **NPC autonomy** — NPCs act on their own even without the player
5. **Vice City flavor** — 80s Miami crime aesthetic in names, dialogue, and world design
6. **Modular and reusable** — Each component works independently in other games

---

## 📂 Project Structure

```
my-game-repo/
├── antihero_system/
│   ├── __init__.py        # Package exports
│   ├── models.py          # Core data models
│   ├── generator.py       # Procedural generation
│   ├── memory.py          # Memory & event tracking
│   ├── hierarchy.py       # Dynamic hierarchy system
│   ├── consequence.py     # Consequence engine
│   ├── dialogue.py        # Dialogue generation
│   └── simulation.py      # Main engine orchestrator
├── tests/
│   └── test_antihero.py   # 64 unit tests
├── main.py                # Interactive CLI demo
├── requirements.txt       # Dependencies
└── README.md              # This file
```

---

## License

MIT License — free to use in your own game projects.

---

*"In this city, everybody's got an angle. The question is whether yours is sharper."*
