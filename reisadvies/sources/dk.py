"""Denemarken – um.dk rejsevejledninger.

- Index: /rejse-og-ophold/rejse-til-udlandet/rejsevejledninger -> links per land (Deense slug)
- Land: 'Rejsevejledning opdateret: dd.mm.jjjj' en gekleurde balken
  (li.travel-guide-accordion__item) met titel ('Vær ekstra forsigtig:') en ondertitel
  (het gebied, bv. 'Hele landet, undtagen ...').
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

WEB = "https://um.dk/rejse-og-ophold/rejse-til-udlandet/rejsevejledninger"


# 'Hele landet, undtagen ...' of '... og resten af landet, undtagen ...'
_LANDELIJK = re.compile(
    r"\bhele landet\b|\bresten af landet\b|^hele (?:landets? )?[A-ZÆØÅ][\wæøåÆØÅ-]+(?:\s[A-ZÆØÅ][\wæøåÆØÅ-]+)?\s*(?:[,.]|$)",
    re.IGNORECASE,
)  # ook 'Hele Palæstina, undtagen Østjerusalem.' (naam van het land in plaats van 'landet')


def _sleutel(titel: str) -> str | None:
    t = titel.lower()
    if "ikke-nødvendige" in t or "ikke nødvendige" in t:
        return "ikke_noedvendige"
    if "fraråder alle rejser" in t:
        return "alle"
    if "ekstra forsigtig" in t:
        return "ekstra_forsigtig"
    if "opmærksom" in t:
        return "opmaerksom"
    return None


@lru_cache(maxsize=1)
def index() -> dict[str, str]:
    s = soep(http.text(WEB))
    out = {}
    # Landenkeuzelijst: <option value="Afghanistan" data-href="/.../rejsevejledninger/afghanistan/">
    for o in s.find_all("option", attrs={"data-href": True}):
        m = re.search(r"/rejsevejledninger/([^/]+)/?$", o["data-href"])
        if m:
            u = urljoin(WEB, o["data-href"])
            out[m.group(1)] = u
            out.setdefault(o.get("value") or tekst(o), u)
    return out


def parse(html: str, iso: str, url: str) -> Advies:
    s = soep(html)
    adv = Advies("dk", iso, Status.OK, url=url)
    m = re.search(r"Rejsevejledning opdateret:\s*([\d.]+)", html)
    if m:
        adv.gewijzigd_op = datum(m.group(1))
        adv.gewijzigd_label = "Rejsevejledning opdateret"

    balken = []
    for li in s.select("li.travel-guide-accordion__item"):
        titel = tekst(li.select_one(".travel-guide-accordion__title"))
        sub = tekst(li.select_one(".travel-guide-accordion__subtitle"))
        sl = _sleutel(titel)
        if sl:
            balken.append((sl, titel, sub, tekst(li.select_one(".content-rte"))))

    for sl, titel, sub, uitleg in balken:
        if _LANDELIJK.search(sub) or (len(balken) == 1 and not sub):
            adv.landelijk = niveau("dk", sl)
            adv.brontekst = f"{titel} {sub}".strip()
        else:
            adv.gebieden.append(Gebied(sub or titel, niveau("dk", sl), brontekst=uitleg))
    if adv.landelijk is None and not balken and re.search(r"vi har ingen rejsevejledning", html, re.IGNORECASE):
        adv.status = Status.NIET_GEVONDEN
        adv.melding = "Denemarken heeft voor dit land geen reisadvies. Op de Deense pagina staat letterlijk: "
        "'Vi har ingen rejsevejledning' (we hebben geen reisadvies). Het land staat er dus gewoon niet bij."
    elif adv.landelijk is None and adv.gebieden:
        adv.melding = (
            "Denemarken noemt alleen gebieden; er is geen balk voor 'hele landet'. "
            "Het niveau voor de rest van het land is daarom niet vastgesteld."
        )
    elif adv.landelijk is None:
        adv.melding = "Geen niveaubalken gevonden; landelijk niveau niet herkend."
    return adv


def ophalen(iso: str) -> Advies:
    url = koppel(iso, "da", index())
    if not url:
        return niet_gevonden("dk", iso, WEB)
    return parse(http.text(url), iso, url)


BRON = Bron("dk", "Denemarken", "🇩🇰", "da", WEB, _ophalen=ophalen)
