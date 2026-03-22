"""
Antihero System — Dynamic NPC rivalry, memory, and hierarchy engine.

Exports the main public API surface.
"""

from .models import NPC, Gang, District, Event, Rank, EventType
from .generator import generate_npc, generate_gang, generate_district, generate_vice_city
from .memory import MemoryManager
from .hierarchy import HierarchyManager
from .consequence import ConsequenceEngine
from .dialogue import DialogueGenerator
from .simulation import AntiHeroEngine

__all__ = [
    # Models
    "NPC",
    "Gang",
    "District",
    "Event",
    "Rank",
    "EventType",
    # Generators
    "generate_npc",
    "generate_gang",
    "generate_district",
    "generate_vice_city",
    # Engine subsystems
    "MemoryManager",
    "HierarchyManager",
    "ConsequenceEngine",
    "DialogueGenerator",
    # Main engine
    "AntiHeroEngine",
]
