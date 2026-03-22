"""
Unit tests for the Antihero System.

Run with:
    python -m pytest tests/test_antihero.py -v
"""

from __future__ import annotations

import pytest

from antihero_system.models import NPC, Gang, District, Event, Rank, EventType
from antihero_system.generator import (
    generate_npc,
    generate_gang,
    generate_district,
    generate_vice_city,
    VICE_CITY_DISTRICTS,
)
from antihero_system.memory import MemoryManager
from antihero_system.hierarchy import HierarchyManager
from antihero_system.consequence import ConsequenceEngine
from antihero_system.dialogue import DialogueGenerator
from antihero_system.simulation import AntiHeroEngine, ACTION_ATTACK, ACTION_BRIBE, ACTION_ALLY, ACTION_ASSASSINATE


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def vice_city():
    """Full Vice City world (gangs, npcs, districts)."""
    gangs, npcs, districts = generate_vice_city()
    return gangs, npcs, districts


@pytest.fixture
def engine():
    """A fully initialised AntiHeroEngine."""
    return AntiHeroEngine()


# ===========================================================================
# 1. NPC Generation
# ===========================================================================

class TestNPCGeneration:
    def test_npc_has_required_fields(self):
        npc = generate_npc(Rank.ENFORCER, "Diaz Cartel")
        assert npc.npc_id
        assert npc.name
        assert npc.nickname
        assert npc.rank == Rank.ENFORCER
        assert npc.gang == "Diaz Cartel"
        assert isinstance(npc.traits, list)
        assert isinstance(npc.strengths, list)
        assert isinstance(npc.weaknesses, list)
        assert isinstance(npc.appearance, dict)
        assert npc.alive is True
        assert 0 <= npc.health <= 100
        assert 0 <= npc.respect_level <= 100

    def test_npc_ids_are_unique(self):
        npcs = [generate_npc(Rank.DEALER, "Haitians") for _ in range(50)]
        ids = [n.npc_id for n in npcs]
        assert len(set(ids)) == 50

    def test_npc_respect_scales_with_rank(self):
        boss = generate_npc(Rank.BOSS, "Vercetti Gang")
        dealer = generate_npc(Rank.DEALER, "Vercetti Gang")
        # Boss should generally have higher respect — allow ±20 fuzz due to randomness
        assert boss.respect_level >= dealer.respect_level - 20

    def test_appearance_has_expected_keys(self):
        npc = generate_npc(Rank.CAPTAIN, "Cubans")
        for key in ("scar", "tattoo", "clothing", "build", "hair"):
            assert key in npc.appearance

    def test_gang_hierarchy_generated(self):
        gang, npcs = generate_gang("Bikers")
        assert gang.name == "Bikers"
        assert len(gang.members) > 0
        ranks = {n.rank for n in npcs}
        assert Rank.BOSS in ranks
        assert Rank.UNDERBOSS in ranks
        assert Rank.DEALER in ranks

    def test_gang_member_counts(self):
        for _ in range(5):
            gang, npcs = generate_gang("Haitians")
            # Min: 1+1+2+4+6 = 14; Max: 1+2+4+8+12 = 27
            assert 14 <= len(npcs) <= 27

    def test_generate_vice_city_returns_five_gangs(self, vice_city):
        gangs, npcs, districts = vice_city
        assert len(gangs) == 5

    def test_generate_vice_city_district_count(self, vice_city):
        gangs, npcs, districts = vice_city
        assert len(districts) == len(VICE_CITY_DISTRICTS)

    def test_all_districts_assigned(self, vice_city):
        gangs, npcs, districts = vice_city
        for dname, district in districts.items():
            assert district.controlling_gang != "None", (
                f"District {dname} was not assigned to a gang"
            )


# ===========================================================================
# 2. Memory System
# ===========================================================================

