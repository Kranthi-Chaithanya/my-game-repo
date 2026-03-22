"""
Procedural generation engine for the Antihero System.

Generates NPCs, gangs, districts, and an entire Vice City world
using themed name pools and randomized attributes.
"""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

from .models import District, Gang, NPC, Rank

# ---------------------------------------------------------------------------
# Name pools — themed by gang identity
# ---------------------------------------------------------------------------

_LATIN_FIRST = [
    "Miguel", "Carlos", "Jorge", "Luis", "Hector", "Alejandro", "Raul",
    "Eduardo", "Diego", "Roberto", "Juan", "Fernando", "Manuel", "Pedro",
    "Ernesto", "Cesar", "Oscar", "Gustavo", "Ricardo", "Victor",
]
_LATIN_LAST = [
    "Diaz", "Vega", "Reyes", "Cruz", "Mendez", "Gutierrez", "Morales",
    "Fuentes", "Herrera", "Ramirez", "Castillo", "Espinoza", "Ramos",
    "Torres", "Vargas", "Rios", "Medina", "Soto", "Guerrero", "Pena",
]

_ITALIAN_FIRST = [
    "Tommy", "Sal", "Vinnie", "Marco", "Nico", "Gino", "Frank", "Tony",
    "Luca", "Bruno", "Marco", "Dante", "Angelo", "Rico", "Rocco",
    "Dominic", "Vito", "Carlo", "Adriano", "Lorenzo",
]
_ITALIAN_LAST = [
    "Vercetti", "Corleone", "Mancini", "Ferraro", "Ricci", "Conti",
    "Esposito", "Bianchi", "Russo", "Marino", "Greco", "Bruno",
    "Santoro", "Rizzo", "Romano", "Lombardi", "Gallo", "Costa",
    "Fontana", "De Luca",
]

_HAITIAN_FIRST = [
    "Jean", "Pierre", "Jacques", "Henri", "Joseph", "Michel", "Paul",
    "Andre", "Remy", "Claude", "Baptiste", "Cedric", "Emile", "Fritz",
    "Gilles", "Lucien", "Marcel", "Noel", "Thierry", "Yves",
]
_HAITIAN_LAST = [
    "Baptiste", "Toussaint", "Desroches", "Lafleur", "Pierre", "Jean",
    "Chery", "Dorvil", "Gilles", "Henri", "Juste", "Laguerre",
    "Massena", "Noel", "Oge", "Petit", "Remy", "Saint-Juste",
    "Thermidor", "Voltaire",
]

_BIKER_FIRST = [
    "Axle", "Duke", "Hammer", "Brock", "Rusty", "Spike", "Gator",
    "Rex", "Dagger", "Boomer", "Hank", "Wade", "Clint", "Buck", "Cody",
    "Dale", "Earl", "Floyd", "Glen", "Hoss",
]
_BIKER_LAST = [
    "Malone", "Stone", "Steele", "Iron", "Cross", "Kane", "Wolf",
    "Ryder", "Burns", "Cash", "Blaze", "Colt", "Dagger", "Edge",
    "Frost", "Hatch", "Krane", "Lynch", "Madden", "Nash",
]

_CUBAN_FIRST = [
    "Armando", "Umberto", "Rafael", "Ernesto", "Camilo", "Fidel",
    "Lazaro", "Reinaldo", "Orlando", "Sergio", "Augusto", "Bernardo",
    "Ciro", "Dario", "Elio", "Fabian", "Gilberto", "Hiram", "Ignacio",
    "Julio",
]
_CUBAN_LAST = [
    "Robina", "Martinez", "Garcia", "Rodriguez", "Perez", "Gonzalez",
    "Sanchez", "Lopez", "Fernandez", "Alvarez", "Gomez", "Diaz",
    "Castillo", "Moreno", "Jimenez", "Ruiz", "Hernandez", "Molina",
    "Delgado", "Ortega",
]

# Gang-specific name pools
_GANG_NAMES: Dict[str, Tuple[List[str], List[str]]] = {
    "Diaz Cartel":   (_LATIN_FIRST,  _LATIN_LAST),
    "Vercetti Gang": (_ITALIAN_FIRST, _ITALIAN_LAST),
    "Haitians":      (_HAITIAN_FIRST, _HAITIAN_LAST),
    "Cubans":        (_CUBAN_FIRST,  _CUBAN_LAST),
    "Bikers":        (_BIKER_FIRST,  _BIKER_LAST),
}

