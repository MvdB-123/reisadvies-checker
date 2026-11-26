"""Duitsland – Auswärtiges Amt Open Data (officieel, JSON).

- Index: /opendata/travelwarning -> per land countryCode (ISO), vlaggen
  warning / partialWarning / situationWarning / situationPartWarning, lastModified (epoch)
- Land:  /opendata/travelwarning/<id> -> idem + 'content' (HTML) en 'lastChanges'

Het AA zet alleen (Teil)Reisewarnungen in de vlaggen; 'situationWarning' wordt in de praktijk niet
gebruikt (19-11-2026: bij geen enkel land). Afraden staat alleen in de tekst, met vaste zinnen:
  'Vor Reisen in/nach ... wird gewarnt.'              -> (gedeeltelijke) reiswaarschuwing, rood
  'Von Reisen in/nach ... wird dringend abgeraten.'   -> oranje (afgeleid)
  'Von Reisen in/nach ... wird abgeraten.'            -> oranje (afgeleid)
  'Von nicht notwendigen Reisen ... wird abgeraten.'  -> oranje
Die zinnen lezen we letterlijk; het gebied is het stuk tussen 'Reisen in/nach' en 'wird'. Gaat het
over het hele land ('in die Russische Föderation', 'in andere Landesteile Israels'), dan is het het
landelijke niveau. Verwijzingen naar andere landen ('siehe Reise- und Sicherheitshinweise ...') tellen
niet mee.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from functools import lru_cache

from .. import http
from ..countries import normaliseer
from ..mapping import niveau
from ..model import Advies, Gebied, Status
from .base import Bron, niet_gevonden, soep, tekst

API = "https://www.auswaertiges-amt.de/opendata/travelwarning"
WEB = "https://www.auswaertiges-amt.de/de/ReiseUndSicherheit/10.2.8Reisewarnungen"


@lru_cache(maxsize=1)
def index() -> dict[str, tuple[str, dict]]:
    data = http.json(API)["response"]
    return {v["countryCode"]: (k, v) for k, v in data.items() if isinstance(v, dict) and "countryCode" in v}


# 'Vor Reisen in den Süden Libanons ... wird gewarnt.' / 'Von nicht notwendigen Reisen nach X wird derzeit
# dringend abgeraten.' Het voorvoegsel kan een kop zijn die in de tekst is meegekomen ('Aktuelles').
_ZIN = re.compile(
    r"\b(?P<vorm>Vor|Von)\s+(?P<soort>nicht (?:unbedingt )?notwendigen\s+|touristischen\s+)?(?:Reisen|Aufenthalten)\s+"
    r"(?P<vz>in|nach|auf|an|zu)\s+(?P<gebied>[^.]+?)\s+wird\s+(?:derzeit\s+|weiterhin\s+|ausdrücklich\s+)*"
    r"(?P<dringend>dringend\s+)?(?P<werk>gewarnt|abgeraten)\b[^.]*\.",
)
_REST = re.compile(
    r"\b(?:andere|anderen|übrige|übrigen|restliche|restlichen)\s+(?:Landesteile|Gebiete|Regionen|Teile)"
    r"|\bnicht genannte\w*\s+(?:Landesteile|Gebiete|Regionen)",
    re.IGNORECASE,
)
_VERWIJZING = re.compile(r"^(?:die\s+)?(?:folgende|folgenden|diese|dieser|diesen)\b", re.IGNORECASE)


def _sleutel(m: re.Match) -> str:
    if m.group("werk") == "gewarnt":
        return "teilreisewarnung"
    if m.group("soort") and "notwendig" in m.group("soort"):
        return "abraten_niet_noodzakelijk"
    return "dringend_abraten" if m.group("dringend") else "abraten"


def _ernst(sleutel: str) -> int:
    return {
        "teilreisewarnung": 4,
        "reisewarnung": 4,
        "dringend_abraten": 3,
        "abraten": 3,
        "abraten_niet_noodzakelijk": 3,
    }[sleutel]


def _zinnen(content_html: str) -> list[re.Match]:
    gezien, out = set(), []
    for m in _ZIN.finditer(tekst(soep(content_html)).replace("bzw.", "bzw")):
        zin = m.group(0)
        if "siehe Reise- und Sicherheitshinweise" in zin:
            continue  # verwijzing naar een ander land
        sleutel = (m.group("gebied"), m.group("werk"), bool(m.group("dringend")))
        if sleutel in gezien:
            continue  # 'Aktuelles' en 'Sicherheit' herhalen dezelfde zin
        gezien.add(sleutel)
        out.append(m)
    return out


def _heel_land(gebied: str, v: dict) -> bool:
    naam = normaliseer(v.get("countryName", "")).replace(" ", "")
    g = normaliseer(gebied).replace(" ", "")
    # 'die Russische Föderation', 'Afghanistan', 'Israel' (geen deel ervan: 'den Norden Israels' telt niet)
    kaal = re.sub(r"^(?:die|den|das|der)", "", g)
    return bool(_REST.search(gebied)) or kaal == naam or kaal.rstrip("s") == naam


def parse(id_: str, v: dict, iso: str) -> Advies:
    url = f"https://www.auswaertiges-amt.de/de/service/laender/{id_}"  # stuurt door naar de landpagina
    adv = Advies("de", iso, Status.OK, url=url)
    if v.get("lastModified"):
        adv.gewijzigd_op = datetime.fromtimestamp(v["lastModified"], UTC).date().isoformat()
        adv.gewijzigd_label = "lastModified (Auswärtiges Amt Open Data)"
    adv.brontekst = v.get("title", "")

    if v.get("warning"):
        adv.landelijk = niveau("de", "reisewarnung")

    for m in _zinnen(v.get("content", "")):
        sleutel = _sleutel(m)
        zin = re.sub(r"^\S+\s+(?=V[oe][rn]\s+Reisen)", "", m.group(0)).strip()
        if _heel_land(m.group("gebied"), v):
            kandidaat = niveau("de", "reisewarnung" if sleutel == "teilreisewarnung" else sleutel)
            if adv.landelijk is None:
                adv.landelijk = kandidaat
                adv.brontekst = zin
            continue
        if adv.landelijk and adv.landelijk.kleur and adv.landelijk.kleur.ernst == _ernst(sleutel):
            continue  # zelfde niveau als het hele land: geen afwijking
        gebied = m.group("gebied")
        if _VERWIJZING.search(gebied):
            gebied = (
                f"{zin} (de lijst staat op de bronpagina)"  # 'die folgenden Regionen' zegt zonder lijst niets
            )
        adv.gebieden.append(Gebied(gebied, niveau("de", sleutel), brontekst=zin))

    # Dezelfde waarschuwing staat vaak ook als aparte zin per gebied ('Gazastreifen' én 'Gazastreifen und
    # Westjordanland'): een gebied dat letterlijk in een ander gebied met hetzelfde niveau voorkomt, vervalt.
    def _kern(t: str) -> str:
        return normaliseer(re.sub(r"^(?:in\s+)?(?:den|die|das|dem|der)\s+", "", t))

    kernen = [(g, _kern(g.omschrijving)) for g in adv.gebieden]
    adv.gebieden = [
        g
        for g, k in kernen
        if not any(k != k2 and k in k2 and g2.niveau.kleur == g.niveau.kleur for g2, k2 in kernen)
    ]
    for g in adv.gebieden:
        g.omschrijving = re.sub(r"\bbzw\b(?!\.)", "bzw.", g.omschrijving)
        g.brontekst = re.sub(r"\bbzw\b(?!\.)", "bzw.", g.brontekst)
    if adv.landelijk is not None and adv.landelijk.kleur:
        # zinnen over het hele land kunnen ná de gebieden staan: gebieden met dezelfde kleur weghalen
        adv.gebieden = [g for g in adv.gebieden if g.niveau.kleur != adv.landelijk.kleur]
    if adv.landelijk is None:
        adv.landelijk = niveau("de", "geen")
        if adv.gebieden:
            adv.landelijk.toelichting += (
                " Let op: wél waarschuwing of afraden voor delen van het land (zie gebieden)."
            )
    if v.get("partialWarning") and not any(
        g.niveau.kleur and g.niveau.kleur.ernst == 4 for g in adv.gebieden
    ):
        # Vaste zinnen niet herkend: val terug op elke zin 'wird gewarnt', letterlijk als gebied.
        tekst_ = tekst(soep(v.get("content", ""))).replace("bzw.", "bzw")
        for zm in re.finditer(r"[^.]*\bwird\s+(?:dringend\s+)?gewarnt[^.]*\.", tekst_):
            zin = re.sub(r"^.*?(?=Vor\s)", "", zm.group(0).strip())
            if "siehe" in zin.lower() or any(zin == g.brontekst for g in adv.gebieden):
                continue
            adv.gebieden.append(Gebied(zin, niveau("de", "teilreisewarnung"), brontekst=zin))
    if v.get("partialWarning") and not any(
        g.niveau.kleur and g.niveau.kleur.ernst == 4 for g in adv.gebieden
    ):
        adv.melding = (
            "Het AA heeft een Teilreisewarnung, maar het gebied is niet automatisch herkend; zie de bron."
        )
    return adv


def ophalen(iso: str) -> Advies:
    rij = index().get(iso)
    if not rij:
        return niet_gevonden("de", iso, WEB)
    id_, _ = rij
    # Altijd de details ophalen: afraden staat alleen in de tekst, niet in de vlaggen.
    v = http.json(f"{API}/{id_}")["response"][id_]
    return parse(id_, v, iso)


BRON = Bron("de", "Duitsland", "🇩🇪", "de", WEB, _ophalen=ophalen)
