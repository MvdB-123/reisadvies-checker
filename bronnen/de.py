"""Duitsland — Auswärtiges Amt.

Duitsland biedt zijn reisadviezen als open data aan. De lijst met alle landen kost
één verzoek; alleen voor landen met een waarschuwing halen we de volledige tekst op,
want alleen daar valt iets te citeren.
"""

import re
from datetime import datetime, timezone

from .gedeeld import OphaalFout, citaat, haal_json, plat, zinnen

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
        land["de_iso2"]: land["iso2"]
        for land in register
        if land.get("de_iso2") and (alleen is None or land["iso2"] in alleen)
    }
    resultaat = {}

    antwoord = haal_json(LIJST).get("response", {})
    for sleutel, item in antwoord.items():
        if not isinstance(item, dict) or "countryCode" not in item:
            continue
        iso2 = gevraagd.get(item["countryCode"])
        if not iso2:
            continue

        heeft_warning = bool(item.get("warning"))
        heeft_partial = bool(item.get("partialWarning"))
        uit = {
            "gelukt": True,
            "bron_url": PAGINA.format(id=sleutel),
            "gewijzigd_op": _datum(item.get("lastModified")),
            "landniveau": None,
            "gebieden": [],
            "opmerking": None,
        }

        if not heeft_warning and not heeft_partial:
            uit["opmerking"] = (
                "Duitsland heeft voor dit land geen reiswaarschuwing afgegeven."
            )
            resultaat[iso2] = uit
            continue

        try:
            tekst = plat(_detail(sleutel).get("content", ""))
            waarschuwingen = _zinnen_met_waarschuwing(tekst)
        except OphaalFout:
            waarschuwingen = []

        if heeft_warning:
            uit["landniveau"] = {
                "label": "warning",
                "citaat": citaat(waarschuwingen[0]) if waarschuwingen else "",
            }
        if heeft_partial:
            for zin in waarschuwingen or [""]:
                uit["gebieden"].append({
                    "label": "partialWarning",
                    "gebied": citaat(zin, 200) if zin else "Zie de bronpagina",
                    "citaat": citaat(zin) if zin else "",
                })
        resultaat[iso2] = uit

    for iso2 in gevraagd.values():
        resultaat.setdefault(iso2, {
            "gelukt": False, "bron_url": None, "gewijzigd_op": None,
            "landniveau": None, "gebieden": [],
            "opmerking": "Duitsland noemt dit land niet in zijn open data.",
        })
    return resultaat


def _detail(sleutel):
    gegevens = haal_json(DETAIL.format(id=sleutel))
    binnenin = gegevens.get("response", gegevens)
    return binnenin.get(sleutel, binnenin) or {}


def _datum(stempel):
    """Duitsland geeft een tijdstempel in seconden; wij willen alleen de datum."""
    if not stempel:
        return None
    return datetime.fromtimestamp(int(stempel), timezone.utc).date().isoformat()
