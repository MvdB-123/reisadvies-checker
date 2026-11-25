"""Nederland – nederlandwereldwijd.nl (referentie).

Landen-slugs uit de sitemap /reisadvies/sitemap.xml. Per landpagina:
- 'Laatst gewijzigd op: dd-mm-jjjj'
- 'In het kort': o.a. 'De kleurcode van het reisadvies voor X is rood' of
  'Voor de rest van X geldt kleurcode geel'
- accordeon 'Regionale risico's': per kleur een kop (h4 'Rood: niet reizen') en een lijst
  'Voor de volgende gebieden geldt kleurcode rood:'.

Primair halen we de gegevens uit de officiële open-data-API (CC0):
  /v2/sources/nederlandwereldwijd/infotypes/traveladvice?output=json&rows=200&offset=N  (alle landen,
  met ISO3-code), en per land 'dataurl' + '?output=json': 'introduction' (In het kort, HTML),
  'modificationdate' ('Laatst gewijzigd op: ...') en 'content[].contentblocks[]' (dezelfde HTML-blokken
  als de website, waaronder 'Regionale risico's'). Lukt de API niet, dan lezen we de webpagina.
"""

from __future__ import annotations

import re
from dataclasses import replace
from functools import lru_cache

from .. import http
from ..countries import koppel
from ..mapping import niveau
from ..model import Advies, Gebied, Soort, Status
from .base import Bron, datum, niet_gevonden, soep, tekst

BASIS = "https://www.nederlandwereldwijd.nl/reisadvies/"
KLEUREN = ("groen", "geel", "oranje", "rood")
# 'Voor de volgende gebieden/vulkanen/grensgebieden ... geldt kleurcode rood:' en 'Kleurcode rood geldt voor:'
_GEBIEDEN_ZIN = re.compile(
    r"^(?:voor de volgende [^:]*? geldt (?:de )?kleurcode (groen|geel|oranje|rood)"
    r"|kleurcode (groen|geel|oranje|rood) geldt voor)\s*:\s*$",
    re.IGNORECASE,
)


# 'In het kort': 'De kleurcode van het reisadvies is rood voor de strook van 5 kilometer ...' en
# 'Kleurcode oranje geldt voor de strook van 5 tot 20 kilometer ...'. Niet: 'Voor de rest van ...'.
_KORT_GEBIED = re.compile(
    r"^(?:de )?kleurcode (?:van (?:het|dit) reisadvies )?(?:is (groen|geel|oranje|rood) voor|(groen|geel|oranje|rood) geldt voor)"
    r"\s+(?!de rest\b|het hele\b|heel\b)([^.]+)\.",
    re.IGNORECASE,
)
# 'Voor de Koerdistan Regio Irak en de zuidelijke provincies geldt grotendeels kleurcode oranje.'
_KORT_GEBIED_2 = re.compile(
    r"\bvoor (?!de rest\b|het hele\b|heel\b)([^.]+?) geldt (?:grotendeels |deels )?kleurcode (groen|geel|oranje|rood)\b",
    re.IGNORECASE,
)


API = "https://opendata.nederlandwereldwijd.nl/v2/sources/nederlandwereldwijd/infotypes/traveladvice"
_ISO3_UITZONDERINGEN = {"XKX": "XK", "KOS": "XK", "BQ-BO": "BQ-BO", "BQ-SE": "BQ-SE", "BQ-SA": "BQ-SA"}


@lru_cache(maxsize=1)
def api_index() -> dict[str, dict]:
    """{ISO2: lijstregel uit de API}."""
    from babel.core import get_global

    alias = get_global("territory_aliases")
    out: dict[str, dict] = {}
    offset = 0
    while True:
        rijen = http.json(f"{API}?output=json&rows=200&offset={offset}")
        for r in rijen:
            iso3 = (r.get("isocode") or "").upper()
            iso2 = _ISO3_UITZONDERINGEN.get(iso3) or (alias.get(iso3) or [None])[0]
            if iso2:
                out.setdefault(iso2, r)
        if len(rijen) < 200:
            return out
        offset += 200


