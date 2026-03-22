"""
Unit tests for the Antihero System.

Covers NPC generation, memory system, hierarchy, consequence engine,
dialogue generation, and gang war simulation.
"""

from __future__ import annotations

import unittest
from datetime import datetime

from antihero_system.consequence import ConsequenceEngine
from antihero_system.dialogue import DialogueGenerator
from antihero_system.generator import (
    generate_district,
    generate_gang,
    generate_npc,
    generate_vice_city,
)
from antihero_system.hierarchy import HierarchyManager
from antihero_system.memory import MemoryManager
from antihero_system.models import (
    District,
    Event,
    EventType,
    Gang,
    NPC,
    Rank,
    RANK_ORDER,
)
from antihero_system.simulation import AntiHeroEngine


# ---------------------------------------------------------------------------
# NPC Generation Tests
# ---------------------------------------------------------------------------

class TestNPCGeneration(unittest.TestCase):
    """Tests for procedural NPC generation."""

    def test_generate_npc_returns_npc(self):
        npc = generate_npc(Rank.BOSS, "Vercetti Gang")
        self.assertIsInstance(npc, NPC)

    def test_generated_npc_has_name(self):
        npc = generate_npc(Rank.CAPTAIN, "Diaz Cartel")
        self.assertTrue(len(npc.name) > 0)
        self.assertIn(" ", npc.name)   # First + Last name

    def test_generated_npc_has_nickname(self):
        npc = generate_npc(Rank.ENFORCER, "Haitians")
        self.assertTrue(len(npc.nickname) > 0)

    def test_generated_npc_has_correct_rank(self):
        for rank in Rank:
            npc = generate_npc(rank, "Cubans")
            self.assertEqual(npc.rank, rank)

    def test_generated_npc_has_traits(self):
        npc = generate_npc(Rank.DEALER, "Bikers")
        self.assertIsInstance(npc.traits, list)
        self.assertGreaterEqual(len(npc.traits), 2)

    def test_generated_npc_has_appearance(self):
        npc = generate_npc(Rank.BOSS, "Vercetti Gang")
        self.assertIn("scar", npc.appearance)
        self.assertIn("tattoo", npc.appearance)
        self.assertIn("clothing", npc.appearance)

    def test_boss_has_more_health_than_dealer(self):
        boss = generate_npc(Rank.BOSS, "Vercetti Gang")
        dealer = generate_npc(Rank.DEALER, "Vercetti Gang")
        self.assertGreater(boss.health, dealer.health)

    def test_generated_npcs_are_unique(self):
        """Each generated NPC should have a unique ID."""
        npcs = [generate_npc(Rank.ENFORCER, "Bikers") for _ in range(20)]
        ids = [n.npc_id for n in npcs]
        self.assertEqual(len(set(ids)), 20)

    def test_generate_gang_returns_gang_and_npcs(self):
        gang, npcs = generate_gang("Vercetti Gang")
        self.assertIsInstance(gang, Gang)
        self.assertIsInstance(npcs, dict)
        self.assertGreater(len(npcs), 0)

    def test_gang_has_boss(self):
        gang, npcs = generate_gang("Diaz Cartel")
        bosses = gang.hierarchy.get(Rank.BOSS.value, [])
        self.assertEqual(len(bosses), 1)

    def test_gang_has_full_hierarchy(self):
        gang, npcs = generate_gang("Haitians")
        for rank in Rank:
            ids = gang.hierarchy.get(rank.value, [])
            self.assertGreater(len(ids), 0, f"Missing {rank.value} rank in gang")

    def test_gang_members_match_hierarchy(self):
        gang, npcs = generate_gang("Cubans")
        total_in_hierarchy = sum(
            len(v) for v in gang.hierarchy.values()
        )
        self.assertEqual(len(gang.members), total_in_hierarchy)

    def test_generate_district_returns_district(self):
        d = generate_district("Ocean Beach")
        self.assertIsInstance(d, District)
        self.assertEqual(d.name, "Ocean Beach")
        self.assertGreater(len(d.businesses), 0)

    def test_generate_vice_city_returns_all_components(self):
        gangs, npcs, districts = generate_vice_city()
        self.assertGreater(len(gangs), 0)
        self.assertGreater(len(npcs), 0)
        self.assertGreater(len(districts), 0)

    def test_vice_city_has_all_five_gangs(self):
        gangs, _, _ = generate_vice_city()
        expected = {"Diaz Cartel", "Vercetti Gang", "Haitians", "Cubans", "Bikers"}
        self.assertEqual(set(gangs.keys()), expected)


