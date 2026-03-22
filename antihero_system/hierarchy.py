"""
Dynamic hierarchy and power management for the Antihero System.

Handles promotions, demotions, power vacuums, gang wars, and the display
of the full gang hierarchy tree.
"""

from __future__ import annotations

import random

from .models import District, Gang, NPC, Rank

# Rank ordering — lower index = higher power
_RANK_ORDER = [
    Rank.BOSS,
    Rank.UNDERBOSS,
    Rank.CAPTAIN,
    Rank.ENFORCER,
    Rank.DEALER,
]


def _rank_index(rank: Rank) -> int:
    try:
        return _RANK_ORDER.index(rank)
    except ValueError:
        return len(_RANK_ORDER)


def _next_rank_up(rank: Rank) -> Rank | None:
    idx = _rank_index(rank)
    if idx > 0:
        return _RANK_ORDER[idx - 1]
    return None


def _next_rank_down(rank: Rank) -> Rank | None:
    idx = _rank_index(rank)
    if idx < len(_RANK_ORDER) - 1:
        return _RANK_ORDER[idx + 1]
    return None


class HierarchyManager:
    """Manages gang hierarchies, promotions, and turf wars.

    Args:
        gangs: Shared gang registry (``gang_name → Gang``).
        npcs:  Shared NPC registry (``npc_id → NPC``).
        districts: Shared district registry (``district_name → District``).
    """

    def __init__(
        self,
        gangs: dict[str, Gang],
        npcs: dict[str, NPC],
        districts: dict[str, District],
    ) -> None:
        self._gangs = gangs
        self._npcs = npcs
        self._districts = districts

    # ------------------------------------------------------------------
    # Promotion / Demotion
    # ------------------------------------------------------------------

    def promote_npc(self, npc_id: str) -> str | None:
        """Promote *npc_id* one rank within their gang.

        Returns:
            A descriptive message, or ``None`` if promotion is impossible.
        """
        npc = self._npcs.get(npc_id)
        if not npc or not npc.alive:
            return None
        new_rank = _next_rank_up(npc.rank)
        if new_rank is None:
            return f"{npc.nickname} is already a {npc.rank.value} — can't go higher."
        old_rank = npc.rank
        npc.rank = new_rank
        npc.respect_level = min(100, npc.respect_level + 10)
        self._refresh_hierarchy(npc.gang)
        return (
            f"{npc.nickname} ({npc.name}) has been promoted from "
            f"{old_rank.value} to {new_rank.value} in {npc.gang}!"
        )

    def demote_npc(self, npc_id: str) -> str | None:
        """Demote *npc_id* one rank within their gang.

        Returns:
            A descriptive message, or ``None`` if demotion is impossible.
        """
        npc = self._npcs.get(npc_id)
        if not npc or not npc.alive:
            return None
        new_rank = _next_rank_down(npc.rank)
        if new_rank is None:
            return f"{npc.nickname} is already a {npc.rank.value} — can't go lower."
        old_rank = npc.rank
        npc.rank = new_rank
        npc.respect_level = max(0, npc.respect_level - 10)
        self._refresh_hierarchy(npc.gang)
        return (
            f"{npc.nickname} ({npc.name}) has been demoted from "
            f"{old_rank.value} to {new_rank.value} in {npc.gang}."
        )

    def _refresh_hierarchy(self, gang_name: str) -> None:
        """Re-sort the gang's hierarchy list by rank (boss first)."""
        gang = self._gangs.get(gang_name)
        if not gang:
            return
        gang.hierarchy.sort(
            key=lambda nid: (
                _rank_index(self._npcs[nid].rank) if nid in self._npcs else 999,
                -(self._npcs[nid].respect_level if nid in self._npcs else 0),
            )
        )

    # ------------------------------------------------------------------
    # Power vacuum
    # ------------------------------------------------------------------

    def fill_power_vacuum(self, gang_name: str, vacant_rank: Rank) -> str | None:
        """Promote the most suitable NPC to fill a vacant rank.

        The best candidate is the highest-ranking living NPC below the
        vacant slot, with the highest respect level.  If no candidates
        exist inside the gang, an external gang may opportunistically move
        to fill the gap (territorial expansion).

        Args:
            gang_name:    Name of the gang with the vacancy.
            vacant_rank:  The rank that has become empty.

        Returns:
            A narrative string describing what happened, or ``None``.
        """
        gang = self._gangs.get(gang_name)
        if not gang:
            return None

        # Gather candidates: living members ranked *below* vacant_rank
        vacant_idx = _rank_index(vacant_rank)
        candidates: list[NPC] = []
        for npc_id in gang.members:
            npc = self._npcs.get(npc_id)
            if npc and npc.alive and _rank_index(npc.rank) > vacant_idx:
                candidates.append(npc)

        if not candidates:
            # No internal candidates — a rival gang sees opportunity
            for rival_name in gang.rival_gangs:
                rival = self._gangs.get(rival_name)
                if rival and rival.territory:
                    return (
                        f"Power vacuum in {gang_name}! "
                        f"No successor found — {rival_name} moves to fill the void."
                    )
            return f"Power vacuum in {gang_name} — the gang is leaderless and in disarray."

        # Best candidate: highest rank closest to vacant slot, then highest respect
        candidates.sort(key=lambda n: (_rank_index(n.rank), -n.respect_level))
        chosen = candidates[0]
        old_rank = chosen.rank
        chosen.rank = vacant_rank
        chosen.respect_level = min(100, chosen.respect_level + 15)

        return (
            f"Power vacuum in {gang_name}! "
            f"{chosen.nickname} ({chosen.name}) rises from {old_rank.value} "
            f"to {vacant_rank.value}!"
        )

    # ------------------------------------------------------------------
    # Gang war
    # ------------------------------------------------------------------

    def gang_war(
        self,
        gang1_name: str,
        gang2_name: str,
        district_name: str,
    ) -> tuple[str, list[str]]:
        """Simulate a turf war between two gangs over a district.

        Power levels determine the winner with some randomness.  Casualties
        are chosen from the losing gang's lowest-rank members first.

        Args:
            gang1_name:    Attacking gang.
            gang2_name:    Defending gang.
            district_name: The district being contested.

        Returns:
            A ``(narrative, casualties)`` tuple where *casualties* is a list
            of NPC IDs who were killed.
        """
        gang1 = self._gangs.get(gang1_name)
        gang2 = self._gangs.get(gang2_name)
        district = self._districts.get(district_name)

        if not gang1 or not gang2:
            return "One or both gangs are unknown.", []

        p1 = self.calculate_gang_power(gang1_name)
        p2 = self.calculate_gang_power(gang2_name)

        # Add randomness (±20 %)
        p1_roll = p1 * random.uniform(0.8, 1.2)
        p2_roll = p2 * random.uniform(0.8, 1.2)

        winner_name = gang1_name if p1_roll >= p2_roll else gang2_name
        loser_name = gang2_name if winner_name == gang1_name else gang1_name
        loser = self._gangs[loser_name]

        # Casualties: 1–3 members from the losing side (lowest ranks first)
        living_losers = [
            self._npcs[nid]
            for nid in loser.members
            if nid in self._npcs and self._npcs[nid].alive
        ]
        living_losers.sort(key=lambda n: -_rank_index(n.rank))  # dealers first
        num_casualties = min(len(living_losers), random.randint(1, 3))
        casualties = living_losers[:num_casualties]
        casualty_ids: list[str] = []
        for c in casualties:
            c.alive = False
            c.health = 0
            casualty_ids.append(c.npc_id)

        # Territory changes hands
        if district:
            district.controlling_gang = winner_name
            district.heat_level = min(100, district.heat_level + 20)
            if district_name not in self._gangs[winner_name].territory:
                self._gangs[winner_name].territory.append(district_name)
            if district_name in loser.territory:
                loser.territory.remove(district_name)

        casualty_names = ", ".join(c.nickname for c in casualties) if casualties else "none"
        narrative = (
            f"GANG WAR: {gang1_name} vs {gang2_name} for {district_name}!\n"
            f"  Winner: {winner_name} (power {p1} vs {p2})\n"
            f"  {district_name} now controlled by {winner_name}.\n"
            f"  Casualties from {loser_name}: {casualty_names}."
        )
        return narrative, casualty_ids

    # ------------------------------------------------------------------
    # Power calculation
    # ------------------------------------------------------------------

    def calculate_gang_power(self, gang_name: str) -> int:
        """Compute overall strength of a gang.

        Args:
            gang_name: Target gang name.

        Returns:
            Integer power score (higher = stronger).
        """
        gang = self._gangs.get(gang_name)
        if not gang:
            return 0
        return gang.power_level(self._npcs)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def get_hierarchy_display(self, gang_name: str) -> str:
        """Return a formatted, human-readable hierarchy tree for a gang.

        Args:
            gang_name: Target gang name.

        Returns:
            A multi-line string suitable for terminal output.
        """
        gang = self._gangs.get(gang_name)
        if not gang:
            return f"Gang '{gang_name}' not found."

        lines = [f"=== {gang_name} Hierarchy ==="]
        rank_groups: dict[Rank, list[NPC]] = {r: [] for r in _RANK_ORDER}

        for npc_id in gang.members:
            npc = self._npcs.get(npc_id)
            if npc:
                rank_groups[npc.rank].append(npc)

        indent_map = {
            Rank.BOSS: 0,
            Rank.UNDERBOSS: 2,
            Rank.CAPTAIN: 4,
            Rank.ENFORCER: 6,
            Rank.DEALER: 8,
        }
        for rank in _RANK_ORDER:
            members = rank_groups[rank]
            if not members:
                continue
            indent = " " * indent_map[rank]
            lines.append(f"{indent}[{rank.value}]")
            for npc in members:
                status = "✓" if npc.alive else "✗ DEAD"
                lines.append(
                    f"{indent}  └─ {npc.nickname} ({npc.name}) "
                    f"| Respect: {npc.respect_level} | {status}"
                )
        return "\n".join(lines)