def api_html(data: dict) -> str:
    """Zet de API-velden om naar dezelfde HTML-structuur als de webpagina, voor parse()."""
    delen = [f"<p>{data.get('modificationdate', '')}</p>", data.get("introduction", "")]
    for cat in data.get("content", []):
        delen.append(f"<h2>{cat.get('category', '')}</h2>")
        for blok in cat.get("contentblocks", []):
            delen.append(f"<h3>{blok.get('paragraphtitle', '')}</h3>{blok.get('paragraph', '')}")
    return "\n".join(delen)


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

    # Gebieden: alleen de lijst direct na een vaste zin ('Voor de volgende gebieden geldt kleurcode
    # rood:' / 'Kleurcode rood geldt voor:'). Die zin staat in een <p> met de lijst erna, of als
    # lijstitem met een sublijst. Andere lijsten (tips, voorbeelden) tellen niet als gebied.
    for el in s.find_all(["p", "li"]):
        if el.name == "p":
            zin, lijst = tekst(el), el.find_next_sibling()
        elif (lijst := el.find("ul")) is not None:
            zin = tekst(el)[: len(tekst(el)) - len(tekst(lijst))].strip()
        else:
            zin, lijst = tekst(el), None  # de zin als eerste item; de gebieden zijn de items erna
        m = _GEBIEDEN_ZIN.search(zin)
        if not m:
            continue
        kleur = (m.group(1) or m.group(2)).lower()
        if lijst is not None and lijst.name == "ul":
            items = lijst.find_all("li", recursive=False)
        elif el.name == "li":
            items = el.find_next_siblings("li")
        else:
            items = []
        for li in items:
            adv.gebieden.append(Gebied(tekst(li), niveau("nl", kleur)))

    # Gebieden die alleen in 'In het kort' staan (bijvoorbeeld Cambodja: een strook langs de grens),
    # voor kleuren die nog niet uit een lijst onder 'Regionale risico's' kwamen.
    al = {g.niveau.kleur for g in adv.gebieden}
    if kort:
        for el in kort.find_all_next("li"):
            if el.find_previous("h2") is not kort:
                break
            zin = tekst(el)
            if m := _KORT_GEBIED.search(zin):
                kleur, gebied = (m.group(1) or m.group(2)).lower(), m.group(3)
            elif m := _KORT_GEBIED_2.search(zin):
                kleur, gebied = m.group(2).lower(), m.group(1)
            else:
                continue
            nv = niveau("nl", kleur)
            if nv.kleur not in al:
                adv.gebieden.append(Gebied(gebied.strip(), nv, brontekst=zin))

    # Landelijk niveau (voor de rest van het land)
    zoektekst = kort_tekst or tekst(s)
    m = re.search(
        r"rest van [^.]*?(?:geldt kleurcode|kleurcode (?:van|voor) het reisadvies[^.]*? is|is)\s+"
        r"(groen|geel|oranje|rood)",
        zoektekst,
    )
    if not m:
        m = re.search(
            r"kleurcode (?:van|voor) het reisadvies (?:voor|van) [^.]*? is (?:voor het grootste deel )?(groen|geel|oranje|rood)",
            zoektekst,
        )
    if not m and not adv.gebieden:
        m = re.search(r"kleurcode (groen|geel|oranje|rood)", zoektekst)
    if m:
        adv.landelijk = niveau("nl", m.group(1))
        # Gebieden met dezelfde kleur als het land zijn geen afwijking.
        adv.gebieden = [g for g in adv.gebieden if g.niveau.kleur != adv.landelijk.kleur]
    elif adv.gebieden:
        # Geen kleur voor 'de rest van het land' (bijvoorbeeld Irak: rood voor grote delen, oranje voor
        # Koerdistan en het zuiden). Dan de laagste genoemde kleur als landelijk niveau, als afgeleid.
        laagste = min(adv.gebieden, key=lambda g: g.niveau.kleur.ernst).niveau.kleur
        adv.landelijk = replace(
            niveau("nl", laagste.value),
            soort=Soort.AFGELEID,
            toelichting="Het Nederlandse advies noemt geen kleur voor de rest van het land; aangenomen is "
            "de laagste genoemde kleur. Zie de kaart bij de bron.",
        )
        adv.gebieden = [g for g in adv.gebieden if g.niveau.kleur != laagste]
    else:
        adv.melding = "Landelijk niveau niet automatisch herkend; zie brontekst."
    return adv


def ophalen(iso: str) -> Advies:
    try:
        rij = api_index().get(iso)
        if rij:
            data = http.json(rij["dataurl"] + "?output=json")
            adv = parse(api_html(data), iso, data.get("canonical") or rij.get("canonical") or BASIS)
            adv.gewijzigd_label += " (open-data-API)"
            return adv
    except http.OphaalFout:
        pass  # terugvallen op de webpagina
    url = koppel(iso, "nl", index())
    if not url:
        return niet_gevonden("nl", iso, BASIS)
    return parse(http.text(url), iso, url)


BRON = Bron("nl", "Nederland", "🇳🇱", "nl", BASIS, _ophalen=ophalen)