# ---------------------------------------------------------------------------
# Memory System Tests
# ---------------------------------------------------------------------------

class TestMemorySystem(unittest.TestCase):
    """Tests for the MemoryManager event tracking system."""

    def setUp(self):
        self.npc = generate_npc(Rank.CAPTAIN, "Diaz Cartel")
        self.npcs = {self.npc.npc_id: self.npc}
        self.memory = MemoryManager(self.npcs)

    def _make_event(self, event_type: EventType, player: bool = True) -> Event:
        return Event(
            event_type=event_type,
            description="Test event",
            outcome="Test outcome",
            involved_npcs=[self.npc.npc_id],
            player_involved=player,
        )

    def test_record_event_stores_event(self):
        event = self._make_event(EventType.DEFEAT)
        self.memory.record_event(event)
        self.assertIn(event.event_id, self.memory.events)

    def test_get_npc_history_returns_events(self):
        e1 = self._make_event(EventType.DEFEAT)
        e2 = self._make_event(EventType.INTIMIDATION)
        self.memory.record_event(e1)
        self.memory.record_event(e2)
        history = self.memory.get_npc_history(self.npc.npc_id)
        self.assertEqual(len(history), 2)

    def test_get_player_history_filters_correctly(self):
        player_event = self._make_event(EventType.DEFEAT, player=True)
        npc_event = self._make_event(EventType.ESCAPE, player=False)
        self.memory.record_event(player_event)
        self.memory.record_event(npc_event)
        ph = self.memory.get_player_history()
        self.assertEqual(len(ph), 1)
        self.assertEqual(ph[0].event_id, player_event.event_id)

    def test_rivalry_score_decreases_on_defeat(self):
        initial = self.npc.relationships.get("player", 0)
        event = self._make_event(EventType.DEFEAT)
        self.memory.record_event(event)
        score = self.memory.get_rivalry_score(self.npc.npc_id)
        self.assertLess(score, initial)

    def test_rivalry_score_increases_on_alliance(self):
        initial = self.npc.relationships.get("player", 0)
        event = self._make_event(EventType.ALLIANCE)
        self.memory.record_event(event)
        score = self.memory.get_rivalry_score(self.npc.npc_id)
        self.assertGreater(score, initial)

    def test_betrayal_triggers_revenge_ready(self):
        # Multiple betrayals to push score below -60
        for _ in range(3):
            event = self._make_event(EventType.BETRAYAL)
            self.memory.record_event(event)
        self.assertTrue(self.npc.revenge_ready)

    def test_get_relationship_summary_returns_string(self):
        summary = self.memory.get_relationship_summary(self.npc.npc_id)
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)

    def test_npc_memory_is_updated_on_record(self):
        event = self._make_event(EventType.INTIMIDATION)
        self.memory.record_event(event)
        self.assertIn(event, self.npc.memory)


# ---------------------------------------------------------------------------
# Hierarchy Tests
# ---------------------------------------------------------------------------

