"""
Procedural dialogue generation for the Antihero System.

Generates Vice City-style 80s crime movie dialogue based on
NPC attributes and relationship history with the player.
"""

from __future__ import annotations

import random
from typing import List, Optional

from .models import Event, EventType, NPC, Rank


# ---------------------------------------------------------------------------
# Dialogue template banks
# ---------------------------------------------------------------------------

_GREETING_NEUTRAL = [
    "You got some nerve showing up here, {name}.",
    "Well, well. Look what the cat dragged in.",
    "I heard you were making moves. Smart to come see me.",
    "You're either brave or stupid for coming to {territory}.",
    "What brings a player like you to my side of town?",
]

_GREETING_HOSTILE = [
    "You got ten seconds to explain why I shouldn't have my boys bury you right here.",
    "I've been waiting for this moment, you two-faced snake.",
    "Every night I dreamed of the day you'd come crawling back. Now you're here.",
    "You think showing your face in {territory} is a good idea? Big mistake.",
    "'{nickname}' doesn't forget. And '{nickname}' doesn't forgive.",
    "You better have an army behind you, because you're gonna need one.",
]

_GREETING_FRIENDLY = [
    "My friend! Come in, come in — we have business to discuss.",
    "The streets are talking about you. Good things, mostly.",
    "I knew you'd be back. A smart operator always knows where to find good company.",
    "You're welcome in {territory} any time, hermano.",
    "Good to see you in one piece. Sit down, have a drink.",
]

_GREETING_ALLIED = [
    "Amigo! My operation is your operation. What do you need?",
    "Brother from another gang. What's the word?",
    "I'd take a bullet for you — you know that. Now what's the plan?",
    "The city belongs to us both. What's on your mind?",
    "Always good to see an honest face in this dishonest city.",
]

_THREAT_TEMPLATES = [
    "You made a big mistake crossing me. {gang} has a long memory.",
    "I'm going to burn everything you built to the ground, starting with your reputation.",
    "You think you're untouchable? Nobody is untouchable in this city.",
    "Next time I see you, '{nickname}' won't be in a talking mood.",
    "Every alley, every corner, every safe house — nowhere will be safe for you.",
    "I'll destroy everything you love, piece by piece, just to watch you suffer.",
    "You think defeating me once means anything? I've been knocked down before. I always get up.",
    "Your days are numbered, and when the clock hits zero, I'll be there.",
]

_TAUNT_TEMPLATES = [
    "Look at you — down on the ground where you belong.",
    "Is that it? I've seen scarier things in Little Havana.",
    "You had potential. Too bad you wasted it on the wrong side.",
    "Tell your friends — if you have any left — what happened here today.",
    "'{nickname}' never loses. Remember that when you're limping home.",
    "They're gonna be telling this story on every corner in {territory}.",
    "I almost feel bad for you. Almost.",
]

_RESPECT_TEMPLATES = [
    "You've earned my respect, and that's not something I hand out easy.",
    "The way you handled that situation — that was professional.",
    "In this business, there's two kinds of people: survivors and victims. You're a survivor.",
    "Word travels fast on these streets. People are talking about you — good things.",
    "I don't trust many people. But you? You've proved yourself.",
    "The old ways are dying. People like you are what keeps this city breathing.",
]

_BETRAYAL_REACTIONS = [
    "I trusted you. I TRUSTED you! Do you know what trust means in this business?!",
    "You snake. You absolute snake. I'm going to make you wish you never set foot in this city.",
    "After everything I did for you — this is what I get?",
    "I should have known. Nobody survives this long without stabbing a few backs.",
    "You played me. Fine. But know this: '{nickname}' never forgets, and '{nickname}' never dies.",
    "I gave you everything — territory, protection, respect. And you threw it all away.",
]

