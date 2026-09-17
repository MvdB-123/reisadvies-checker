"""Nederland — Ministerie van Buitenlandse Zaken, nederlandwereldwijd.nl.

De pagina noemt de kleurcodes in lopende tekst. Het blok 'In het kort' bevat de
samenvatting; verderop wordt dezelfde inhoud herhaald, door elkaar met algemene
uitleg over wat een kleurcode betekent. We lezen daarom alleen 'In het kort'.
"""

import re

from .gedeeld import OphaalFout, citaat, haal_tekst, plat

PAGINA = "https://www.nederlandwereldwijd.nl/reisadvies/{slug}"

KLEUREN = ("groen", "geel", "oranje", "rood")

# 'In het kort' is een opsomming. We lezen de lijstitems zelf, want op tekst
# afgaan gaat mis: verwijzingen als "Lees meer onder Paspoort, visum, rijbewijs"
# lijken op een kopje en kappen het blok dan te vroeg af.
# Van het kopje tot het volgende kopje. Op opmaak knippen en niet op woorden,
# want verwijzingen als "Lees meer onder Paspoort, visum, rijbewijs" lijken op
# een kopje en kappen het blok dan te vroeg af. De kleurcode staat soms in een
# alinea (rustige landen) en soms in de opsomming (landen met gebieden).
KORT_BLOK = re.compile(
    r"<h2[^>]*>\s*In het kort\s*</h2>(.*?)(?=<h2|\Z)", re.IGNORECASE | re.DOTALL)

# De formuleringen waarmee Nederland een kleurcode aan een gebied toekent. Een
# zin die de kleurcode alleen noemt ("Ook in de delen waarvoor kleurcode geel
# geldt, kan een aanslag plaatsvinden") is geen toekenning en telt niet mee.
TOEKENNING = [
    re.compile(r"\bkleurcode\s+(groen|geel|oranje|rood)\s+geldt\s+voor\b", re.I),
    re.compile(r"\bgeldt\s+kleurcode\s+(groen|geel|oranje|rood)\b", re.I),
    re.compile(r"\bde\s+kleurcode[^.]{0,80}?\bis\s+(?:ook\s+)?(groen|geel|oranje|rood)\b", re.I),
]

# Algemene uitleg over wat een kleurcode betekent — geen uitspraak over dit land.
UITLEG = re.compile(
    r"(?:gebieden met kleurcode|reis niet naar gebieden|u kunt reizen naar gebieden"
    r"|reis alleen naar gebieden|lees meer over reisadviezen|wat uw situatie ook is)",
    re.IGNORECASE,
)

DATUM = re.compile(r"Laatst gewijzigd op:\s*(\d{2})-(\d{2})-(\d{4})", re.IGNORECASE)
GELDIG = re.compile(r"Nog steeds geldig op:\s*(\d{2})-(\d{2})-(\d{4})", re.IGNORECASE)


def haal_alles(register, alleen=None):
    resultaat = {}
    for land in register:
        slug = land.get("nl_slug")
        if not slug or (alleen is not None and land["iso2"] not in alleen):
            continue
        resultaat[land["iso2"]] = _haal_land(slug, land["naam"])
    return resultaat


def _haal_land(slug, landsnaam):
    uit = {
        "gelukt": False, "bron_url": PAGINA.format(slug=slug), "gewijzigd_op": None,
        "bevestigd_op": None, "landniveau": None, "gebieden": [], "opmerking": None,
    }
    try:
        rauw = haal_tekst(PAGINA.format(slug=slug))
        tekst = plat(rauw)
    except OphaalFout as fout:
        uit["opmerking"] = f"Niet opgehaald: {fout}"
        return uit

    uit["gelukt"] = True
    uit["gewijzigd_op"] = _datum(DATUM, tekst)
    uit["bevestigd_op"] = _datum(GELDIG, tekst)

    zinnen = _kort_blok(rauw)
    if not zinnen:
        uit["opmerking"] = "Geen blok 'In het kort' gevonden op de pagina."
        return uit

    for zin in zinnen:
        if "kleurcode" not in zin.lower() or UITLEG.search(zin):
            continue
        kleur = next((tr.group(1).lower() for tr in
                      (patroon.search(zin) for patroon in TOEKENNING) if tr), None)
        if not kleur:
            continue
        if _gaat_over_heel_land(zin, landsnaam):
            uit["landniveau"] = {"label": f"kleurcode {kleur}", "citaat": citaat(zin)}
        else:
            uit["gebieden"].append({
                "label": f"kleurcode {kleur}",
                "gebied": citaat(_gebied_uit(zin), 200),
                "citaat": citaat(zin),
            })

    if not uit["landniveau"] and not uit["gebieden"]:
        uit["opmerking"] = "Geen kleurcode gevonden in 'In het kort'."
    return uit


def _gaat_over_heel_land(zin, landsnaam):
    """'Voor de rest van X geldt…' en 'voor heel X' beschrijven het landniveau."""
    naam = re.escape(landsnaam)
    return bool(
        re.search(rf"(?:rest van|heel)\s+(?:{naam}\b|het land\b)", zin, re.I)
        or re.search(rf"reisadvies voor {naam} is", zin, re.I)
        or re.search(rf"kleurcode \w+ voor heel", zin, re.I)
    )


def _gebied_uit(zin):
    """Het gebied waar de kleurcode voor geldt, zonder de kleur zelf erachter."""
    treffer = re.search(r"\bvoor\s+(.*)", zin, re.IGNORECASE)
    gebied = (treffer.group(1) if treffer else zin).strip(" .")
    gebied = re.sub(r"\s+is\s+(?:ook\s+)?(?:groen|geel|oranje|rood)\s*$", "",
                    gebied, flags=re.IGNORECASE)
    return gebied.strip(" .")


def _datum(patroon, tekst):
    treffer = patroon.search(tekst)
    if not treffer:
        return None
    dag, maand, jaar = treffer.groups()
    return f"{jaar}-{maand}-{dag}"


def _kort_blok(rauw):
    """De tekst van het blok 'In het kort', als losse zinnen."""
    ontsnapt = (rauw.replace("\\u003c", "<").replace("\\u003e", ">")
                    .replace('\\"', '"'))
    blok = KORT_BLOK.search(ontsnapt)
    if not blok:
        return []
    tekst = plat(blok.group(1))
    return [z.strip() for z in re.split(r"(?<=[.!?])\s+", tekst) if z.strip()]
