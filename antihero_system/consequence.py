"""
Consequence engine — translates events into world changes.

Processes events and applies cascading consequences across NPCs,
gangs, and districts.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional

from .hierarchy import HierarchyManager
from .memory import MemoryManager
from .models import District, Event, EventType, Gang, NPC, Rank


class ConsequenceEngine:
    """
    Processes world events and applies appropriate consequences.

    Args:
        npcs: Mapping of npc_id → NPC.
        gangs: Mapping of gang name → Gang.
        districts: Mapping of district name → District.
        memory_manager: The shared MemoryManager.
        hierarchy_manager: The shared HierarchyManager.
    """

    def __init__(
        self,
        npcs: Dict[str, NPC],
        gangs: Dict[str, Gang],
        districts: Dict[str, District],
        memory_manager: MemoryManager,
        hierarchy_manager: HierarchyManager,
    ) -> None:
        self.npcs = npcs
        self.gangs = gangs
        self.districts = districts
        self.memory = memory_manager
        self.hierarchy = hierarchy_manager
        self._world_log: List[str] = []   # Narrative world-event log

    # ------------------------------------------------------------------
    # Core event processing
    # ------------------------------------------------------------------

    def process_event(self, event: Event) -> List[str]:
        """
        Process an event and apply all cascading consequences.

        Returns a list of narrative consequence strings describing what
        happened as a result.
        """
        consequences: List[str] = []

        self.memory.record_event(event)

        handlers = {
            EventType.DEFEAT:        self._handle_defeat,
            EventType.ASSASSINATION: self._handle_assassination,
            EventType.BETRAYAL:      self._handle_betrayal,
            EventType.ALLIANCE:      self._handle_alliance,
            EventType.TURF_WAR:      self._handle_turf_war,
            EventType.BRIBE:         self._handle_bribe,
            EventType.INTIMIDATION:  self._handle_intimidation,
            EventType.VICTORY:       self._handle_victory,
            EventType.ESCAPE:        self._handle_escape,
        }

        handler = handlers.get(event.event_type)
        if handler:
            result = handler(event)
            consequences.extend(result)

        self._world_log.extend(consequences)
        return consequences

    # ------------------------------------------------------------------
    # Individual event handlers
    # ------------------------------------------------------------------

    def _handle_defeat(self, event: Event) -> List[str]:
        """NPC defeated but still alive — returns scarred/stronger, may seek revenge."""
        consequences = []
        for npc_id in event.involved_npcs:
            npc = self.npcs.get(npc_id)
            if not npc or not npc.alive:
                continue
            # NPC survived but is weakened
            npc.health = max(10, npc.health - random.randint(20, 40))
            if not npc.scarred:
                npc.scarred = True
                npc.health = min(npc.health + 20, 200)  # Returns tougher
                consequences.append(
                    f"{npc.name} survived the encounter. They'll come back scarred and angrier."
                )
            if npc.relationships.get("player", 0) <= -40:
                npc.revenge_ready = True
                consequences.append(
                    f"'{npc.nickname}' is now actively plotting revenge against you."
                )
        return consequences

    def _handle_assassination(self, event: Event) -> List[str]:
        """NPC killed — trigger power vacuum and notify allies."""
        consequences = []
        for npc_id in event.involved_npcs:
            npc = self.npcs.get(npc_id)
            if not npc:
                continue
            npc.alive = False
            npc.health = 0
            consequences.append(f"{npc.name} ('{npc.nickname}') has been eliminated.")

            gang = self.gangs.get(npc.gang)
            if gang:
                # Notify gang members
                for member_id in gang.members:
                    member = self.npcs.get(member_id)
                    if member and member.alive and member.npc_id != npc_id:
                        member.update_relationship("player", -15)

                # Fill the power vacuum
                successor = self.hierarchy.fill_power_vacuum(npc.gang, npc.rank)
                if successor:
                    consequences.append(
                        f"Power vacuum filled: {successor.name} ('{successor.nickname}') "
                        f"rises to {successor.rank.value} of {npc.gang}."
                    )
                else:
                    consequences.append(
                        f"{npc.gang} has no one to fill the vacancy at {npc.rank.value}. "
                        f"The gang is weakened."
                    )

            # Notify rival gangs — they celebrate
            for g_name, gang_obj in self.gangs.items():
                if npc.gang in gang_obj.rival_gangs:
                    consequences.append(
                        f"{g_name} is pleased by the death of {npc.name}."
                    )

        return consequences

    def _handle_betrayal(self, event: Event) -> List[str]:
        """Player betrayed an NPC — massive relationship penalty, NPC may flip gangs."""
        consequences = []
        for npc_id in event.involved_npcs:
            npc = self.npcs.get(npc_id)
            if not npc:
                continue
            # Betrayal causes extreme hatred
            npc.update_relationship("player", -50)
            npc.revenge_ready = True
            consequences.append(
                f"{npc.name} will never forgive this betrayal. "
                f"They've sworn to destroy everything you've built."
            )

            # Possible gang flip — betrayed NPC may defect to a rival gang
            if random.random() < 0.3:
                old_gang = npc.gang
                rival_gangs = [
                    g for g in self.gangs
                    if g != old_gang and npc.gang not in self.gangs[g].rival_gangs
                ]
                if rival_gangs:
                    new_gang_name = random.choice(rival_gangs)
                    old_gang_obj = self.gangs.get(old_gang)
                    new_gang_obj = self.gangs.get(new_gang_name)
                    if old_gang_obj:
                        old_gang_obj.remove_member(npc.npc_id)
                    if new_gang_obj:
                        npc.gang = new_gang_name
                        new_gang_obj.add_member(npc)
                    consequences.append(
                        f"{npc.name} has defected to {new_gang_name} after your betrayal."
                    )

        return consequences

    def _handle_alliance(self, event: Event) -> List[str]:
        """Alliance formed — relationship boost, possible cooperation."""
        consequences = []
        for npc_id in event.involved_npcs:
            npc = self.npcs.get(npc_id)
            if not npc:
                continue
            npc.update_relationship("player", 30)
            consequences.append(
                f"{npc.name} considers you an ally. Doors that were closed are now open."
            )
            # Inform gang members — they warm up to the player too
            gang = self.gangs.get(npc.gang)
            if gang:
                for member_id in gang.members[:3]:  # Affect nearest members
                    member = self.npcs.get(member_id)
                    if member and member.alive and member.npc_id != npc_id:
                        member.update_relationship("player", 10)

        return consequences

    def _handle_turf_war(self, event: Event) -> List[str]:
        """Turf war event — resolve and update district control."""
        consequences = []
        # Outcome is embedded in event description; update district heat
        for npc_id in event.involved_npcs:
            npc = self.npcs.get(npc_id)
            if npc:
                # NPCs involved in turf wars gain or lose respect
                if "won" in event.outcome.lower():
                    npc.respect_level = min(100, npc.respect_level + 5)
                else:
                    npc.respect_level = max(0, npc.respect_level - 5)

        # Increase heat in all districts
        for district in self.districts.values():
            district.add_heat(random.randint(5, 15))

        consequences.append(
            "The turf war spills blood across the streets. Police presence increases citywide."
        )
        return consequences

    def _handle_bribe(self, event: Event) -> List[str]:
        """Bribe event — temporary alliance but NPC loses respect in gang."""
        consequences = []
        for npc_id in event.involved_npcs:
            npc = self.npcs.get(npc_id)
            if not npc:
                continue
            npc.update_relationship("player", 15)
            npc.respect_level = max(0, npc.respect_level - 10)
            consequences.append(
                f"{npc.name} took your money. Their loyalty to {npc.gang} is now questioned."
            )
        return consequences

    def _handle_intimidation(self, event: Event) -> List[str]:
        """Intimidation — NPC complies but harbors resentment."""
        consequences = []
        for npc_id in event.involved_npcs:
            npc = self.npcs.get(npc_id)
            if not npc:
                continue
            if "cowardly" in npc.traits:
                npc.update_relationship("player", -5)
                consequences.append(
                    f"{npc.name} cowered before you. They'll give you what you want — for now."
                )
            else:
                npc.update_relationship("player", -20)
                npc.revenge_ready = True
                consequences.append(
                    f"{npc.name} won't forget being disrespected. "
                    f"'{npc.nickname}' is already planning their response."
                )
        return consequences

    def _handle_victory(self, event: Event) -> List[str]:
        """NPC defeated the player — they gain confidence and respect."""
        consequences = []
        for npc_id in event.involved_npcs:
            npc = self.npcs.get(npc_id)
            if not npc:
                continue
            npc.respect_level = min(100, npc.respect_level + 15)
            consequences.append(
                f"{npc.name} has proven themselves by besting you. "
                f"Their reputation on the street grows."
            )
        return consequences

    def _handle_escape(self, event: Event) -> List[str]:
        """NPC escaped — they'll return more cautious."""
        consequences = []
        for npc_id in event.involved_npcs:
            npc = self.npcs.get(npc_id)
            if not npc:
                continue
            consequences.append(
                f"{npc.name} got away. '{npc.nickname}' is now more careful — "
                f"and more dangerous."
            )
        return consequences

    # ------------------------------------------------------------------
    # Revenge and world state updates
    # ------------------------------------------------------------------

    def check_revenge_triggers(self) -> List[str]:
        """
        Scan all NPCs for revenge-ready status and generate consequence strings.

        Returns a list of narrative strings for each NPC seeking revenge.
        """
        results = []
        for npc_id, npc in self.npcs.items():
            if npc.alive and npc.revenge_ready:
                results.append(
                    f"⚠  {npc.name} ('{npc.nickname}', {npc.gang}) is hunting you down!"
                )
        return results

    def update_world_state(self) -> List[str]:
        """
        Periodic world update: NPCs scheme, gangs expand, new rivalries form.

        Simulates one "tick" of autonomous world activity.
        Returns a list of narrative world-change strings.
        """
        events = []

        # Random chance of an autonomous gang war
        gang_names = list(self.gangs.keys())
        if len(gang_names) >= 2 and random.random() < 0.3:
            g1, g2 = random.sample(gang_names, 2)
            if g2 in self.gangs[g1].rival_gangs or random.random() < 0.2:
                district_name = random.choice(list(self.districts.keys()))
                result = self.hierarchy.gang_war(g1, g2, district_name)
                if "winner" in result:
                    # Update district control
                    district = self.districts.get(district_name)
                    if district:
                        district.controlling_gang = result["winner"]
                        district.add_heat(random.randint(10, 25))
                    events.append(
                        f"📍 Gang war: {g1} vs {g2} over {district_name}. "
                        f"{result['winner']} takes control!"
                    )

        # Random chance of an NPC promotion (rising star)
        if random.random() < 0.2:
            all_alive = [n for n in self.npcs.values() if n.alive and n.rank != Rank.BOSS]
            if all_alive:
                star = random.choice(all_alive)
                new_rank = self.hierarchy.promote_npc(star.npc_id)
                if new_rank:
                    events.append(
                        f"📈 {star.name} has risen to {new_rank.value} "
                        f"within {star.gang}."
                    )

        # Heat naturally decreases over time
        for district in self.districts.values():
            district.reduce_heat(random.randint(1, 5))

        return events

    @property
    def world_log(self) -> List[str]:
        """Return the full narrative world event log."""
        return list(self._world_log)
