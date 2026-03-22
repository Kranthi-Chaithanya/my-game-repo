"""
Memory and event tracking system for the Antihero System.

Every player–NPC and NPC–NPC interaction is logged here.  NPCs can then
query their personal history to decide how to react to the player.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .models import Event, EventType, NPC


# ---------------------------------------------------------------------------
# Rivalry score deltas per event type
# ---------------------------------------------------------------------------
# Positive = NPC respects/likes the player more.
# Negative = NPC hates the player more.

_RIVALRY_DELTAS: Dict[EventType, int] = {
    EventType.DEFEAT: -25,          # player beat the NPC
    EventType.VICTORY: +15,         # NPC beat the player (they enjoy it)
    EventType.BETRAYAL: -40,        # player betrayed the NPC
    EventType.ALLIANCE: +20,        # player allied with the NPC
    EventType.INTIMIDATION: -10,    # player intimidated the NPC
    EventType.ESCAPE: -5,           # NPC escaped — minor humiliation
    EventType.TURF_WAR: -20,        # player stole territory
    EventType.ASSASSINATION: -50,   # player killed someone important
    EventType.BRIBE: +10,           # player bribed the NPC (pragmatic trust)
}


class MemoryManager:
    """Centralised store for all world events.

    NPCs reference events by ID; the full :class:`~antihero_system.models.Event`
    objects live here.

    Args:
        npcs: Shared NPC registry (``npc_id → NPC``).  The manager updates
              NPC memory lists whenever a relevant event is recorded.
    """

    def __init__(self, npcs: Dict[str, NPC]) -> None:
        self._events: Dict[str, Event] = {}          # event_id → Event
        self._player_events: List[str] = []          # event_ids involving player
        self._npcs = npcs

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_event(self, event: Event) -> None:
        """Log *event* and push it into every involved NPC's memory.

        Args:
            event: The :class:`~antihero_system.models.Event` to record.
        """
        self._events[event.event_id] = event

        if event.player_involved:
            self._player_events.append(event.event_id)

        # Push event into involved NPCs' memory lists
        for npc_id in event.involved_npcs:
            npc = self._npcs.get(npc_id)
            if npc:
                if event.event_id not in npc.memory:
                    npc.memory.append(event.event_id)
                # Adjust player relationship score when player was involved
                if event.player_involved:
                    delta = _RIVALRY_DELTAS.get(event.event_type, 0)
                    npc.adjust_player_relationship(delta)

    def get_event(self, event_id: str) -> Optional[Event]:
        """Return the :class:`~antihero_system.models.Event` for *event_id*."""
        return self._events.get(event_id)

    def get_npc_history(self, npc_id: str) -> List[Event]:
        """Return all events that *npc_id* personally remembers.

        Args:
            npc_id: The ID of the NPC whose history to retrieve.

        Returns:
            Chronologically ordered list of :class:`~antihero_system.models.Event`
            objects, oldest first.
        """
        npc = self._npcs.get(npc_id)
        if not npc:
            return []
        events = [self._events[eid] for eid in npc.memory if eid in self._events]
        return sorted(events, key=lambda e: e.timestamp)

    def get_player_history(self) -> List[Event]:
        """Return all player-involved events, oldest first."""
        events = [self._events[eid] for eid in self._player_events if eid in self._events]
        return sorted(events, key=lambda e: e.timestamp)

    def get_rivalry_score(self, npc_id: str) -> int:
        """Calculate how much *npc_id* hates / respects the player.

        The score is the NPC's current ``relationships["player"]`` value, which
        is updated incrementally each time an event is recorded.

        Returns:
            An integer in the range −100 (pure hatred) to +100 (full respect).
        """
        npc = self._npcs.get(npc_id)
        if not npc:
            return 0
        return npc.relationships.get("player", 0)

    def get_relationship_summary(self, npc_id: str) -> str:
        """Return a narrative description of the NPC's feelings toward the player.

        Args:
            npc_id: Target NPC identifier.

        Returns:
            A short English sentence describing the relationship.
        """
        score = self.get_rivalry_score(npc_id)
        npc = self._npcs.get(npc_id)
        name = npc.nickname if npc else npc_id

        if score >= 60:
            return f'"{name}" deeply respects and trusts you. They consider you a true ally.'
        elif score >= 30:
            return f'"{name}" likes you and is open to cooperation.'
        elif score >= 0:
            return f'"{name}" is neutral toward you — watching and waiting.'
        elif score >= -30:
            return f'"{name}" is suspicious of you and keeps their distance.'
        elif score >= -60:
            return f'"{name}" resents you and will look for an opportunity to strike back.'
        else:
            return f'"{name}" hates you with a passion and is actively plotting revenge.'

    def all_events(self) -> List[Event]:
        """Return every recorded event, oldest first."""
        return sorted(self._events.values(), key=lambda e: e.timestamp)
