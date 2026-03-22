"""
Dynamic hierarchy and power system for the Antihero System.

Manages gang promotions, demotions, power vacuums, and gang wars.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from .models import Gang, NPC, Rank, RANK_ORDER


class HierarchyManager:
    """
    Manages the internal hierarchy of all gangs.

    Args:
        gangs: Mapping of gang name → Gang.
        npcs: Mapping of npc_id → NPC.
    """

    def __init__(self, gangs: Dict[str, Gang], npcs: Dict[str, NPC]) -> None:
        self.gangs = gangs
        self.npcs = npcs

    # ------------------------------------------------------------------
    # Promotion / Demotion
    # ------------------------------------------------------------------

    def promote_npc(self, npc_id: str) -> Optional[Rank]:
        """
        Move an NPC one rank up in their gang's hierarchy.

        Returns the new Rank, or None if already at the top.
        """
        npc = self.npcs.get(npc_id)
        if not npc or not npc.alive:
            return None
        gang = self.gangs.get(npc.gang)
        if not gang:
            return None

        current_idx = RANK_ORDER.index(npc.rank)
        if current_idx == 0:
            return None  # Already Boss

        new_rank = RANK_ORDER[current_idx - 1]
        self._change_rank(gang, npc, new_rank)
        npc.respect_level = min(100, npc.respect_level + 10)
        return new_rank

    def demote_npc(self, npc_id: str) -> Optional[Rank]:
        """
        Move an NPC one rank down in their gang's hierarchy.

        Returns the new Rank, or None if already at the bottom.
        """
        npc = self.npcs.get(npc_id)
        if not npc or not npc.alive:
            return None
        gang = self.gangs.get(npc.gang)
        if not gang:
            return None

        current_idx = RANK_ORDER.index(npc.rank)
        if current_idx == len(RANK_ORDER) - 1:
            return None  # Already Dealer

        new_rank = RANK_ORDER[current_idx + 1]
        self._change_rank(gang, npc, new_rank)
        npc.respect_level = max(0, npc.respect_level - 10)
        return new_rank

    def _change_rank(self, gang: Gang, npc: NPC, new_rank: Rank) -> None:
        """Update internal structures when an NPC changes rank."""
        old_rank_key = npc.rank.value
        new_rank_key = new_rank.value

        # Remove from old rank list
        if old_rank_key in gang.hierarchy and npc.npc_id in gang.hierarchy[old_rank_key]:
            gang.hierarchy[old_rank_key].remove(npc.npc_id)

        # Add to new rank list
        if new_rank_key not in gang.hierarchy:
            gang.hierarchy[new_rank_key] = []
        if npc.npc_id not in gang.hierarchy[new_rank_key]:
            gang.hierarchy[new_rank_key].append(npc.npc_id)

        npc.rank = new_rank

    # ------------------------------------------------------------------
    # Power vacuum
    # ------------------------------------------------------------------

    def fill_power_vacuum(self, gang_name: str, rank: Rank) -> Optional[NPC]:
        """
        When a leader dies, promote the best candidate to fill the vacancy.

        Looks at the rank immediately below and selects the NPC with the
        highest respect. Returns the promoted NPC, or None if none available.
        """
        gang = self.gangs.get(gang_name)
        if not gang:
            return None

        rank_idx = RANK_ORDER.index(rank)
        # Search downward for candidates
        for candidate_rank in RANK_ORDER[rank_idx + 1:]:
            candidates = [
                self.npcs[nid]
                for nid in gang.hierarchy.get(candidate_rank.value, [])
                if nid in self.npcs and self.npcs[nid].alive
            ]
            if candidates:
                # Best candidate: highest respect level
                best = max(candidates, key=lambda n: n.respect_level)
                # Promote all the way up to the vacant rank
                while best.rank != rank:
                    self.promote_npc(best.npc_id)
                return best

        return None  # Gang has no living members left

    # ------------------------------------------------------------------
    # Gang war
    # ------------------------------------------------------------------

    def gang_war(
        self,
        gang1_name: str,
        gang2_name: str,
        district_name: str,
    ) -> Dict:
        """
        Simulate a turf war between two gangs over a district.

        Outcomes:
        - Attacker wins → district changes hands, some defenders die/are demoted
        - Defender wins → attackers suffer casualties

        Returns a summary dict with winner, casualties, and district outcome.
        """
        gang1 = self.gangs.get(gang1_name)
        gang2 = self.gangs.get(gang2_name)
        if not gang1 or not gang2:
            return {"error": "Unknown gang(s)"}

        power1 = self.calculate_gang_power(gang1_name)
        power2 = self.calculate_gang_power(gang2_name)

        # Add randomness — even a weaker gang can win
        roll1 = power1 * random.uniform(0.7, 1.3)
        roll2 = power2 * random.uniform(0.7, 1.3)

        winner_name = gang1_name if roll1 >= roll2 else gang2_name
        loser_name = gang2_name if winner_name == gang1_name else gang1_name
        loser_gang = self.gangs[loser_name]

        casualties: List[str] = []
        # Losers take 1-3 casualties among living non-boss members
        losers_alive = [
            self.npcs[nid]
            for nid in loser_gang.members
            if nid in self.npcs
            and self.npcs[nid].alive
            and self.npcs[nid].rank != Rank.BOSS
        ]
        num_casualties = min(len(losers_alive), random.randint(1, 3))
        for victim in random.sample(losers_alive, num_casualties):
            victim.alive = False
            victim.health = 0
            casualties.append(victim.npc_id)
            # Fill any power vacuums created
            self.fill_power_vacuum(loser_name, victim.rank)

        return {
            "winner": winner_name,
            "loser": loser_name,
            "district": district_name,
            "district_captured": True,
            "casualties": casualties,
            "attacker_power": power1,
            "defender_power": power2,
        }

    # ------------------------------------------------------------------
    # Power calculation
    # ------------------------------------------------------------------

    def calculate_gang_power(self, gang_name: str) -> int:
        """Compute overall gang strength from living member ranks."""
        gang = self.gangs.get(gang_name)
        if not gang:
            return 0
        return gang.power_level(self.npcs)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def get_hierarchy_display(self, gang_name: str) -> str:
        """Return a formatted hierarchy tree for the given gang."""
        gang = self.gangs.get(gang_name)
        if not gang:
            return f"Gang '{gang_name}' not found."

        lines = [f"\n{'='*50}", f"  {gang.name.upper()} HIERARCHY", f"{'='*50}"]
        indent = {
            Rank.BOSS: "",
            Rank.UNDERBOSS: "  ",
            Rank.CAPTAIN: "    ",
            Rank.ENFORCER: "      ",
            Rank.DEALER: "        ",
        }
        symbols = {
            Rank.BOSS: "★",
            Rank.UNDERBOSS: "◆",
            Rank.CAPTAIN: "▲",
            Rank.ENFORCER: "●",
            Rank.DEALER: "○",
        }

        for rank in RANK_ORDER:
            npc_ids = gang.hierarchy.get(rank.value, [])
            living = [self.npcs[nid] for nid in npc_ids if nid in self.npcs]
            if not living:
                continue
            lines.append(f"\n{indent[rank]}{symbols[rank]} {rank.value}:")
            for npc in living:
                status = "✓" if npc.alive else "✗ [DEAD]"
                lines.append(
                    f"{indent[rank]}  {status} {npc.name} "
                    f"('{npc.nickname}') — Respect: {npc.respect_level}"
                )

        lines.append(f"\n  Total Power: {self.calculate_gang_power(gang_name)}")
        lines.append(f"{'='*50}\n")
        return "\n".join(lines)