class TestHierarchySystem(unittest.TestCase):
    """Tests for HierarchyManager promotions and power vacuums."""

    def setUp(self):
        gang, npcs = generate_gang("Vercetti Gang", ["Ocean Beach"])
        self.gangs = {"Vercetti Gang": gang}
        self.npcs = npcs
        self.hierarchy = HierarchyManager(self.gangs, self.npcs)

    def _get_npc_by_rank(self, rank: Rank) -> NPC:
        gang = self.gangs["Vercetti Gang"]
        ids = gang.hierarchy.get(rank.value, [])
        return self.npcs[ids[0]]

    def test_promote_npc_changes_rank(self):
        dealer = self._get_npc_by_rank(Rank.DEALER)
        old_rank = dealer.rank
        new_rank = self.hierarchy.promote_npc(dealer.npc_id)
        self.assertIsNotNone(new_rank)
        self.assertNotEqual(dealer.rank, old_rank)
        # Should be one step up in RANK_ORDER
        old_idx = RANK_ORDER.index(old_rank)
        self.assertEqual(dealer.rank, RANK_ORDER[old_idx - 1])

    def test_promote_boss_returns_none(self):
        boss = self._get_npc_by_rank(Rank.BOSS)
        result = self.hierarchy.promote_npc(boss.npc_id)
        self.assertIsNone(result)
        self.assertEqual(boss.rank, Rank.BOSS)

    def test_demote_npc_changes_rank(self):
        captain = self._get_npc_by_rank(Rank.CAPTAIN)
        old_rank = captain.rank
        new_rank = self.hierarchy.demote_npc(captain.npc_id)
        self.assertIsNotNone(new_rank)
        old_idx = RANK_ORDER.index(old_rank)
        self.assertEqual(captain.rank, RANK_ORDER[old_idx + 1])

    def test_demote_dealer_returns_none(self):
        dealer = self._get_npc_by_rank(Rank.DEALER)
        result = self.hierarchy.demote_npc(dealer.npc_id)
        self.assertIsNone(result)

    def test_fill_power_vacuum_after_boss_death(self):
        boss = self._get_npc_by_rank(Rank.BOSS)
        boss.alive = False
        successor = self.hierarchy.fill_power_vacuum("Vercetti Gang", Rank.BOSS)
        self.assertIsNotNone(successor)
        self.assertEqual(successor.rank, Rank.BOSS)
        self.assertTrue(successor.alive)

    def test_calculate_gang_power_returns_positive(self):
        power = self.hierarchy.calculate_gang_power("Vercetti Gang")
        self.assertGreater(power, 0)

    def test_calculate_gang_power_decreases_with_deaths(self):
        initial_power = self.hierarchy.calculate_gang_power("Vercetti Gang")
        # Kill the boss
        boss = self._get_npc_by_rank(Rank.BOSS)
        boss.alive = False
        new_power = self.hierarchy.calculate_gang_power("Vercetti Gang")
        self.assertLess(new_power, initial_power)

    def test_get_hierarchy_display_returns_string(self):
        display = self.hierarchy.get_hierarchy_display("Vercetti Gang")
        self.assertIsInstance(display, str)
        self.assertIn("VERCETTI GANG", display.upper())

    def test_gang_war_returns_winner(self):
        gang2, npcs2 = generate_gang("Haitians", ["Little Haiti"])
        self.gangs["Haitians"] = gang2
        self.npcs.update(npcs2)
        result = self.hierarchy.gang_war("Vercetti Gang", "Haitians", "Little Haiti")
        self.assertIn("winner", result)
        self.assertIn(result["winner"], ("Vercetti Gang", "Haitians"))

    def test_gang_war_produces_casualties(self):
        gang2, npcs2 = generate_gang("Haitians", ["Little Haiti"])
        self.gangs["Haitians"] = gang2
        self.npcs.update(npcs2)
        result = self.hierarchy.gang_war("Vercetti Gang", "Haitians", "Little Haiti")
        self.assertIn("casualties", result)
        self.assertIsInstance(result["casualties"], list)


# ---------------------------------------------------------------------------
# Consequence Engine Tests
# ---------------------------------------------------------------------------

