"""Verenigde Staten – travel.state.gov RSS-feed (officieel, alle landen in één keer).

Per <item>: titel 'Land - Level N: ...', categorie Threat-Level, Country-Tag (LET OP: dat is
een FIPS-code, geen ISO: 'AU' = Oostenrijk, 'GM' = Duitsland; we koppelen daarom op naam),
pubDate, en de volledige onderbouwing in <description> (HTML).

De gewone landenpagina's weigeren geautomatiseerd ophalen; de feed niet.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from functools import lru_cache

from .. import http
from ..countries import koppel
from ..mapping import niveau
from ..model import Advies, Gebied, Status
from .base import Bron, datum, niet_gevonden, soep, tekst

FEED = "https://travel.state.gov/_res/rss/TAsTWs.xml"
WEB = "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html"

_GEBIED = re.compile(
    r"^(Do not travel|Reconsider travel|Exercise increased caution)\s+(?:to|in)\s+(.+?)(?:\s+due to\b.*)?\.?$",
    re.IGNORECASE,
)
_NIVEAU_VAN_ZIN = {"do not travel": "4", "reconsider travel": "3", "exercise increased caution": "2"}
# De feed laat het werkwoord soms weg ('in Cambodia due to crime'); wij vullen het zichtbaar aan.
_ZINSBEGIN = {"1": "Exercise normal precautions", "2": "Exercise increased caution", "3": "Reconsider travel", "4": "Do not travel"}


def _naam(titel: str) -> str:
    return re.sub(r"\s+Travel Advisory$", "", titel.split(" - Level")[0]).strip()


@lru_cache(maxsize=1)
def index() -> dict[str, ET.Element]:
    root = ET.fromstring(http.get(FEED).content)
    return {_naam(it.findtext("title", "")): it for it in root.iter("item")}


def parse(item: ET.Element, iso: str) -> Advies:
    adv = Advies("us", iso, Status.OK, url=item.findtext("link") or WEB)
    pub = item.findtext("pubDate")
    if pub:
        try:
            adv.gewijzigd_op = parsedate_to_datetime(pub).date().isoformat()
        except (TypeError, ValueError):
            # de feed laat de tijd weg: 'Fri, 28 Aug 2026'
            adv.gewijzigd_op = datum(pub)
        adv.gewijzigd_label = "pubDate (State Department-feed)"

    niveau_txt = next(
        (c.text or "" for c in item.findall("category") if c.get("domain") == "Threat-Level"),
        item.findtext("title", ""),
    )
    m = re.search(r"Level (\d)", niveau_txt)
    landelijk_sleutel = m.group(1) if m else None
    if m:
        adv.landelijk = niveau("us", m.group(1))
    else:
        adv.melding = f"Niveau niet herkend in '{niveau_txt}'."

    s = soep(item.findtext("description", ""))
    eerste = s.find("p")
    adv.brontekst = tekst(eerste) if eerste else ""
    if re.match(r"(?:in|to)\b", adv.brontekst) and landelijk_sleutel in _ZINSBEGIN:
        adv.brontekst = f"[{_ZINSBEGIN[landelijk_sleutel]}] {adv.brontekst}"  # [ ] = aanvulling van ons
    for el in s.find_all(["p", "li"]):
        if el is eerste:
            continue
        zin = tekst(el)
        g = _GEBIED.match(zin)
        if g and g.group(2).lower() not in ("the country", "this country"):
            sleutel = _NIVEAU_VAN_ZIN[g.group(1).lower()]
            if sleutel == landelijk_sleutel:
                continue  # zelfde niveau als landelijk: geen afwijking
            adv.gebieden.append(Gebied(g.group(2).strip(), niveau("us", sleutel), brontekst=zin))
    if not adv.gebieden and "some areas have increased risk" in adv.brontekst.lower():
        adv.melding = (
            "De VS melden dat sommige gebieden een hoger risico hebben, maar de feed noemt ze "
            "niet. Zie de volledige pagina via de link."
        )
    return adv


def ophalen(iso: str) -> Advies:
    item = koppel(iso, "en", index())
    if item is None:
        return niet_gevonden("us", iso, WEB)
    return parse(item, iso)


BRON = Bron("us", "Verenigde Staten", "🇺🇸", "en", WEB, _ophalen=ophalen)
