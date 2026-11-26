"""Controle: voor alle landen en alle bronnen, waar levert de tool geen (betrouwbaar) niveau?

    python scripts/audit_niveaus.py uitvoer/audit.json

Meldt per bron en land: geen landelijk niveau, een melding, een gebied zonder kleur, of een fout.
Ierland en Australië (die in de cloud geblokkeerd zijn) worden overgeslagen.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor

from reisadvies.sources import BRONNEN, au, ie
from reisadvies.sources import nl as nl_bron

for m in (ie, au):
    m._geblokkeerd = True


def controleer(iso: str) -> list[dict]:
    out = []
    for sleutel, b in BRONNEN.items():
        a = b.haal(iso)
        if a.status.value in ("n.v.t.", "handmatig"):
            continue
        if a.status.value in ("niet gevonden",):
            out.append({"iso": iso, "bron": sleutel, "soort": "niet gevonden", "url": a.url, "melding": a.melding})
            continue
        if a.status.value == "fout":
            out.append({"iso": iso, "bron": sleutel, "soort": "fout", "url": a.url, "melding": a.melding[:200]})
            continue
        probleem = []
        if a.landelijk is None:
            probleem.append("geen landelijk niveau")
        elif a.landelijk.kleur is None and sleutel not in ("uk", "de", "se"):
            probleem.append("landelijk zonder kleur")
        if a.melding:
            probleem.append("melding: " + a.melding[:160])
        if any(g.niveau.kleur is None for g in a.gebieden):
            probleem.append("gebied zonder kleur")
        if probleem:
            out.append({"iso": iso, "bron": sleutel, "soort": "; ".join(probleem), "url": a.url,
                        "brontekst": (a.brontekst or "")[:500],
                        "gebieden": [g.omschrijving[:120] for g in a.gebieden][:4]})
    return out


def main() -> None:
    landen = sorted(nl_bron.api_index())
    with ThreadPoolExecutor(6) as ex:
        resultaten = [r for lijst in ex.map(controleer, landen) for r in lijst]
    json.dump(resultaten, open(sys.argv[1] if len(sys.argv) > 1 else "audit.json", "w"), ensure_ascii=False, indent=1)
    from collections import Counter

    print(len(landen), "landen;", len(resultaten), "bevindingen")
    for sleutel, n in Counter(r["bron"] for r in resultaten).most_common():
        print(f"  {sleutel}: {n}")


if __name__ == "__main__":
    main()