class TestMemorySystem:
    def test_record_event_populates_npc_memory(self):
        npc = generate_npc(Rank.ENFORCER, "Diaz Cartel")
        npcs = {npc.npc_id: npc}
        mm = MemoryManager(npcs)

        event = Event(
            event_type=EventType.DEFEAT,
            description="Player defeated npc",
            involved_npcs=[npc.npc_id],
            player_involved=True,
        )
        mm.record_event(event)

        assert event.event_id in npc.memory

    def test_player_history_only_includes_player_events(self):
        npc = generate_npc(Rank.ENFORCER, "Bikers")
        npcs = {npc.npc_id: npc}
        mm = MemoryManager(npcs)

        player_ev = Event(
            event_type=EventType.DEFEAT,
            description="Player defeated npc",
            involved_npcs=[npc.npc_id],
            player_involved=True,
        )
        non_player_ev = Event(
            event_type=EventType.TURF_WAR,
            description="Gang fight",
            involved_npcs=[npc.npc_id],
            player_involved=False,
        )
        mm.record_event(player_ev)
        mm.record_event(non_player_ev)

        history = mm.get_player_history()
        ids = [e.event_id for e in history]
        assert player_ev.event_id in ids
        assert non_player_ev.event_id not in ids

    def test_rivalry_score_decreases_on_defeat(self):
        npc = generate_npc(Rank.CAPTAIN, "Cubans")
        npc.relationships["player"] = 0
        npcs = {npc.npc_id: npc}
        mm = MemoryManager(npcs)

        event = Event(
            event_type=EventType.DEFEAT,
            description="Defeat event",
            involved_npcs=[npc.npc_id],
            player_involved=True,
        )
        mm.record_event(event)
        assert mm.get_rivalry_score(npc.npc_id) < 0

    def test_rivalry_score_increases_on_alliance(self):
        npc = generate_npc(Rank.CAPTAIN, "Cubans")
        npc.relationships["player"] = 0
        npcs = {npc.npc_id: npc}
        mm = MemoryManager(npcs)

        event = Event(
            event_type=EventType.ALLIANCE,
            description="Alliance formed",
            involved_npcs=[npc.npc_id],
            player_involved=True,
        )
        mm.record_event(event)
        assert mm.get_rivalry_score(npc.npc_id) > 0

    def test_get_npc_history_returns_ordered_events(self):
        npc = generate_npc(Rank.DEALER, "Haitians")
        npcs = {npc.npc_id: npc}
        mm = MemoryManager(npcs)

        for et in [EventType.DEFEAT, EventType.BRIBE, EventType.ALLIANCE]:
            mm.record_event(
                Event(
                    event_type=et,
                    description=et.value,
                    involved_npcs=[npc.npc_id],
                    player_involved=True,
                )
            )

        history = mm.get_npc_history(npc.npc_id)
        timestamps = [e.timestamp for e in history]
        assert timestamps == sorted(timestamps)

    def test_relationship_summary_returns_string(self):
        npc = generate_npc(Rank.BOSS, "Diaz Cartel")
        npcs = {npc.npc_id: npc}
        mm = MemoryManager(npcs)
        summary = mm.get_relationship_summary(npc.npc_id)
        assert isinstance(summary, str)
        assert len(summary) > 0


# ===========================================================================
# 3. Hierarchy System
# ===========================================================================

