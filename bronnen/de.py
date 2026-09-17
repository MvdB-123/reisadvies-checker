"""Duitsland — Auswärtiges Amt.

Duitsland biedt zijn reisadviezen als open data aan. De lijst met alle landen kost
één verzoek; alleen voor landen met een waarschuwing halen we de volledige tekst op,
want alleen daar valt iets te citeren.
"""

import re
from datetime import datetime, timezone

from .gedeeld import (OphaalFout, citaat, haal_json, normaliseer, plat,
                      zinnen)

LIJST = "https://www.auswaertiges-amt.de/opendata/travelwarning"
DETAIL = "https://www.auswaertiges-amt.de/opendata/travelwarning/{id}"
PAGINA = "https://www.auswaertiges-amt.de/-/{id}"

# De operatieve formulering waarmee het Auswärtiges Amt waarschuwt. Bewust niet
# op het woord 'Reisewarnung' alleen: dat staat ook in verwijzingen als
# "Beachten Sie die Reisewarnung", en dat is geen uitspraak over een gebied.
WAARSCHUWING = re.compile(
    r"\bwird\s+(?:dringend\s+|derzeit\s+|generell\s+)?(?:gewarnt|abgeraten)\b",
    re.IGNORECASE,
)

# Dezelfde formulering gebruikt het Auswärtiges Amt ook voor waarschuwingen die
# niets met reizen te maken hebben ("Vor Erwerb, Besitz, Konsum von Rauschgiften
# wird dringend abgeraten"). De zin moet dus over reizen of verblijf gaan.
OVER_REIZEN = re.compile(
    r"\b(?:Vor|Von)\s+(?:\w+\s+){0,3}?"
    r"(?:Reisen|Aufenthalt(?:en)?|Fahrten|Besuchen|Überfahrten)\b",
    re.IGNORECASE,
)

# Kopjes lopen in de platte tekst door in de eerste zin eronder.
KOPJE = re.compile(
    r"^(?:Siehe\s+Aktuelles|Aktuelles|Sicherheit|Reisewarnung|Teilreisewarnung"
    r"|Reise- und Sicherheitshinweise)"
    r"(?:\s*[-–]\s*(?:Teilreisewarnung|Reisewarnung|Aktuelles))?\s+(?=[A-ZÄÖÜ])"
)


def _zonder_kopje(zin):
    vorige = None
    while zin != vorige:
        vorige = zin
        zin = KOPJE.sub("", zin).strip()
    return zin


# Het Auswärtiges Amt hanteert verschillende formuleringen die NIET hetzelfde
# niveau uitdrukken. 'Vor Reisen ... wird gewarnt' is de formele (Teil-)
# Reisewarnung; 'Von Reisen ... wird abgeraten' is lichter. Gemeten op
# 17-09-2026: van de 46 landen met een vlag gebruiken er 23 beide formuleringen
# naast elkaar, wat bevestigt dat ze naast elkaar bestaan en iets anders zeggen.
# Volgorde telt: de meest specifieke formulering eerst.
FORMULERINGEN = [
    ("gewarnt", re.compile(r"wird\s+\w*\s*gewarnt", re.IGNORECASE)),
    ("nicht_notwendige_reisen_abgeraten",
     re.compile(r"nicht\s+notwendigen?\s+Reisen[^.]*abgeraten", re.IGNORECASE)),
    ("dringend_abgeraten", re.compile(r"dringend\s+abgeraten", re.IGNORECASE)),
    ("abgeraten", re.compile(r"\babgeraten\b", re.IGNORECASE)),
]

# Waar de waarschuwing over gaat: het stuk tussen het reiswoord en 'wird'.
DOELWIT = re.compile(
    r"\b(?:Vor|Von)\s+(?:\w+\s+){0,3}?"
    r"(?:Reisen|Aufenthalt(?:en)?|Fahrten|Besuchen|Überfahrten)\s+"
    r"(?:nach|in|ins|in die|in das|in den|zu|zur|zum|auf|über)\s+(.+?)\s+wird\b",
    re.IGNORECASE)


def _formulering(zin):
    for naam, patroon in FORMULERINGEN:
        if patroon.search(zin):
            return naam
    return None


VOORUITWIJZEND = re.compile(r"^(?:die\s+)?folgenden?\b", re.IGNORECASE)

# 'Von Fahrten in Überlandbussen wird dringend abgeraten' gaat over vervoer en
# niet over een streek; 'in' betekent daar niet een bestemming. Zulke adviezen
# horen niet als gebied in het overzicht.
VERVOERMIDDEL = re.compile(
    r"(?:bussen|busse|zügen|züge|taxis|booten|boote|fähren|flügen|bahnen"
    r"|fahrzeugen|minibussen|sammeltaxis|nachtzügen)\b", re.IGNORECASE)


