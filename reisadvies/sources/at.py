"""Oostenrijk – bmeia.gv.at Reiseinformation.

- Index: /reise-services/laender-a-bis-z -> links /reise-services/reiseinformation/land/<slug>
- Land: 'Stand dd.mm.jjjj (Unverändert gültig seit: dd.mm.jjjj)', zijbalk
  'Sicherheitsstufe N' of 'Sicherheitsstufe N (regional)' (= hoogste regionale niveau),
  en een gekleurde kaart met per alinea '(Sicherheitsstufe N von 4) gilt ...'.
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

WEB = "https://www.bmeia.gv.at/reise-services/laender-a-bis-z"

# Formuleringen waarmee Oostenrijk aangeeft dat een niveau voor (de rest van) het land geldt.
_LANDELIJK = re.compile(
    r"Rest des Landes|(?:restlich|übrig)\w*\s+(?:Regionen|Landesteil\w*|Gebiet\w*|Land\w*|Teil\w*)"
    r"|gesamte\w*\s+(?:Land|Staatsgebiet)|ganze\w*\s+Land|landesweit",
    re.IGNORECASE,
)
# 'Sicherheitsstufe 4 von 4', '( Sicherheitsstufe 4 von 4)', 'Sicherheitsstufe 4 (von 4)' en
# '( Sicherheitsstufe 4 )'. Alleen binnen de gekleurde kaart gebruikt, niet in de zijbalk.
_STUFE = re.compile(r"Sicherheitsstufe\s*([1-4])\b", re.IGNORECASE)
# Een nieuw niveau begint met het label vóór 'Sicherheitsstufe'.
_SEGMENT = re.compile(
    r"(?<!Regionale )(?<!Partielle )(?<!Landesweite )(?<!Hohes )(?<!Erhöhtes )(?=(?:Regionale |Partielle |Landesweite )?(?:Reisewarnung|Hohes Sicherheitsrisiko|Sicherheitsrisiko"
    r"|Erhöhtes Sicherheitsrisiko|Guter Sicherheitsstandard)\s*\(?\s*Sicherheitsstufe)"
)


@lru_cache(maxsize=1)
def index() -> dict[str, str]:
    s = soep(http.text(WEB))
    out = {}
    for a in s.find_all("a", href=True):
        m = re.search(r"/reiseinformation/land/([^/?#]+)", a["href"])
        if m:
            u = urljoin(WEB, a["href"])
            out[m.group(1)] = u
            if tekst(a):
                out.setdefault(tekst(a), u)
    return out


def parse(html: str, iso: str, url: str) -> Advies:
    s = soep(html)
    adv = Advies("at", iso, Status.OK, url=url)
    m = re.search(r"Unverändert gültig seit:\s*([\d.]+)", html)
    if m:
        adv.gewijzigd_op = datum(m.group(1))
        adv.gewijzigd_label = "Unverändert gültig seit"

    kop_link = s.find("a", string=re.compile(r"Sicherheitsstufe"))
    kop = tekst(kop_link)
    km = re.search(r"Sicherheitsstufe\s*(\d)\s*(\(regional\))?", kop)

    kaart = s.select_one("div.card[class*=background-]")
    for segment in _SEGMENT.split(tekst(kaart)) if kaart else []:
        t = segment.strip()
        nm = _STUFE.search(t)
        if not nm:
            continue
        n = niveau("at", nm.group(1))
        if _LANDELIJK.search(t) and adv.landelijk is None:
            adv.landelijk = n
            adv.brontekst = t
        else:
            adv.gebieden.append(Gebied(t, n, brontekst=t))

    if adv.landelijk is None and km and not km.group(2):
        # Zonder '(regional)' geldt het niveau in de zijbalk voor het hele land.
        # Mét '(regional)' is het alleen het hoogste regionale niveau: dan nooit landelijk maken.
        adv.landelijk = niveau("at", km.group(1))
        adv.gebieden = [g for g in adv.gebieden if g.niveau.kleur != adv.landelijk.kleur]
    if not adv.brontekst:
        adv.brontekst = kop
    if adv.landelijk is None:
        adv.melding = "Niveau voor de rest van het land niet herkend; zie brontekst."
    return adv


def ophalen(iso: str) -> Advies:
    url = koppel(iso, "de", index())
    if not url:
        return niet_gevonden("at", iso, WEB)
    return parse(http.text(url), iso, url)


BRON = Bron("at", "Oostenrijk", "🇦🇹", "de", WEB, _ophalen=ophalen)