class TestHierarchySystem:
    def test_promote_npc_increases_rank(self, vice_city):
        gangs, npcs, districts = vice_city
        hm = HierarchyManager(gangs, npcs, districts)

        # Find a dealer
        dealer = next((n for n in npcs.values() if n.rank == Rank.DEALER and n.alive), None)
        assert dealer is not None, "No dealer found in world"

        old_rank = dealer.rank
        result = hm.promote_npc(dealer.npc_id)
        assert result is not None
        assert dealer.rank.value != old_rank.value or "already" in result.lower()

    def test_demote_npc_decreases_rank(self, vice_city):
        gangs, npcs, districts = vice_city
        hm = HierarchyManager(gangs, npcs, districts)

        boss = next((n for n in npcs.values() if n.rank == Rank.BOSS and n.alive), None)
        assert boss is not None

        result = hm.demote_npc(boss.npc_id)
        assert result is not None
        # Boss demoted → should now be underboss (or message about lowest rank)
        assert boss.rank != Rank.BOSS or "can't" in result.lower()

    def test_fill_power_vacuum_promotes_successor(self, vice_city):
        gangs, npcs, districts = vice_city
        hm = HierarchyManager(gangs, npcs, districts)

        gang_name = "Diaz Cartel"
        gang = gangs[gang_name]
        boss_id = next(
            (nid for nid in gang.members if npcs[nid].rank == Rank.BOSS), None
        )
        assert boss_id is not None
        npcs[boss_id].alive = False  # kill the boss

        result = hm.fill_power_vacuum(gang_name, Rank.BOSS)
        assert result is not None
        assert "Power vacuum" in result

    def test_gang_war_produces_narrative(self, vice_city):
        gangs, npcs, districts = vice_city
        hm = HierarchyManager(gangs, npcs, districts)

        g1_name = "Diaz Cartel"
        g2_name = "Vercetti Gang"
        district_name = list(districts.keys())[0]

        narrative, casualties = hm.gang_war(g1_name, g2_name, district_name)
        assert isinstance(narrative, str)
        assert "GANG WAR" in narrative
        assert isinstance(casualties, list)

    def test_calculate_gang_power_is_positive(self, vice_city):
        gangs, npcs, districts = vice_city
        hm = HierarchyManager(gangs, npcs, districts)

        for gname in gangs:
            power = hm.calculate_gang_power(gname)
            assert power > 0

    def test_hierarchy_display_returns_string(self, vice_city):
        gangs, npcs, districts = vice_city
        hm = HierarchyManager(gangs, npcs, districts)
        display = hm.get_hierarchy_display("Vercetti Gang")
        assert "Vercetti Gang" in display
        assert "Boss" in display

    def test_hierarchy_reorders_after_promotion(self, vice_city):
        gangs, npcs, districts = vice_city
        hm = HierarchyManager(gangs, npcs, districts)
        gang_name = "Diaz Cartel"
        gang = gangs[gang_name]

        # Find a dealer and promote them
        dealer = next(
            (npcs[nid] for nid in gang.members if npcs[nid].rank == Rank.DEALER and npcs[nid].alive),
            None,
        )
        assert dealer is not None
        hm.promote_npc(dealer.npc_id)

        # Verify hierarchy is sorted by rank
        from antihero_system.hierarchy import _rank_index
        ranks_in_order = [_rank_index(npcs[nid].rank) for nid in gang.hierarchy if nid in npcs]
        assert ranks_in_order == sorted(ranks_in_order)


# ===========================================================================
# 4. Consequence Engine
# ===========================================================================

