"""Zweden – swedenabroad.se (UD:s reseinformation).

- Index: de landenkeuzelijst (<option class="dropdown-option-link" label="Turkiet" value=...>)
  op elke reseinformation-pagina. De doelpagina verschilt per land
  ('.../reseinformation/ambassadens-reseinformation/' of '.../reseinformation-om-turkiet/').
- Land: blok 'Avrådan' bovenaan (vrije tekst met 'avråder ... från alla resor till ...' en
  '... icke nödvändiga resor till ...'), plus 'Senast uppdaterad dd mmm. jjjj'.
  Geen blok = geen avrådan.

Zweden kent alleen 'avrådan' (oranje/rood). De gebieden staan in lopende tekst; we tonen per
zin met 'avråder' het niveau en de zin zelf, zonder het gebied verder te interpreteren.
"""

from __future__ import annotations

import html as htmllib
import re
from functools import lru_cache
from urllib.parse import urljoin

from .. import http
from ..countries import koppel, naam, normaliseer
from ..mapping import niveau
from ..model import Advies, Gebied, Status
from .base import Bron, datum, niet_gevonden, soep, tekst

BASIS = "https://www.swedenabroad.se"
START = (
    BASIS + "/sv/om-utlandet-f%C3%B6r-svenska-medborgare/turkiet/reseinformation/reseinformation-om-turkiet/"
)
WEB = "https://www.regeringen.se/uds-reseinformation/"

_ZIN = re.compile(r"[^.]*avråder[^.]*\.", re.IGNORECASE)
_BESLUT = re.compile(r"Beslut(?:et)? om avrådan[^.]*\.", re.IGNORECASE)


@lru_cache(maxsize=1)
def index() -> dict[str, str]:
    h = http.text(START)
    out = {}
    for m in re.finditer(
        r'<option class="dropdown-option-link" label="([^"]+)" lang="sv" value="([^"]+)"', h
    ):
        if "/om-utlandet-f" in m.group(2):
            out[htmllib.unescape(m.group(1))] = urljoin(BASIS, htmllib.unescape(m.group(2)))
    return out


def _sleutel(zin: str) -> str:
    return "icke_nodvandiga" if re.search(r"icke[ -]nödvändiga", zin, re.IGNORECASE) else "alla"


def _heel_land(zin: str, landnaam: str) -> bool:
    """'avråder från alla resor till Afghanistan.' of '... till övriga delar av Ukraina' -> True."""
    z = normaliseer(zin)
    n = normaliseer(landnaam)
    return (
        bool(re.search(rf"resor till {re.escape(n)}$", z))
        or "ovriga delar" in z
        or "hela landet" in z
        or bool(re.search(rf"resor till hela {re.escape(n)}", z))
    )


def parse(html: str, iso: str, url: str) -> Advies:
    s = soep(html)
    adv = Advies("se", iso, Status.OK, url=url)
    m = re.search(r"Senast uppdaterad\s*([^<,]+)", html)
    if m:
        adv.gewijzigd_op = datum(m.group(1).replace("\xa0", " "))
        adv.gewijzigd_label = "Senast uppdaterad (hele landpagina)"

    blok = s.select_one(".notice-block__wrapper--dissuasion .notice-block__content__body")
    blok_tekst = tekst(blok)
    if not blok_tekst:
        adv.landelijk = niveau("se", "geen")
        adv.brontekst = "Geen 'avrådan' op de pagina."
        return adv

    adv.brontekst = blok_tekst
    besluit = _BESLUT.search(blok_tekst)
    if besluit:
        d = datum(besluit.group(0))
        if d:
            pagina = adv.gewijzigd_op
            adv.gewijzigd_op = d
            adv.gewijzigd_label = "Besluit over avrådan" + (
                f" (pagina bijgewerkt {pagina})" if pagina else ""
            )

    landnaam = naam(iso, "sv")
    for zm in _ZIN.finditer(blok_tekst):
        zin = zm.group(0).strip()
        sl = _sleutel(zin)
        if _heel_land(zin, landnaam):
            if adv.landelijk is None or sl == "alla":
                adv.landelijk = niveau("se", sl)
        else:
            adv.gebieden.append(Gebied(zin, niveau("se", sl), brontekst=zin))
    if adv.landelijk is None:
        adv.landelijk = niveau("se", "geen")
        adv.landelijk.toelichting += " Er is wel een avrådan voor delen van het land (zie gebieden)."
    return adv


GEBLOKKEERD = (
    "swedenabroad.se houdt geautomatiseerde verzoeken tegen met een Cloudflare-controle "
    "(HTTP 403). Die controle omzeilen we bewust niet. Handmatig nalopen via de link."
)


def ophalen(iso: str) -> Advies:
    try:
        url = koppel(iso, "sv", index())
        if not url:
            return niet_gevonden("se", iso, WEB)
        return parse(http.text(url), iso, url)
    except http.OphaalFout as e:
        if e.status == 403:
            landurl = BASIS + "/sv/om-utlandet-f%C3%B6r-svenska-medborgare/"
            return Advies("se", iso, Status.HANDMATIG, url=landurl, melding=GEBLOKKEERD)
        raise


BRON = Bron("se", "Zweden", "🇸🇪", "sv", WEB, _ophalen=ophalen)
