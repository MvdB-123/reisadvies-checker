"""Loopt de acceptatiecriteria uit het bouwplan na op de werkelijke gegevens.

Dit is geen unittest maar een controle op het eindresultaat: klopt wat er in
data/adviezen.json en dist/reisadvies-checker.html staat met wat we beloofd
hebben? Draaien na een ophaalronde.

    python3 acceptatie.py
"""

import json
import re
import sys
from pathlib import Path

HIER = Path(__file__).parent
ADVIEZEN = HIER / "data" / "adviezen.json"
UITVOER = HIER / "dist" / "reisadvies-checker.html"

MAX_CITAAT = 320  # 300 plus de afkapmarkering


def criterium(nummer, omschrijving, controle):
    try:
        goed, toelichting = controle()
    except Exception as fout:  # een criterium mag de rest niet meeslepen
        goed, toelichting = False, f"controle zelf liep vast: {fout}"
    merk = "GOED" if goed else "FOUT"
    print(f"[{merk}] {nummer}. {omschrijving}")
    for regel in toelichting.splitlines():
        print(f"        {regel}")
    return goed


def main():
    gegevens = json.loads(ADVIEZEN.read_text(encoding="utf-8"))
    html = UITVOER.read_text(encoding="utf-8")
    landen = {l["iso2"]: l for l in gegevens["landen"]}
    uitslagen = []

    def een():
        th = landen["TH"]["adviezen"]
        werkend = {b: a for b, a in th.items() if a["gelukt"]}
        regels = []
        for bron, advies in sorted(werkend.items()):
            stukken = [advies["landniveau"]] if advies["landniveau"] else []
            stukken += advies["gebieden"]
            heeft_label = all(s.get("bronlabel") for s in stukken)
            heeft_link = bool(advies["bron_url"] and advies["bron_url"].startswith("http"))
            regels.append(f"{bron}: {len(stukken)} niveaus, datum "
                          f"{advies['gewijzigd_op']}, link {'ja' if heeft_link else 'NEE'}, "
                          f"labels {'ja' if heeft_label else 'NEE'}")
            if not (stukken and heeft_link and heeft_label and advies["gewijzigd_op"]):
                return False, "\n".join(regels)
        return len(werkend) == 5, "\n".join(regels)

    def twee():
        stempel = gegevens.get("opgehaald_op", "")
        klopt = bool(re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", stempel))
        in_html = "Opgehaald op" in html and stempel[:16] in html
        return klopt and in_html, (f"tijdstempel {stempel}\n"
                                   f"staat in het overzicht: {in_html}")

    def drie():
        meldingen = []
        fr_land = sum(1 for l in landen.values()
                      if (l["adviezen"].get("fr") or {}).get("landniveau"))
        meldingen.append(f"Frankrijk geeft bij {fr_land} van {len(landen)} landen een "
                         "landniveau (alleen waar het letterlijk 'l'ensemble du "
                         "territoire' schrijft)")

        # Niveaus die een overheid aantoonbaar niet kent, mogen nooit voorkomen.
        for bron, kleur in (("de", "geel"), ("vk", "geel"), ("vk", "groen")):
            gevonden = [l["naam"] for l in landen.values()
                        for s in [(l["adviezen"].get(bron) or {}).get("landniveau")]
                        + list((l["adviezen"].get(bron) or {}).get("gebieden", []))
                        if s and s.get("kleur") == kleur]
            meldingen.append(f"{bron.upper()} met kleur {kleur}: {len(gevonden)} "
                             f"(moet 0 zijn)")
            if gevonden:
                meldingen.append(f"   o.a. {', '.join(gevonden[:3])}")
                return False, "\n".join(meldingen)

        # Waar wij twee schalen gelijkstellen, moet dat als keuze zichtbaar zijn.
        # Duitsland kent geen oranje; onze oranje daar is altijd een afleiding.
        ten_onrechte = [
            f"{l['naam']} ({s['bronlabel']})" for l in landen.values()
            for s in [(l["adviezen"].get("de") or {}).get("landniveau")]
            + list((l["adviezen"].get("de") or {}).get("gebieden", []))
            if s and s.get("kleur") == "oranje" and s.get("type") != "afgeleid"
        ]
        oranje = sum(1 for l in landen.values()
                     for s in [(l["adviezen"].get("de") or {}).get("landniveau")]
                     + list((l["adviezen"].get("de") or {}).get("gebieden", []))
                     if s and s.get("kleur") == "oranje")
        meldingen.append(f"DE met kleur oranje: {oranje}, waarvan "
                         f"{oranje - len(ten_onrechte)} gemarkeerd als afgeleid")
        if ten_onrechte:
            meldingen.append("   ten onrechte als letterlijk: "
                             + ", ".join(ten_onrechte[:3]))
            return False, "\n".join(meldingen)

        zonder_bron = [
            f"{l['naam']}/{bron}" for l in landen.values()
            for bron, a in l["adviezen"].items()
            for s in [a.get("landniveau")] + list(a.get("gebieden", []))
            if s and s.get("kleur") and not s.get("citaat")
        ]
        meldingen.append(f"kleurcodes zonder citaat: {len(zonder_bron)}"
                         + (f" — {', '.join(zonder_bron[:4])}" if zonder_bron else ""))
        return not zonder_bron, "\n".join(meldingen)

    def vier():
        regels = []
        for bron in ("nl", "de", "vk", "fr"):
            met = sum(1 for l in landen.values()
                      if (l["adviezen"].get(bron) or {}).get("gebieden"))
            regels.append(f"{bron.upper()}: {met} landen met aparte gebieden")
            if met < 5:
                return False, "\n".join(regels)
        th = landen["TH"]["adviezen"]
        losse = {b: (bool(a["landniveau"]), len(a["gebieden"]))
                 for b, a in th.items() if a["gelukt"]}
        regels.append(f"Thailand (landniveau, aantal gebieden): {losse}")
        return True, "\n".join(regels)

    def vijf():
        te_lang, eigen_tekst = [], []
        for land in landen.values():
            for bron, advies in land["adviezen"].items():
                for stuk in [advies.get("landniveau")] + list(advies.get("gebieden", [])):
                    if not stuk:
                        continue
                    if len(stuk.get("citaat") or "") > MAX_CITAAT:
                        te_lang.append(f"{land['naam']}/{bron} ({len(stuk['citaat'])})")
                    if stuk.get("kleur") and not stuk.get("weergave"):
                        eigen_tekst.append(f"{land['naam']}/{bron}")
        knop = html.count("deepl.com/translator")
        return (not te_lang and not eigen_tekst and knop > 0,
                f"citaten langer dan {MAX_CITAAT} tekens: {len(te_lang)}\n"
                f"niveaus zonder Nederlandse weergave: {len(eigen_tekst)}\n"
                f"vertaalknop aanwezig in het overzicht: {'ja' if knop else 'NEE'}")

    def zes():
        # Een bron die niets oplevert, mag de andere niet meeslepen.
        gedeeltelijk = [l for l in landen.values()
                        if 0 < sum(1 for a in l["adviezen"].values() if not a["gelukt"])
                        < len(l["adviezen"])]
        met_reden = [l for l in gedeeltelijk
                     if all(a["opmerking"] for a in l["adviezen"].values()
                            if not a["gelukt"])]
        return (len(gedeeltelijk) == len(met_reden),
                f"landen waar een deel van de bronnen niets gaf: {len(gedeeltelijk)}\n"
                f"daarvan met een uitgeschreven reden: {len(met_reden)}")

    uitslagen.append(criterium(1, "Thailand: per overheid kleurcode, bronlabel, "
                                  "wijzigingsdatum en werkende bronlink", een))
    uitslagen.append(criterium(2, "'Opgehaald op' komt uit de ophaalronde zelf", twee))
    uitslagen.append(criterium(3, "Nooit een kleur zonder bron, nooit een niveau dat "
                                  "een overheid niet kent, en elke gelijkstelling "
                                  "zichtbaar als afgeleid", drie))
    uitslagen.append(criterium(4, "Gebieden staan los van het landniveau", vier))
    uitslagen.append(criterium(5, "Onderbouwing: letterlijk citaat, Nederlandse "
                                  "weergave, vertaalknop", vijf))
    uitslagen.append(criterium(6, "Valt één bron weg, dan blijft de rest staan, "
                                  "met reden", zes))

    print(f"\n{sum(uitslagen)} van {len(uitslagen)} criteria gehaald.")
    return 0 if all(uitslagen) else 1


if __name__ == "__main__":
    sys.exit(main())
