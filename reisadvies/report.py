"""Het overzicht: één zelfstandig HTML-bestand per land, geschikt om door te sturen."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

from jinja2 import Environment, PackageLoader, select_autoescape

from .countries import naam
from .model import Advies, Kleur, Status
from .sources import BRONNEN
from .vertaling import vertaal

RECENT_DAGEN = 7
OUD_DAGEN = 365  # ouder dan dit: waarschuwing naast de kleurcode
REDEN_MIN = 60  # kortere brontekst (een paginatitel, 'Hele landet') zegt niets over de reden
REDEN_LENGTE = 300  # lengte van het korte, letterlijke citaat bij het landelijke niveau
TOON_REDEN = True  # citaat bij het landelijke niveau; op False zetten om het te laten vervallen


def deepl_link(tekst: str, taal: str) -> str:
    """Link naar DeepL met de tekst al ingevuld, zodat de redactie de vertaling zelf kan nalopen."""
    return f"https://www.deepl.com/translator#{quote(taal)}/nl/{quote(tekst, safe='')}"


def citaat(tekst: str, lengte: int = REDEN_LENGTE) -> str:
    """Begin van de brontekst, zonder iets te herschrijven; bij inkorten op een zinseinde en met '…'."""
    t = " ".join(tekst.split())
    if len(t) <= lengte:
        return t
    knip = t[:lengte]
    punt = max(knip.rfind(". "), knip.rfind("! "), knip.rfind("? "))
    return (knip[: punt + 1] if punt > lengte // 3 else knip.rsplit(" ", 1)[0]) + " …"


def verzamel(iso: str, bronnen: list[str] | None = None) -> list[Advies]:
    gekozen = [BRONNEN[b] for b in (bronnen or BRONNEN)]
    with ThreadPoolExecutor(max_workers=len(gekozen)) as ex:
        return list(ex.map(lambda b: b.haal(iso), gekozen))


def _dagen_geleden(d: str | None, vandaag: date) -> int | None:
    if not d:
        return None
    try:
        return (vandaag - date.fromisoformat(d[:10])).days
    except ValueError:
        return None


def samenvatting(adviezen: list[Advies]) -> dict:
    """Vergelijk elk landelijk niveau met het Nederlandse."""
    nl = next((a for a in adviezen if a.bron == "nl"), None)
    nl_kleur = nl.landelijk.kleur if nl and nl.landelijk else None
    strenger, gelijk, milder, geen_kleur, niet_beschikbaar, onzeker = [], [], [], [], [], []
    for a in adviezen:
        if a.bron == "nl":
            continue
        naam_bron = BRONNEN[a.bron].naam
        if a.status == Status.NVT:
            continue
        if a.status == Status.OK and a.landelijk and not a.gewijzigd_op and not a.gewijzigd_label:
            onzeker.append(naam_bron)
        if a.status != Status.OK:
            niet_beschikbaar.append(naam_bron)
        elif not a.landelijk:
            geen_kleur.append(naam_bron + " (niet herkend)")
        elif a.landelijk.kleur is None or nl_kleur is None:
            geen_kleur.append(naam_bron)
        elif a.landelijk.kleur.ernst > nl_kleur.ernst:
            strenger.append(naam_bron)
        elif a.landelijk.kleur.ernst < nl_kleur.ernst:
            milder.append(naam_bron)
        else:
            gelijk.append(naam_bron)
    met_strengere_gebieden = [
        BRONNEN[a.bron].naam
        for a in adviezen
        if a.bron != "nl"
        and nl_kleur
        and any(g.niveau.kleur and g.niveau.kleur.ernst > nl_kleur.ernst for g in a.gebieden)
    ]
    return {
        "nl_kleur": nl_kleur,
        "strenger": strenger,
        "gelijk": gelijk,
        "milder": milder,
        "geen_kleur": geen_kleur,
        "niet_beschikbaar": niet_beschikbaar,
        "onzeker": onzeker,
        "strengere_gebieden": met_strengere_gebieden,
    }


def _env() -> Environment:
    env = Environment(
        loader=PackageLoader("reisadvies", "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


def render(iso: str, adviezen: list[Advies], nu: datetime | None = None, terug: str | None = None) -> str:
    nu = nu or datetime.now(UTC)
    vandaag = nu.date()
    rijen = []
    for a in adviezen:
        b = BRONNEN[a.bron]
        dagen = _dagen_geleden(a.gewijzigd_op, vandaag)
        heeft_niveau = a.status == Status.OK and a.landelijk is not None
        reden = citaat(a.brontekst) if TOON_REDEN and a.status == Status.OK and a.brontekst else ""
        if a.bron == "nl" or len(reden) < REDEN_MIN:
            reden = ""  # de Nederlandse brontekst is het referentiepunt en staat in de details
        rijen.append(
            {
                "a": a,
                "bron": b,
                "dagen": dagen,
                "recent": dagen is not None and dagen <= RECENT_DAGEN,
                # Geen wijzigingsdatum (en geen andere bevestiging van actualiteit) = onzeker.
                "geen_datum": heeft_niveau and not a.gewijzigd_op and not a.gewijzigd_label,
                "oud": dagen is not None and dagen > OUD_DAGEN,
                "reden": reden,
                "reden_link": deepl_link(reden, b.taal) if reden and b.taal != "nl" else "",
                "reden_nl": vertaal(reden) if reden and b.taal != "nl" else None,
                "gebieden": sorted(
                    a.gebieden, key=lambda g: -(g.niveau.kleur.ernst if g.niveau.kleur else 0)
                ),
            }
        )
    return (
        _env()
        .get_template("overzicht.html")
        .render(
            iso=iso,
            land=naam(iso, "nl"),
            rijen=rijen,
            som=samenvatting(adviezen),
            Status=Status,
            Kleur=Kleur,
            gegenereerd=nu.astimezone(ZoneInfo("Europe/Amsterdam")).strftime("%d-%m-%Y %H:%M"),
            recent_dagen=RECENT_DAGEN,
            oud_dagen=OUD_DAGEN,
            deepl=deepl_link,
            vertaal=vertaal,
            terug=terug,
        )
    )


def te_vertalen(iso: str, adviezen: list[Advies]) -> list[dict]:
    """De citaten die het overzicht toont en die nog geen vastgelegde vertaling hebben."""
    out, gezien = [], set()
    for a in adviezen:
        taal = BRONNEN[a.bron].taal
        if a.status != Status.OK or taal == "nl":
            continue
        teksten = [g.omschrijving for g in a.gebieden]
        if TOON_REDEN and a.brontekst and len(citaat(a.brontekst)) >= REDEN_MIN:
            teksten.insert(0, citaat(a.brontekst))
        for t in teksten:
            if t and t not in gezien and vertaal(t) is None:
                gezien.add(t)
                out.append({"land": iso, "overheid": a.bron, "taal": taal, "bron": t, "nl": ""})
    return out
