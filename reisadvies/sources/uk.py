"""Verenigd Koninkrijk – GOV.UK Content API (officieel, JSON).

- Index: /api/content/foreign-travel-advice -> links.children (naam, synoniemen, pad)
- Land:  /api/content/foreign-travel-advice/<slug>
  - details.alert_status: lijst met o.a. avoid_all_travel_to_whole_country,
    avoid_all_but_essential_travel_to_parts, ...
  - details.parts[slug=warnings-and-insurance].body: HTML met de gebieden onder de kopjes
    'Areas where FCDO advises against (all) travel' en '... all but essential travel'.
  - public_updated_at + details.change_description
"""

from __future__ import annotations

import re
from functools import lru_cache

from .. import http
from ..countries import koppel
from ..mapping import niveau
from ..model import Advies, Gebied, Status
from .base import Bron, niet_gevonden, soep, tekst

API = "https://www.gov.uk/api/content/foreign-travel-advice"
WEB = "https://www.gov.uk/foreign-travel-advice"


@lru_cache(maxsize=1)
def index() -> dict[str, str]:
    data = http.json(API)
    out: dict[str, str] = {}
    for c in data["links"]["children"]:
        land = c.get("details", {}).get("country", {})
        for n in [land.get("name", "")] + land.get("synonyms", []):
            if n:
                out[n] = c["api_url"]
    return out


# 'FCDO advises against all travel to Crimea.' / '... all but essential travel to parts of the south:'
_ADVIES = re.compile(
    r"advises against (all but essential|all) travel\s+(?:to|on|in|within|along|by)\b\s*(.*)", re.IGNORECASE
)


def _gebieden(body_html: str) -> list[Gebied]:
    """Gebieden uit de zinnen 'FCDO advises against all (but essential) travel to ...'.

    Het niveau komt uit de vaste formulering in de zin zelf, niet uit de kop: het VK zet de
    gebieden soms onder h3's per niveau, soms onder h2's per regio. De dichtstbijzijnde kop
    gaat mee als context; een lijst direct na de zin hoort bij het gebied.
    """
    s = soep(body_html)
    out: list[Gebied] = []
    kop = ""
    laatste: Gebied | None = None  # gebied waar een direct volgende lijst bij hoort
    vervolg: Gebied | None = None  # zin eindigde op ':' zonder lijst; de h3's eronder zijn deelgebieden
    vervolg_sleutel = ""
    uitleg_voor: list[Gebied] = []  # gebieden waar een volgende gewone alinea de uitleg van is
    # Alleen elementen op het hoogste niveau; <p> binnen <li> of een notitie-<div> overslaan.
    for el in s.find_all(["h2", "h3", "p", "ul"]):
        if el.name in ("p", "ul") and el.find_parent(["ul", "div"]) is not None:
            continue
        if el.name in ("h2", "h3"):
            uitleg_voor = []
            t = tekst(el).rstrip(": ")
            if el.name == "h3" and vervolg is not None:
                # 'All parts:' onder '... all but essential travel to the following regions:'
                laatste = Gebied(t, niveau("uk", vervolg_sleutel), brontekst=vervolg.brontekst)
                out.append(laatste)
                continue
            kop = "" if "advises against" in t.lower() else t
            laatste = vervolg = None
            continue
        if el.name == "ul":
            if laatste is not None:
                items = ", ".join(tekst(li) for li in el.find_all("li"))
                laatste.omschrijving = f"{laatste.omschrijving.rstrip(': ')}: {items}"
                if laatste is vervolg:
                    vervolg = None  # de dubbele punt is beantwoord door deze lijst
                laatste = None
            continue
        zin = tekst(el)
        m = _ADVIES.search(zin)
        if not m:
            # Een gewone alinea direct onder een adviesregel is de uitleg bij dat gebied
            # ('Heavy fighting along parts of the border ... took place in 2025.').
            if uitleg_voor and el.name == "p" and zin and not _BOILERPLATE.search(zin):
                for g in uitleg_voor:
                    if len(g.brontekst) < _UITLEG_MAX:
                        weg = " […]" if g.brontekst.endswith(":") else ""  # de lijst staat in de gebiedsnaam
                        g.brontekst = f"{g.brontekst}{weg} {zin}"
            continue
        sleutel = "avoid_non_essential" if "but essential" in m.group(1).lower() else "avoid_all"
        wat = m.group(2).strip().rstrip(".")
        omschrijving = f"{kop}: {wat}" if kop and kop.lower() not in wat.lower() else wat
        laatste = Gebied(omschrijving, niveau("uk", sleutel), brontekst=zin)
        out.append(laatste)
        uitleg_voor = [laatste]
        vervolg, vervolg_sleutel = (laatste, sleutel) if wat.endswith(":") else (None, "")
    # Een verwijzende zin zonder eigen lijst ('the following regions:') is zelf geen gebied.
    return [
        g
        for g in out
        if not (g.omschrijving.endswith(":") and any(h.brontekst == g.brontekst and h is not g for h in out))
    ]


