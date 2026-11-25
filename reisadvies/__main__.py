"""Opdrachtregel.

python -m reisadvies Turkije            # overzicht naar uitvoer/TR.html (+ .json)
python -m reisadvies TR UA --uit map/   # meerdere landen
python -m reisadvies mapping            # MAPPING.md opnieuw genereren
python -m reisadvies bronnen            # bronnen en hun status tonen
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .countries import naam, zoek
from .mapping import als_markdown
from .report import render, verzamel
from .sources import BRONNEN

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="reisadvies", description="Vergelijk reisadviezen van gelijkgestemde landen."
    )
    p.add_argument(
        "landen", nargs="+", help="landnaam (Nederlands of Engels) of ISO-code; of 'mapping' / 'bronnen'"
    )
    p.add_argument("--uit", default="uitvoer", help="map voor de overzichten (standaard: uitvoer/)")
    p.add_argument("--vorige", help="data.json van de vorige ronde, om wijzigingen te tonen (alleen bij 'site')")
    p.add_argument("--bron", action="append", choices=list(BRONNEN), help="alleen deze bron(nen)")
    args = p.parse_args(argv)

    if args.landen == ["mapping"]:
        (ROOT / "MAPPING.md").write_text(als_markdown() + "\n", encoding="utf-8")
        print("MAPPING.md bijgewerkt.")
        return 0
    if args.landen[0] == "site":
        from .site import bouw

        iso_lijst = [zoek(x) for x in args.landen[1:]] or None
        if iso_lijst and None in iso_lijst:
            print("Land niet herkend.", file=sys.stderr)
            return 1
        uit = Path(args.uit if args.uit != "uitvoer" else "site")
        print(f"Site gebouwd: {bouw(uit, iso_lijst, vorige=Path(args.vorige) if args.vorige else None)}")
        return 0
    if args.landen == ["bronnen"]:
        for b in BRONNEN.values():
            print(
                f"{b.sleutel:3} {b.naam:20} {'automatisch' if b.automatisch else 'HANDMATIG':12} {b.startpagina}"
            )
        return 0

    uit = Path(args.uit)
    uit.mkdir(parents=True, exist_ok=True)
    fouten = 0
    for invoer in args.landen:
        iso = zoek(invoer)
        if not iso:
            print(f"Land niet herkend: {invoer!r}", file=sys.stderr)
            fouten += 1
            continue
        adviezen = verzamel(iso, args.bron)
        (uit / f"{iso}.html").write_text(render(iso, adviezen), encoding="utf-8")
        (uit / f"{iso}.json").write_text(
            json.dumps([a.to_dict() for a in adviezen], ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"{naam(iso)} ({iso}): {uit / (iso + '.html')}")
        for a in adviezen:
            kleur = a.landelijk.kleur.value if a.landelijk and a.landelijk.kleur else "–"
            print(
                f"   {BRONNEN[a.bron].naam:20} {a.status.value:14} {kleur:7} {len(a.gebieden)} gebied(en)  {a.gewijzigd_op or ''}"
            )
    return 1 if fouten else 0


if __name__ == "__main__":
    raise SystemExit(main())
