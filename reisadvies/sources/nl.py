"""Nederland – nederlandwereldwijd.nl (referentie).

Landen-slugs uit de sitemap /reisadvies/sitemap.xml. Per landpagina:
- 'Laatst gewijzigd op: dd-mm-jjjj'
- 'In het kort': o.a. 'De kleurcode van het reisadvies voor X is rood' of
  'Voor de rest van X geldt kleurcode geel'
- accordeon 'Regionale risico's': per kleur een kop (h4 'Rood: niet reizen') en een lijst
  'Voor de volgende gebieden geldt kleurcode rood:'.

Er bestaat ook een open-data-API (opendata.nederlandwereldwijd.nl), maar die host staat
(nog) niet in de netwerkregels van de omgeving. Zie OPEN_VRAGEN.md.
"""

from __future__ import annotations

import re
from functools import lru_cache

from .. import http
from ..countries import koppel
from ..mapping import niveau
from ..model import Advies, Gebied, Status
from .base import Bron, datum, niet_gevonden, soep, tekst

BASIS = "https://www.nederlandwereldwijd.nl/reisadvies/"
KLEUREN = ("groen", "geel", "oranje", "rood")


@lru_cache(maxsize=1)
def index() -> dict[str, str]:
    xml = http.text(BASIS + "sitemap.xml")
    urls = re.findall(r"<loc>(https://www\.nederlandwereldwijd\.nl/reisadvies/[^<]+)</loc>", xml)
    return {u.rstrip("/").rsplit("/", 1)[-1]: u for u in urls}


def parse(html: str, iso: str, url: str) -> Advies:
    s = soep(html)
    adv = Advies("nl", iso, Status.OK, url=url)

    m = re.search(r"Laatst gewijzigd op:\s*([\d-]+)", html)
    if m:
        adv.gewijzigd_op = datum(m.group(1))
        adv.gewijzigd_label = "Laatst gewijzigd op"

    kort = s.find(lambda t: t.name == "h2" and tekst(t) == "In het kort")
    kort_tekst = ""
    if kort:
        delen = []
        for sib in kort.find_next_siblings():
            if sib.name == "h2":
                break
            delen.append(tekst(sib))
        kort_tekst = " ".join(delen)
    adv.brontekst = kort_tekst

    # Gebieden per kleur uit 'Regionale risico's'
    for h4 in s.find_all("h4"):
        kop = tekst(h4).lower()
        kleur = next((k for k in KLEUREN if kop.startswith(k)), None)
        if not kleur:
            continue
        for sib in h4.find_next_siblings():
            if sib.name == "h4":
                break
            if sib.name == "ul":
                for li in sib.find_all("li"):
                    adv.gebieden.append(Gebied(tekst(li), niveau("nl", kleur)))

    # Landelijk niveau (voor de rest van het land)
    zoektekst = kort_tekst or tekst(s)
    m = re.search(
        r"rest van [^.]*?(?:geldt kleurcode|kleurcode (?:van|voor) het reisadvies[^.]*? is|is)\s+"
        r"(groen|geel|oranje|rood)",
        zoektekst,
    )
    if not m:
        m = re.search(
            r"kleurcode (?:van|voor) het reisadvies (?:voor|van) [^.]*? is (groen|geel|oranje|rood)",
            zoektekst,
        )
    if not m and not adv.gebieden:
        m = re.search(r"kleurcode (groen|geel|oranje|rood)", zoektekst)
    if m:
        adv.landelijk = niveau("nl", m.group(1))
    else:
        adv.melding = "Landelijk niveau niet automatisch herkend; zie brontekst."
    return adv


def ophalen(iso: str) -> Advies:
    url = koppel(iso, "nl", index())
    if not url:
        return niet_gevonden("nl", iso, BASIS)
    return parse(http.text(url), iso, url)


BRON = Bron("nl", "Nederland", "🇳🇱", "nl", BASIS, _ophalen=ophalen)
