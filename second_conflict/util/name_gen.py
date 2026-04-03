"""Random player name generator for new game setup."""
import random

_PREFIXES = [
    "Admiral", "Commander", "Emperor", "Lord", "General",
    "Warlord", "Chancellor", "Regent", "Overlord", "Viceroy",
]

_NAMES = [
    "Arcturus", "Vega", "Sirius", "Orion", "Lyra",
    "Draco", "Cygnus", "Altair", "Rigel", "Antares",
    "Zephyr", "Cassian", "Mira", "Oberon", "Theron",
    "Kael", "Vorn", "Dax", "Solan", "Revan",
    "Nexus", "Pyros", "Krynn", "Valdor", "Solus",
    "Xeran", "Marak", "Tyron", "Calix", "Iven",
    "Rynn", "Brant", "Torvan", "Quen", "Doran",
    "Hux", "Zar", "Pellan", "Arvid", "Castor",
]

_used: set[str] = set()


def random_name() -> str:
    """Return a random commander name, avoiding recent repeats."""
    global _used
    candidates = [n for n in _NAMES if n not in _used]
    if not candidates:
        _used.clear()
        candidates = _NAMES[:]
    name = random.choice(candidates)
    _used.add(name)
    prefix = random.choice(_PREFIXES)
    return f"{prefix} {name}"


def reset():
    """Clear the used-name set (call before generating a full set of names)."""
    _used.clear()