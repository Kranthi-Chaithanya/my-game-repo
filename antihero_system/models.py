"""
Core data models for the Antihero System.

Defines NPC, Event, Gang, and District dataclasses that power the
dynamic NPC rivalry, memory, and hierarchy engine.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Rank(Enum):
    """Criminal hierarchy ranks, from highest to lowest."""
    BOSS = "Boss"
    UNDERBOSS = "Underboss"
    CAPTAIN = "Captain"
    ENFORCER = "Enforcer"
    DEALER = "Dealer"


RANK_ORDER: List[Rank] = [
    Rank.BOSS,
    Rank.UNDERBOSS,
    Rank.CAPTAIN,
    Rank.ENFORCER,
    Rank.DEALER,
]


class EventType(Enum):
    """Types of events that can be recorded in the memory system."""
    DEFEAT = "DEFEAT"               # Player defeated NPC
    VICTORY = "VICTORY"             # NPC defeated player
    BETRAYAL = "BETRAYAL"           # NPC was betrayed by player
    ALLIANCE = "ALLIANCE"           # Alliance formed
    INTIMIDATION = "INTIMIDATION"   # NPC was intimidated
    ESCAPE = "ESCAPE"               # NPC escaped from player
    TURF_WAR = "TURF_WAR"           # Turf war event
    ASSASSINATION = "ASSASSINATION" # NPC was assassinated
    BRIBE = "BRIBE"                 # NPC was bribed


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

@dataclass
class Event:
    """Represents a recorded interaction in the world."""

    event_type: EventType
    description: str
    outcome: str
    involved_npcs: List[str] = field(default_factory=list)   # NPC IDs
    player_involved: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if isinstance(self.event_type, str):
            self.event_type = EventType(self.event_type)


# ---------------------------------------------------------------------------
# NPC
# ---------------------------------------------------------------------------

@dataclass
class NPC:
    """Represents a crime figure NPC in the world."""

    name: str
    nickname: str
    rank: Rank
    gang: str
    traits: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    appearance: Dict[str, str] = field(default_factory=dict)
    alive: bool = True
    health: int = 100
    respect_level: int = 50           # 0-100
    memory: List[Event] = field(default_factory=list)
    relationships: Dict[str, int] = field(default_factory=dict)  # npc_id → score (-100..100)
    territory: str = ""
    npc_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scarred: bool = False             # Returned stronger after defeat
    revenge_ready: bool = False       # Ready to seek revenge on the player

    def __post_init__(self) -> None:
        if isinstance(self.rank, str):
            self.rank = Rank(self.rank)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def add_memory(self, event: Event) -> None:
        """Append an event to this NPC's personal memory."""
        self.memory.append(event)

    def update_relationship(self, other_id: str, delta: int) -> None:
        """Adjust the relationship score toward another NPC/player."""
        current = self.relationships.get(other_id, 0)
        self.relationships[other_id] = max(-100, min(100, current + delta))

    def is_hostile_to_player(self) -> bool:
        """Return True if this NPC has a negative relationship with the player."""
        return self.relationships.get("player", 0) < -20

    def is_friendly_to_player(self) -> bool:
        """Return True if this NPC has a positive relationship with the player."""
        return self.relationships.get("player", 0) > 20

    def display_name(self) -> str:
        """Return the NPC's formatted display name."""
        return f"{self.name} '{self.nickname}'"

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"NPC({self.name!r}, rank={self.rank.value}, "
            f"gang={self.gang!r}, alive={self.alive})"
        )


# ---------------------------------------------------------------------------
# Gang
# ---------------------------------------------------------------------------

@dataclass
class Gang:
    """Represents a criminal organization."""

    name: str
    color: str                                      # Terminal color identifier
    territory: List[str] = field(default_factory=list)   # district names
    members: List[str] = field(default_factory=list)     # NPC IDs
    hierarchy: Dict[str, List[str]] = field(default_factory=dict)  # rank → [npc_id]
    rival_gangs: List[str] = field(default_factory=list)
    allied_gangs: List[str] = field(default_factory=list)
    gang_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def power_level(self, npcs: Dict[str, NPC]) -> int:
        """Calculate overall gang strength from living members."""
        total = 0
        rank_weights = {
            Rank.BOSS: 20,
            Rank.UNDERBOSS: 15,
            Rank.CAPTAIN: 10,
            Rank.ENFORCER: 5,
            Rank.DEALER: 2,
        }
        for npc_id in self.members:
            npc = npcs.get(npc_id)
            if npc and npc.alive:
                total += rank_weights.get(npc.rank, 1)
        return total

    def get_leader(self, npcs: Dict[str, NPC]) -> Optional[NPC]:
        """Return the current Boss of the gang, or None."""
        boss_ids = self.hierarchy.get(Rank.BOSS.value, [])
        for bid in boss_ids:
            npc = npcs.get(bid)
            if npc and npc.alive:
                return npc
        return None

    def living_members(self, npcs: Dict[str, NPC]) -> List[NPC]:
        """Return all living members of this gang."""
        return [npcs[mid] for mid in self.members if mid in npcs and npcs[mid].alive]

    def add_member(self, npc: NPC) -> None:
        """Add an NPC to the gang's membership and hierarchy."""
        if npc.npc_id not in self.members:
            self.members.append(npc.npc_id)
        rank_key = npc.rank.value
        if rank_key not in self.hierarchy:
            self.hierarchy[rank_key] = []
        if npc.npc_id not in self.hierarchy[rank_key]:
            self.hierarchy[rank_key].append(npc.npc_id)

    def remove_member(self, npc_id: str) -> None:
        """Remove an NPC from the gang roster and hierarchy."""
        if npc_id in self.members:
            self.members.remove(npc_id)
        for rank_list in self.hierarchy.values():
            if npc_id in rank_list:
                rank_list.remove(npc_id)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Gang({self.name!r}, members={len(self.members)})"


# ---------------------------------------------------------------------------
# District
# ---------------------------------------------------------------------------

@dataclass
class District:
    """Represents a city area / turf."""

    name: str
    controlling_gang: Optional[str] = None   # Gang name
    heat_level: int = 20                     # Police attention 0-100
    businesses: List[str] = field(default_factory=list)  # racket types
    district_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def add_heat(self, amount: int) -> None:
        """Increase police attention."""
        self.heat_level = min(100, self.heat_level + amount)

    def reduce_heat(self, amount: int) -> None:
        """Reduce police attention."""
        self.heat_level = max(0, self.heat_level - amount)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"District({self.name!r}, "
            f"gang={self.controlling_gang!r}, heat={self.heat_level})"
        )