_NICKNAMES = [
    "The Ghost", "Scarface", "Iron Fist", "Snake Eyes", "El Diablo",
    "The Butcher", "Chainsaw", "The Shadow", "Sidewinder", "Copperhead",
    "The Shark", "Viper", "Tombstone", "Blackout", "The Reaper",
    "Switchblade", "The Hammer", "Iceman", "The Wolf", "Kingpin",
    "El Toro", "Jawbreaker", "The Phantom", "Thunderbolt", "Nightcrawler",
    "The Surgeon", "Razorblade", "El Fuego", "The Fixer", "Deadshot",
]

_TRAITS = [
    "aggressive", "cunning", "loyal", "cowardly", "vengeful", "charismatic",
    "paranoid", "ruthless", "calculating", "impulsive", "diplomatic",
    "sadistic", "street-smart", "power-hungry", "protective",
]

_STRENGTHS = [
    "immune to melee attacks", "expert marksman", "fast runner",
    "heavily armored", "skilled driver", "gang always nearby",
    "police connections", "unpredictable fighter", "ambush expert",
    "never fights alone", "highly intelligent tactician",
]

_WEAKNESSES = [
    "vulnerable to ambush", "fears water", "overconfident",
    "easily bribed", "weak under pressure", "underestimates opponents",
    "no backup in rival territory", "predictable attack patterns",
    "trusts allies too easily", "motivated purely by money",
]

_SCARS = [
    "knife scar on left cheek", "burn mark on right hand", "missing left ear",
    "bullet wound scar on neck", "tattooed tears under right eye",
    "broken nose (badly set)", "eyepatch over left eye", "none",
]

_TATTOOS = [
    "full sleeve tattoo", "gang symbol on neck", "skull tattoo on forearm",
    "religious iconography across back", "barbed wire around wrist",
    "snake coiling up right arm", "none",
]

_CLOTHING = [
    "white linen suit", "wife-beater and gold chains", "biker leathers",
    "Hawaiian shirt and cargo pants", "army surplus jacket",
    "sharp pinstripe suit", "tracksuit", "wife-beater and bandana",
    "military fatigues", "expensive Italian loafers and slacks",
]

_BUSINESSES = ["drugs", "weapons", "protection", "gambling", "prostitution", "loan sharking"]

# Vice City districts
VICE_CITY_DISTRICTS = [
    "Ocean Beach",
    "Washington Beach",
    "Little Havana",
    "Little Haiti",
    "Downtown",
    "Starfish Island",
    "Prawn Island",
    "Vice Point",
    "Leaf Links",
    "Escobar International",
]

# Gang definitions: name, color, initial districts
GANG_DEFINITIONS = [
    ("Diaz Cartel",   "red",    ["Starfish Island", "Prawn Island"]),
    ("Vercetti Gang", "blue",   ["Ocean Beach", "Washington Beach"]),
    ("Haitians",      "yellow", ["Little Haiti"]),
    ("Cubans",        "green",  ["Little Havana"]),
    ("Bikers",        "cyan",   ["Vice Point", "Leaf Links"]),
]


# ---------------------------------------------------------------------------
# NPC generation
# ---------------------------------------------------------------------------

def _random_name(gang: str) -> Tuple[str, str]:
    """Return (full_name, nickname) for the given gang."""
    pool = _GANG_NAMES.get(gang, (_ITALIAN_FIRST, _ITALIAN_LAST))
    first = random.choice(pool[0])
    last = random.choice(pool[1])
    nickname = random.choice(_NICKNAMES)
    return f"{first} {last}", nickname


def _random_appearance() -> Dict[str, str]:
    return {
        "scar": random.choice(_SCARS),
        "tattoo": random.choice(_TATTOOS),
        "clothing": random.choice(_CLOTHING),
    }


def generate_npc(rank: Rank, gang: str) -> NPC:
    """Create a unique NPC with randomized attributes for the given rank and gang."""
    name, nickname = _random_name(gang)
    num_traits = random.randint(2, 4)
    traits = random.sample(_TRAITS, num_traits)
    strengths = random.sample(_STRENGTHS, random.randint(1, 3))
    weaknesses = random.sample(_WEAKNESSES, random.randint(1, 2))
    appearance = _random_appearance()

    # Health and respect scale with rank
    health_by_rank = {
        Rank.BOSS: 200,
        Rank.UNDERBOSS: 150,
        Rank.CAPTAIN: 120,
        Rank.ENFORCER: 100,
        Rank.DEALER: 80,
    }
    respect_by_rank = {
        Rank.BOSS: random.randint(80, 100),
        Rank.UNDERBOSS: random.randint(60, 80),
        Rank.CAPTAIN: random.randint(40, 65),
        Rank.ENFORCER: random.randint(20, 45),
        Rank.DEALER: random.randint(5, 25),
    }

    return NPC(
        name=name,
        nickname=nickname,
        rank=rank,
        gang=gang,
        traits=traits,
        strengths=strengths,
        weaknesses=weaknesses,
        appearance=appearance,
        health=health_by_rank[rank],
        respect_level=respect_by_rank[rank],
    )


