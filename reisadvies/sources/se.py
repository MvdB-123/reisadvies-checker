"""Zweden – UD:s lijst van avrådan op regeringen.se (officieel), met swedenabroad.se als achtergrond.

- Index: https://www.regeringen.se/ud-avrader/ ('Här listas länder där det finns en avrådan'):
  één link per land, '<Land> - avrådan' -> /ud-avrader/<slug>/. Staat een land er niet op, dan is
  er geen avrådan: dat is een officieel antwoord, geen ontbrekend gegeven.
- Land: de tekst tussen 'Publicerad <datum>' en 'Nivåer av avrådan', met de zinnen
  'avråder ... från alla resor till ...' en '... icke nödvändiga resor till ...', en
  'Beslut(et) om avrådan ... den <datum>'. 'Borttagen avrådan' / 'avråder inte längre' = opgeheven.
- Niveaus (UD zelf): icke nödvändiga resor (oranje), alla resor (rood), uppmaning att lämna landet
  (rood: alle reizen plus de oproep het land te verlaten).

swedenabroad.se toont dezelfde tekst, maar houdt geautomatiseerde verzoeken tegen met een
Cloudflare-controle; die omzeilen we niet. parse_swedenabroad() blijft voor als dat verandert.
"""

from __future__ import annotations

import html as htmllib
import re
from functools import lru_cache
from urllib.parse import urljoin

from .. import http
from ..countries import koppel, normaliseer
from ..mapping import niveau
from ..model import Advies, Gebied, Status
from .base import Bron, datum, soep, tekst

RG = "https://www.regeringen.se"
LIJST = RG + "/ud-avrader/"
BASIS = "https://www.swedenabroad.se"
START = (
    BASIS + "/sv/om-utlandet-f%C3%B6r-svenska-medborgare/turkiet/reseinformation/reseinformation-om-turkiet/"
)
WEB = LIJST

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


@lru_cache(maxsize=1)
def ud_index() -> dict[str, str]:
    """{'Turkiet': 'https://www.regeringen.se/ud-avrader/turkiet--avradan/', ...}"""
    s = soep(http.text(LIJST))
    out = {}
    for a in s.find_all("a", href=True):
        if re.match(r"^/ud-avrader/[^/]+/?$", a["href"]):
            land = re.split(r"\s+[-–]\s+", tekst(a), maxsplit=1)[0].strip()
            out[land] = urljoin(RG, a["href"])
            # 'Ryska Federationen (Ryssland)': beide namen
            for deel in re.findall(r"^(.*?)\s*\((.*?)\)", land):
                for n in deel:
                    out.setdefault(n.strip(), urljoin(RG, a["href"]))
    return out


def _sleutel(zin: str) -> str:
    """Het eerstgenoemde niveau in de zin; een later genoemd niveau is een uitzondering
    ('alla resor till Gaza samt till Västbanken, med undantag för ... icke nödvändiga resor')."""
    if re.search(r"uppmana\w*[^.]*lämna", zin, re.IGNORECASE):
        return "lamna"
    alla = re.search(r"från alla resor", zin, re.IGNORECASE)
    icke = re.search(r"från icke[ -]nödvändiga resor", zin, re.IGNORECASE)
    if alla and (not icke or alla.start() < icke.start()):
        return "alla"
    return "icke_nodvandiga" if icke else "alla"


def _heel_land(zin: str, iso: str) -> bool:
    """Gaat de zin over het hele land (of 'de rest' ervan)?

    'resor till Afghanistan.', 'resor till Ryska Federationen (Ryssland).', 'resor till övriga Israel.',
    'resor till övriga delar av Ukraina.', 'resor till hela landet.'
    """
    m = re.search(r"resor\s+(?:inom|till)\s+(.+?)\.?$", zin.strip())
    if not m:
        return False
    doel = re.sub(r"\s*\([^)]*\)", "", m.group(1)).strip()
    doel = re.sub(r"^(?:hela|övriga(?:\s+delar\s+av)?|resten\s+av)\s+", "", doel, flags=re.IGNORECASE)
    if normaliseer(doel) in ("landet", "lander"):
        return True
    namen = {doel, m.group(1)} | set(re.findall(r"\(([^)]*)\)", m.group(1)))
    return any(koppel(iso, "sv", {n: True}) for n in namen)


def parse_regeringen(html: str, iso: str, url: str) -> Advies:
    t = tekst(soep(html).find("main") or soep(html).body)
    adv = Advies("se", iso, Status.OK, url=url)
    m = re.search(r"Publicerad\s+(\d{1,2}\s+\w+\s+\d{4})", t)
    if m:
        adv.gewijzigd_op = datum(m.group(1))
        adv.gewijzigd_label = "Publicerad (UD, regeringen.se)"
    start = m.end() if m else 0
    eind = t.find("Nivåer av avrådan", start)
    return _uit_tekst(adv, t[start : eind if eind > 0 else None].strip(), iso)


def _uit_tekst(adv: Advies, blok_tekst: str, iso: str) -> Advies:
    # 'Föregående avrådan ...' beschrijft de vorige, vervallen avrådan: niet meenemen.
    blok_tekst = re.split(r"Föregående avrådan", blok_tekst, maxsplit=1)[0].strip()
    if not blok_tekst or re.search(r"borttagen avrådan|avråder inte längre", blok_tekst, re.IGNORECASE):
        adv.landelijk = niveau("se", "geen")
        adv.brontekst = blok_tekst or "Geen avrådan."
        return adv
    adv.brontekst = blok_tekst
    besluit = _BESLUT.search(blok_tekst)
    if besluit and (d := datum(besluit.group(0))):
        adv.gewijzigd_op = d
        adv.gewijzigd_label = "Besluit over avrådan"
    for zm in _ZIN.finditer(blok_tekst):
        zin = zm.group(0).strip()
        sl = _sleutel(zin)
        if _heel_land(zin, iso) or sl == "lamna":
            if adv.landelijk is None or sl in ("alla", "lamna"):
                adv.landelijk = niveau("se", sl)
        else:
            adv.gebieden.append(Gebied(zin, niveau("se", sl), brontekst=zin))
    if adv.landelijk is None:
        adv.landelijk = niveau("se", "geen")
        adv.landelijk.toelichting += " Er is wel een avrådan voor delen van het land (zie gebieden)."
    elif adv.landelijk.kleur:
        # zelfde kleur als het land is geen afwijking; mildere gebieden (West-Oekraïne) wél tonen
        adv.gebieden = [g for g in adv.gebieden if g.niveau.kleur != adv.landelijk.kleur]
    return adv


def parse(html: str, iso: str, url: str) -> Advies:
    """swedenabroad.se-landpagina (blok 'Avrådan')."""
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

    return _uit_tekst(adv, blok_tekst, iso)


GEBLOKKEERD = (
    "swedenabroad.se houdt geautomatiseerde verzoeken tegen met een Cloudflare-controle "
    "(HTTP 403). Die controle omzeilen we bewust niet. Handmatig nalopen via de link."
)


def ophalen(iso: str) -> Advies:
    url = koppel(iso, "sv", ud_index())
    if not url:
        # Niet op UD's lijst: officieel geen avrådan.
        adv = Advies("se", iso, Status.OK, url=LIJST, landelijk=niveau("se", "geen"))
        adv.brontekst = "Dit land staat niet op UD's lijst van landen met een avrådan."
        adv.gewijzigd_label = "lijst geraadpleegd"
        return adv
    return parse_regeringen(http.text(url), iso, url)


BRON = Bron("se", "Zweden", "🇸🇪", "sv", WEB, _ophalen=ophalen)