# Reference phrases that incorporate past event history
_PAST_EVENT_REFS: dict[EventType, List[str]] = {
    EventType.DEFEAT: [
        "Remember that day in {territory}? You think I've forgotten?",
        "You humiliated me once. It won't happen again.",
        "The scar you gave me reminds me every morning what I owe you.",
    ],
    EventType.VICTORY: [
        "Last time we met, I put you on the ground. Don't make me repeat it.",
        "You came crawling after I was done with you. Now look at you — back for more.",
    ],
    EventType.BETRAYAL: [
        "You stabbed me in the back and had the nerve to show your face again.",
        "I trusted you once. Once.",
    ],
    EventType.ALLIANCE: [
        "We built something together. That matters.",
        "You stood by me when others ran. I don't forget that.",
    ],
    EventType.BRIBE: [
        "Yeah, I took your money. Doesn't mean I like you.",
        "Cash solves a lot of problems. But not all of them.",
    ],
}


def _pick(templates: List[str], npc: NPC) -> str:
    """Fill in a random template with NPC data."""
    template = random.choice(templates)
    return template.format(
        name=npc.name,
        nickname=npc.nickname,
        gang=npc.gang,
        territory=npc.territory or "these streets",
        rank=npc.rank.value,
    )


def _past_reference(npc: NPC, player_history: List[Event]) -> str:
    """Return a past-event reference line if relevant history exists."""
    # Filter events involving this NPC
    relevant = [e for e in player_history if npc.npc_id in e.involved_npcs]
    if not relevant:
        return ""
    event = random.choice(relevant)
    refs = _PAST_EVENT_REFS.get(event.event_type, [])
    if not refs:
        return ""
    template = random.choice(refs)
    return template.format(
        name=npc.name,
        nickname=npc.nickname,
        gang=npc.gang,
        territory=npc.territory or "these streets",
    )


class DialogueGenerator:
    """
    Generates Vice City-style procedural dialogue for NPCs.

    All methods return a single dialogue string ready for display.
    """

    def generate_greeting(self, npc: NPC, player_history: List[Event]) -> str:
        """NPC greets player based on relationship history."""
        score = npc.relationships.get("player", 0)

        if score <= -60:
            base = _pick(_GREETING_HOSTILE, npc)
        elif score <= -20:
            base = _pick(_GREETING_NEUTRAL, npc)
        elif score <= 20:
            base = _pick(_GREETING_NEUTRAL, npc)
        elif score <= 60:
            base = _pick(_GREETING_FRIENDLY, npc)
        else:
            base = _pick(_GREETING_ALLIED, npc)

        past_ref = _past_reference(npc, player_history)
        if past_ref and random.random() < 0.5:
            return f"{base} {past_ref}"
        return base

    def generate_threat(self, npc: NPC, player_history: List[Event]) -> str:
        """Personalized threat referencing past events where possible."""
        base = _pick(_THREAT_TEMPLATES, npc)
        past_ref = _past_reference(npc, player_history)
        if past_ref and random.random() < 0.6:
            return f"{past_ref} {base}"
        return base

    def generate_taunt(self, npc: NPC, event: Optional[Event] = None) -> str:
        """Taunt after NPC defeats the player."""
        return _pick(_TAUNT_TEMPLATES, npc)

    def generate_respect(self, npc: NPC, player_history: List[Event]) -> str:
        """Respectful dialogue if player has earned it."""
        base = _pick(_RESPECT_TEMPLATES, npc)
        past_ref = _past_reference(npc, player_history)
        if past_ref and random.random() < 0.4:
            return f"{base} {past_ref}"
        return base

    def generate_betrayal_reaction(self, npc: NPC) -> str:
        """Reaction to being betrayed by the player."""
        template = random.choice(_BETRAYAL_REACTIONS)
        return template.format(
            name=npc.name,
            nickname=npc.nickname,
            gang=npc.gang,
            territory=npc.territory or "these streets",
        )

    def get_contextual_line(self, npc: NPC, player_history: List[Event]) -> str:
        """
        Return the most contextually appropriate dialogue line
        based on the NPC's current relationship with the player.
        """
        score = npc.relationships.get("player", 0)
        if score <= -60:
            return self.generate_threat(npc, player_history)
        elif score <= -20:
            return self.generate_greeting(npc, player_history)
        elif score <= 20:
            return self.generate_greeting(npc, player_history)
        elif score <= 60:
            return self.generate_respect(npc, player_history)
        else:
            return self.generate_respect(npc, player_history)
