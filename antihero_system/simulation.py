"""
Main simulation engine for the Antihero System.

``AntiHeroEngine`` is the single entry-point for game code: it wires all
subsystems together and exposes a clean, action-based API.
"""

from __future__ import annotations

import random
import uuid
from typing import Any, Dict, List, Optional

from .consequence import ConsequenceEngine
from .dialogue import DialogueGenerator
from .generator import generate_vice_city
from .hierarchy import HierarchyManager
from .memory import MemoryManager
from .models import District, Event, EventType, Gang, NPC, Rank


# ---------------------------------------------------------------------------
# Action type literals
# ---------------------------------------------------------------------------

ACTION_ATTACK = "attack"
ACTION_ASSASSINATE = "assassinate"
ACTION_BRIBE = "bribe"
ACTION_ALLY = "ally"
ACTION_INTIMIDATE = "intimidate"
ACTION_TURF_WAR = "turf_war"


class AntiHeroEngine:
    """The main orchestrator for the Antihero System.

    On construction, a complete Vice City world is generated.  All
    subsequent interactions flow through this object.

    Example::

        engine = AntiHeroEngine()
        results = engine.player_action("attack", some_npc_id)
        engine.advance_time()
        state = engine.get_world_state()
    """

    def __init__(self) -> None:
        self.gangs: Dict[str, Gang]
        self.npcs: Dict[str, NPC]
        self.districts: Dict[str, District]

        self.gangs, self.npcs, self.districts = generate_vice_city()

        self.memory = MemoryManager(self.npcs)
        self.hierarchy = HierarchyManager(self.gangs, self.npcs, self.districts)
        self.consequence = ConsequenceEngine(
            self.gangs, self.npcs, self.districts, self.hierarchy, self.memory
        )
        self.dialogue = DialogueGenerator()

        self._time_step: int = 0

    # ------------------------------------------------------------------
    # Player actions
    # ------------------------------------------------------------------

    def player_action(
        self,
        action_type: str,
        target_npc_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Process a player action against a target NPC.

        Args:
            action_type:   One of the ``ACTION_*`` constants.
            target_npc_id: The NPC being acted upon.
            **kwargs:      Extra context (e.g., ``district`` for turf_war).

        Returns:
            A dict with keys:
            - ``"success"`` (bool)
            - ``"dialogue"`` (str) — NPC's reaction
            - ``"consequences"`` (list[str]) — world changes
            - ``"revenge_alerts"`` (list[str]) — newly enraged NPCs
        """
        npc = self.npcs.get(target_npc_id)
        if not npc:
            return {"success": False, "dialogue": "Target not found.", "consequences": [], "revenge_alerts": []}
        if not npc.alive:
            return {"success": False, "dialogue": f"{npc.nickname} is already dead.", "consequences": [], "revenge_alerts": []}

        event_type, description, outcome, dialogue = self._resolve_action(
            action_type, npc, **kwargs
        )

        event = Event(
            event_type=event_type,
            description=description,
            involved_npcs=[target_npc_id],
            outcome=outcome,
            player_involved=True,
        )
        self.memory.record_event(event)
        consequences = self.consequence.process_event(event)
        revenge_alerts = self.consequence.check_revenge_triggers()

        return {
            "success": True,
            "dialogue": dialogue,
            "consequences": consequences,
            "revenge_alerts": revenge_alerts,
        }

    # ------------------------------------------------------------------
    # World simulation
    # ------------------------------------------------------------------

    def advance_time(self) -> List[str]:
        """Simulate one world time step.

        NPCs act autonomously, gang wars may break out, and hierarchy
        changes happen without player input.

        Returns:
            List of narrative strings describing what happened this tick.
        """
        self._time_step += 1
        updates = self.consequence.update_world_state()
        return updates

    # ------------------------------------------------------------------
    # Information queries
    # ------------------------------------------------------------------

    def get_world_state(self) -> Dict[str, Any]:
        """Return a snapshot of the current world state.

        Returns:
            Dict containing ``"gangs"``, ``"districts"``, and ``"npc_count"``.
        """
        gang_summaries = {}
        for gname, gang in self.gangs.items():
            living = sum(1 for nid in gang.members if (npc := self.npcs.get(nid)) and npc.alive)
            gang_summaries[gname] = {
                "territory": gang.territory,
                "power": self.hierarchy.calculate_gang_power(gname),
                "living_members": living,
                "total_members": len(gang.members),
                "color": gang.color,
            }
        district_summaries = {
            dname: {
                "controlling_gang": d.controlling_gang,
                "heat_level": d.heat_level,
                "businesses": d.businesses,
            }
            for dname, d in self.districts.items()
        }
        return {
            "time_step": self._time_step,
            "gangs": gang_summaries,
            "districts": district_summaries,
            "npc_count": len(self.npcs),
        }

    def get_active_rivals(self) -> List[NPC]:
        """Return all living NPCs who are actively hostile to the player."""
        return [
            npc for npc in self.npcs.values()
            if npc.alive and npc.is_hostile_to_player()
        ]

    def get_potential_allies(self) -> List[NPC]:
        """Return all living NPCs who are open to alliance with the player."""
        return [
            npc for npc in self.npcs.values()
            if npc.alive and npc.relationships.get("player", 0) >= 0
            and not npc.is_hostile_to_player()
        ]

    def get_npc_info(self, npc_id: str) -> Optional[Dict[str, Any]]:
        """Return a detailed NPC profile including history and relationships.

        Args:
            npc_id: Target NPC identifier.

        Returns:
            A dict with full NPC info, or ``None`` if not found.
        """
        npc = self.npcs.get(npc_id)
        if not npc:
            return None
        history = self.memory.get_npc_history(npc_id)
        relationship_summary = self.memory.get_relationship_summary(npc_id)
        return {
            "npc_id": npc.npc_id,
            "name": npc.name,
            "nickname": npc.nickname,
            "rank": npc.rank.value,
            "gang": npc.gang,
            "alive": npc.alive,
            "health": npc.health,
            "respect_level": npc.respect_level,
            "traits": npc.traits,
            "strengths": npc.strengths,
            "weaknesses": npc.weaknesses,
            "appearance": npc.appearance,
            "territory": npc.territory,
            "relationships": npc.relationships,
            "relationship_summary": relationship_summary,
            "event_count": len(history),
            "recent_events": [
                {"type": e.event_type.value, "description": e.description, "outcome": e.outcome}
                for e in history[-5:]
            ],
        }

    def get_npc_dialogue(self, npc_id: str, dialogue_type: str = "greeting") -> str:
        """Get procedurally generated dialogue from an NPC.

        Args:
            npc_id:        Target NPC.
            dialogue_type: One of ``"greeting"``, ``"threat"``, ``"taunt"``,
                           ``"respect"``, ``"betrayal"``.

        Returns:
            A dialogue string.
        """
        npc = self.npcs.get(npc_id)
        if not npc:
            return "..."
        history = self.memory.get_npc_history(npc_id)
        player_events = [e for e in history if e.player_involved]

        gen = self.dialogue
        if dialogue_type == "greeting":
            return gen.generate_greeting(npc, player_events)
        elif dialogue_type == "threat":
            return gen.generate_threat(npc, player_events)
        elif dialogue_type == "taunt":
            return gen.generate_taunt(npc)
        elif dialogue_type == "respect":
            return gen.generate_respect(npc, player_events)
        elif dialogue_type == "betrayal":
            return gen.generate_betrayal_reaction(npc)
        return gen.generate_greeting(npc, player_events)

    def display_world_map(self) -> str:
        """Return a text-based map showing gang territories.

        Returns:
            A multi-line ASCII map string.
        """
        lines = [
            "=" * 60,
            "  VICE CITY — GANG TERRITORY MAP",
            "=" * 60,
        ]
        for dname, district in self.districts.items():
            gang = district.controlling_gang
            gang_obj = self.gangs.get(gang)
            power = self.hierarchy.calculate_gang_power(gang) if gang_obj else 0
            heat_bar = "🔴" * (district.heat_level // 20) or "⬜"
            businesses = ", ".join(district.businesses)
            lines.append(
                f"  {dname:<22} │ {gang:<18} │ "
                f"Heat: {district.heat_level:>3} {heat_bar}  │ {businesses}"
            )
        lines.append("=" * 60)
        return "\n".join(lines)

    def list_npcs(self, gang_name: Optional[str] = None, alive_only: bool = True) -> List[NPC]:
        """Return NPCs, optionally filtered by gang and alive status.

        Args:
            gang_name:  If given, only return NPCs from this gang.
            alive_only: If ``True`` (default), exclude dead NPCs.

        Returns:
            Filtered list of :class:`~antihero_system.models.NPC` objects.
        """
        result = list(self.npcs.values())
        if gang_name:
            result = [n for n in result if n.gang == gang_name]
        if alive_only:
            result = [n for n in result if n.alive]
        return result

    def get_hierarchy_display(self, gang_name: str) -> str:
        """Return a formatted hierarchy tree for *gang_name*."""
        return self.hierarchy.get_hierarchy_display(gang_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_action(
        self,
        action_type: str,
        npc: NPC,
        **kwargs: Any,
    ):
        """Map an action type to an (EventType, description, outcome, dialogue) tuple."""
        gen = self.dialogue

        if action_type == ACTION_ATTACK:
            # Simulate combat outcome
            player_wins = random.random() > 0.4
            if player_wins:
                npc.health = max(0, npc.health - random.randint(20, 50))
                outcome = f"{npc.nickname} beaten but alive (health: {npc.health})"
                history = self.memory.get_npc_history(npc.npc_id)
                dialogue = gen.generate_threat(npc, [e for e in history if e.player_involved])
                return EventType.DEFEAT, f"Player attacked {npc.nickname}", outcome, dialogue
            else:
                outcome = "Player driven back"
                dialogue = gen.generate_taunt(npc)
                return EventType.VICTORY, f"{npc.nickname} repelled the player", outcome, dialogue

        elif action_type == ACTION_ASSASSINATE:
            npc.alive = False
            npc.health = 0
            outcome = f"{npc.nickname} eliminated"
            dialogue = f'*{npc.nickname} is gone. The streets will remember.*'
            return (
                EventType.ASSASSINATION,
                f"Player assassinated {npc.nickname} in {npc.territory}",
                outcome,
                dialogue,
            )

        elif action_type == ACTION_BRIBE:
            npc.adjust_player_relationship(+15)
            outcome = f"{npc.nickname} accepts bribe"
            history = self.memory.get_npc_history(npc.npc_id)
            dialogue = gen.generate_greeting(npc, [e for e in history if e.player_involved])
            return EventType.BRIBE, f"Player bribed {npc.nickname}", outcome, dialogue

        elif action_type == ACTION_ALLY:
            npc.adjust_player_relationship(+25)
            outcome = f"Alliance formed with {npc.nickname}"
            history = self.memory.get_npc_history(npc.npc_id)
            dialogue = gen.generate_respect(npc, [e for e in history if e.player_involved])
            return EventType.ALLIANCE, f"Player formed alliance with {npc.nickname}", outcome, dialogue

        elif action_type == ACTION_INTIMIDATE:
            outcome = f"{npc.nickname} intimidated"
            history = self.memory.get_npc_history(npc.npc_id)
            dialogue = gen.generate_threat(npc, [e for e in history if e.player_involved])
            return (
                EventType.INTIMIDATION,
                f"Player intimidated {npc.nickname}",
                outcome,
                dialogue,
            )

        elif action_type == ACTION_TURF_WAR:
            district_name = kwargs.get("district", npc.territory)
            narrative, casualties = self.hierarchy.gang_war(
                "Vercetti Gang", npc.gang, district_name
            )
            for cid in casualties:
                c = self.npcs.get(cid)
                if c:
                    vac = self.hierarchy.fill_power_vacuum(c.gang, c.rank)
            outcome = narrative
            dialogue = f"The war for {district_name} has begun!"
            return (
                EventType.TURF_WAR,
                f"Turf war in {district_name} involving {npc.gang}",
                outcome,
                dialogue,
            )

        # Default fallback
        return EventType.DEFEAT, "Unknown action", "", "..."
