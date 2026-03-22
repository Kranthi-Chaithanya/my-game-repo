"""
Procedural generation engine for the Antihero System.

Generates NPCs, gangs, districts, and a complete Vice City world from
themed name pools and randomised attribute tables.
"""

from __future__ import annotations

import random
import uuid

from .models import District, Gang, NPC, Rank

# ---------------------------------------------------------------------------
# Name pools — themed to match Vice City's 80s Miami crime aesthetic
# ---------------------------------------------------------------------------

_LATIN_FIRST = [
    "Ricardo", "Carlos", "Miguel", "Diego", "Roberto", "Ernesto",
    "Alejandro", "Hector", "Juan", "Raul", "Fernando", "Antonio",
    "Luis", "Marco", "Cesar", "Eduardo", "Arturo", "Manuel",
]

_LATIN_LAST = [
    "Diaz", "Mendez", "Fuentes", "Reyes", "Vargas", "Dominguez",
    "Herrera", "Gutierrez", "Castillo", "Flores", "Morales", "Cruz",
    "Vega", "Ortiz", "Torres", "Jimenez", "Rojas", "Sandoval",
]

_ITALIAN_FIRST = [
    "Tommy", "Sonny", "Sal", "Vinnie", "Tony", "Marco", "Luca",
    "Franco", "Enzo", "Bruno", "Rocco", "Dante", "Sergio", "Gino",
]

_ITALIAN_LAST = [
    "Vercetti", "Leone", "Corleone", "Cipriani", "Forelli", "Sindacco",
    "Barzini", "Tattaglia", "Cuneo", "Stracci", "Falcone", "Rossi",
]

_HAITIAN_FIRST = [
    "Jean", "Pierre", "Luc", "Claude", "Henri", "Jacques", "Baptiste",
    "Remy", "Etienne", "Marc", "Thierry", "Pascal", "Cedric",
]

_HAITIAN_LAST = [
    "Lapointe", "Delacroix", "Beaumont", "Duchamp", "Renard",
    "Leblanc", "Duval", "Moreau", "Bonnet", "Fontaine",
]

_BIKER_FIRST = [
    "Billy", "Chuck", "Hank", "Ricky", "Dale", "Bobby", "Wayne",
    "Travis", "Clint", "Rusty", "Bud", "Earl", "Lenny", "Cody",
]

_BIKER_LAST = [
    "Stone", "Hawk", "Razor", "Steele", "Cross", "Blaze", "Thorn",
    "Ryder", "Wolf", "Savage", "Hunter", "Striker", "Drake",
]

_CUBAN_FIRST = [
    "Umberto", "Jorge", "Pepe", "Ernesto", "Fidel", "Ramon",
    "Guillermo", "Armando", "Osvaldo", "Lazaro",
]

_CUBAN_LAST = [
    "Robina", "Acosta", "Castellano", "Alvarez", "Benitez",
    "Delgado", "Espinoza", "Ferrer", "Galvez", "Ibarra",
]

# Mapping: gang name → (first-name pool, last-name pool)
_GANG_NAME_POOLS: dict[str, tuple[list[str], list[str]]] = {
    "Diaz Cartel": (_LATIN_FIRST, _LATIN_LAST),
    "Vercetti Gang": (_ITALIAN_FIRST, _ITALIAN_LAST),
    "Haitians": (_HAITIAN_FIRST, _HAITIAN_LAST),
    "Cubans": (_CUBAN_FIRST, _CUBAN_LAST),
    "Bikers": (_BIKER_FIRST, _BIKER_LAST),
}

_DEFAULT_POOL = (_LATIN_FIRST + _ITALIAN_FIRST, _LATIN_LAST + _ITALIAN_LAST)

# ---------------------------------------------------------------------------
# Nickname templates
# ---------------------------------------------------------------------------

_NICKNAMES = [
    "El Diablo", "The Ghost", "Scarface", "Iron Fist", "The Shark",
    "El Toro", "Razor", "Chainsaw", "The Viper", "El Lobo",
    "Nails", "Blaze", "The Snake", "Iron Mike", "Cold Blood",
    "Machete", "The Hammer", "El Fuego", "Two-Face", "Switchblade",
    "The Butcher", "El Coyote", "Silencer", "Black Market", "The Ox",
    "Stone Cold", "Tombstone", "The Reaper", "Iceman", "El Patron",
    "Bloodhound", "The Vulture", "Copkiller", "The Surgeon", "Vendetta",
]

# ---------------------------------------------------------------------------
# Trait pools
# ---------------------------------------------------------------------------