def _doelwit(zin):
    treffer = DOELWIT.search(zin)
    if not treffer:
        return ""
    doelwit = treffer.group(1).strip(" .,:;")
    # 'in folgende Regionen bzw. Gebiete wird gewarnt: in die Region des
    # Tschadsees, ...' — de opsomming erachter benoemt het gebied, niet het
    # vooruitwijzende woord ervoor.
    if VOORUITWIJZEND.match(doelwit) and ":" in zin:
        na_dubbelepunt = zin.split(":", 1)[1].strip(" .,;")
        if na_dubbelepunt:
            return na_dubbelepunt
    return doelwit


def _zinnen_met_waarschuwing(tekst, maximaal=3):
    """De letterlijke zinnen waarin Duitsland zegt waarvoor het waarschuwt."""
    gevonden = []
    for zin in zinnen(tekst):
        if not WAARSCHUWING.search(zin) or not OVER_REIZEN.search(zin):
            continue
        zin = re.sub(r"\s+([.!?,;:])", r"\1", _zonder_kopje(zin))
        if zin and zin not in gevonden:
            gevonden.append(zin)
        if len(gevonden) >= maximaal:
            break
    return gevonden


def haal_alles(register, alleen=None):
    """Geeft per ISO2-code wat Duitsland over dat land zegt."""
    gevraagd = {
        land["de_iso2"]: (land["iso2"], land["naam"])
        for land in register
        if land.get("de_iso2") and (alleen is None or land["iso2"] in alleen)
    }
    resultaat = {}

    antwoord = haal_json(LIJST).get("response", {})
    for sleutel, item in antwoord.items():
        if not isinstance(item, dict) or "countryCode" not in item:
            continue
        gevonden = gevraagd.get(item["countryCode"])
        if not gevonden:
            continue
        iso2, landsnaam = gevonden

        uit = {
            "gelukt": True,
            "bron_url": PAGINA.format(id=sleutel),
            "gewijzigd_op": _datum(item.get("lastModified")),
            "landniveau": None,
            "gebieden": [],
            "opmerking": None,
        }

        if not item.get("warning") and not item.get("partialWarning"):
            # Duitsland geeft alleen waarschuwingen. Geen waarschuwing is zelf
            # informatie, en hoort dus in het overzicht te staan.
            uit["landniveau"] = {"label": "geen_waarschuwing", "citaat": ""}
            resultaat[iso2] = uit
            continue

        try:
            tekst = plat(_detail(sleutel).get("content", ""))
            uitspraken = _uitspraken(tekst, landsnaam, item.get("countryName"))
        except OphaalFout:
            uitspraken = []

        for label, zin, doelwit, heel in uitspraken:
            if heel and not uit["landniveau"]:
                uit["landniveau"] = {"label": label, "citaat": citaat(zin)}
            elif not heel:
                uit["gebieden"].append({
                    "label": label,
                    "gebied": citaat(doelwit or zin, 200),
                    "citaat": citaat(zin),
                })

        if uit["gebieden"] and not uit["landniveau"]:
            uit["landniveau"] = {"label": "geen_waarschuwing", "citaat": ""}

        if not uit["landniveau"] and not uit["gebieden"]:
            uit["opmerking"] = (
                "Duitsland geeft een waarschuwing af, maar de bijbehorende tekst "
                "is niet herkend. Zie de bronpagina."
            )
        resultaat[iso2] = uit

    for iso2, _naam in gevraagd.values():
        resultaat.setdefault(iso2, {
            "gelukt": False, "bron_url": None, "gewijzigd_op": None,
            "landniveau": None, "gebieden": [],
            "opmerking": "Duitsland noemt dit land niet in zijn open data.",
        })
    return resultaat


def _uitspraken(tekst, landsnaam, duitse_naam):
    """Elke waarschuwingszin met zijn eigen formulering en doelgebied."""
    uit = []
    for zin in _zinnen_met_waarschuwing(tekst, maximaal=8):
        label = _formulering(zin)
        if not label:
            continue
        doelwit = _doelwit(zin)
        if not doelwit or VERVOERMIDDEL.search(doelwit):
            continue
        heel = _gaat_over_heel_land(doelwit, landsnaam, duitse_naam)
        if label == "gewarnt":
            label = "warning" if heel else "partialWarning"
        uit.append((label, zin, doelwit, heel))
    return uit


def _gaat_over_heel_land(doelwit, *namen):
    """Geldt de waarschuwing voor het hele land, of voor een gebied erbinnen?"""
    if not doelwit:
        return False
    doel = normaliseer(doelwit)
    for naam in namen:
        kort = normaliseer(naam or "")
        if kort and (doel == kort or (doel.startswith(kort)
                                      and len(doel) - len(kort) <= 12)):
            return True
    return False


def _detail(sleutel):
    gegevens = haal_json(DETAIL.format(id=sleutel))
    binnenin = gegevens.get("response", gegevens)
    return binnenin.get(sleutel, binnenin) or {}


def _datum(stempel):
    """Duitsland geeft een tijdstempel in seconden; wij willen alleen de datum."""
    if not stempel:
        return None
    return datetime.fromtimestamp(int(stempel), timezone.utc).date().isoformat()
