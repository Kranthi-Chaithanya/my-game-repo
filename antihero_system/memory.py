"""
Memory and event tracking system for the Antihero System.

MemoryManager logs all events, maintains NPC memory, and provides
analysis utilities for understanding rivalries and relationships.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from .models import Event, EventType, NPC


# Weights for calculating rivalry/respect scores from event history
_EVENT_SCORE: Dict[EventType, int] = {
    EventType.DEFEAT:        -20,   # Player defeated NPC → NPC hates player more
    EventType.VICTORY:        15,   # NPC beat player → NPC gains confidence
    EventType.BETRAYAL:      -40,   # Player betrayed NPC → massive hatred
    EventType.ALLIANCE:       25,   # Alliance formed → positive relationship
    EventType.INTIMIDATION:  -10,   # Player intimidated NPC → fear/resentment
    EventType.ESCAPE:         10,   # NPC escaped → small confidence boost
    EventType.TURF_WAR:      -15,   # Turf war → territorial resentment
    EventType.ASSASSINATION: -50,   # Targeted assassination → max hatred
    EventType.BRIBE:           5,   # Bribe → mild positive (but respect loss)
}

# Narrative templates for relationship summaries
_RELATIONSHIP_TEMPLATES: Dict[str, List[str]] = {
    "hostile": [
        "{name} wants you dead. They haven't forgotten what you did.",
        "{name} seethes with rage every time your name comes up.",
        "'{nickname}' has sworn vengeance. Watch your back.",
        "{name} is biding their time, waiting for the perfect moment to strike.",
    ],
    "unfriendly": [
        "{name} doesn't trust you. Every deal is done with a gun on the table.",
        "'{nickname}' has no love for you, but business is business.",
        "{name} tolerates your presence — for now.",
    ],
    "neutral": [
        "{name} doesn't have strong feelings about you. Yet.",
        "'{nickname}' has heard your name but you're not on their radar.",
        "{name} is sizing you up. Could go either way.",
    ],
    "friendly": [
        "{name} respects what you've built. They're open to conversation.",
        "'{nickname}' considers you a useful contact.",
        "{name} has heard good things about you on the street.",
    ],
    "allied": [
        "{name} has your back. A true partner in crime.",
        "'{nickname}' would take a bullet for you — probably.",
        "{name} considers you family. That means something in this city.",
    ],
}


class MemoryManager:
    """
    Central event log and NPC memory system.

    Attributes:
        events: All recorded events ordered chronologically.
        npc_events: Mapping from npc_id to list of relevant event IDs.
        player_events: List of event IDs involving the player.
    """

    def __init__(self, npcs: Optional[Dict[str, NPC]] = None) -> None:
        self._npcs: Dict[str, NPC] = npcs or {}
        self.events: Dict[str, Event] = {}            # event_id → Event
        self._npc_events: Dict[str, List[str]] = defaultdict(list)  # npc_id → [event_id]
        self._player_events: List[str] = []

    def set_npcs(self, npcs: Dict[str, NPC]) -> None:
        """Update the NPC registry (called after world generation)."""
        self._npcs = npcs

    # ------------------------------------------------------------------
    # Event recording
    # ------------------------------------------------------------------

    def record_event(self, event: Event) -> None:
        """
        Log an event and update relevant NPC memories.

        Also adjusts NPC relationships with the player based on event type.
        """
        self.events[event.event_id] = event

        # Index by involved NPCs
        for npc_id in event.involved_npcs:
            self._npc_events[npc_id].append(event.event_id)
            # Update the NPC's personal memory and player relationship
            npc = self._npcs.get(npc_id)
            if npc:
                npc.add_memory(event)
                if event.player_involved:
                    delta = _EVENT_SCORE.get(event.event_type, 0)
                    npc.update_relationship("player", delta)
                    # If hatred is deep enough, flag for revenge
                    if npc.relationships.get("player", 0) <= -60:
                        npc.revenge_ready = True

        if event.player_involved:
            self._player_events.append(event.event_id)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_npc_history(self, npc_id: str) -> List[Event]:
        """Return all events involving the specified NPC."""
        event_ids = self._npc_events.get(npc_id, [])
        return [self.events[eid] for eid in event_ids if eid in self.events]

    def get_player_history(self) -> List[Event]:
        """Return all player-involved events in chronological order."""
        return [self.events[eid] for eid in self._player_events if eid in self.events]

    def get_rivalry_score(self, npc_id: str) -> int:
        """
        Calculate how much an NPC hates/respects the player.

        Returns a score between -100 (max hatred) and +100 (max respect).
        Negative = hostile, positive = friendly.
        """
        npc = self._npcs.get(npc_id)
        if npc:
            return npc.relationships.get("player", 0)
        # Fallback: compute from event history
        score = 0
        for event in self.get_npc_history(npc_id):
            if event.player_involved:
                score += _EVENT_SCORE.get(event.event_type, 0)
        return max(-100, min(100, score))

    def get_relationship_summary(self, npc_id: str) -> str:
        """Return a narrative summary of an NPC's feelings toward the player."""
        npc = self._npcs.get(npc_id)
        if not npc:
            return "Unknown NPC."

        score = self.get_rivalry_score(npc_id)

        if score <= -60:
            category = "hostile"
        elif score <= -20:
            category = "unfriendly"
        elif score <= 20:
            category = "neutral"
        elif score <= 60:
            category = "friendly"
        else:
            category = "allied"

        import random
        template = random.choice(_RELATIONSHIP_TEMPLATES[category])
        return template.format(name=npc.name, nickname=npc.nickname)

    def npcs_seeking_revenge(self) -> List[str]:
        """Return list of NPC IDs that are currently seeking revenge."""
        return [
            npc_id
            for npc_id, npc in self._npcs.items()
            if npc.alive and npc.revenge_ready
        ]
