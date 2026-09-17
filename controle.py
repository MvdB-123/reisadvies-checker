"""Controleert of een ophaalronde bruikbaar is voordat het resultaat wordt vastgelegd.

Draait in de workflow na bouw.py. Bij een fout stopt de workflow en blijft de
vorige, wél werkende versie staan. Beter een dag oude stand dan een leeg of
half overzicht dat de redactie doorstuurt.
"""

import json
import sys
from pathlib import Path

HIER = Path(__file__).parent
ADVIEZEN = HIER / "data" / "adviezen.json"
UITVOER = HIER / "dist" / "reisadvies-checker.html"

# Ondergrenzen. Ruim onder wat een gezonde ronde oplevert, zodat normale
# schommelingen geen alarm geven, maar een stille storing wel.
MINIMAAL_LANDEN = 150
MINIMAAL_PER_BRON = {"nl": 150, "de": 150, "vk": 150, "vs": 120, "fr": 120}


def controleer():
    fouten, waarschuwingen = [], []

    if not ADVIEZEN.exists():
        return ["data/adviezen.json ontbreekt."], []
    if not UITVOER.exists():
        return ["dist/reisadvies-checker.html ontbreekt."], []

    gegevens = json.loads(ADVIEZEN.read_text(encoding="utf-8"))
    landen = gegevens.get("landen", [])

    if len(landen) < MINIMAAL_LANDEN:
        fouten.append(f"Maar {len(landen)} landen; verwacht minstens {MINIMAAL_LANDEN}.")

    # Per bron: hoeveel landen hebben een bruikbaar oordeel?
    for bron, ondergrens in MINIMAAL_PER_BRON.items():
        met_oordeel = sum(
            1 for land in landen
            if (land["adviezen"].get(bron) or {}).get("gelukt")
        )
        if met_oordeel < ondergrens:
            fouten.append(f"Bron {bron.upper()}: {met_oordeel} landen opgehaald, "
                          f"verwacht minstens {ondergrens}. Waarschijnlijk is de "
                          "opzet van die website veranderd.")

    # Labels die de mappingtabel niet kent: nooit stilzwijgend doorlaten.
    onbekend = {}
    for land in landen:
        for bron, advies in land["adviezen"].items():
            for stuk in [advies.get("landniveau")] + list(advies.get("gebieden", [])):
                if stuk and stuk.get("type") == "niet in de mappingtabel":
                    onbekend.setdefault(f"{bron}: {stuk['bronlabel']}", []).append(
                        land["naam"])
    for label, betrokken in sorted(onbekend.items()):
        fouten.append(f"Onbekend label {label!r} bij {len(betrokken)} landen "
                      f"(o.a. {', '.join(betrokken[:3])}). Vul mapping.json aan.")

    # Een kleurcode zonder citaat is niet te controleren door de redactie.
    zonder_citaat = sum(
        1 for land in landen for advies in land["adviezen"].values()
        for stuk in [advies.get("landniveau")] + list(advies.get("gebieden", []))
        if stuk and stuk.get("kleur") and not stuk.get("citaat")
    )
    if zonder_citaat:
        waarschuwingen.append(f"{zonder_citaat} kleurcodes zonder citaat; die kan "
                              "de redactie niet nalopen.")

    # Thailand is onze ijkwaarde: vijf bronnen, gebieden bij meerdere.
    thailand = next((l for l in landen if l["iso2"] == "TH"), None)
    if not thailand:
        fouten.append("Thailand ontbreekt; dat is onze vaste controlewaarde.")
    else:
        gelukt = [b for b, a in thailand["adviezen"].items() if a.get("gelukt")]
        if len(gelukt) < 5:
            fouten.append(f"Thailand heeft maar {len(gelukt)} werkende bronnen: "
                          f"{', '.join(sorted(gelukt))}.")
        met_gebieden = [b for b, a in thailand["adviezen"].items() if a.get("gebieden")]
        if len(met_gebieden) < 3:
            waarschuwingen.append(
                f"Thailand toont maar bij {len(met_gebieden)} bronnen gebieden; "
                "normaal zijn dat er minstens drie.")

    return fouten, waarschuwingen


def main():
    fouten, waarschuwingen = controleer()
    for regel in waarschuwingen:
        print(f"Let op: {regel}")
    for regel in fouten:
        print(f"FOUT: {regel}", file=sys.stderr)
    if fouten:
        print("\nDe ophaalronde is niet vastgelegd. De vorige versie blijft staan.",
              file=sys.stderr)
        return 1
    print("Controle in orde.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
