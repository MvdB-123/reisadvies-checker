"""Australië – smartraveller.gov.au (DFAT).

- Index: /destinations -> links /destinations/<regio>/<slug>
- Land:  'Overall: <niveau>' (.views-field-field-overall-advice-level)
         'Updated: <datum>' (.views-field-changed). Bewust niet 'Still current at': die verspringt
         ook bij een controle zonder inhoudelijke wijziging.
         Blok 'Advice levels': per .paragraph--type--advice-level het niveau (link #level1-4) en
         een letterlijke zin met gebied en reden. Het blok met het 'Overall'-niveau is het land.

Smartraveller weigert verzoeken uit datacenters; vanaf een kantoornetwerk werkt het wel.
"""

from __future__ import annotations

import re
from functools import lru_cache
from urllib.parse import urljoin

from .. import http
from ..countries import koppel
from ..mapping import niveau
from ..model import Advies, Gebied, Status
from .base import Bron, datum, niet_gevonden, soep, tekst

BASIS = "https://www.smartraveller.gov.au"
WEB = BASIS + "/destinations"


def _niveau_uit_tekst(t: str) -> str | None:
    l = t.lower()
    for woorden, n in (
        ("do not travel", "4"),
        ("reconsider your need to travel", "3"),
        ("high degree of caution", "2"),
        ("normal safety precautions", "1"),
    ):
        if woorden in l:
            return n
    return None


def parse(html: str, iso: str, url: str) -> Advies:
    s = soep(html)
    adv = Advies("au", iso, Status.OK, url=url)
    bijgewerkt = s.select_one(".views-field-changed .right")
    if bijgewerkt:
        adv.gewijzigd_op = datum(tekst(bijgewerkt))
        adv.gewijzigd_label = "Updated (Smartraveller)"

    overall = _niveau_uit_tekst(tekst(s.select_one(".views-field-field-overall-advice-level")))
    for p in s.select(".paragraph--type--advice-level"):
        a = p.select_one(".field--name-field-location a[href*='#level']")
        n = a["href"].rsplit("#level", 1)[-1] if a else _niveau_uit_tekst(tekst(p))
        zin = tekst(p.select_one(".field--name-field-description"))
        if n not in ("1", "2", "3", "4") or not zin:
            continue
        if adv.landelijk is None and n == overall:
            adv.landelijk = niveau("au", n)
            adv.brontekst = zin
        else:
            adv.gebieden.append(Gebied(zin, niveau("au", n), brontekst=zin))
    if adv.landelijk is None and overall:
        adv.landelijk = niveau("au", overall)
    if adv.landelijk is None:
        adv.melding = "Landelijk niveau niet herkend; zie bron."
    return adv


@lru_cache(maxsize=1)
def index() -> dict[str, str]:
    s = soep(http.text(WEB))
    out: dict[str, str] = {}
    for a in s.find_all("a", href=True):
        if re.search(r"/destinations/[a-z-]+/[a-z0-9-]+/?$", a["href"]) and tekst(a):
            out.setdefault(tekst(a), urljoin(BASIS, a["href"]))
    return out


GEBLOKKEERD = (
    "Australië laat ons programma niet bij de pagina: de website weigert geautomatiseerde verzoeken uit de "
    "cloud waar deze pagina elke ochtend wordt opgebouwd (dat is een andere computer dan de jouwe). "
    "Open de bron en lees het advies daar zelf."
)


_geblokkeerd = False  # na één weigering niet bij elk land opnieuw wachten


def ophalen(iso: str) -> Advies:
    global _geblokkeerd
    if _geblokkeerd:
        return Advies("au", iso, Status.HANDMATIG, url=WEB, melding=GEBLOKKEERD)
    try:
        url = koppel(iso, "en", index())
        if not url:
            return niet_gevonden("au", iso, WEB)
        return parse(http.text(url), iso, url)
    except http.OphaalFout as e:
        if e.status in (401, 403) or e.status is None or e.status >= 500:
            _geblokkeerd = True
            return Advies("au", iso, Status.HANDMATIG, url=WEB, melding=GEBLOKKEERD)
        raise


BRON = Bron("au", "Australië", "🇦🇺", "en", WEB, _ophalen=ophalen)
