"""
Consequence engine for the Antihero System.

Translates raw :class:`~antihero_system.models.Event` objects into concrete
world-state changes: hierarchy reshuffles, territory swaps, NPC revenge arcs,
and autonomous gang behaviour.
"""

from __future__ import annotations

import random

from .models import District, Event, EventType, Gang, NPC, Rank
from .hierarchy import HierarchyManager
from .memory import MemoryManager


class ConsequenceEngine:
    """Processes events and applies their consequences to the world.

    Args:
        gangs:     Shared gang registry.
        npcs:      Shared NPC registry.
        districts: Shared district registry.
        hierarchy: :class:`~antihero_system.hierarchy.HierarchyManager` instance.
        memory:    :class:`~antihero_system.memory.MemoryManager` instance.
    """

    def __init__(
        self,
        gangs: dict[str, Gang],
        npcs: dict[str, NPC],
        districts: dict[str, District],
        hierarchy: HierarchyManager,
        memory: MemoryManager,
    ) -> None:
        self._gangs = gangs
        self._npcs = npcs
        self._districts = districts
        self._hierarchy = hierarchy
        self._memory = memory
        self._revenge_queue: set[str] = set()   # npc_ids ready to seek revenge

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_event(self, event: Event) -> list[str]:
        """Apply all consequences of *event* to the world state.

        Args:
            event: A recorded :class:`~antihero_system.models.Event`.

        Returns:
            A list of human-readable consequence strings.
        """
        consequences: list[str] = []

        if event.event_type == EventType.ASSASSINATION:
            consequences.extend(self._handle_assassination(event))

        elif event.event_type == EventType.DEFEAT:
            consequences.extend(self._handle_defeat(event))

        elif event.event_type == EventType.BETRAYAL:
            consequences.extend(self._handle_betrayal(event))

        elif event.event_type == EventType.ALLIANCE:
            consequences.extend(self._handle_alliance(event))

        elif event.event_type == EventType.TURF_WAR:
            consequences.extend(self._handle_turf_war(event))

        elif event.event_type == EventType.BRIBE:
            consequences.extend(self._handle_bribe(event))

        elif event.event_type == EventType.INTIMIDATION:
            consequences.extend(self._handle_intimidation(event))

        return consequences

    def check_revenge_triggers(self) -> list[str]:
        """Scan all living NPCs for those ready to seek revenge on the player.

        An NPC is revenge-ready when their player relationship score drops
        below −50 and they have not yet been queued.

        Returns:
            List of revenge announcement strings.
        """
        messages: list[str] = []
        for npc_id, npc in self._npcs.items():
            if not npc.alive:
                continue
            score = npc.relationships.get("player", 0)
            if score < -50 and npc_id not in self._revenge_queue:
                self._revenge_queue.add(npc_id)
                messages.append(
                    f"⚠  REVENGE: {npc.nickname} ({npc.name}) is coming for you! "
                    f"[{npc.gang} | {npc.rank.value}]"
                )
        return messages

    def update_world_state(self) -> list[str]:
        """Advance one autonomous world-simulation tick.

        NPCs scheme, gangs expand, and new rivalries may form even without
        player involvement.

        Returns:
            A list of world-update narrative strings.
        """
        updates: list[str] = []

        # Random autonomous gang war (low probability each tick)
        if random.random() < 0.3:
            gang_names = [g for g, gang in self._gangs.items() if gang.rival_gangs]
            if len(gang_names) >= 2:
                g1_name = random.choice(gang_names)
                g1 = self._gangs[g1_name]
                if g1.rival_gangs:
                    g2_name = random.choice(g1.rival_gangs)
                    g2 = self._gangs.get(g2_name)
                    if g2 is not None:
                        # Pick a contested district (owned by either gang)
                        possible = list(set(g1.territory + g2.territory))
                        if possible:
                            district_name = random.choice(possible)
                            narrative, casualties = self._hierarchy.gang_war(
                                g1_name, g2_name, district_name
                            )
                            updates.append(narrative)
                            for cid in casualties:
                                c = self._npcs[cid]
                                vacuum_msg = self._hierarchy.fill_power_vacuum(c.gang, c.rank)
                                if vacuum_msg:
                                    updates.append(vacuum_msg)

        # Random NPC promotion (reward loyalty)
        if random.random() < 0.2:
            candidates = [
                npc for npc in self._npcs.values()
                if npc.alive and npc.rank != Rank.BOSS and npc.respect_level >= 70
            ]
            if candidates:
                lucky = random.choice(candidates)
                msg = self._hierarchy.promote_npc(lucky.npc_id)
                if msg:
                    updates.append(f"[Autonomous] {msg}")

        return updates

    # ------------------------------------------------------------------
    # Private handlers
    # ------------------------------------------------------------------

    def _handle_assassination(self, event: Event) -> list[str]:
        results: list[str] = []
        for npc_id in event.involved_npcs:
            npc = self._npcs.get(npc_id)
            if not npc:
                continue
            if not npc.alive:
                # NPC was the assassination target
                msg = self._hierarchy.fill_power_vacuum(npc.gang, npc.rank)
                if msg:
                    results.append(msg)
                # Notify gang allies
                gang_obj = self._gangs.get(npc.gang)
                if gang_obj:
                    for ally_id in gang_obj.members:
                        ally = self._npcs.get(ally_id)
                        if ally and ally.alive and ally.npc_id != npc_id:
                            ally.adjust_player_relationship(-30)
                results.append(
                    f"The {npc.gang} is mourning the death of {npc.nickname}. "
                    f"Retaliation is likely."
                )
        return results

    def _handle_defeat(self, event: Event) -> list[str]:
        results: list[str] = []
        for npc_id in event.involved_npcs:
            npc = self._npcs.get(npc_id)
            if not npc or not npc.alive:
                continue
            # NPC survived but was beaten — may return stronger
            if random.random() < 0.5:
                npc.respect_level = max(0, npc.respect_level - 5)
                npc.health = max(10, npc.health - 30)
                if "vengeful" not in npc.traits:
                    npc.traits.append("vengeful")
                results.append(
                    f"{npc.nickname} survived the encounter — scarred and furious, "
                    f"they vow to get even."
                )
            # Queue for potential revenge
            if npc.relationships.get("player", 0) < -30:
                if npc.npc_id not in self._revenge_queue:
                    self._revenge_queue.add(npc.npc_id)
        return results

    def _handle_betrayal(self, event: Event) -> list[str]:
        results: list[str] = []
        for npc_id in event.involved_npcs:
            npc = self._npcs.get(npc_id)
            if not npc or not npc.alive:
                continue
            # Massive relationship penalty already applied by MemoryManager;
            # additionally the NPC may defect.
            if random.random() < 0.4:
                old_gang = npc.gang
                # Find a rival gang to defect to
                current_gang = self._gangs.get(old_gang)
                if current_gang and current_gang.rival_gangs:
                    new_gang_name = random.choice(current_gang.rival_gangs)
                    new_gang = self._gangs.get(new_gang_name)
                    if new_gang:
                        # Move NPC to new gang
                        if npc.npc_id in current_gang.members:
                            current_gang.members.remove(npc.npc_id)
                        if npc.npc_id in current_gang.hierarchy:
                            current_gang.hierarchy.remove(npc.npc_id)
                        npc.gang = new_gang_name
                        new_gang.members.append(npc.npc_id)
                        new_gang.hierarchy.append(npc.npc_id)
                        npc.rank = Rank.ENFORCER  # start fresh
                        results.append(
                            f"DEFECTION: {npc.nickname} has abandoned {old_gang} "
                            f"and joined {new_gang_name} after the betrayal!"
                        )
        return results

    def _handle_alliance(self, event: Event) -> list[str]:
        results: list[str] = []
        for npc_id in event.involved_npcs:
            npc = self._npcs.get(npc_id)
            if not npc or not npc.alive:
                continue
            results.append(
                f"{npc.nickname} considers the alliance a smart move. "
                f"Their crew will give you some breathing room."
            )
        return results

    def _handle_turf_war(self, event: Event) -> list[str]:
        # Territory changes are handled by HierarchyManager.gang_war;
        # here we just update heat levels and note the consequence.
        results: list[str] = []
        for dname, district in self._districts.items():
            if event.description and dname in event.description:
                district.heat_level = min(100, district.heat_level + 15)
                results.append(
                    f"Heat in {dname} rises to {district.heat_level} — "
                    f"cops are swarming the area."
                )
        return results

    def _handle_bribe(self, event: Event) -> list[str]:
        results: list[str] = []
        for npc_id in event.involved_npcs:
            npc = self._npcs.get(npc_id)
            if not npc or not npc.alive:
                continue
            # The NPC's own gang loses respect for them
            npc.respect_level = max(0, npc.respect_level - 10)
            results.append(
                f"{npc.nickname} took your money but lost face with {npc.gang}. "
                f"Don't expect the favour to last."
            )
        return results

    def _handle_intimidation(self, event: Event) -> list[str]:
        results: list[str] = []
        for npc_id in event.involved_npcs:
            npc = self._npcs.get(npc_id)
            if not npc or not npc.alive:
                continue
            if "cowardly" in npc.traits:
                results.append(
                    f"{npc.nickname} is shaken — their cowardly nature means "
                    f"they'll likely back down."
                )
            else:
                results.append(
                    f"{npc.nickname} doesn't scare easy. That intimidation may "
                    f"have made things worse."
                )
        return results
