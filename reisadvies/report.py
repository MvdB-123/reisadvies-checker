"""Het overzicht: één zelfstandig HTML-bestand per land, geschikt om door te sturen."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from jinja2 import Environment, PackageLoader, select_autoescape

from .countries import naam
from .model import Advies, Kleur, Status
from .sources import BRONNEN

RECENT_DAGEN = 7


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
    strenger, gelijk, milder, geen_kleur, niet_beschikbaar = [], [], [], [], []
    for a in adviezen:
        if a.bron == "nl":
            continue
        naam_bron = BRONNEN[a.bron].naam
        if a.status == Status.NVT:
            continue
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


def render(iso: str, adviezen: list[Advies], nu: datetime | None = None) -> str:
    nu = nu or datetime.now(UTC)
    vandaag = nu.date()
    rijen = []
    for a in adviezen:
        b = BRONNEN[a.bron]
        dagen = _dagen_geleden(a.gewijzigd_op, vandaag)
        rijen.append(
            {
                "a": a,
                "bron": b,
                "dagen": dagen,
                "recent": dagen is not None and dagen <= RECENT_DAGEN,
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
        )
    )