_ALL_TRAITS = [
    "aggressive", "cunning", "loyal", "cowardly", "vengeful",
    "charismatic", "paranoid", "ruthless", "strategic", "impulsive",
    "sadistic", "cautious", "greedy", "fearless", "manipulative",
    "hot-headed", "calculating", "merciless", "honourable", "treacherous",
]

_STRENGTHS = [
    "immune to melee", "expert marksman", "heavily armoured",
    "backed by large crew", "fearless under fire", "escape artist",
    "street network informants", "controls police bribes",
    "drives armoured vehicles", "ambush specialist",
    "knife fighter", "explosives expert", "crowd controller",
]

_WEAKNESSES = [
    "vulnerable to ambush", "fears water", "slow on foot",
    "overconfident", "small crew", "addicted to cocaine",
    "trusts no one (even allies)", "susceptible to bribes",
    "afraid of assassination", "avoids open spaces",
    "paranoid, shoots first", "predictable patrol routes",
    "careless with evidence",
]

# ---------------------------------------------------------------------------
# Appearance descriptors
# ---------------------------------------------------------------------------

_SCARS = [
    "scar across left cheek", "burn mark on right hand",
    "missing left ear", "scar through right eyebrow",
    "knife scar on neck", "no visible scars",
    "bullet wound scar on shoulder", "broken nose, badly healed",
]

_TATTOOS = [
    "skull on forearm", "gang insignia on neck",
    "cross on back of hand", "no tattoos", "teardrop under left eye",
    "spider web on elbow", "barbed wire around bicep",
    "name of a deceased across chest",
]

_CLOTHING = {
    "Diaz Cartel": ["white linen suit", "guayabera shirt", "gold chains and slacks"],
    "Vercetti Gang": ["Hawaiian shirt and slacks", "pinstripe suit", "leather jacket"],
    "Haitians": ["colourful tracksuit", "denim vest", "cargo pants and hoodie"],
    "Cubans": ["vest and cargo pants", "sports shirt", "fatigue jacket"],
    "Bikers": ["leather vest with patches", "denim cut-off", "biker jacket"],
}

_DEFAULT_CLOTHING = ["street clothes", "casual wear", "dark jacket"]

# ---------------------------------------------------------------------------
# Business types for districts
# ---------------------------------------------------------------------------

_BUSINESS_TYPES = ["drugs", "weapons", "protection", "gambling", "loan sharking", "prostitution"]

# ---------------------------------------------------------------------------
# Vice City districts
# ---------------------------------------------------------------------------

VICE_CITY_DISTRICTS = [
    "Ocean Beach",
    "Little Havana",
    "Little Haiti",
    "Downtown",
    "Starfish Island",
    "Leaf Links",
    "Vice Point",
    "Washington Beach",
    "Prawn Island",
    "Escobar International",
]


# ---------------------------------------------------------------------------
# Public generation functions
# ---------------------------------------------------------------------------

def generate_npc(rank: Rank, gang: str) -> NPC:
    """Create a unique, procedurally generated NPC.

    Args:
        rank: The NPC's initial :class:`~antihero_system.models.Rank`.
        gang: The name of the gang this NPC belongs to.

    Returns:
        A fully populated :class:`~antihero_system.models.NPC` instance.
    """
    first_pool, last_pool = _GANG_NAME_POOLS.get(gang, _DEFAULT_POOL)
    name = f"{random.choice(first_pool)} {random.choice(last_pool)}"
    nickname = random.choice(_NICKNAMES)

    num_traits = random.randint(2, 4)
    traits = random.sample(_ALL_TRAITS, num_traits)

    num_strengths = random.randint(1, 3)
    strengths = random.sample(_STRENGTHS, num_strengths)

    num_weaknesses = random.randint(1, 2)
    weaknesses = random.sample(_WEAKNESSES, num_weaknesses)

    clothing_pool = _CLOTHING.get(gang, _DEFAULT_CLOTHING)
    appearance = {
        "scar": random.choice(_SCARS),
        "tattoo": random.choice(_TATTOOS),
        "clothing": random.choice(clothing_pool),
        "build": random.choice(["stocky", "lean", "muscular", "average", "hulking"]),
        "hair": random.choice(["slicked back", "shaved", "afro", "mullet", "bald", "curly"]),
    }

    # Respect level scales with rank
    base_respect = {
        Rank.BOSS: 80,
        Rank.UNDERBOSS: 65,
        Rank.CAPTAIN: 50,
        Rank.ENFORCER: 35,
        Rank.DEALER: 20,
    }
    respect = base_respect.get(rank, 40) + random.randint(-10, 10)
    respect = max(0, min(100, respect))

    return NPC(
        npc_id=str(uuid.uuid4()),
        name=name,
        nickname=nickname,
        rank=rank,
        gang=gang,
        traits=traits,
        strengths=strengths,
        weaknesses=weaknesses,
        appearance=appearance,
        health=100,
        respect_level=respect,
    )