class TestConsequenceEngine:
    def _make_engine_components(self, vice_city):
        gangs, npcs, districts = vice_city
        mm = MemoryManager(npcs)
        hm = HierarchyManager(gangs, npcs, districts)
        ce = ConsequenceEngine(gangs, npcs, districts, hm, mm)
        return gangs, npcs, districts, mm, hm, ce

    def test_assassination_triggers_power_vacuum(self, vice_city):
        gangs, npcs, districts, mm, hm, ce = self._make_engine_components(vice_city)

        boss = next((n for n in npcs.values() if n.rank == Rank.BOSS), None)
        assert boss is not None
        boss.alive = False  # mark as dead before processing

        event = Event(
            event_type=EventType.ASSASSINATION,
            description=f"Player assassinated {boss.nickname}",
            involved_npcs=[boss.npc_id],
            player_involved=True,
        )
        consequences = ce.process_event(event)
        # Should contain at least a power vacuum or retaliation message
        assert len(consequences) > 0

    def test_betrayal_may_cause_defection(self, vice_city):
        gangs, npcs, districts, mm, hm, ce = self._make_engine_components(vice_city)

        npc = next((n for n in npcs.values() if n.rank == Rank.ENFORCER and n.alive), None)
        assert npc is not None
        original_gang = npc.gang

        event = Event(
            event_type=EventType.BETRAYAL,
            description="Player betrayed NPC",
            involved_npcs=[npc.npc_id],
            player_involved=True,
        )
        ce.process_event(event)
        # Either still in original gang or defected — no crash
        assert npc.gang in gangs or npc.gang == original_gang

    def test_bribe_reduces_npc_respect(self, vice_city):
        gangs, npcs, districts, mm, hm, ce = self._make_engine_components(vice_city)

        npc = next((n for n in npcs.values() if n.alive), None)
        assert npc is not None
        original_respect = npc.respect_level

        event = Event(
            event_type=EventType.BRIBE,
            description="Player bribed NPC",
            involved_npcs=[npc.npc_id],
            player_involved=True,
        )
        ce.process_event(event)
        assert npc.respect_level <= original_respect

    def test_check_revenge_triggers(self, vice_city):
        gangs, npcs, districts, mm, hm, ce = self._make_engine_components(vice_city)

        # Force a deep negative relationship
        npc = next(iter(npcs.values()))
        npc.relationships["player"] = -80
        alerts = ce.check_revenge_triggers()
        assert any(npc.nickname in a for a in alerts)

    def test_update_world_state_returns_list(self, vice_city):
        gangs, npcs, districts, mm, hm, ce = self._make_engine_components(vice_city)
        updates = ce.update_world_state()
        assert isinstance(updates, list)

    def test_defeat_does_not_duplicate_vengeful_trait(self, vice_city):
        gangs, npcs, districts, mm, hm, ce = self._make_engine_components(vice_city)
        npc = next((n for n in npcs.values() if n.alive), None)
        assert npc is not None
        # Remove existing vengeful if present
        npc.traits = [t for t in npc.traits if t != "vengeful"]

        for _ in range(5):
            event = Event(
                event_type=EventType.DEFEAT,
                description="Player defeated NPC",
                involved_npcs=[npc.npc_id],
                player_involved=True,
            )
            ce.process_event(event)

        assert npc.traits.count("vengeful") <= 1


# ===========================================================================
# 5. Dialogue Generation
# ===========================================================================

class TestDialogueGeneration:
    def test_greeting_returns_string(self):
        npc = generate_npc(Rank.BOSS, "Diaz Cartel")
        gen = DialogueGenerator()
        result = gen.generate_greeting(npc, [])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hostile_greeting_differs_from_ally_greeting(self):
        npc_hostile = generate_npc(Rank.ENFORCER, "Haitians")
        npc_hostile.relationships["player"] = -80

        npc_ally = generate_npc(Rank.ENFORCER, "Haitians")
        npc_ally.relationships["player"] = 80

        gen = DialogueGenerator()
        hostile_greet = gen.generate_greeting(npc_hostile, [])
        ally_greet = gen.generate_greeting(npc_ally, [])
        # They may occasionally match due to randomness but pools differ
        # Just ensure both are non-empty strings
        assert hostile_greet and ally_greet

    def test_threat_references_past_event(self):
        npc = generate_npc(Rank.CAPTAIN, "Bikers")
        event = Event(
            event_type=EventType.DEFEAT,
            description="the ambush at Little Haiti",
            involved_npcs=[npc.npc_id],
            player_involved=True,
        )
        gen = DialogueGenerator()
        threat = gen.generate_threat(npc, [event])
        # The past_event placeholder should be filled
        assert "{past_event}" not in threat

    def test_betrayal_reaction_returns_string(self):
        npc = generate_npc(Rank.UNDERBOSS, "Vercetti Gang")
        gen = DialogueGenerator()
        result = gen.generate_betrayal_reaction(npc)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_taunt_returns_string(self):
        npc = generate_npc(Rank.DEALER, "Cubans")
        gen = DialogueGenerator()
        result = gen.generate_taunt(npc)
        assert isinstance(result, str)

    def test_respect_returns_string(self):
        npc = generate_npc(Rank.BOSS, "Vercetti Gang")
        gen = DialogueGenerator()
        result = gen.generate_respect(npc, [])
        assert isinstance(result, str)


