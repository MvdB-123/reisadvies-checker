"""Canada – travel.gc.ca.

- Index: /travelling/advisories -> tabel Destination | Risk level | Last updated
- Land:  /destinations/<slug> -> div.AdvisoryContainer per niveau; 'RegionalAdv' = gebied.
  Kop: '<gebied> - <niveau>'. Het niveau herkennen we aan de vaste formulering.
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

WEB = "https://travel.gc.ca/travelling/advisories"


def _sleutel(label: str) -> str | None:
    l = label.lower()
    if "avoid all travel" in l:
        return "all"
    if "non-essential" in l:
        return "non_essential"
    if "high degree of caution" in l:
        return "high"
    if "normal security precautions" in l:
        return "normal"
    return None


@lru_cache(maxsize=1)
def index() -> dict[str, tuple[str, str]]:
    s = soep(http.text(WEB))
    out: dict[str, tuple[str, str]] = {}
    for tr in s.select("table tr"):
        tds = tr.find_all("td")
        a = tr.find("a", href=True)
        if len(tds) >= 3 and a:
            out[tekst(tds[0])] = (urljoin(WEB, a["href"]), tekst(tds[2]))
    return out


def parse(html: str, iso: str, url: str, bijgewerkt: str = "") -> Advies:
    s = soep(html)
    adv = Advies("ca", iso, Status.OK, url=url)
    d = datum(bijgewerkt) if bijgewerkt else None
    if not d:
        m = re.search(r"Last updated:\s*</[^>]+>\s*(?:<[^>]+>\s*)*([^<]+)", html)
        d = datum(m.group(1)) if m else None
    adv.gewijzigd_op = d
    adv.gewijzigd_label = "Last updated (travel.gc.ca)"

    for div in s.select("div.AdvisoryContainer"):
        kop = tekst(div.find(["h2", "h3", "h4"]))
        gebied, _, label = kop.rpartition(" - ")
        sl = _sleutel(label or kop)
        if not sl:
            continue
        uitleg = tekst(div.find("p"))
        if "RegionalAdv" in div.get("class", []):
            if not gebied or gebied.lower() == "regional advisory":
                gebied = uitleg  # geen gebiedsnaam in de kop: de uitleg noemt het gebied
            adv.gebieden.append(Gebied(gebied, niveau("ca", sl), brontekst=uitleg))
        elif adv.landelijk is None:
            adv.landelijk = niveau("ca", sl)
            adv.brontekst = uitleg
    if adv.landelijk is None:
        adv.melding = "Landelijk niveau niet herkend; zie bron."
    return adv


def ophalen(iso: str) -> Advies:
    rij = koppel(iso, "en", index())
    if not rij:
        return niet_gevonden("ca", iso, WEB)
    url, bijgewerkt = rij
    return parse(http.text(url), iso, url, bijgewerkt)


BRON = Bron("ca", "Canada", "🇨🇦", "en", WEB, _ophalen=ophalen)