def _is_rest(omschrijving: str, land: dict) -> bool:
    """'all other regions of Ukraine', 'the rest of Chad': het niveau voor de rest van het land.
    'the rest of the Savanes region' is een deelgebied: de landnaam moet er direct op volgen."""
    namen = "|".join(re.escape(n) for n in [land.get("name", "")] + land.get("synonyms", []) if n)
    if not namen:
        return False
    patroon = (
        r"^(?:[^:]*:\s*)?(?:all )?(?:(?:other|remaining) (?:regions|parts|areas) of|(?:the )?rest of) "
        rf"(?:the )?(?:{namen})(?![\w'’-])"
    )
    return bool(re.match(patroon, omschrijving, re.I))

_UITLEG_MAX = 500  # tekens: genoeg voor de reden, zonder het overzicht vol te laten lopen
_BOILERPLATE = re.compile(r"travel insurance could be invalidated|^Find out more|^Read all the advice|^No travel can be guaranteed", re.I)
_STOP_KOPPEN = re.compile(r"^(Support from the UK government|Before you travel|Travel insurance)", re.I)


def _kern(body_html: str) -> str:
    """Letterlijke openingsalinea's van 'Warnings and insurance': het advies en de reden, zonder
    de vaste zinnen over verzekering en doorverwijzingen. Stopt bij de algemene kopjes."""
    s = soep(body_html)
    delen: list[str] = []
    for el in s.find_all(["h2", "p"]):
        if el.find_parent(["ul", "div"]) is not None:
            continue
        t = tekst(el)
        if el.name == "h2":
            if _STOP_KOPPEN.search(t) and delen:
                break
            continue
        if t and not _BOILERPLATE.search(t):
            # De lijst na een ':' staat bij de gebieden; hier markeren we de weglating als citaat.
            delen.append(t + " […]" if t.endswith(":") else t)
        if sum(len(d) for d in delen) > 600:
            break
    return " ".join(delen)


def parse(data: dict, iso: str) -> Advies:
    det = data["details"]
    url = data.get("web_url") or WEB + "/" + data["base_path"].rsplit("/", 1)[-1]
    adv = Advies("uk", iso, Status.OK, url=url)
    adv.gewijzigd_op = (data.get("public_updated_at") or "")[:10] or None
    wijziging = det.get("change_description", "")
    adv.gewijzigd_label = "Laatst bijgewerkt (GOV.UK)" + (f": {wijziging}" if wijziging else "")

    status = set(det.get("alert_status") or [])
    if "avoid_all_travel_to_whole_country" in status:
        adv.landelijk = niveau("uk", "avoid_all")
    elif "avoid_all_but_essential_travel_to_whole_country" in status:
        adv.landelijk = niveau("uk", "avoid_non_essential")
    else:
        adv.landelijk = niveau("uk", "geen")

    deel = next((p for p in det.get("parts", []) if p.get("slug") == "warnings-and-insurance"), None)
    # Zonder alert_status is 'Warnings and insurance' alleen algemene tekst (verzekering e.d.).
    adv.brontekst = _kern(deel.get("body", "")) if deel and det.get("alert_status") else ""
    if deel and ("_to_parts" in " ".join(status)):
        adv.gebieden = _gebieden(deel.get("body", ""))
        # 'all other regions of Ukraine' is het niveau voor de rest van het land, geen deelgebied.
        rest = next((g for g in adv.gebieden if _is_rest(g.omschrijving, det.get("country", {}))), None)
        if rest is not None and adv.landelijk.kleur is None:
            adv.landelijk = rest.niveau
            adv.landelijk.toelichting = (
                f"Het VK noemt dit niveau voor '{rest.omschrijving}'. De uitzonderingen staan bij de gebieden."
            )
            adv.gebieden = [g for g in adv.gebieden if g is not rest]
        if not adv.gebieden:
            adv.melding = "Het VK waarschuwt voor delen van het land, maar de gebieden zijn niet automatisch herkend; zie de bron."
    return adv


def ophalen(iso: str) -> Advies:
    api = koppel(iso, "en", index())
    if not api:
        return niet_gevonden("uk", iso, WEB)
    return parse(http.json(api), iso)


BRON = Bron("uk", "Verenigd Koninkrijk", "🇬🇧", "en", WEB, _ophalen=ophalen)
