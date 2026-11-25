"""Vertalingen van citaten, vastgelegd in vertalingen.json.

Elke vertaling hoort bij precies één brontekst. Verandert de brontekst ook maar iets, dan past de
vertaling niet meer en toont het overzicht alleen de DeepL-link. Zo staat er nooit een vertaling
naast een tekst waar hij niet bij hoort.

De vertalingen worden in een Claude-sessie gemaakt: zin voor zin, niets samenvatten of weglaten.
  python -m reisadvies vertaal-open TR UA   # schrijft uitvoer/te-vertalen.json
  (vertalen, veld "nl" invullen)
  python -m reisadvies vertaal-in uitvoer/te-vertalen.json
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

BESTAND = Path(__file__).resolve().parents[1] / "vertalingen.json"


def sleutel(tekst: str) -> str:
    return hashlib.sha256(" ".join(tekst.split()).encode()).hexdigest()[:16]


@lru_cache(maxsize=1)
def _alles() -> dict[str, dict]:
    if not BESTAND.exists():
        return {}
    return json.loads(BESTAND.read_text(encoding="utf-8"))


def vertaal(tekst: str) -> str | None:
    """De vastgelegde vertaling, alleen als de brontekst exact (op witruimte na) overeenkomt."""
    if not tekst:
        return None
    rij = _alles().get(sleutel(tekst))
    if rij and " ".join(rij["bron"].split()) == " ".join(tekst.split()) and rij.get("nl"):
        return rij["nl"]
    return None


def voeg_toe(rijen: list[dict]) -> int:
    """Voeg vertaalde rijen ({bron, taal, nl}) toe. Geeft het aantal nieuwe of gewijzigde terug."""
    alles = dict(_alles())
    n = 0
    for r in rijen:
        if not r.get("nl"):
            continue
        k = sleutel(r["bron"])
        if alles.get(k, {}).get("nl") != r["nl"]:
            alles[k] = {"taal": r["taal"], "bron": r["bron"], "nl": r["nl"]}
            n += 1
    BESTAND.write_text(json.dumps(dict(sorted(alles.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    _alles.cache_clear()
    return n
