"""
Interactive CLI demo for the Antihero System.

A text-based menu-driven game that demonstrates the full Antihero System
with Vice City-style emergent storytelling.
"""

from __future__ import annotations

import sys

try:
    import colorama
    from colorama import Fore, Style, Back
    colorama.init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False

from antihero_system import AntiHeroEngine
from antihero_system.models import Rank

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def _c(text: str, color: str = "") -> str:
    if not HAS_COLOR:
        return text
    color_map = {
        "red":    Fore.RED,
        "green":  Fore.GREEN,
        "yellow": Fore.YELLOW,
        "cyan":   Fore.CYAN,
        "blue":   Fore.BLUE,
        "white":  Fore.WHITE,
        "bold":   Style.BRIGHT,
        "reset":  Style.RESET_ALL,
    }
    code = color_map.get(color, "")
    return f"{code}{text}{Style.RESET_ALL}"


GANG_COLORS = {
    "Diaz Cartel":   "red",
    "Vercetti Gang": "blue",
    "Haitians":      "yellow",
    "Cubans":        "green",
    "Bikers":        "cyan",
}


def _gang_color(gang_name: str, text: str) -> str:
    return _c(text, GANG_COLORS.get(gang_name, "white"))


def print_header(text: str) -> None:
    width = 60
    print(_c(f"\n{'═'*width}", "cyan"))
    print(_c(f"  {text}", "bold"))
    print(_c(f"{'═'*width}", "cyan"))


def print_divider() -> None:
    print(_c("─" * 60, "cyan"))


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def display_npc_profile(engine: AntiHeroEngine, npc_id: str) -> None:
    info = engine.get_npc_info(npc_id)
    if not info:
        print(_c("NPC not found.", "red"))
        return
    npc = info["npc"]
    alive_str = _c("ALIVE", "green") if npc.alive else _c("DEAD", "red")
    print_header(f"NPC PROFILE — {npc.display_name()}")
    print(f"  Status:     {alive_str}")
    print(f"  Rank:       {_c(info['rank'], 'yellow')}")
    print(f"  Gang:       {_gang_color(info['gang'], info['gang'])}")
    print(f"  Territory:  {info['territory']}")
    print(f"  Health:     {info['health']}")
    print(f"  Respect:    {info['respect']}")
    print(f"  Traits:     {', '.join(npc.traits)}")
    print(f"  Strengths:  {', '.join(npc.strengths)}")
    print(f"  Weaknesses: {', '.join(npc.weaknesses)}")
    print(f"  Appearance: {', '.join(f'{k}: {v}' for k, v in npc.appearance.items())}")
    if npc.scarred:
        print(f"  {_c('★ SCARRED — Returned stronger after defeat', 'yellow')}")
    if npc.revenge_ready:
        print(f"  {_c('⚠ REVENGE READY — Actively hunting you!', 'red')}")
    player_rel = info["player_relationship"]
    rel_color = "green" if player_rel > 0 else "red" if player_rel < 0 else "white"
    print(f"\n  Player Relationship: {_c(str(player_rel), rel_color)}")
    print(f"  {_c(info['relationship_summary'], 'cyan')}")
    if info["recent_events"]:
        print(f"\n  Recent Events:")
        for ev in info["recent_events"]:
            print(f"    [{ev['type']}] {ev['description']}")


