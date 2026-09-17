"""Frankrijk — Ministère de l'Europe et des Affaires étrangères.

Frankrijk werkt met zones op een kaart, niet met een niveau voor een heel land.
Onder het kopje 'Zones de vigilance' staat per niveau een kopje met daaronder de
gebieden. De datum staat in het bijschrift van de kaart.
"""

import re

from .gedeeld import OphaalFout, citaat, haal_tekst, plat

PAGINA = ("https://www.diplomatie.gouv.fr/fr/information-par-pays/{slug}"
          "/conseils-aux-voyageurs-securite")

# Het blok met de zones, tot het volgende hoofdstuk ('Risques encourus').
# Sommige landen, zoals Oekraïne, hebben het kopje twee keer: eerst boven de
# kaart en daarna boven de zones zelf. Een herhaling telt daarom niet als einde.
ZONEBLOK = re.compile(
    r"<h3[^>]*>\s*Zones de vigilance\s*</h3>"
    r"(.*?)(?=<h3[^>]*>\s*(?!Zones de vigilance)|\Z)",
    re.IGNORECASE | re.DOTALL)

# Elk niveau is een kopje met daaronder de gebieden.
NIVEAUKOP = re.compile(r"<h4[^>]*>(.*?)</h4>(.*?)(?=<h4|\Z)",
                       re.IGNORECASE | re.DOTALL)

# Meestal noemt Frankrijk alleen zones, maar soms staat er letterlijk dat het
# hele land in één zone valt. Dat is dan wél een uitspraak over het hele land.
HEEL_LAND = re.compile(
    r"\b(?:l['’]ensemble\s+du\s+(?:territoire|pays)|la\s+totalit[ée]\s+du\s+pays"
    r"|tout\s+le\s+pays|l['’]int[ée]gralit[ée]\s+du\s+(?:territoire|pays))\b",
    re.IGNORECASE)

DATUM = re.compile(r"Derni[eè]re actualisation le\s*(\d{2})/(\d{2})/(\d{4})",
                   re.IGNORECASE)

# Van kopje naar het label in mapping.json. Volgorde telt: 'déconseillées sauf
# raison impérative' bevat ook het woord 'déconseillées'.
NIVEAUS = [
    ("deconseillee_sauf_imperative",
     re.compile(r"d[ée]conseill[ée]{1,2}s?\s+sauf\s+raison\s+imp[ée]rative", re.I)),
    ("formellement_deconseillee",
     re.compile(r"formellement\s+d[ée]conseill[ée]{1,2}s?", re.I)),
    ("vigilance_renforcee", re.compile(r"vigilance\s+renforc[ée]{1,2}e?", re.I)),
    ("vigilance_normale", re.compile(r"vigilance\s+normale", re.I)),
]


def haal_alles(register, alleen=None):
    resultaat = {}
    for land in register:
        slug = land.get("fr_slug")
        if not slug or (alleen is not None and land["iso2"] not in alleen):
            continue
        resultaat[land["iso2"]] = _haal_land(slug)
    return resultaat


def _haal_land(slug):
    url = PAGINA.format(slug=slug)
    uit = {
        "gelukt": False, "bron_url": url, "gewijzigd_op": None,
        "landniveau": None, "gebieden": [],
        "opmerking": None,
    }
    try:
        rauw = haal_tekst(url)
    except OphaalFout as fout:
        uit["opmerking"] = f"Niet opgehaald: {fout}"
        return uit

    uit["gelukt"] = True
    blok = ZONEBLOK.search(rauw)
    if not blok:
        uit["opmerking"] = (
            "Frankrijk noemt voor dit land geen 'Zones de vigilance'."
        )
        return uit

    datum = DATUM.search(plat(blok.group(1)))
    if datum:
        dag, maand, jaar = datum.groups()
        uit["gewijzigd_op"] = f"{jaar}-{maand}-{dag}"

    for kop, inhoud in NIVEAUKOP.findall(blok.group(1)):
        koptekst = plat(kop)
        label = next((naam for naam, patroon in NIVEAUS if patroon.search(koptekst)),
                     None)
        if not label:
            continue
        for gebied in _gebieden_uit(inhoud, koptekst):
            if HEEL_LAND.search(gebied["citaat"]) and not uit["landniveau"]:
                uit["landniveau"] = {"label": label, "citaat": gebied["citaat"]}
            else:
                uit["gebieden"].append({"label": label, **gebied})

    if uit["landniveau"]:
        uit["opmerking"] = None
    elif uit["gebieden"]:
        # Frankrijk deelt landen niet als geheel in; zie mapping.json, 'kent_niet'.
        uit["opmerking"] = (
            "Frankrijk geeft geen niveau voor het hele land, alleen voor zones."
        )
    else:
        uit["opmerking"] = (
            "Frankrijk markeert voor dit land geen afwijkende zones en geeft "
            "geen niveau voor het hele land."
        )
    return uit


def _gebieden_uit(inhoud, koptekst):
    """De gebieden onder een niveaukopje: de opsomming, of anders de alinea."""
    punten = [plat(p) for p in re.findall(r"<li[^>]*>(.*?)</li>", inhoud,
                                          re.IGNORECASE | re.DOTALL)]
    punten = [p for p in punten if p.strip()]
    if not punten:
        tekst = plat(inhoud).strip()
        punten = [tekst] if tekst else []
    if not punten:
        # Het kopje benoemt soms zelf het gebied ('… : Bangkok et autres régions').
        na_dubbelepunt = koptekst.split(":", 1)
        punten = [na_dubbelepunt[1].strip()] if len(na_dubbelepunt) == 2 else []

    uit = []
    for punt in punten:
        uit.append({"gebied": citaat(punt, 200), "citaat": citaat(punt)})
    return uit
