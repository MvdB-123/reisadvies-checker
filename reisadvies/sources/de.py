"""Duitsland – Auswärtiges Amt Open Data (officieel, JSON).

- Index: /opendata/travelwarning -> per land countryCode (ISO), vlaggen
  warning / partialWarning / situationWarning / situationPartWarning, lastModified (epoch)
- Land:  /opendata/travelwarning/<id> -> idem + 'content' (HTML) en 'lastChanges'

De vlaggen bepalen het niveau. Bij een gedeeltelijke waarschuwing halen we de zinnen
waarin gewaarschuwd/afgeraden wordt letterlijk uit de content: de gebieden zelf staan
alleen in lopende tekst.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from functools import lru_cache

from .. import http
from ..mapping import niveau
from ..model import Advies, Gebied, Status
from .base import Bron, niet_gevonden, soep, tekst

API = "https://www.auswaertiges-amt.de/opendata/travelwarning"
WEB = "https://www.auswaertiges-amt.de/de/ReiseUndSicherheit/10.2.8Reisewarnungen"


@lru_cache(maxsize=1)
def index() -> dict[str, tuple[str, dict]]:
    data = http.json(API)["response"]
    return {v["countryCode"]: (k, v) for k, v in data.items() if isinstance(v, dict) and "countryCode" in v}


_WAARSCHUW = re.compile(
    r"[^.]*\b(?:wird (?:dringend )?gewarnt|wird (?:dringend )?abgeraten|Reisewarnung besteht|"
    r"Teilreisewarnung)\b[^.]*\.",
)


def _waarschuwzinnen(content_html: str) -> list[str]:
    """Zinnen met 'wird gewarnt/abgeraten' uit het eerste deel (vóór 'Sicherheit'-details)."""
    t = tekst(soep(content_html))
    zinnen = []
    for m in _WAARSCHUW.finditer(t[:6000]):
        z = m.group(0).strip()
        if "Beachten Sie" in z:  # verwijzing naar ándere landen
            continue
        if z not in zinnen:
            zinnen.append(z)
    return zinnen


def parse(id_: str, v: dict, iso: str) -> Advies:
    url = f"https://www.auswaertiges-amt.de/de/service/laender/{id_}"  # stuurt door naar de landpagina
    adv = Advies("de", iso, Status.OK, url=url)
    if v.get("lastModified"):
        adv.gewijzigd_op = datetime.fromtimestamp(v["lastModified"], UTC).date().isoformat()
        adv.gewijzigd_label = "lastModified (Auswärtiges Amt Open Data)"

    if v.get("warning"):
        adv.landelijk = niveau("de", "reisewarnung")
    elif v.get("situationWarning"):
        adv.landelijk = niveau("de", "abraten")
    else:
        adv.landelijk = niveau("de", "geen")

    if (v.get("partialWarning") or v.get("situationPartWarning")) and v.get("content"):
        sleutel = "teilreisewarnung" if v.get("partialWarning") else "teil_abraten"
        for z in _waarschuwzinnen(v["content"]):
            n = niveau("de", "teilreisewarnung" if "gewarnt" in z or "Reisewarnung" in z else "teil_abraten")
            adv.gebieden.append(Gebied(z, n, brontekst=z))
        if not adv.gebieden:
            adv.gebieden.append(
                Gebied("Zie brontekst (gebied niet automatisch herkend)", niveau("de", sleutel))
            )
    adv.brontekst = v.get("title", "")
    return adv


def ophalen(iso: str) -> Advies:
    rij = index().get(iso)
    if not rij:
        return niet_gevonden("de", iso, WEB)
    id_, v = rij
    if v.get("partialWarning") or v.get("situationPartWarning"):
        v = http.json(f"{API}/{id_}")["response"][id_]
    return parse(id_, v, iso)


BRON = Bron("de", "Duitsland", "🇩🇪", "de", WEB, _ophalen=ophalen)
