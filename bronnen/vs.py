"""Verenigde Staten — Department of State.

De Amerikaanse RSS bevat alle landen in één bestand, met het niveau in de titel
en de onderbouwing in de omschrijving. Binnen die omschrijving benoemt de VS ook
afwijkende gebieden, met dezelfde niveaunamen.
"""

import html
import re
from datetime import datetime

from .gedeeld import citaat, haal_tekst, normaliseer, plat, zinnen

RSS = "https://travel.state.gov/_res/rss/TAsTWs.xml"

# De Amerikaanse feed wordt vanaf meerdere servers geserveerd met ONGELIJKE
# inhoud: bij herhaald ophalen ontbreken er telkens andere landen, waaronder
# zware gevallen als Mali en Noord-Korea. Gemeten op 17-09-2026: van de 219
# landen kwamen er 10 niet in elke ronde voor. We halen de feed daarom een paar
# keer op en voegen samen. Wat dan nog ontbreekt, vult bouw.py aan met de stand
# van de vorige ophaalronde, met datum erbij.
RONDEN = 3

NIVEAU_IN_TITEL = re.compile(r"^(?P<land>.*?)\s+-\s+Level\s+(?P<niveau>[1-4])\b")

# De zin waarin de VS het niveau voor het hele land uitspreekt.
LANDZIN = re.compile(
    r"\b(?:Exercise\s+normal\s+precautions|Exercise\s+increased\s+caution"
    r"|Reconsider\s+travel|Do\s+not\s+travel)\s+(?:to|in)?\s*[^.]*\.",
    re.IGNORECASE,
)

# Gebiedsuitspraken. De VS gebruikt per gebied dezelfde niveaunamen als voor het
# hele land, dus die vertalen we naar hetzelfde nummer.
# Kopjes lopen in de platte tekst door in de zin eronder.
KOPJE = re.compile(r"^(?:Advisory\s+summary|Summary|Country\s+Summary)\s+(?=[A-Z])",
                   re.IGNORECASE)

# Gebiedsaanduidingen die niets aanwijzen; die zeggen de lezer niets zonder de
# bronpagina erbij, dus tonen we ze niet als losse gebiedsregel.
VAAG = re.compile(r"^(?:these|those|the following|the above)\b", re.IGNORECASE)

GEBIEDSNIVEAUS = [
    ("4", re.compile(r"Do\s+Not\s+Travel\s+to:?\s*", re.IGNORECASE)),
    ("3", re.compile(r"Reconsider\s+Travel\s+to:?\s*", re.IGNORECASE)),
    ("2", re.compile(r"Exercise\s+Increased\s+Caution\s+(?:in|near|when)\s*", re.IGNORECASE)),
]


def _zinnen(tekst):
    uit = []
    for zin in zinnen(tekst):
        zin = KOPJE.sub("", zin.strip()).strip()
        if zin:
            uit.append(zin)
    return uit


def _datum(pubdate):
    """'Tue, 07 Jul 2026' -> '2026-07-07'."""
    schoon = re.sub(r"^[A-Za-z]{3},\s*", "", (pubdate or "").strip())
    for vorm in ("%d %b %Y", "%d %B %Y", "%d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(schoon[:len(datetime.now().strftime(vorm)) + 4]
                                     if False else schoon, vorm).date().isoformat()
        except ValueError:
            continue
    treffer = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", schoon)
    if treffer:
        try:
            return datetime.strptime(" ".join(treffer.groups()), "%d %b %Y").date().isoformat()
        except ValueError:
            pass
    return None


def haal_alles(register, alleen=None):
    gevraagd = {
        normaliseer(land["vs_naam"]): land["iso2"]
        for land in register
        if land.get("vs_naam") and (alleen is None or land["iso2"] in alleen)
    }
    resultaat = {}
    for ronde in range(RONDEN):
        _lees_ronde(RSS, gevraagd, resultaat)

    for iso2 in gevraagd.values():
        resultaat.setdefault(iso2, {
            "gelukt": False, "bron_url": None, "gewijzigd_op": None,
            "landniveau": None, "gebieden": [],
            "opmerking": "De Verenigde Staten noemden dit land in geen van de "
                         f"{RONDEN} ophaalrondes.",
        })
    return resultaat


def _lees_ronde(url, gevraagd, resultaat):
    """Vult aan wat deze ronde oplevert; een nieuwere datum wint."""
    xml = haal_tekst(url)
    for blok in re.findall(r"<item>(.*?)</item>", xml, re.S):
        titel = html.unescape(_veld(blok, "title"))
        treffer = NIVEAU_IN_TITEL.match(titel.strip())
        if not treffer:
            continue
        iso2 = gevraagd.get(normaliseer(treffer.group("land")))
        if not iso2:
            continue

        tekst = plat(_veld(blok, "description"))
        tekst = re.sub(r"\s+([.!?,;:])", r"\1", tekst)
        niveau = treffer.group("niveau")

        zinnen = _zinnen(tekst)
        landzin = next((z for z in zinnen if LANDZIN.match(z)), "")

        gewijzigd = _datum(_veld(blok, "pubDate"))
        bestaand = resultaat.get(iso2)
        if bestaand and (bestaand["gewijzigd_op"] or "") >= (gewijzigd or ""):
            continue

        resultaat[iso2] = {
            "gelukt": True,
            "bron_url": _veld(blok, "link").strip(),
            "gewijzigd_op": gewijzigd,
            "landniveau": {"label": niveau, "citaat": citaat(landzin or titel)},
            "gebieden": _gebieden(zinnen, overslaan=landzin),
            "opmerking": None,
        }


def _gebieden(zinnen, overslaan=""):
    """De gebieden die de VS apart noemt, zonder de zin over het hele land."""
    uit = []
    for zin in zinnen:
        if zin == overslaan:
            continue
        for niveau, patroon in GEBIEDSNIVEAUS:
            treffer = patroon.match(zin)
            if not treffer:
                continue
            omschrijving = zin[treffer.end():].strip()
            if omschrijving and len(omschrijving) > 3 and not VAAG.match(omschrijving):
                uit.append({
                    "label": niveau,
                    "gebied": citaat(omschrijving, 200),
                    "citaat": citaat(zin),
                })
            break
    return uit


def _veld(blok, naam):
    treffer = re.search(
        rf"<{naam}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{naam}>", blok, re.S)
    return treffer.group(1) if treffer else ""
