"""Het overzicht: één zelfstandig HTML-bestand per land, geschikt om door te sturen."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

from jinja2 import Environment, PackageLoader, select_autoescape

from .countries import naam
from .model import Advies, Kleur, Status
from .sources import BRONNEN

RECENT_DAGEN = 7
OUD_DAGEN = 365  # ouder dan dit: waarschuwing naast de kleurcode
KORT_CITAAT = 320  # tekens: het gebied en de reden, meestal de eerste één of twee zinnen


KORT_GEBIED = 130  # tekens: boven staat alleen kort om welk gebied het gaat; de volledige tekst staat in de uitklapper


def _gebiedregels(a: Advies) -> list[dict]:
    """Per afwijkend gebied: de naam (kort, voor boven) en de volledige tekst uit de bron (voor de uitklapper)."""
    out = []
    for g in sorted(a.gebieden, key=lambda g: -(g.niveau.kleur.ernst if g.niveau.kleur else 0)):
        naam = " ".join(g.omschrijving.split())
        uitleg = " ".join((g.brontekst or "").split())
        kort = naam if len(naam) <= KORT_GEBIED else naam[:KORT_GEBIED].rsplit(" ", 1)[0] + " …"
        out.append({
            "kleur": g.niveau.kleur.value if g.niveau.kleur else "geen",
            "naam": naam,
            "kort": kort,
            "volledig": uitleg or naam,
            "meer": bool(uitleg and uitleg != naam) or kort != naam,  # er is méér te lezen dan de korte naam
        })
    return out


def deepl_link(tekst: str, taal: str) -> str:
    """Link naar DeepL met de tekst al ingevuld, zodat de redactie de vertaling zelf kan nalopen.

    DeepL leest '/' en '|' in de link als scheidingsteken en knipt de tekst daar af ('M16/H26' werd 'M16');
    die tekens moeten met een backslash ervoor ('\\/'), en een backslash zelf als '\\\\'."""
    veilig = tekst.replace("\\", "\\\\").replace("/", "\\/").replace("|", "\\|")
    return f"https://www.deepl.com/translator#{quote(taal)}/nl/{quote(veilig, safe='')}"


def citaat(tekst: str, lengte: int = KORT_CITAAT, zinnen: int = 2) -> str:
    """De eerste zinnen van de brontekst (meestal: welk gebied en waarom), letterlijk.
    Ingekort wordt alleen aan het eind, op een zinseinde, en altijd met '…' erachter."""
    t = " ".join(tekst.split())
    delen = re.split(r"(?<=[.!?])\s+", t)
    kort = " ".join(delen[:zinnen])
    if len(kort) > lengte:
        kort = kort[:lengte].rsplit(" ", 1)[0]
    return kort if kort == t else kort + " …"


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


def render(
    iso: str,
    adviezen: list[Advies],
    nu: datetime | None = None,
    terug: str | None = None,
    fonts: str | None = None,
) -> str:
    """fonts: pad naar de meegeleverde lettertypen (alleen in de site); los bestand: systeemletters."""
    nu = nu or datetime.now(UTC)
    vandaag = nu.date()
    nl = next((x for x in adviezen if x.bron == "nl"), None)
    nl_kleur = nl.landelijk.kleur if nl and nl.status == Status.OK and nl.landelijk else None
    rijen = []
    for a in adviezen:
        b = BRONNEN[a.bron]
        eigen = a.landelijk.kleur if a.status == Status.OK and a.landelijk else None
        if a.bron == "nl" or not (eigen and nl_kleur):
            vergelijk = None
        else:
            vergelijk = "strenger" if eigen.ernst > nl_kleur.ernst else "milder" if eigen.ernst < nl_kleur.ernst else "gelijk"
        # De niveaus van de deelgebieden, één keer per kleur/typering, strengste eerst.
        gebiedniveaus: dict[tuple, object] = {}
        for g in sorted(a.gebieden, key=lambda g: -(g.niveau.kleur.ernst if g.niveau.kleur else 0)):
            gebiedniveaus.setdefault((g.niveau.kleur, g.niveau.bronlabel), g.niveau)
        dagen = _dagen_geleden(a.gewijzigd_op, vandaag)
        heeft_niveau = a.status == Status.OK and a.landelijk is not None
        rijen.append(
            {
                "a": a,
                "bron": b,
                "dagen": dagen,
                "recent": dagen is not None and dagen <= RECENT_DAGEN,
                # Geen wijzigingsdatum (en geen andere bevestiging van actualiteit) = onzeker.
                "geen_datum": heeft_niveau and not a.gewijzigd_op and not a.gewijzigd_label,
                "oud": dagen is not None and dagen > OUD_DAGEN,
                "vergelijk": vergelijk,
                "gebiedregels": (gr := _gebiedregels(a)),
                # Uitklapper met de volledige teksten: altijd bij een vreemde taal (voor de DeepL-link), anders
                # alleen als er meer te lezen is dan de korte namen.
                "gebieden_uitklap": bool(gr) and (b.taal != "nl" or any(x["meer"] for x in gr)),
                "gebieden_deepl": deepl_link("\n".join(x["volledig"] for x in gr)[:1800], b.taal)
                if gr and b.taal != "nl"
                else "",
                "gebiedniveaus": list(gebiedniveaus.values()),
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
            citaat=citaat,
            terug=terug,
            fonts=fonts,
        )
    )

