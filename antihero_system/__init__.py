"""
Antihero System — Dynamic NPC Rivalry, Memory & Hierarchy Engine

A Vice City-style open-world crime simulation NPC engine featuring:
- Procedural NPC generation
- Persistent NPC memory and rivalry tracking
- Dynamic gang hierarchies with power vacuums
- Consequence-driven world changes
- 80s crime-movie procedural dialogue
"""

from .consequence import ConsequenceEngine
from .dialogue import DialogueGenerator
from .generator import (
    generate_district,
    generate_gang,
    generate_npc,
    generate_vice_city,
)
from .hierarchy import HierarchyManager
from .memory import MemoryManager
from .models import District, Event, EventType, Gang, NPC, Rank
from .simulation import AntiHeroEngine

__all__ = [
    # Engine
    "AntiHeroEngine",
    # Managers
    "MemoryManager",
    "HierarchyManager",
    "ConsequenceEngine",
    "DialogueGenerator",
    # Generation
    "generate_npc",
    "generate_gang",
    "generate_district",
    "generate_vice_city",
    # Models
    "NPC",
    "Gang",
    "District",
    "Event",
    "EventType",
    "Rank",
]
