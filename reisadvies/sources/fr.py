"""Frankrijk – diplomatie.gouv.fr Conseils aux voyageurs.

- Land: /fr/information-par-pays/<slug>/conseils-aux-voyageurs-securite
  - Onder 'Zones de vigilance': kaart (afbeelding) met bijschrift
    'Dernière actualisation le dd/mm/jjjj', daarna h4-koppen per kleur:
    'Zones formellement déconseillées (rouge sur la carte)' enz.
- Frankrijk gebruikt dezelfde vier kleuren als wij. Welke kleur voor 'de rest van het land'
  geldt, staat vaak alleen op de kaart (afbeelding). Zie parse().
"""

from __future__ import annotations

import re
from dataclasses import replace
from functools import lru_cache

from .. import http
from ..countries import koppel, naam, normaliseer
from ..mapping import niveau
from ..model import Advies, Gebied, Soort, Status
from .base import Bron, datum, niet_gevonden, soep, tekst

BASIS = "https://www.diplomatie.gouv.fr"
WEB = BASIS + "/fr/conseils-aux-voyageurs"
PAD = BASIS + "/fr/information-par-pays/{slug}/conseils-aux-voyageurs-securite"

_KLEUR = re.compile(r"\(\s*(?:en\s+)?(rouge|orange|jaune|vert)\b[^)]*\)", re.IGNORECASE)
# Vaste formuleringen van de vier Franse niveaus (strengste eerst).
_FORMULERING = [
    (re.compile(r"formellement d[ée]conseill", re.IGNORECASE), "rouge"),
    (
        re.compile(r"d[ée]conseill\w*,? sauf (?:pour )?(?:des )?raisons? imp[ée]rative", re.IGNORECASE),
        "orange",
    ),
    (re.compile(r"vigilance renforc[ée]e", re.IGNORECASE), "jaune"),
    (re.compile(r"vigilance normale", re.IGNORECASE), "vert"),
]
# Zin die over het hele land gaat: 'L'ensemble du pays est ...', 'L'intégralité du pays ...'
_HEEL_LAND = re.compile(
    r"(?:ensemble|int[ée]gralit[ée]) du (?:pays|territoire)|tout le (?:pays|territoire)"
    r"|reste du (?:pays|territoire)",
    re.IGNORECASE,
)
_ERNST = {"vert": 1, "jaune": 2, "orange": 3, "rouge": 4}


def _kleur_van(t: str) -> str | None:
    """De eerstgenoemde kleur in de tekst: '(rouge sur la carte)', '( vert )' of een vaste formulering.

    'vigilance normale ( vert ), à l'exception de ... ( jaune )' -> 'vert': wat vooraan staat,
    geldt voor het onderwerp van de zin; de rest is een uitzondering.
    """
    kandidaten = [(m.start(), m.group(1).lower()) for m in _KLEUR.finditer(t)]
    for rx, kleur in _FORMULERING:
        m = rx.search(t)
        if m:
            kandidaten.append((m.start(), kleur))
    return min(kandidaten)[1] if kandidaten else None


def _kleur_heel_land(zin: str) -> str | None:
    """Kleur voor het hele land uit één zin, of None.

    Eerst de kleur direct ná 'le reste du territoire' / 'l'ensemble du pays' (de zin kan met een
    uitzondering beginnen: 'À l'exception des zones formellement déconseillées, le reste du
    territoire est placé en vigilance renforcée'). Staat daarna geen kleur, dan de kleur ervóór
    ('il est formellement déconseillé de se rendre dans l'ensemble du territoire').
    """
    m = _HEEL_LAND.search(zin)
    if not m:
        return None
    return _kleur_van(zin[m.end() :]) or _kleur_van(zin[: m.start()])


def _zone_elementen(s) -> list:
    """Alle koppen en alinea's onder 'Zones de vigilance', tot de volgende h2/h3."""
    kop = s.find(lambda t: t.name in ("h2", "h3") and tekst(t) == "Zones de vigilance")
    if not kop:
        return []
    out: list = []
    lijsten: list = []
    for el in kop.find_all_next(["p", "h3", "h4", "h5", "ul"]):
        if el.name == "h3" and tekst(el) != "Zones de vigilance":
            break
        if any(el in lijst.descendants for lijst in lijsten):
            continue  # zit al in een verzamelde lijst
        if el.name == "ul":
            lijsten.append(el)
        out.append(el)
    return out