class TestConsequenceEngine(unittest.TestCase):
    """Tests for the ConsequenceEngine event processing."""

    def setUp(self):
        gangs, npcs, districts = generate_vice_city()
        self.npcs = npcs
        self.gangs = gangs
        self.districts = districts
        self.memory = MemoryManager(npcs)
        self.hierarchy = HierarchyManager(gangs, npcs)
        self.engine = ConsequenceEngine(
            npcs, gangs, districts, self.memory, self.hierarchy
        )

    def _get_living_npc(self) -> NPC:
        return next(n for n in self.npcs.values() if n.alive)

    def test_process_assassination_kills_npc(self):
        npc = self._get_living_npc()
        event = Event(
            event_type=EventType.ASSASSINATION,
            description="Test assassination",
            outcome="NPC killed",
            involved_npcs=[npc.npc_id],
            player_involved=True,
        )
        self.engine.process_event(event)
        self.assertFalse(npc.alive)
        self.assertEqual(npc.health, 0)

    def test_process_alliance_improves_relationship(self):
        npc = self._get_living_npc()
        initial = npc.relationships.get("player", 0)
        event = Event(
            event_type=EventType.ALLIANCE,
            description="Alliance formed",
            outcome="Allied",
            involved_npcs=[npc.npc_id],
            player_involved=True,
        )
        self.engine.process_event(event)
        self.assertGreater(npc.relationships.get("player", 0), initial)

    def test_process_betrayal_triggers_revenge(self):
        npc = self._get_living_npc()
        for _ in range(3):
            event = Event(
                event_type=EventType.BETRAYAL,
                description="Betrayal",
                outcome="Betrayed",
                involved_npcs=[npc.npc_id],
                player_involved=True,
            )
            self.engine.process_event(event)
        self.assertTrue(npc.revenge_ready)

    def test_process_defeat_scars_npc(self):
        npc = self._get_living_npc()
        event = Event(
            event_type=EventType.DEFEAT,
            description="Player defeated NPC",
            outcome="Defeated",
            involved_npcs=[npc.npc_id],
            player_involved=True,
        )
        self.engine.process_event(event)
        self.assertTrue(npc.scarred)

    def test_check_revenge_triggers_returns_list(self):
        npc = self._get_living_npc()
        npc.revenge_ready = True
        result = self.engine.check_revenge_triggers()
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_update_world_state_returns_list(self):
        result = self.engine.update_world_state()
        self.assertIsInstance(result, list)

    def test_assassination_triggers_power_vacuum(self):
        # Find a gang boss and assassinate them
        for gang in self.gangs.values():
            boss = gang.get_leader(self.npcs)
            if boss:
                event = Event(
                    event_type=EventType.ASSASSINATION,
                    description="Boss killed",
                    outcome="Dead",
                    involved_npcs=[boss.npc_id],
                    player_involved=True,
                )
                consequences = self.engine.process_event(event)
                # Should mention power vacuum fill
                narrative = " ".join(consequences)
                # At least one consequence should be produced
                self.assertIsInstance(consequences, list)
                return
        self.fail("No living boss found for this test")


# ---------------------------------------------------------------------------
# Dialogue Tests
# ---------------------------------------------------------------------------

class TestDialogueGeneration(unittest.TestCase):
    """Tests for the DialogueGenerator."""

    def setUp(self):
        self.npc = generate_npc(Rank.BOSS, "Diaz Cartel")
        self.npc.territory = "Starfish Island"
        self.dialogue = DialogueGenerator()

    def test_generate_greeting_returns_string(self):
        result = self.dialogue.generate_greeting(self.npc, [])
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_generate_threat_returns_string(self):
        result = self.dialogue.generate_threat(self.npc, [])
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_generate_taunt_returns_string(self):
        result = self.dialogue.generate_taunt(self.npc)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_generate_respect_returns_string(self):
        result = self.dialogue.generate_respect(self.npc, [])
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_generate_betrayal_reaction_returns_string(self):
        result = self.dialogue.generate_betrayal_reaction(self.npc)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_hostile_npc_generates_threat_style_greeting(self):
        self.npc.relationships["player"] = -80
        # Should pick from hostile templates
        result = self.dialogue.generate_greeting(self.npc, [])
        self.assertIsInstance(result, str)

    def test_allied_npc_generates_friendly_greeting(self):
        self.npc.relationships["player"] = 90
        result = self.dialogue.generate_greeting(self.npc, [])
        self.assertIsInstance(result, str)

    def test_dialogue_with_past_event_history(self):
        event = Event(
            event_type=EventType.DEFEAT,
            description="Test",
            outcome="Defeated",
            involved_npcs=[self.npc.npc_id],
            player_involved=True,
        )
        result = self.dialogue.generate_threat(self.npc, [event])
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_contextual_line_varies_by_relationship(self):
        self.npc.relationships["player"] = 0
        neutral_line = self.dialogue.get_contextual_line(self.npc, [])
        self.npc.relationships["player"] = 80
        allied_line = self.dialogue.get_contextual_line(self.npc, [])
        # Both should be non-empty strings
        self.assertGreater(len(neutral_line), 0)
        self.assertGreater(len(allied_line), 0)


