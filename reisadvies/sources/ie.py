"""Ierland – ireland.ie (Department of Foreign Affairs).

- Index: /en/dfa/overseas-travel/advice/ -> één link per land: /en/dfa/overseas-travel/advice/<slug>/
- Land:  div.accordion_travel draagt het niveau als CSS-klasse en als koptekst
         (Normal Precautions / High Degree of Caution / Avoid Non-Essential Travel / Do Not Travel).
         'Updated on: <datum>' is de echte wijzigingsdatum; 'Still current at' verspringt ook
         zonder inhoudelijke wijziging en gebruiken we dus niet.
         De gebieden staan als zinnen onder 'Travel Alert' / 'General Travel Advice'.

ireland.ie weigert verzoeken uit datacenters (HTTP 403). Vanaf een kantoornetwerk werkt het wel;
vanuit de cloud tonen we 'handmatig nalopen' met link in plaats van een fout.
"""

from __future__ import annotations

import re
from dataclasses import replace
from functools import lru_cache
from urllib.parse import urljoin

from .. import http
from ..countries import koppel
from ..mapping import niveau
from ..model import Advies, Gebied, Soort, Status
from .base import Bron, datum, niet_gevonden, soep, tekst

BASIS = "https://www.ireland.ie"
WEB = BASIS + "/en/dfa/overseas-travel/advice/"

_KLASSEN = {
    "do-not-travel": "all",
    "avoid-non-essential-travel": "non_essential",
    "high-degree-of-caution": "high",
    "normal-precautions": "normal",
}
_KOPPEN = ("travel alert", "general travel advice")
_ADVIES = [
    (re.compile(r"advises? against all but essential travel\s+(?:to\s+)?(.+)", re.I), "non_essential", False),
    (re.compile(r"advises? against all travel\s+(?:to\s+)?(.+)", re.I), "all", False),
    # 'strongly advised not to travel to ...' is geen officieel niveau: rood, maar afgeleid.
    (re.compile(r"strongly advised not to travel\s+(?:to\s+)?(.+)", re.I), "all", True),
]
_RELEVANT = re.compile(r"advis|caution|do not travel|should leave", re.I)


def _sleutel_uit_tekst(t: str) -> str | None:
    l = t.lower()
    for woorden, sl in (
        ("do not travel", "all"),
        ("non-essential", "non_essential"),
        ("high degree of caution", "high"),
        ("normal precautions", "normal"),
    ):
        if woorden in l:
            return sl
    return None


def _landnamen(h1: str) -> list[str]:
    # 'Türkiye (Turkey)' -> ['Türkiye', 'Turkey']
    return [n.strip() for n in re.split(r"[()]", h1) if n.strip()]


def _blok(s) -> list[str]:
    """Alinea's en opsommingen onder 'Travel Alert' / 'General Travel Advice' in het overzicht."""
    rt = s.select_one("#answer-1 .rich-text") or s.select_one(".rich-text")
    if rt is None:
        return []
    uit, actief = [], False
    for el in rt.find_all(["h3", "p", "li"]):
        if el.name == "h3":
            actief = tekst(el).lower().rstrip(": ") in _KOPPEN
            continue
        if actief and not (el.name == "p" and el.find_parent("li")):
            t = tekst(el)
            if t:
                uit.append(t)
    return uit


def parse(html: str, iso: str, url: str) -> Advies:
    s = soep(html)
    adv = Advies("ie", iso, Status.OK, url=url)
    for el in s.select(".update-text"):
        m = re.search(r"Updated on:\s*(.+)", tekst(el))
        if m:
            adv.gewijzigd_op = datum(m.group(1))
            adv.gewijzigd_label = "Updated on (ireland.ie)"

    acc = s.select_one("div.accordion_travel")
    sl = None
    if acc is not None:
        sl = next((v for k, v in _KLASSEN.items() if k in acc.get("class", [])), None)
        sl = sl or _sleutel_uit_tekst(tekst(acc.select_one(".accordion_travel__header")))
    if sl:
        adv.landelijk = niveau("ie", sl)
    else:
        adv.melding = "Landelijk niveau niet herkend; zie bron."

    namen = _landnamen(tekst(s.find("h1")))
    regels = _blok(s)
    adv.brontekst = " ".join(r for r in regels if _RELEVANT.search(r))
    for regel in regels:
        for zin in re.split(r"(?<=\.)\s+", regel):
            for patroon, gsl, afgeleid in _ADVIES:
                m = patroon.search(zin)
                if not m:
                    continue
                wat = m.group(1).strip().rstrip(".")
                if any(re.match(rf"(?:the )?{re.escape(n)}(?![\w-])", wat, re.I) for n in namen):
                    break  # het hele land: dat is het landelijke niveau, geen gebied
                nv = niveau("ie", gsl)
                if afgeleid:
                    nv = replace(
                        nv,
                        soort=Soort.AFGELEID,
                        toelichting="Ierland schrijft 'strongly advised not to travel', geen officieel niveau.",
                    )
                if not (adv.landelijk and adv.landelijk.kleur == nv.kleur):
                    adv.gebieden.append(Gebied(wat, nv, brontekst=zin))
                break
    return adv


@lru_cache(maxsize=1)
def index() -> dict[str, str]:
    s = soep(http.text(WEB))
    out: dict[str, str] = {}
    for a in s.find_all("a", href=True):
        m = re.search(r"/en/dfa/overseas-travel/advice/([a-z0-9-]+)/?$", a["href"])
        naam = tekst(a)
        if m and naam:
            for n in _landnamen(naam):
                out.setdefault(n, urljoin(BASIS, a["href"]))
    return out


GEBLOKKEERD = (
    "ireland.ie weigert verzoeken uit datacenters (HTTP 403). Vanaf een kantoornetwerk werkt het wel. "
    "Handmatig nalopen via de link."
)


_geblokkeerd = False  # na één weigering niet bij elk land opnieuw wachten


def ophalen(iso: str) -> Advies:
    global _geblokkeerd
    if _geblokkeerd:
        return Advies("ie", iso, Status.HANDMATIG, url=WEB, melding=GEBLOKKEERD)
    try:
        url = koppel(iso, "en", index())
        if not url:
            return niet_gevonden("ie", iso, WEB)
        return parse(http.text(url), iso, url)
    except http.OphaalFout as e:
        if e.status in (401, 403) or e.status is None or e.status >= 500:
            _geblokkeerd = True
            return Advies("ie", iso, Status.HANDMATIG, url=WEB, melding=GEBLOKKEERD)
        raise


BRON = Bron("ie", "Ierland", "🇮🇪", "en", WEB, _ophalen=ophalen)