@lru_cache(maxsize=1)
def index() -> dict[str, str]:
    html = http.text(WEB)
    slugs = set(re.findall(r"/fr/information-par-pays/([a-z0-9-]+)/", html))
    return {s: PAD.format(slug=s) for s in slugs}


def parse(html: str, iso: str, url: str) -> Advies:
    s = soep(html)
    adv = Advies("fr", iso, Status.OK, url=url)
    m = re.search(r"Dernière actualisation le\s*([\d/]+)", html)
    if m:
        adv.gewijzigd_op = datum(m.group(1))
        adv.gewijzigd_label = "Zones de vigilance: dernière actualisation"
    else:
        m = re.search(r"Date de mise à jour le\s*:\s*([^<]+)", html)
        if m:
            adv.gewijzigd_op = datum(m.group(1))
            adv.gewijzigd_label = "Date de mise à jour (hele pagina)"

    elementen = _zone_elementen(s)
    adv.brontekst = " ".join(tekst(e) for e in elementen if tekst(e))

    # 1. Een expliciete zin over het hele land ('L'ensemble du pays est formellement déconseillé').
    for e in elementen:
        if e.name not in ("p", "ul"):
            continue
        for zin in re.split(r"(?<=[.!?])\s+", tekst(e)):
            if kleur := _kleur_heel_land(zin):
                adv.landelijk = niveau("fr", kleur)
                break
        if adv.landelijk:
            break

    # 2. Koppen per kleur ('Zones formellement déconseillées (rouge sur la carte)').
    secties: list[tuple[str, str]] = []
    huidig: list | None = None
    for e in elementen:
        if e.name in ("h4", "h5"):
            kop = tekst(e)
            kleur = (
                _kleur_van(kop)
                if re.match(r"(?:zones?|r[ée]gions?|parties?)\b", kop, re.IGNORECASE)
                else None
            )
            huidig = [kleur, []] if kleur else None
            if huidig:
                secties.append(huidig)
        elif huidig is not None and tekst(e):
            huidig[1].append(tekst(e))
    secties = [(k, " ".join(t)) for k, t in secties]

    if not adv.landelijk:
        expliciet = next((i for i, (_, t) in enumerate(secties) if _HEEL_LAND.search(t)), None)
        if expliciet is not None:
            adv.landelijk = niveau("fr", secties.pop(expliciet)[0])
        elif len(secties) >= 2:
            # De laagste genoemde kleur geldt in de praktijk voor de rest van het land, maar dat
            # staat alleen op de kaart. Daarom 'afgeleid'.
            laagste = min(range(len(secties)), key=lambda i: _ERNST[secties[i][0]])
            adv.landelijk = replace(
                niveau("fr", secties.pop(laagste)[0]),
                soort=Soort.AFGELEID,
                toelichting="Frankrijk noemt niet in tekst welke kleur voor de rest van het land geldt; "
                "aangenomen is de laagste genoemde kleur. Controleer op de kaart.",
            )

    for kleur, t in secties:
        adv.gebieden.append(Gebied(t[:300], niveau("fr", kleur), brontekst=t))

    if not adv.landelijk:
        if secties:
            adv.melding = (
                "Frankrijk noemt alleen gebieden met een kleur; welke kleur voor de rest van het land geldt, "
                "staat alleen op de kaart. Controleer de kaart via de link."
            )
        else:
            adv.melding = (
                "Frankrijk beschrijft de zones hier in vrije tekst zonder vaste formulering; niveau niet "
                "automatisch vastgesteld. Lees de brontekst of de kaart."
            )
    return adv


def ophalen(iso: str) -> Advies:
    url = koppel(iso, "fr", index())
    if not url:
        # niet in de index: probeer de slug van de Franse landnaam
        url = PAD.format(slug=normaliseer(naam(iso, "fr")).replace(" ", "-"))
    try:
        html = http.text(url)
    except http.OphaalFout:
        return niet_gevonden("fr", iso, WEB)
    return parse(html, iso, url)


BRON = Bron("fr", "Frankrijk", "🇫🇷", "fr", WEB, _ophalen=ophalen)