def display_world_state(engine: AntiHeroEngine) -> None:
    print(engine.display_world_map())
    state = engine.get_world_state()
    print_header(f"GANG POWER RANKINGS  [Turn {state['time_step']}]")
    gangs_sorted = sorted(
        state["gangs"].items(),
        key=lambda x: x[1]["power"],
        reverse=True,
    )
    for rank_pos, (name, data) in enumerate(gangs_sorted, 1):
        power_bar = "█" * (data["power"] // 5)
        print(
            f"  {rank_pos}. {_gang_color(name, name):<20} "
            f"Power: {_c(str(data['power']), 'yellow'):>5}  "
            f"{_c(power_bar, GANG_COLORS.get(name, 'white'))}"
        )
        print(
            f"     Members alive: {data['members_alive']}/{data['total_members']}  "
            f"Territory: {', '.join(data['territory']) or 'None'}"
        )


def select_npc(engine: AntiHeroEngine) -> str | None:
    """Let the player select an NPC from a list."""
    living = engine.get_living_npcs()
    if not living:
        print(_c("No living NPCs found.", "red"))
        return None

    print_header("SELECT AN NPC")
    # Show up to 20 NPCs for readability
    shown = living[:20]
    for idx, npc in enumerate(shown, 1):
        rel = npc.relationships.get("player", 0)
        rel_str = _c(f"{rel:+d}", "green" if rel > 0 else "red" if rel < 0 else "white")
        revenge_flag = _c(" ⚠", "red") if npc.revenge_ready else ""
        print(
            f"  {idx:>2}. {npc.name:<22} "
            f"({_gang_color(npc.gang, npc.gang):<20}) "
            f"{npc.rank.value:<10} "
            f"Rel: {rel_str}{revenge_flag}"
        )
    print("   0. Cancel")
    try:
        choice = int(input(_c("\nEnter number: ", "bold")))
        if choice == 0:
            return None
        if 1 <= choice <= len(shown):
            return shown[choice - 1].npc_id
    except (ValueError, IndexError):
        pass
    print(_c("Invalid choice.", "red"))
    return None


def display_consequences(consequences: list[str]) -> None:
    if consequences:
        print(_c("\n  ⟹ World Consequences:", "yellow"))
        for c in consequences:
            print(_c(f"    • {c}", "cyan"))


# ---------------------------------------------------------------------------
# Main game loop
# ---------------------------------------------------------------------------

MENU = """
{divider}
  {title}
{divider}
  1. View World Map & Gang Power
  2. Browse NPC Profiles & Hierarchies
  3. Attack an NPC
  4. Assassinate an NPC
  5. Bribe an NPC
  6. Form Alliance with NPC
  7. Intimidate an NPC
  8. Start a Turf War
  9. Advance Time (world simulates)
  A. View Your Rivalry History
  B. View Active Rivals & Potential Allies
  Q. Quit
{divider}
"""


def main() -> None:
    print(_c("\n" + "🌴 " * 20, "green"))
    print(_c("  ANTIHERO SYSTEM — VICE CITY", "bold"))
    print(_c("  A Dynamic NPC Rivalry Engine", "cyan"))
    print(_c("🌴 " * 20 + "\n", "green"))

    print("Generating Vice City world...")
    engine = AntiHeroEngine()
    state = engine.get_world_state()
    total_npcs = sum(d["total_members"] for d in state["gangs"].values())
    print(_c(f"✓ World generated: {len(engine.gangs)} gangs, "
             f"{total_npcs} NPCs, "
             f"{len(engine.districts)} districts\n", "green"))

    while True:
        print(MENU.format(
            divider=_c("─" * 50, "cyan"),
            title=_c("MAIN MENU", "bold"),
        ))
        choice = input(_c("Choice: ", "bold")).strip().upper()

        if choice == "Q":
            print(_c("\nStay off my turf. Ciao.\n", "yellow"))
            sys.exit(0)

        elif choice == "1":
            display_world_state(engine)

        elif choice == "2":
            # Show hierarchy browser
            print_header("GANG HIERARCHY BROWSER")
            for i, name in enumerate(engine.gangs.keys(), 1):
                print(f"  {i}. {_gang_color(name, name)}")
            try:
                idx = int(input(_c("\nSelect gang (0 to browse NPCs instead): ", "bold")))
                if idx == 0:
                    npc_id = select_npc(engine)
                    if npc_id:
                        display_npc_profile(engine, npc_id)
                elif 1 <= idx <= len(engine.gangs):
                    gang_name = list(engine.gangs.keys())[idx - 1]
                    print(engine.get_gang_hierarchy(gang_name))
            except ValueError:
                pass

        elif choice in ("3", "4", "5", "6", "7"):
            action_map = {
                "3": "attack",
                "4": "assassinate",
                "5": "bribe",
                "6": "ally",
                "7": "intimidate",
            }
            action = action_map[choice]
            npc_id = select_npc(engine)
            if npc_id:
                print(_c(f"\nExecuting: {action.upper()}...", "yellow"))
                result = engine.player_action(action, npc_id)
                if result["success"]:
                    npc = result["npc"]
                    print(_c(f"\n  [{action.upper()}] {npc.display_name()}", "bold"))
                    print(f"\n  {_gang_color(npc.gang, npc.name)}: "
                          f"\"{_c(result['dialogue'], 'cyan')}\"")
                    display_consequences(result["consequences"])
                else:
                    print(_c(f"\n  Error: {result.get('error', 'Unknown error')}", "red"))

        elif choice == "8":
            # Turf war
            print_header("START A TURF WAR")
            gang_names = list(engine.gangs.keys())
            for i, name in enumerate(gang_names, 1):
                print(f"  {i}. {_gang_color(name, name)}")
            try:
                a_idx = int(input(_c("\nSelect attacking gang: ", "bold"))) - 1
                d_idx = int(input(_c("Select defending gang: ", "bold"))) - 1
                if a_idx == d_idx:
                    print(_c("Cannot war with yourself.", "red"))
                    continue
                attacker = gang_names[a_idx]
                defender = gang_names[d_idx]

                dist_names = list(engine.districts.keys())
                for i, dname in enumerate(dist_names, 1):
                    d = engine.districts[dname]
                    ctrl = d.controlling_gang or "Contested"
                    print(f"  {i}. {dname} [{ctrl}]")
                d_choice = int(input(_c("Select district: ", "bold"))) - 1
                district = dist_names[d_choice]

                print(_c(f"\n  WAR: {attacker} vs {defender} in {district}!", "red"))
                result = engine.start_turf_war(attacker, defender, district)
                if "winner" in result:
                    print(_c(f"\n  WINNER: {result['winner']}", "green"))
                    print(_c(f"  {result.get('outcome', '')}", "cyan"))
                    if result.get("casualties"):
                        print(_c(f"  Casualties: {len(result['casualties'])} NPC(s) killed", "red"))
            except (ValueError, IndexError):
                print(_c("Invalid selection.", "red"))

        elif choice == "9":
            print(_c("\n  ⏩ Time advances...", "yellow"))
            events = engine.advance_time()
            state = engine.get_world_state()
            print(_c(f"  [Turn {state['time_step']}]", "cyan"))
            if events:
                for ev in events:
                    print(_c(f"  • {ev}", "white"))
            else:
                print(_c("  The city is quiet... for now.", "cyan"))
            # Show revenge warnings
            revenge_warnings = engine.consequence.check_revenge_triggers()
            for w in revenge_warnings:
                print(_c(f"  {w}", "red"))

        elif choice == "A":
            print_header("YOUR RIVALRY HISTORY")
            history = engine.memory.get_player_history()
            if not history:
                print(_c("  You haven't made any moves yet.", "cyan"))
            else:
                for event in history[-15:]:  # last 15 events
                    ts = event.timestamp.strftime("%H:%M:%S")
                    print(
                        f"  [{_c(event.event_type.value, 'yellow')}] "
                        f"{_c(ts, 'cyan')} — {event.description}"
                    )

        elif choice == "B":
            print_header("ACTIVE RIVALS & POTENTIAL ALLIES")
            rivals = engine.get_active_rivals()
            allies = engine.get_potential_allies()
            if rivals:
                print(_c(f"\n  🔴 ACTIVE RIVALS ({len(rivals)}):", "red"))
                for npc in rivals[:10]:
                    rel = npc.relationships.get("player", 0)
                    print(
                        f"    • {npc.display_name()} "
                        f"[{_gang_color(npc.gang, npc.gang)}] "
                        f"Rel: {_c(str(rel), 'red')}"
                        + (_c(" ⚠ REVENGE", "red") if npc.revenge_ready else "")
                    )
            else:
                print(_c("  No active rivals yet.", "green"))

            if allies:
                print(_c(f"\n  🟢 POTENTIAL ALLIES ({len(allies)}):", "green"))
                for npc in allies[:10]:
                    rel = npc.relationships.get("player", 0)
                    print(
                        f"    • {npc.display_name()} "
                        f"[{_gang_color(npc.gang, npc.gang)}] "
                        f"Rel: {_c(str(rel), 'green')}"
                    )
            else:
                print(_c("  No potential allies yet.", "yellow"))

        else:
            print(_c("  Unknown option. Try again.", "red"))


if __name__ == "__main__":
    main()
