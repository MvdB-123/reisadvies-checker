"""Haalt de reisadviezen op, past de mappingtabel toe en bouwt het overzicht.

Gebruik:
    python3 bouw.py                     alles ophalen en bouwen
    python3 bouw.py --landen TH,ML      alleen deze landen verversen
    python3 bouw.py --alleen-bouwen     geen verkeer, alleen het HTML opnieuw maken
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from bronnen import de, fr, nl, vk, vs
from bronnen.gedeeld import OphaalFout

HIER = Path(__file__).parent
REGISTER = HIER / "data" / "landen.json"
MAPPING = HIER / "mapping.json"
ADVIEZEN = HIER / "data" / "adviezen.json"
SJABLOON = HIER / "sjabloon.html"
UITVOER = HIER / "dist" / "reisadvies-checker.html"

OPHALERS = {"nl": nl, "de": de, "vk": vk, "vs": vs, "fr": fr}

# Welk veld in het landenregister zegt of deze bron dit land kent.
SLEUTELVELD = {"nl": "nl_slug", "de": "de_iso2", "vk": "vk_slug",
               "vs": "vs_naam", "fr": "fr_slug"}

# Het land van de bron zelf. Een overheid publiceert geen reisadvies over het
# eigen land; dat is geen storing en moet dus ook niet zo klinken.
EIGEN_LAND = {"nl": "NL", "de": "DE", "vk": "GB", "vs": "US", "fr": "FR"}


def pas_mapping_toe(bronsleutel, ruw, mapping):
    """Zet bronlabels om in onze kleurcodes. Hier, en alleen hier, valt het oordeel."""
    regels = mapping["bronnen"][bronsleutel]
    labels = regels["labels"]

    def duid(stuk):
        info = labels.get(stuk["label"])
        if not info:
            # Een label dat de mappingtabel niet kent. Niet raden: benoemen.
            return {
                "kleur": None,
                "type": "niet in de mappingtabel",
                "weergave": stuk["label"],
                "bronlabel": stuk["label"],
                "onderbouwing": (
                    f"'{stuk['label']}' staat niet in mapping.json. De redactie moet "
                    "bepalen welke kleurcode hierbij hoort."
                ),
                "citaat": stuk.get("citaat", ""),
            }
        return {
            "kleur": info["kleur"],
            "type": info["type"],
            "weergave": info["weergave"],
            "bronlabel": info.get("bronlabel", stuk["label"]),
            "onderbouwing": info["onderbouwing"],
            "citaat": stuk.get("citaat", ""),
        }

    uit = {
        "gelukt": ruw.get("gelukt", False),
        "bron_url": ruw.get("bron_url"),
        "gewijzigd_op": ruw.get("gewijzigd_op"),
        "bevestigd_op": ruw.get("bevestigd_op"),
        "opmerking": ruw.get("opmerking"),
        "overgenomen_van": None,
        "landniveau": duid(ruw["landniveau"]) if ruw.get("landniveau") else None,
        "gebieden": [
            {**duid(g), "gebied": g.get("gebied", "")}
            for g in ruw.get("gebieden", [])
        ],
        "kent_niet": regels.get("kent_niet", {}),
        "taal": regels["taal"],
    }
    return uit


def haal_op(register, mapping, alleen=None):
    """Draait alle ophalers. Een bron die valt, laat de rest overeind."""
    verzameld = {}
    stand = {}
    for sleutel, module in OPHALERS.items():
        print(f"  {sleutel.upper()} ophalen…", end="", flush=True)
        try:
            ruw = module.haal_alles(register, alleen=alleen)
            stand[sleutel] = {"gelukt": True, "fout": None}
            print(f" {len(ruw)} landen")
        except OphaalFout as fout:
            ruw = {}
            stand[sleutel] = {"gelukt": False, "fout": str(fout)}
            print(f" MISLUKT: {fout}")
        for iso2, gegevens in ruw.items():
            verzameld.setdefault(iso2, {})[sleutel] = pas_mapping_toe(
                sleutel, gegevens, mapping)
    return verzameld, stand


def vul_aan_uit_vorige(nieuw, vorige_pad, nu):
    """Houdt de vorige stand aan waar een bron een land liet vallen.

    De Amerikaanse feed laat willekeurig landen weg. Een leeg vakje tonen terwijl
    we gisteren nog wisten dat er niveau 4 gold, is slechter dan de oude stand
    tonen met de datum erbij.
    """
    if not vorige_pad.exists():
        return 0
    vorige = json.loads(vorige_pad.read_text(encoding="utf-8"))
    oud = {land["iso2"]: land["adviezen"] for land in vorige.get("landen", [])}
    toen = vorige.get("opgehaald_op", "")[:10]
    overgenomen = 0
    for iso2, adviezen in nieuw.items():
        for sleutel in OPHALERS:
            huidig = adviezen.get(sleutel)
            leeg = (huidig is None or (not huidig["gelukt"])
                    or (huidig["landniveau"] is None and not huidig["gebieden"]
                        and huidig["opmerking"] and "geen van de" in huidig["opmerking"]))
            if not leeg:
                continue
            eerder = oud.get(iso2, {}).get(sleutel)
            if eerder and (eerder.get("landniveau") or eerder.get("gebieden")):
                hergebruikt = dict(eerder)
                hergebruikt["overgenomen_van"] = eerder.get("overgenomen_van") or toen
                adviezen[sleutel] = hergebruikt
                overgenomen += 1
    return overgenomen


def main(argv=None):
    keuzes = argparse.ArgumentParser(description=__doc__)
    keuzes.add_argument("--landen", help="Komma-gescheiden ISO2-codes, bv. TH,ML")
    keuzes.add_argument("--alleen-bouwen", action="store_true",
                        help="Niets ophalen; alleen het HTML opnieuw maken")
    argumenten = keuzes.parse_args(argv)

    register = json.loads(REGISTER.read_text(encoding="utf-8"))["landen"]
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    nu = datetime.now(timezone.utc).astimezone()

    if argumenten.alleen_bouwen:
        if not ADVIEZEN.exists():
            print("Er is nog geen data/adviezen.json om te bouwen.", file=sys.stderr)
            return 1
        gegevens = json.loads(ADVIEZEN.read_text(encoding="utf-8"))
    else:
        alleen = None
        if argumenten.landen:
            alleen = {c.strip().upper() for c in argumenten.landen.split(",") if c.strip()}
            print(f"Alleen: {', '.join(sorted(alleen))}")
        print("Ophalen bij vijf overheden…")
        verzameld, stand = haal_op(register, mapping, alleen=alleen)
        overgenomen = vul_aan_uit_vorige(verzameld, ADVIEZEN, nu)
        if overgenomen:
            print(f"  {overgenomen} vakjes aangevuld uit de vorige ophaalronde.")

        namen = {land["iso2"]: land for land in register}
        _vul_ontbrekende_bronnen(verzameld, namen, mapping)
        gegevens = {
            "opgehaald_op": nu.isoformat(timespec="seconds"),
            "bronnen": {s: {k: v for k, v in b.items() if k != "labels"}
                        for s, b in mapping["bronnen"].items()},
            "kleuren": mapping["kleuren"],
            "ophaalstand": stand,
            "landen": [
                {
                    "iso2": iso2,
                    "naam": namen[iso2]["naam"],
                    "adviezen": adviezen,
                }
                for iso2, adviezen in sorted(
                    verzameld.items(), key=lambda p: namen[p[0]]["naam"])
            ],
        }
        if alleen and ADVIEZEN.exists():
            gegevens = _voeg_samen_met_bestaand(gegevens, alleen)

        ADVIEZEN.parent.mkdir(exist_ok=True)
        ADVIEZEN.write_text(json.dumps(gegevens, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        print(f"Geschreven: {ADVIEZEN}")

    bouw_html(gegevens)
    return 0


def _voeg_samen_met_bestaand(nieuw, alleen):
    """Bij een deelronde blijven de overige landen staan zoals ze waren."""
    bestaand = json.loads(ADVIEZEN.read_text(encoding="utf-8"))
    op_code = {land["iso2"]: land for land in bestaand.get("landen", [])}
    for land in nieuw["landen"]:
        op_code[land["iso2"]] = land
    nieuw["landen"] = sorted(op_code.values(), key=lambda l: l["naam"])
    return nieuw


def bouw_html(gegevens):
    sjabloon = SJABLOON.read_text(encoding="utf-8")
    inhoud = json.dumps(gegevens, ensure_ascii=False, separators=(",", ":"))
    # </script> in de data zou het script voortijdig sluiten.
    inhoud = inhoud.replace("</", "<\\/")
    UITVOER.parent.mkdir(exist_ok=True)
    UITVOER.write_text(sjabloon.replace("/*GEGEVENS*/null", inhoud), encoding="utf-8")
    grootte = UITVOER.stat().st_size / 1024
    print(f"Geschreven: {UITVOER} ({grootte:.0f} kB, "
          f"{len(gegevens['landen'])} landen)")



def _vul_ontbrekende_bronnen(verzameld, namen, mapping):
    """Zegt met zoveel woorden waarom een bron niets over dit land heeft.

    Zonder dit zou een ontbrekende bron eruitzien als een storing, terwijl het
    meestal betekent dat die overheid dit land simpelweg niet behandelt — een
    overheid publiceert bijvoorbeeld geen reisadvies over het eigen land.
    """
    for iso2, adviezen in verzameld.items():
        land = namen.get(iso2, {})
        for sleutel in OPHALERS:
            if sleutel in adviezen or land.get(SLEUTELVELD[sleutel]):
                continue
            regels = mapping["bronnen"][sleutel]
            if EIGEN_LAND[sleutel] == iso2:
                reden = (f"{regels['naam']} publiceert geen reisadvies over het "
                         "eigen land.")
            else:
                reden = (f"{regels['naam']} heeft voor {land.get('naam', iso2)} "
                         "geen reisadvies gepubliceerd.")
            adviezen[sleutel] = {
                "gelukt": False, "bron_url": None, "gewijzigd_op": None,
                "bevestigd_op": None, "opmerking": reden, "overgenomen_van": None,
                "landniveau": None, "gebieden": [],
                "kent_niet": regels.get("kent_niet", {}), "taal": regels["taal"],
                "niet_van_toepassing": True,
            }

if __name__ == "__main__":
    sys.exit(main())