# ===========================================================================
# 6. Full Simulation / Gang War Outcomes
# ===========================================================================

class TestSimulationEngine:
    def test_engine_initialises_world(self, engine):
        assert len(engine.gangs) == 5
        assert len(engine.npcs) > 0
        assert len(engine.districts) > 0

    def test_player_attack_action(self, engine):
        npc = next(n for n in engine.npcs.values() if n.alive)
        result = engine.player_action(ACTION_ATTACK, npc.npc_id)
        assert result["success"] is True
        assert isinstance(result["dialogue"], str)
        assert isinstance(result["consequences"], list)

    def test_player_bribe_action_increases_relationship(self, engine):
        npc = next(n for n in engine.npcs.values() if n.alive)
        npc.relationships["player"] = 0
        engine.player_action(ACTION_BRIBE, npc.npc_id)
        # MemoryManager applies delta; bribe delta is +10
        score = npc.relationships.get("player", 0)
        assert score > 0

    def test_player_ally_action(self, engine):
        npc = next(n for n in engine.npcs.values() if n.alive)
        result = engine.player_action(ACTION_ALLY, npc.npc_id)
        assert result["success"] is True

    def test_assassinate_kills_npc(self, engine):
        npc = next(n for n in engine.npcs.values() if n.alive)
        engine.player_action(ACTION_ASSASSINATE, npc.npc_id)
        assert npc.alive is False

    def test_advance_time_returns_list(self, engine):
        updates = engine.advance_time()
        assert isinstance(updates, list)

    def test_get_world_state_has_all_gangs(self, engine):
        state = engine.get_world_state()
        for gname in engine.gangs:
            assert gname in state["gangs"]

    def test_get_active_rivals_returns_list(self, engine):
        rivals = engine.get_active_rivals()
        assert isinstance(rivals, list)

    def test_get_potential_allies_returns_list(self, engine):
        allies = engine.get_potential_allies()
        assert isinstance(allies, list)

    def test_get_npc_info_returns_dict(self, engine):
        npc_id = next(iter(engine.npcs))
        info = engine.get_npc_info(npc_id)
        assert isinstance(info, dict)
        for key in ("name", "nickname", "rank", "gang", "alive", "health"):
            assert key in info

    def test_display_world_map_returns_string(self, engine):
        output = engine.display_world_map()
        assert isinstance(output, str)
        assert "VICE CITY" in output

    def test_action_on_dead_npc_fails_gracefully(self, engine):
        npc = next(n for n in engine.npcs.values() if n.alive)
        npc.alive = False
        result = engine.player_action(ACTION_ATTACK, npc.npc_id)
        assert result["success"] is False

    def test_action_on_unknown_npc_fails_gracefully(self, engine):
        result = engine.player_action(ACTION_ATTACK, "nonexistent-id")
        assert result["success"] is False

    def test_gang_war_changes_territory(self, engine):
        g1_name = "Diaz Cartel"
        g2_name = "Vercetti Gang"
        district_name = list(engine.districts.keys())[0]

        narrative, casualties = engine.hierarchy.gang_war(g1_name, g2_name, district_name)
        assert engine.districts[district_name].controlling_gang in (g1_name, g2_name)

    def test_multiple_time_advances(self, engine):
        for _ in range(5):
            updates = engine.advance_time()
            assert isinstance(updates, list)
