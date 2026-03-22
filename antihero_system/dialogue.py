"""
Procedural dialogue generation for the Antihero System.

Generates Vice City-flavoured, 80s crime-movie-style dialogue using template
strings populated from NPC data and event history.
"""

from __future__ import annotations

import random
from typing import List, Optional

from .models import Event, EventType, NPC


# ---------------------------------------------------------------------------
# Template pools
# ---------------------------------------------------------------------------

_GREET_NEUTRAL = [
    "Hey, {nickname}. Don't start nothing, won't be nothing.",
    "You again. What do you want?",
    "I got nothing to say to you, pal. Move along.",
    "Watch yourself. This ain't your turf.",
]

_GREET_HOSTILE = [
    "You've got some nerve showing your face around here after what you pulled.",
    "I've been waiting for this moment, {nickname}. You should've stayed gone.",
    "You think you can just walk around like nothing happened? I don't forget.",
    "Last time we met, things didn't go so well for me. This time's different.",
    "Every dog has its day. Today's mine, and you're the dog.",
]

_GREET_ALLIED = [
    "Hey, my friend! Good to see a familiar face around here.",
    "You're always welcome in {territory}, amigo.",
    "The streets talk — word is you've been making moves. Respect.",
    "Come, come. We have business to discuss.",
]

_GREET_RESPECTED = [
    "I heard what you did. You've earned some respect in this city.",
    "Sit down. Anyone who runs Vice City like you do deserves a moment of my time.",
    "Not many people walk through that door and walk back out. You're one of them.",
]

_THREATS = [
    "You think {past_event} was bad? Wait till you see what I've got planned.",
    "I've got a long memory, and a longer reach. You'll pay for {past_event}.",
    "My boys are everywhere. One phone call and you're done.",
    "You messed with the wrong {rank}. This city ain't big enough for both of us.",
    "Sleep with one eye open — 'cause I won't forget what you did.",
    "Next time you see me coming, you better run. I won't be as gentle.",
]

_TAUNTS = [
    "That all you got? I've seen scarier things at the bottom of a rum bottle.",
    "I told you — this is MY city. Now crawl back to wherever you came from.",
    "Next time, bring more backup. Way more.",
    "Pathetic. Absolutely pathetic. Get this clown outta my sight.",
    "You fought hard. I'll give you that. But hard ain't good enough.",
]

_RESPECT_LINES = [
    "You've proven yourself. Not many people last long in this business.",
    "I don't give compliments easy — but you've earned this city's respect.",
    "Word gets around. You're making a name for yourself. Keep it up.",
    "You're exactly the kind of operator this city needs. Smart. Ruthless. Effective.",
    "I've been watching. You handle business. I respect that.",
]

_BETRAYAL_REACTIONS = [
    "I trusted you. I TRUSTED you! Do you know what that means to someone like me?",
    "Every traitor in this city ends up the same way — face down in the canal.",
    "You just signed your own death warrant. Hope it was worth it.",
    "People who cross me don't get second chances. Remember that.",
    "I built this empire on loyalty. You just spit on everything I stand for.",
    "You want to betray me? Fine. But you better not miss, because I won't.",
]

_VICE_CITY_FLAVOR = [
    "This ain't New York — in Vice City, everything runs on fear and money.",
    "You want respect? You gotta take it. Nobody hands you nothing in this town.",
    "The sun, the beaches, the beautiful people — it's all a cover for the rot underneath.",
    "Vice City chews people up and spits them out. You still here? Then you're different.",
]


class DialogueGenerator:
    """Generates contextual, Vice City-flavoured NPC dialogue.

    All methods accept the NPC object and optional history/event context and
    return a single dialogue string ready for display.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_greeting(self, npc: NPC, player_history: List[Event]) -> str:
        """Generate an NPC greeting based on their relationship with the player.

        Args:
            npc:            The speaking NPC.
            player_history: All player-involved events this NPC remembers.

        Returns:
            A greeting string in the NPC's voice.
        """
        score = npc.relationships.get("player", 0)

        if score >= 60:
            pool = _GREET_RESPECTED
        elif score >= 30:
            pool = _GREET_ALLIED
        elif score <= -40:
            pool = _GREET_HOSTILE
        else:
            pool = _GREET_NEUTRAL

        template = random.choice(pool)
        return self._fill(template, npc, player_history)

    def generate_threat(self, npc: NPC, player_history: List[Event]) -> str:
        """Generate a personalised threat referencing past confrontations.

        Args:
            npc:            The threatening NPC.
            player_history: Player-involved events the NPC remembers.

        Returns:
            A threat string referencing the NPC's history with the player.
        """
        template = random.choice(_THREATS)
        return self._fill(template, npc, player_history)

    def generate_taunt(self, npc: NPC, event: Optional[Event] = None) -> str:
        """Generate a victory taunt after the NPC defeats the player.

        Args:
            npc:   The taunting NPC.
            event: The triggering event (optional context).

        Returns:
            A taunt string.
        """
        base = random.choice(_TAUNTS)
        flavor = random.choice(_VICE_CITY_FLAVOR)
        history: List[Event] = [event] if event else []
        return f'{self._fill(base, npc, history)}  "{flavor}"'

    def generate_respect(self, npc: NPC, player_history: List[Event]) -> str:
        """Generate respectful dialogue for when the NPC acknowledges the player.

        Args:
            npc:            The speaking NPC.
            player_history: Player-involved events the NPC remembers.

        Returns:
            A respectful dialogue string.
        """
        template = random.choice(_RESPECT_LINES)
        return self._fill(template, npc, player_history)

    def generate_betrayal_reaction(self, npc: NPC) -> str:
        """Generate an NPC's emotional reaction to being betrayed.

        Args:
            npc: The betrayed NPC.

        Returns:
            A betrayal-reaction string.
        """
        template = random.choice(_BETRAYAL_REACTIONS)
        return self._fill(template, npc, [])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fill(self, template: str, npc: NPC, history: List[Event]) -> str:
        """Substitute template placeholders with NPC-specific values.

        Supported placeholders:
        - ``{nickname}``  → NPC's street alias
        - ``{name}``      → NPC's full name
        - ``{gang}``      → gang affiliation
        - ``{rank}``      → current rank
        - ``{territory}`` → home district
        - ``{past_event}``→ description of the most recent memorable event

        Args:
            template: Raw template string.
            npc:      The NPC providing context.
            history:  Relevant event history for ``{past_event}``.

        Returns:
            Filled template string.
        """
        past_event = "that little incident"
        if history:
            most_recent = max(history, key=lambda e: e.timestamp)
            past_event = most_recent.description or past_event

        return template.format(
            nickname=npc.nickname,
            name=npc.name,
            gang=npc.gang,
            rank=npc.rank.value.lower(),
            territory=npc.territory,
            past_event=past_event,
        )