# ---------------------------------------------------------------------------
# Gang generation
# ---------------------------------------------------------------------------

def generate_gang(name: str, districts: List[str] | None = None) -> Tuple[Gang, Dict[str, NPC]]:
    """
    Create a full gang with a complete hierarchy of NPCs.

    Returns:
        (Gang, dict mapping npc_id → NPC)
    """
    color_map = {d[0]: d[1] for d in GANG_DEFINITIONS}
    color = color_map.get(name, "white")

    gang = Gang(name=name, color=color, territory=list(districts or []))
    npcs: Dict[str, NPC] = {}

    def _add(rank: Rank, count: int) -> None:
        for _ in range(count):
            npc = generate_npc(rank, name)
            npc.territory = random.choice(gang.territory) if gang.territory else ""
            npcs[npc.npc_id] = npc
            gang.add_member(npc)

    _add(Rank.BOSS,      1)
    _add(Rank.UNDERBOSS, random.randint(1, 2))
    _add(Rank.CAPTAIN,   random.randint(2, 4))
    _add(Rank.ENFORCER,  random.randint(4, 8))
    _add(Rank.DEALER,    random.randint(6, 12))

    return gang, npcs


# ---------------------------------------------------------------------------
# District generation
# ---------------------------------------------------------------------------

def generate_district(name: str, controlling_gang: str | None = None) -> District:
    """Create a district with randomized businesses and attributes."""
    num_businesses = random.randint(2, len(_BUSINESSES))
    businesses = random.sample(_BUSINESSES, num_businesses)
    heat = random.randint(10, 40)
    return District(
        name=name,
        controlling_gang=controlling_gang,
        heat_level=heat,
        businesses=businesses,
    )


# ---------------------------------------------------------------------------
# Full Vice City world generation
# ---------------------------------------------------------------------------

def generate_vice_city() -> Tuple[
    Dict[str, Gang],
    Dict[str, NPC],
    Dict[str, District],
]:
    """
    Bootstrap an entire Vice City world.

    Returns:
        (gangs dict, all_npcs dict, districts dict)
        Keys are name strings for gangs/districts and npc_id for npcs.
    """
    all_gangs: Dict[str, Gang] = {}
    all_npcs: Dict[str, NPC] = {}
    districts: Dict[str, District] = {}

    # Build gang → district mapping
    gang_district_map: Dict[str, List[str]] = {g[0]: g[2] for g in GANG_DEFINITIONS}

    # Create districts, assigning controlling gangs
    district_gang_map: Dict[str, str] = {}
    for gang_name, _, gang_districts in GANG_DEFINITIONS:
        for d_name in gang_districts:
            district_gang_map[d_name] = gang_name

    for d_name in VICE_CITY_DISTRICTS:
        controller = district_gang_map.get(d_name)
        dist = generate_district(d_name, controller)
        districts[d_name] = dist

    # "Downtown" and "Escobar International" are contested — no single controller
    for neutral in ("Downtown", "Escobar International"):
        if neutral in districts:
            districts[neutral].controlling_gang = None

    # Create gangs
    for gang_name, _, gang_districts in GANG_DEFINITIONS:
        gang, npcs = generate_gang(gang_name, gang_districts)
        all_gangs[gang_name] = gang
        all_npcs.update(npcs)

    # Set up rivalries and alliances
    _setup_relationships(all_gangs)

    return all_gangs, all_npcs, districts


def _setup_relationships(gangs: Dict[str, Gang]) -> None:
    """Configure default gang rivalries and alliances."""
    rivalries = [
        ("Diaz Cartel", "Vercetti Gang"),
        ("Diaz Cartel", "Cubans"),
        ("Haitians", "Cubans"),
    ]
    alliances = [
        ("Cubans", "Vercetti Gang"),
    ]

    for g1_name, g2_name in rivalries:
        if g1_name in gangs and g2_name in gangs:
            gangs[g1_name].rival_gangs.append(g2_name)
            gangs[g2_name].rival_gangs.append(g1_name)

    for g1_name, g2_name in alliances:
        if g1_name in gangs and g2_name in gangs:
            gangs[g1_name].allied_gangs.append(g2_name)
            gangs[g2_name].allied_gangs.append(g1_name)
