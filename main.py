#!/usr/bin/env python3
"""
main.py — Interactive CLI demo for the Antihero System.

Run with:
    python main.py
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

    class _FakeColor:
        def __getattr__(self, _):
            return ""

    Fore = Style = Back = _FakeColor()

from antihero_system import AntiHeroEngine
from antihero_system.simulation import (
    ACTION_ATTACK,
    ACTION_ASSASSINATE,
    ACTION_BRIBE,
    ACTION_ALLY,
    ACTION_INTIMIDATE,
    ACTION_TURF_WAR,
)


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def c(text: str, colour: str = "") -> str:
    """Wrap *text* in an ANSI colour code (no-op if colorama unavailable)."""
    if not HAS_COLOR:
        return text
    return f"{colour}{text}{Style.RESET_ALL}"


def header(text: str) -> None:
    print(c(f"\n{'═' * 60}", Fore.CYAN))
    print(c(f"  {text}", Fore.CYAN + Style.BRIGHT))
    print(c(f"{'═' * 60}", Fore.CYAN))


def section(text: str) -> None:
    print(c(f"\n  ─── {text} ───", Fore.YELLOW))


def info(text: str) -> None:
    print(c(f"  {text}", Fore.WHITE))


def success(text: str) -> None:
    print(c(f"  ✔  {text}", Fore.GREEN))


def warning(text: str) -> None:
    print(c(f"  ⚠  {text}", Fore.YELLOW))


def error_msg(text: str) -> None:
    print(c(f"  ✘  {text}", Fore.RED))


def dialogue_line(text: str) -> None:
    print(c(f'\n  🗣  "{text}"', Fore.MAGENTA + Style.BRIGHT))


def consequence_line(text: str) -> None:
    print(c(f"  ➤  {text}", Fore.CYAN))


# ---------------------------------------------------------------------------
# NPC selection helper
# ---------------------------------------------------------------------------

def pick_npc(engine: AntiHeroEngine, prompt: str = "Select NPC") -> str | None:
    """Display a numbered list of living NPCs and return the chosen npc_id."""
    npcs = engine.list_npcs(alive_only=True)
    if not npcs:
        error_msg("No living NPCs available.")
        return None

    print()
    for i, npc in enumerate(npcs, 1):
        score = npc.relationships.get("player", 0)
        mood = "😠" if score < -20 else ("🤝" if score > 20 else "😐")
        print(
            c(f"  [{i:>3}] ", Fore.WHITE)
            + c(f"{npc.nickname:<20}", Fore.YELLOW + Style.BRIGHT)
            + c(f" {npc.rank.value:<12}", Fore.CYAN)
            + c(f" {npc.gang:<20}", Fore.GREEN)
            + c(f" {npc.territory:<20}", Fore.WHITE)
            + c(f" {mood} {score:+d}", Fore.MAGENTA)
        )
    print(c(f"  [  0] Back", Fore.WHITE))

    while True:
        raw = input(c(f"\n  {prompt} (0-{len(npcs)}): ", Fore.WHITE)).strip()
        if raw == "0":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(npcs):
            return npcs[int(raw) - 1].npc_id
        error_msg("Invalid choice.")


# ---------------------------------------------------------------------------
# Menu handlers
# ---------------------------------------------------------------------------

def show_world_map(engine: AntiHeroEngine) -> None:
    header("VICE CITY — GANG TERRITORY MAP")
    print(engine.display_world_map())


def show_hierarchy(engine: AntiHeroEngine) -> None:
    header("GANG HIERARCHIES")
    for gang_name in engine.gangs:
        print(engine.get_hierarchy_display(gang_name))
        print()


def show_npc_profile(engine: AntiHeroEngine) -> None:
    header("NPC PROFILE VIEWER")
    npc_id = pick_npc(engine, "Select NPC to profile")
    if not npc_id:
        return
    info_data = engine.get_npc_info(npc_id)
    if not info_data:
        error_msg("NPC not found.")
        return

    section(f"{info_data['nickname']} — {info_data['name']}")
    info(f"Rank:       {info_data['rank']}")
    info(f"Gang:       {info_data['gang']}")
    info(f"Territory:  {info_data['territory']}")
    info(f"Health:     {info_data['health']}/100")
    info(f"Respect:    {info_data['respect_level']}/100")
    info(f"Traits:     {', '.join(info_data['traits'])}")
    info(f"Strengths:  {', '.join(info_data['strengths'])}")
    info(f"Weaknesses: {', '.join(info_data['weaknesses'])}")

    section("Appearance")
    for k, v in info_data["appearance"].items():
        info(f"  {k.capitalize()}: {v}")

    section("Player Relationship")
    info(info_data["relationship_summary"])

    section(f"Recent Events ({info_data['event_count']} total)")
    if info_data["recent_events"]:
        for ev in info_data["recent_events"]:
            info(f"  [{ev['type']}] {ev['description']} → {ev['outcome']}")
    else:
        info("  No events recorded yet.")

    section("Dialogue Sample")
    dialogue_line(engine.get_npc_dialogue(npc_id, "greeting"))


def do_player_action(engine: AntiHeroEngine, action_type: str, label: str) -> None:
    header(f"ACTION: {label.upper()}")
    kwargs = {}

    if action_type == ACTION_TURF_WAR:
        section("Select target district")
        districts = list(engine.districts.keys())
        for i, d in enumerate(districts, 1):
            dist = engine.districts[d]
            info(f"  [{i:>2}] {d:<22} — Controlled by: {dist.controlling_gang}")
        raw = input(c(f"\n  District (1-{len(districts)}): ", Fore.WHITE)).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(districts):
            kwargs["district"] = districts[int(raw) - 1]
        else:
            error_msg("Invalid selection.")
            return

    npc_id = pick_npc(engine, f"Select target for {label}")
    if not npc_id:
        return

    result = engine.player_action(action_type, npc_id, **kwargs)

    if result["dialogue"]:
        dialogue_line(result["dialogue"])

    if result["consequences"]:
        section("Consequences")
        for cons_msg in result["consequences"]:
            consequence_line(cons_msg)

    if result["revenge_alerts"]:
        section("Revenge Alerts")
        for r_msg in result["revenge_alerts"]:
            warning(r_msg)


def show_rivals(engine: AntiHeroEngine) -> None:
    header("ACTIVE RIVALS")
    rivals = engine.get_active_rivals()
    if not rivals:
        success("No active rivals — the streets are (temporarily) peaceful.")
        return
    for npc in rivals:
        score = npc.relationships.get("player", 0)
        warning(
            f"{npc.nickname} ({npc.name}) — {npc.rank.value}, "
            f"{npc.gang} — Hostility: {score}"
        )


def show_potential_allies(engine: AntiHeroEngine) -> None:
    header("POTENTIAL ALLIES")
    allies = engine.get_potential_allies()
    if not allies:
        error_msg("Nobody trusts you enough to ally right now.")
        return
    for npc in allies:
        score = npc.relationships.get("player", 0)
        success(
            f"{npc.nickname} ({npc.name}) — {npc.rank.value}, "
            f"{npc.gang} — Trust: {score}"
        )


def show_player_history(engine: AntiHeroEngine) -> None:
    header("YOUR RIVALRY HISTORY")
    events = engine.memory.get_player_history()
    if not events:
        info("No events recorded yet. Go make some moves.")
        return
    for ev in events:
        ts = ev.timestamp.strftime("%H:%M:%S")
        print(
            c(f"  [{ts}] ", Fore.WHITE)
            + c(f"[{ev.event_type.value:<14}] ", Fore.YELLOW)
            + c(ev.description, Fore.WHITE)
        )
        if ev.outcome:
            info(f"         → {ev.outcome}")


def advance_time(engine: AntiHeroEngine) -> None:
    header("ADVANCING TIME…")
    updates = engine.advance_time()
    if updates:
        for upd in updates:
            consequence_line(upd)
    else:
        info("A quiet turn — the city holds its breath.")


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

MENU = [
    ("View World Map",              lambda e: show_world_map(e)),
    ("View Gang Hierarchies",       lambda e: show_hierarchy(e)),
    ("View NPC Profile",            lambda e: show_npc_profile(e)),
    ("Attack an NPC",               lambda e: do_player_action(e, ACTION_ATTACK, "Attack")),
    ("Assassinate an NPC",          lambda e: do_player_action(e, ACTION_ASSASSINATE, "Assassinate")),
    ("Bribe an NPC",                lambda e: do_player_action(e, ACTION_BRIBE, "Bribe")),
    ("Ally with an NPC",            lambda e: do_player_action(e, ACTION_ALLY, "Form Alliance")),
    ("Intimidate an NPC",           lambda e: do_player_action(e, ACTION_INTIMIDATE, "Intimidate")),
    ("Start a Turf War",            lambda e: do_player_action(e, ACTION_TURF_WAR, "Turf War")),
    ("View Active Rivals",          lambda e: show_rivals(e)),
    ("View Potential Allies",       lambda e: show_potential_allies(e)),
    ("View Your Rivalry History",   lambda e: show_player_history(e)),
    ("Advance Time (World Ticks)",  lambda e: advance_time(e)),
]


def main() -> None:
    header("ANTIHERO SYSTEM — VICE CITY")
    info("Welcome to Vice City.  The city is yours to take — if you've got the nerve.")
    info("NPCs remember every move you make.  Choose wisely.\n")

    engine = AntiHeroEngine()
    success(
        f"World generated: {len(engine.gangs)} gangs, "
        f"{len(engine.npcs)} NPCs, "
        f"{len(engine.districts)} districts."
    )

    while True:
        header("MAIN MENU")
        for i, (label, _) in enumerate(MENU, 1):
            print(c(f"  [{i:>2}] {label}", Fore.WHITE))
        print(c("  [ 0] Exit", Fore.RED))

        raw = input(c("\n  Choice: ", Fore.WHITE)).strip()

        if raw == "0":
            info("Stay frosty out there.")
            sys.exit(0)

        if raw.isdigit() and 1 <= int(raw) <= len(MENU):
            try:
                MENU[int(raw) - 1][1](engine)
            except KeyboardInterrupt:
                info("\n  (interrupted)")
        else:
            error_msg("Invalid choice — try again.")


if __name__ == "__main__":
    main()
