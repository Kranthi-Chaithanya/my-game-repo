"""
Core data models for the Antihero System.

All models are Python dataclasses, making them easily serializable and
extensible for integration into other game engines.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Rank(Enum):
    """Hierarchical rank within a criminal gang."""
    BOSS = "Boss"
    UNDERBOSS = "Underboss"
    CAPTAIN = "Captain"
    ENFORCER = "Enforcer"
    DEALER = "Dealer"


class EventType(Enum):
    """Types of recorded interactions between the player and NPCs."""
    DEFEAT = "DEFEAT"           # Player defeated the NPC
    VICTORY = "VICTORY"         # NPC defeated the player
    BETRAYAL = "BETRAYAL"       # NPC or player betrayed an alliance
    ALLIANCE = "ALLIANCE"       # Alliance formed
    INTIMIDATION = "INTIMIDATION"  # Player intimidated the NPC
    ESCAPE = "ESCAPE"           # NPC escaped from a confrontation
    TURF_WAR = "TURF_WAR"       # A district changed hands
    ASSASSINATION = "ASSASSINATION"  # An NPC was assassinated
    BRIBE = "BRIBE"             # Player bribed the NPC


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

@dataclass
class Event:
    """A recorded interaction or world occurrence.

    Attributes:
        event_id:       Unique identifier for this event.
        event_type:     Category of event (see :class:`EventType`).
        timestamp:      When the event occurred.
        description:    Human-readable narrative description.
        involved_npcs:  IDs of NPCs who participated in or witnessed the event.
        outcome:        Brief summary of the result (e.g., "NPC fled south").
        player_involved: ``True`` when the player was a direct participant.
    """
    event_type: EventType
    description: str
    involved_npcs: List[str] = field(default_factory=list)
    outcome: str = ""
    player_involved: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# NPC
# ---------------------------------------------------------------------------

@dataclass
class NPC:
    """Represents a crime figure in the Vice City world.

    Attributes:
        npc_id:        Unique identifier.
        name:          Full name (procedurally generated).
        nickname:      Street alias (e.g., "El Diablo").
        rank:          Current rank in the gang hierarchy.
        gang:          Name of the affiliated gang.
        traits:        Personality traits influencing behaviour.
        strengths:     Combat / social advantages.
        weaknesses:    Exploitable vulnerabilities.
        appearance:    Procedural visual descriptors (scars, tattoos, style).
        alive:         Whether the NPC is still alive.
        health:        Hit points (0–100).
        respect_level: Street reputation score (0–100).
        memory:        Ordered list of :class:`Event` IDs this NPC remembers.
        relationships: Mapping of NPC ID → relationship score (−100 to 100).
        territory:     District name this NPC controls or operates in.
    """
    npc_id: str
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
    respect_level: int = 50
    memory: List[str] = field(default_factory=list)          # event_ids
    relationships: Dict[str, int] = field(default_factory=dict)
    territory: str = "Unknown"

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def is_hostile_to_player(self) -> bool:
        """Return ``True`` when this NPC has a negative player relationship."""
        return self.relationships.get("player", 0) < -20

    def is_allied_with_player(self) -> bool:
        """Return ``True`` when this NPC has a positive player relationship."""
        return self.relationships.get("player", 0) > 30

    def adjust_player_relationship(self, delta: int) -> None:
        """Clamp and apply *delta* to the player relationship score."""
        current = self.relationships.get("player", 0)
        self.relationships["player"] = max(-100, min(100, current + delta))

    def __repr__(self) -> str:
        status = "alive" if self.alive else "dead"
        return (
            f"<NPC '{self.nickname}' ({self.name}) | "
            f"{self.rank.value} of {self.gang} | {status}>"
        )


# ---------------------------------------------------------------------------
# Gang
# ---------------------------------------------------------------------------

@dataclass
class Gang:
    """Represents a criminal organisation.

    Attributes:
        name:          Gang name (e.g., "Diaz Cartel").
        color:         Identifying colour used for map display.
        territory:     Districts currently controlled by this gang.
        members:       NPC IDs belonging to this gang.
        hierarchy:     Ordered list of NPC IDs from boss down to dealer.
        rival_gangs:   Names of rival organisations.
        allied_gangs:  Names of allied organisations.
    """
    name: str
    color: str = "white"
    territory: List[str] = field(default_factory=list)
    members: List[str] = field(default_factory=list)      # npc_ids
    hierarchy: List[str] = field(default_factory=list)    # ordered npc_ids
    rival_gangs: List[str] = field(default_factory=list)
    allied_gangs: List[str] = field(default_factory=list)

    def power_level(self, npcs: Dict[str, NPC]) -> int:
        """Compute overall gang strength from living members."""
        total = 0
        for npc_id in self.members:
            npc = npcs.get(npc_id)
            if npc and npc.alive:
                rank_weights = {
                    Rank.BOSS: 20,
                    Rank.UNDERBOSS: 15,
                    Rank.CAPTAIN: 10,
                    Rank.ENFORCER: 5,
                    Rank.DEALER: 2,
                }
                total += rank_weights.get(npc.rank, 1)
        return total

    def __repr__(self) -> str:
        return f"<Gang '{self.name}' | {len(self.members)} members | {len(self.territory)} districts>"


# ---------------------------------------------------------------------------
# District
# ---------------------------------------------------------------------------

@dataclass
class District:
    """Represents a city district / turf.

    Attributes:
        name:             District name (e.g., "Ocean Beach").
        controlling_gang: Name of the gang that currently owns this district.
        heat_level:       Police attention level (0–100).
        businesses:       List of racket types operating here.
    """
    name: str
    controlling_gang: str = "None"
    heat_level: int = 20
    businesses: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"<District '{self.name}' | "
            f"Controlled by: {self.controlling_gang} | "
            f"Heat: {self.heat_level}>"
        )
