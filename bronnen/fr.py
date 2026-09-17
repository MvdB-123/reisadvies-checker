"""Frankrijk — Ministère de l'Europe et des Affaires étrangères.

Frankrijk werkt met zones op een kaart, niet met een niveau voor een heel land.
Onder het kopje 'Zones de vigilance' staat per niveau een kopje met daaronder de
gebieden. De datum staat in het bijschrift van de kaart.
"""

import re

from .gedeeld import OphaalFout, citaat, haal_tekst, plat, zinnen

PAGINA = ("https://www.diplomatie.gouv.fr/fr/information-par-pays/{slug}"
          "/conseils-aux-voyageurs-securite")

# Het blok met de zones, tot het volgende hoofdstuk ('Risques encourus').
# Sommige landen, zoals Oekraïne, hebben het kopje twee keer: eerst boven de
# kaart en daarna boven de zones zelf. Een herhaling telt daarom niet als einde.
# Het kopje staat niet altijd als h3 (Burkina Faso), en op sommige landpagina's
# staat er 'vigilence' in plaats van 'vigilance' — een typefout van de bron zelf
# (Honduras). Beide varianten tellen mee, anders valt het hele land weg.
ZONEKOP = r"Zones?\s+de\s+vigil[ae]nce"
ZONEBLOK = re.compile(
    r"<h([234])[^>]*>\s*" + ZONEKOP + r"\s*</h\1>"
    r"(.*?)(?=<h[23][^>]*>\s*(?!" + ZONEKOP + r")|\Z)",
    re.IGNORECASE | re.DOTALL)

# Elk niveau is een kopje met daaronder de gebieden.
NIVEAUKOP = re.compile(r"<h4[^>]*>(.*?)</h4>(.*?)(?=<h4|\Z)",
                       re.IGNORECASE | re.DOTALL)

# Meestal noemt Frankrijk alleen zones, maar soms staat er letterlijk dat het
# hele land in één zone valt. Dat is dan wél een uitspraak over het hele land.
HEEL_LAND = re.compile(
    r"\b(?:l['’]ensemble|la\s+totalit[ée]|l['’]int[ée]gralit[ée])\s+du\s+"
    r"(?:territoire|pays)\b|\btout\s+le\s+pays\b",
    re.IGNORECASE)

DATUM = re.compile(r"Derni[eè]re actualisation le\s*(\d{2})/(\d{2})/(\d{4})",
                   re.IGNORECASE)

# Het volledige bijschrift onder de kaart; dat hoort niet in een citaat.
BIJSCHRIFT = re.compile(
    r"Derni[eè]re actualisation le\s*\d{2}/\d{2}/\d{4}"
    r"(?:\s*,\s*information\s+toujours\s+valable\s+[^.]*?\bjour\b)?",
    re.IGNORECASE)

# Van kopje naar het label in mapping.json. Volgorde telt: 'déconseillées sauf
# raison impérative' bevat ook het woord 'déconseillées'.
NIVEAUS = [
    ("deconseillee_sauf_imperative",
     # 'déconseillé sauf raison impérative', maar ook met woorden ertussen:
     # 'Il est déconseillé aux ressortissants français, sauf pour des raisons
     # impératives, de se rendre à Bahreïn.'
     re.compile(r"d[ée]conseill[ée]{1,2}s?[^.]{0,70}?sauf\s+(?:pour\s+)?(?:des?\s+)?"
                r"raisons?\s+imp[ée]rative", re.I)),
    ("deconseillee_sauf_imperative",
     # 'les voyages non essentiels vers l'île sont déconseillés' (Cuba).
     re.compile(r"voyages?\s+non\s+essentiels?[^.]{0,70}?d[ée]conseill", re.I)),
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

    datum = DATUM.search(plat(blok.group(2)))
    if datum:
        dag, maand, jaar = datum.groups()
        uit["gewijzigd_op"] = f"{jaar}-{maand}-{dag}"

    # Sommige landen hebben geen zonekopjes maar één zin direct in het blok:
    # Afghanistan zegt "La totalité du territoire est formellement déconseillée."
    # Zonder dit stuk viel dat advies volledig weg.
    inleiding = re.split(r"<h4", blok.group(2), maxsplit=1)[0]
    # Staan er helemaal geen zonekopjes, dan is een uitspraak in de inleiding aan
    # geen enkele zone gebonden en gaat hij dus over het land. Dat is een
    # structureel gegeven, geen uitleg van de zin zelf.
    zonder_zones = not NIVEAUKOP.search(blok.group(2))
    for zin in zinnen(BIJSCHRIFT.sub("", plat(inleiding)).strip(" .,")):
        label = next((naam for naam, patroon in NIVEAUS if patroon.search(zin)), None)
        if not label:
            continue
        if (HEEL_LAND.search(zin) or zonder_zones) and not uit["landniveau"]:
            uit["landniveau"] = {"label": label, "citaat": citaat(zin)}
        else:
            uit["gebieden"].append({"label": label, "gebied": citaat(zin, 200),
                                    "citaat": citaat(zin)})

    kopjes = NIVEAUKOP.findall(blok.group(2))
    onbekende_kopjes = []
    for kop, inhoud in kopjes:
        koptekst = plat(kop)
        label = next((naam for naam, patroon in NIVEAUS if patroon.search(koptekst)),
                     None)
        if not label:
            onbekende_kopjes.append(koptekst)
            continue
        for gebied in _gebieden_uit(inhoud, koptekst):
            if HEEL_LAND.search(gebied["citaat"]) and not uit["landniveau"]:
                uit["landniveau"] = {"label": label, "citaat": gebied["citaat"]}
            else:
                uit["gebieden"].append({"label": label, **gebied})

    # Bewust GEEN regel voor 'de rest van het land'. Frankrijks kaart dekt het
    # hele land met vier zonekleuren, en welke kleur de rest heeft staat niet in
    # de tekst. Vaak dekt de gele zone de rest al ('Bangkok et autres régions');
    # een regel 'geen zone aangewezen' zou die tegenspreken. Bovendien gebruiken
    # sommige landpagina's eigen kopjes in plaats van de vaste zonekopjes, zodat
    # 'niets gevonden' net zo goed een gat in onze herkenning kan zijn.
    if uit["landniveau"]:
        uit["opmerking"] = None
    elif uit["gebieden"]:
        uit["opmerking"] = (
            "Frankrijk geeft geen niveau voor het hele land, alleen voor zones."
        )
    elif onbekende_kopjes:
        # Sommige landpagina's gebruiken eigen kopjes ('Jammu-Cachemire et zones
        # frontalières avec le Pakistan') in plaats van de vaste zonekopjes. De
        # gebieden staan er dan wel, maar het niveau is niet vast te stellen.
        uit["opmerking"] = (
            "Frankrijk noemt hier wel gebieden, maar onder eigen kopjes in plaats "
            "van de vaste zonekopjes: "
            + "; ".join(k[:60] for k in onbekende_kopjes[:3])
            + ". Het niveau is daaruit niet vast te stellen; zie de bronpagina."
        )
    else:
        uit["opmerking"] = (
            "Frankrijk noemt voor dit land geen zones onder het kopje 'Zones de "
            "vigilance'. Op hun kaart heeft het land wel een kleur, maar die "
            "staat niet in de tekst."
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
