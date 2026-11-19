"""Dekkingscontrole: welke landen van elke bron koppelen we (niet) aan een ISO-code?

Gebruik:  python scripts/dekking.py

Een bronnaam die niet gekoppeld wordt, betekent dat dat land bij die overheid als
'niet gevonden' zou verschijnen. Vul dan een alias aan in reisadvies/countries.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reisadvies.countries import alle_landen, koppel
from reisadvies.sources import at, ca, dk, fr, nl, uk, us

BRONNEN = {
    "nl": (nl, "nl"),
    "uk": (uk, "en"),
    "fr": (fr, "fr"),
    "dk": (dk, "da"),
    "at": (at, "de"),
    "us": (us, "en"),
    "ca": (ca, "en"),
}


def sleutel(v):
    return v if isinstance(v, (str, tuple)) else id(v)


def main() -> None:
    for naam, (mod, taal) in BRONNEN.items():
        ix = mod.index()
        gekoppeld = {}
        for iso in alle_landen():
            v = koppel(iso, taal, ix)
            if v is not None:
                gekoppeld[sleutel(v)] = iso
        ongekoppeld = sorted({n for n, v in ix.items() if sleutel(v) not in gekoppeld})
        print(
            f"{naam}: {len(gekoppeld)} landen gekoppeld; niet gekoppeld ({len(ongekoppeld)}): {ongekoppeld}"
        )


if __name__ == "__main__":
    main()