def generate_gang(name: str) -> tuple[Gang, list[NPC]]:
    """Create a full gang with a complete hierarchy.

    Hierarchy composition:
    - 1 Boss
    - 1–2 Underbosses
    - 2–4 Captains
    - 4–8 Enforcers
    - 6–12 Dealers

    Args:
        name: The gang's name.

    Returns:
        A ``(Gang, npcs)`` tuple where *npcs* is the list of generated
        :class:`~antihero_system.models.NPC` objects.
    """
    gang_colors = {
        "Diaz Cartel": "yellow",
        "Vercetti Gang": "cyan",
        "Haitians": "red",
        "Cubans": "green",
        "Bikers": "magenta",
    }
    color = gang_colors.get(name, "white")

    npcs: list[NPC] = []

    def _make(rank: Rank, count: int) -> list[NPC]:
        return [generate_npc(rank, name) for _ in range(count)]

    bosses = _make(Rank.BOSS, 1)
    underbosses = _make(Rank.UNDERBOSS, random.randint(1, 2))
    captains = _make(Rank.CAPTAIN, random.randint(2, 4))
    enforcers = _make(Rank.ENFORCER, random.randint(4, 8))
    dealers = _make(Rank.DEALER, random.randint(6, 12))

    all_members = bosses + underbosses + captains + enforcers + dealers
    npcs.extend(all_members)

    # Assign territory placeholder (real territory assigned by generate_vice_city)
    territory_placeholder: list[str] = []

    gang = Gang(
        name=name,
        color=color,
        territory=territory_placeholder,
        members=[npc.npc_id for npc in all_members],
        hierarchy=[npc.npc_id for npc in all_members],  # ordered boss→dealer
        rival_gangs=[],
        allied_gangs=[],
    )

    # Set NPC territory to "Unassigned" for now
    for npc in npcs:
        npc.territory = "Unassigned"

    return gang, npcs


def generate_district(name: str) -> District:
    """Create a city district with randomised attributes.

    Args:
        name: The district's display name.

    Returns:
        A populated :class:`~antihero_system.models.District` instance.
    """
    num_businesses = random.randint(2, 4)
    businesses = random.sample(_BUSINESS_TYPES, num_businesses)
    heat = random.randint(10, 60)

    return District(
        name=name,
        controlling_gang="None",
        heat_level=heat,
        businesses=businesses,
    )


def generate_vice_city() -> tuple[dict[str, Gang], dict[str, NPC], dict[str, District]]:
    """Bootstrap a complete Vice City world.

    Creates all five canonical gangs with their hierarchies, assigns
    districts, and wires up rival relationships.

    Returns:
        A triple ``(gangs, npcs, districts)`` where each value is a
        ``dict`` keyed by the respective name or ID.
    """
    gang_names = ["Diaz Cartel", "Vercetti Gang", "Haitians", "Cubans", "Bikers"]

    gangs: dict[str, Gang] = {}
    all_npcs: dict[str, NPC] = {}

    for gname in gang_names:
        gang, npcs = generate_gang(gname)
        gangs[gname] = gang
        for npc in npcs:
            all_npcs[npc.npc_id] = npc

    # Generate districts
    districts: dict[str, District] = {}
    for dname in VICE_CITY_DISTRICTS:
        districts[dname] = generate_district(dname)

    # Distribute districts to gangs (2 per gang, shuffle remaining)
    district_names = list(districts.keys())
    random.shuffle(district_names)
    for i, gname in enumerate(gang_names):
        owned = district_names[i * 2: i * 2 + 2]
        gangs[gname].territory = owned
        for dname in owned:
            districts[dname].controlling_gang = gname

    # Set NPC territories to their gang's first district
    for gname, gang in gangs.items():
        home = gang.territory[0] if gang.territory else "Unknown"
        boss_id = gang.hierarchy[0] if gang.hierarchy else None
        for npc_id in gang.members:
            npc = all_npcs[npc_id]
            npc.territory = home
            # Give boss extra respect
            if npc_id == boss_id:
                npc.respect_level = min(100, npc.respect_level + 15)

    # Wire up canonical gang rivalries
    rivalry_pairs = [
        ("Diaz Cartel", "Vercetti Gang"),
        ("Haitians", "Cubans"),
        ("Bikers", "Haitians"),
        ("Diaz Cartel", "Cubans"),
        ("Vercetti Gang", "Bikers"),
    ]
    for g1_name, g2_name in rivalry_pairs:
        gangs[g1_name].rival_gangs.append(g2_name)
        gangs[g2_name].rival_gangs.append(g1_name)

    return gangs, all_npcs, districts
