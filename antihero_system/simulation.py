"""
Main simulation loop and game engine interface for the Antihero System.

AntiHeroEngine is the top-level orchestrator that ties together
generation, memory, hierarchy, consequences, and dialogue.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from .consequence import ConsequenceEngine
from .dialogue import DialogueGenerator
from .generator import generate_vice_city
from .hierarchy import HierarchyManager
from .memory import MemoryManager
from .models import District, Event, EventType, Gang, NPC, Rank, RANK_ORDER


class AntiHeroEngine:
    """
    The main orchestrator for the Antihero System.

    Initializes a Vice City world and exposes a clean API for:
    - Player actions (attack, bribe, ally, intimidate, assassinate)
    - Time advancement (autonomous NPC/gang simulation)
    - World state queries
    """

    def __init__(self) -> None:
        self.gangs, self.npcs, self.districts = generate_vice_city()

        self.memory = MemoryManager(self.npcs)
        self.hierarchy = HierarchyManager(self.gangs, self.npcs)
        self.consequence = ConsequenceEngine(
            self.npcs, self.gangs, self.districts,
            self.memory, self.hierarchy
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
        """
        Process a player action targeting an NPC.

        Args:
            action_type: One of 'attack', 'assassinate', 'bribe',
                         'ally', 'intimidate'.
            target_npc_id: The ID of the target NPC.
            **kwargs: Optional extra data (e.g., district for turf_war).

        Returns:
            A dict with keys: 'success', 'dialogue', 'consequences', 'npc'.
        """
        npc = self.npcs.get(target_npc_id)
        if not npc:
            return {"success": False, "error": "NPC not found"}
        if not npc.alive:
            return {"success": False, "error": f"{npc.name} is already dead"}

        event_map = {
            "attack":      EventType.DEFEAT,
            "assassinate": EventType.ASSASSINATION,
            "bribe":       EventType.BRIBE,
            "ally":        EventType.ALLIANCE,
            "intimidate":  EventType.INTIMIDATION,
        }

        event_type = event_map.get(action_type.lower())
        if not event_type:
            return {"success": False, "error": f"Unknown action: {action_type}"}

        # Determine outcome narrative
        outcome_map = {
            EventType.DEFEAT:        "Player defeated the NPC in combat.",
            EventType.ASSASSINATION: "Player assassinated the NPC.",
            EventType.BRIBE:         "Player successfully bribed the NPC.",
            EventType.ALLIANCE:      "Player and NPC formed an alliance.",
            EventType.INTIMIDATION:  "Player intimidated the NPC into compliance.",
        }

        description = (
            f"Player {action_type}d {npc.name} ('{npc.nickname}') "
            f"of {npc.gang} in {npc.territory}."
        )
        outcome = outcome_map[event_type]

        event = Event(
            event_type=event_type,
            description=description,
            outcome=outcome,
            involved_npcs=[npc.npc_id],
            player_involved=True,
        )

        consequences = self.consequence.process_event(event)

        # Get NPC reaction dialogue
        player_history = self.memory.get_player_history()
        if action_type == "assassinate":
            dialogue_line = f"{npc.name} ('{npc.nickname}'): [silenced]"
        elif action_type == "bribe":
            dialogue_line = self.dialogue.generate_greeting(npc, player_history)
        elif action_type == "ally":
            dialogue_line = self.dialogue.generate_respect(npc, player_history)
        elif action_type in ("attack",):
            if npc.alive:
                dialogue_line = self.dialogue.generate_threat(npc, player_history)
            else:
                dialogue_line = self.dialogue.generate_taunt(npc, event)
        elif action_type == "intimidate":
            dialogue_line = self.dialogue.generate_threat(npc, player_history)
        else:
            dialogue_line = self.dialogue.get_contextual_line(npc, player_history)

        return {
            "success": True,
            "action": action_type,
            "npc": npc,
            "dialogue": dialogue_line,
            "consequences": consequences,
            "event": event,
        }

    def start_turf_war(self, attacker_gang: str, defender_gang: str, district: str) -> Dict:
        """
        Initiate a player-triggered turf war.

        Returns the gang war result plus narrative consequences.
        """
        event = Event(
            event_type=EventType.TURF_WAR,
            description=f"{attacker_gang} attacks {defender_gang} in {district}.",
            outcome="Pending",
            player_involved=True,
        )
        self.memory.record_event(event)

        result = self.hierarchy.gang_war(attacker_gang, defender_gang, district)
        if "winner" in result:
            dist = self.districts.get(district)
            if dist:
                dist.controlling_gang = result["winner"]
                dist.add_heat(30)
            result["outcome"] = (
                f"{result['winner']} has seized control of {district}!"
            )

        return result

    # ------------------------------------------------------------------
    # Time advancement
    # ------------------------------------------------------------------

    def advance_time(self) -> List[str]:
        """
        Simulate one time step of autonomous world activity.

        Returns a list of world-event narrative strings.
        """
        self._time_step += 1
        return self.consequence.update_world_state()

    # ------------------------------------------------------------------
    # World state queries
    # ------------------------------------------------------------------

    def get_world_state(self) -> Dict:
        """Return current state of all gangs, districts, and NPC counts."""
        return {
            "time_step": self._time_step,
            "gangs": {
                name: {
                    "territory": gang.territory,
                    "members_alive": len(gang.living_members(self.npcs)),
                    "total_members": len(gang.members),
                    "power": self.hierarchy.calculate_gang_power(name),
                    "rivals": gang.rival_gangs,
                    "allies": gang.allied_gangs,
                }
                for name, gang in self.gangs.items()
            },
            "districts": {
                name: {
                    "controlling_gang": d.controlling_gang,
                    "heat_level": d.heat_level,
                    "businesses": d.businesses,
                }
                for name, d in self.districts.items()
            },
        }

    def get_active_rivals(self) -> List[NPC]:
        """Return NPCs who are actively hostile to the player (score < -20)."""
        return [
            npc for npc in self.npcs.values()
            if npc.alive and npc.is_hostile_to_player()
        ]

    def get_potential_allies(self) -> List[NPC]:
        """Return NPCs open to alliance (score > 20)."""
        return [
            npc for npc in self.npcs.values()
            if npc.alive and npc.is_friendly_to_player()
        ]

    def get_npc_info(self, npc_id: str) -> Optional[Dict]:
        """Return detailed NPC profile with history and relationships."""
        npc = self.npcs.get(npc_id)
        if not npc:
            return None
        history = self.memory.get_npc_history(npc_id)
        relationship_summary = self.memory.get_relationship_summary(npc_id)
        return {
            "npc": npc,
            "name": npc.display_name(),
            "rank": npc.rank.value,
            "gang": npc.gang,
            "territory": npc.territory,
            "traits": npc.traits,
            "strengths": npc.strengths,
            "weaknesses": npc.weaknesses,
            "appearance": npc.appearance,
            "health": npc.health,
            "respect": npc.respect_level,
            "alive": npc.alive,
            "scarred": npc.scarred,
            "revenge_ready": npc.revenge_ready,
            "player_relationship": npc.relationships.get("player", 0),
            "relationship_summary": relationship_summary,
            "event_count": len(history),
            "recent_events": [
                {"type": e.event_type.value, "description": e.description}
                for e in history[-5:]
            ],
        }

    def get_all_npcs(self) -> List[NPC]:
        """Return all NPCs (living and dead)."""
        return list(self.npcs.values())

    def get_living_npcs(self) -> List[NPC]:
        """Return only living NPCs."""
        return [n for n in self.npcs.values() if n.alive]

    def get_gang_hierarchy(self, gang_name: str) -> str:
        """Return formatted hierarchy tree for a gang."""
        return self.hierarchy.get_hierarchy_display(gang_name)

    def display_world_map(self) -> str:
        """Return a text-based map showing gang territories."""
        lines = [
            "",
            "╔══════════════════════════════════════════╗",
            "║          VICE CITY — TURF MAP            ║",
            "╠══════════════════════════════════════════╣",
        ]
        for d_name, district in self.districts.items():
            controller = district.controlling_gang or "Contested"
            heat_bar = "█" * (district.heat_level // 10)
            lines.append(
                f"║  {d_name:<22} [{controller:<16}]  ║"
            )
            lines.append(
                f"║  {'':22} Heat: {heat_bar:<10} {district.heat_level:>3}%  ║"
            )
            lines.append("║" + "─" * 44 + "║")
        lines.append("╚══════════════════════════════════════════╝")
        return "\n".join(lines)