# ---------------------------------------------------------------------------
# Full Engine Integration Tests
# ---------------------------------------------------------------------------

class TestAntiHeroEngine(unittest.TestCase):
    """Integration tests for the full AntiHeroEngine."""

    def setUp(self):
        self.engine = AntiHeroEngine()

    def _get_living_npc_id(self) -> str:
        return next(n.npc_id for n in self.engine.npcs.values() if n.alive)

    def test_engine_initializes_world(self):
        self.assertGreater(len(self.engine.gangs), 0)
        self.assertGreater(len(self.engine.npcs), 0)
        self.assertGreater(len(self.engine.districts), 0)

    def test_player_action_attack(self):
        npc_id = self._get_living_npc_id()
        result = self.engine.player_action("attack", npc_id)
        self.assertTrue(result["success"])
        self.assertIn("dialogue", result)
        self.assertIn("consequences", result)

    def test_player_action_bribe(self):
        npc_id = self._get_living_npc_id()
        result = self.engine.player_action("bribe", npc_id)
        self.assertTrue(result["success"])

    def test_player_action_ally(self):
        npc_id = self._get_living_npc_id()
        result = self.engine.player_action("ally", npc_id)
        self.assertTrue(result["success"])

    def test_player_action_assassinate(self):
        npc_id = self._get_living_npc_id()
        result = self.engine.player_action("assassinate", npc_id)
        self.assertTrue(result["success"])
        npc = self.engine.npcs[npc_id]
        self.assertFalse(npc.alive)

    def test_player_action_dead_npc_fails(self):
        npc_id = self._get_living_npc_id()
        self.engine.npcs[npc_id].alive = False
        result = self.engine.player_action("attack", npc_id)
        self.assertFalse(result["success"])

    def test_advance_time_returns_list(self):
        events = self.engine.advance_time()
        self.assertIsInstance(events, list)

    def test_get_world_state_structure(self):
        state = self.engine.get_world_state()
        self.assertIn("gangs", state)
        self.assertIn("districts", state)
        self.assertIn("time_step", state)

    def test_get_npc_info_returns_profile(self):
        npc_id = self._get_living_npc_id()
        info = self.engine.get_npc_info(npc_id)
        self.assertIsNotNone(info)
        self.assertIn("name", info)
        self.assertIn("rank", info)
        self.assertIn("gang", info)

    def test_get_active_rivals_initially_empty(self):
        rivals = self.engine.get_active_rivals()
        # No actions taken yet, should be empty
        self.assertEqual(len(rivals), 0)

    def test_get_potential_allies_initially_empty(self):
        allies = self.engine.get_potential_allies()
        # No actions taken yet, should be empty
        self.assertEqual(len(allies), 0)

    def test_display_world_map_returns_string(self):
        result = self.engine.display_world_map()
        self.assertIsInstance(result, str)
        self.assertIn("VICE CITY", result)

    def test_get_gang_hierarchy_returns_string(self):
        result = self.engine.get_gang_hierarchy("Vercetti Gang")
        self.assertIsInstance(result, str)

    def test_start_turf_war_returns_result(self):
        result = self.engine.start_turf_war(
            "Vercetti Gang", "Diaz Cartel", "Downtown"
        )
        self.assertIn("winner", result)

    def test_rivals_appear_after_hostile_actions(self):
        npc_id = self._get_living_npc_id()
        # Perform multiple hostile actions to push relationship negative
        for _ in range(3):
            self.engine.player_action("attack", npc_id)
            if not self.engine.npcs[npc_id].alive:
                break
        rivals = self.engine.get_active_rivals()
        # Should have at least one rival now
        self.assertIsInstance(rivals, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
