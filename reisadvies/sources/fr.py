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
from urllib.parse import urljoin

from .. import http
from ..countries import koppel, naam, normaliseer
from ..mapping import niveau
from ..model import Advies, Gebied, Soort, Status
from .base import Bron, datum, niet_gevonden, soep, tekst

BASIS = "https://www.diplomatie.gouv.fr"
WEB = BASIS + "/fr/conseils-aux-voyageurs"
PAD = BASIS + "/fr/information-par-pays/{slug}/conseils-aux-voyageurs-securite"

_KLEUR = re.compile(
    r"\(\s*(?:en\s+)?(rouge|orange|jaune|vert)\b[^)]*\)"  # '(rouge sur la carte)', '( vert )'
    r"|\b(?:plac[ée]e?s?|class[ée]e?s?)\s+en\s+(rouge|orange|jaune|vert)\b",  # 'placé en rouge sur la carte'
    re.IGNORECASE,
)
# Vaste formuleringen van de vier Franse niveaus (strengste eerst).
_FORMULERING = [
    (re.compile(r"formellement d[ée]conseill", re.IGNORECASE), "rouge"),
    (
        # ook 'déconseillé aux ressortissants français, sauf pour des raisons impératives'
        re.compile(
            r"d[ée]conseill\w*(?:\s+[^\s,]+){0,4}?,?\s+sauf (?:pour )?(?:des? )?raisons? imp[ée]rative",
            re.IGNORECASE,
        ),
        "orange",
    ),
    (re.compile(r"vigilance (?:est )?renforc[ée]e", re.IGNORECASE), "jaune"),
    (re.compile(r"vigilance (?:est )?normale", re.IGNORECASE), "vert"),
]
# Zin die over het hele land gaat: 'L'ensemble du pays est ...', 'L'intégralité du pays ...'
_HEEL_LAND = re.compile(
    r"(?:ensemble|int[ée]gralit[ée]|totalit[ée]) (?:du|de l['’]|de la|des) ?(?:pays|territoire|archipel|[îi]le|[îi]les|r[ée]gion)\w*"
    r"|tout le (?:pays|territoire)|toute l['’][îi]le"
    r"|reste du (?:pays|territoire)"
    r"|^(?:le|l['’])\s*(?:territoire|pays)\b(?:\s+[a-zéèêëïîôûüç-]+)?\s+(?:est|sont)\b",  # 'Le territoire belge est ...'
    re.IGNORECASE,
)
# '... de se rendre au Koweït' / 'en Iran' / 'aux Émirats arabes unis': de landnaam zelf
_NAAR_LAND = re.compile(r"\bse rendre\s+(?:en|au|aux|à|a)\s+([^,.;]+)", re.IGNORECASE)
_ERNST = {"vert": 1, "jaune": 2, "orange": 3, "rouge": 4}


def _kleur_van(t: str) -> str | None:
    """De eerstgenoemde kleur in de tekst: '(rouge sur la carte)', '( vert )' of een vaste formulering.

    'vigilance normale ( vert ), à l'exception de ... ( jaune )' -> 'vert': wat vooraan staat,
    geldt voor het onderwerp van de zin; de rest is een uitzondering.
    """
    kandidaten = [(m.start(), (m.group(1) or m.group(2)).lower()) for m in _KLEUR.finditer(t)]
    for rx, kleur in _FORMULERING:
        m = rx.search(t)
        if m:
            kandidaten.append((m.start(), kleur))
    return min(kandidaten)[1] if kandidaten else None


def _kleur_heel_land(zin: str, iso: str | None = None) -> str | None:
    """Kleur voor het hele land uit één zin, of None.

    Eerst de kleur direct ná 'le reste du territoire' / 'l'ensemble du pays' (de zin kan met een
    uitzondering beginnen: 'À l'exception des zones formellement déconseillées, le reste du
    territoire est placé en vigilance renforcée'). Staat daarna geen kleur, dan de kleur ervóór
    ('il est formellement déconseillé de se rendre dans l'ensemble du territoire').
    """
    m = _HEEL_LAND.search(zin.strip())
    if m:
        z = zin.strip()
        return _kleur_van(z[m.end() :]) or _kleur_van(z[: m.start()])
    if iso:
        for nm in _NAAR_LAND.finditer(zin):
            doel = re.split(r"\s+(?:sauf|hormis|à l['’]exception|en dehors|quel)\b", nm.group(1))[0].strip()
            if koppel(iso, "fr", {doel: True}):
                return _kleur_van(zin)
    return None


# De kop heet 'Zones de vigilance', 'Zone de vigilance' of (typefout op de site) 'Zones de vigilence'.
_ZONE_KOP = re.compile(r"zones?\s+de\s+vigil\w+", re.IGNORECASE)


def _is_zonekop(t) -> bool:
    return t.name in ("h2", "h3") and bool(_ZONE_KOP.fullmatch(tekst(t)))


def _zone_elementen(s) -> list:
    """Alle koppen en alinea's onder 'Zones de vigilance', tot de volgende h2/h3."""
    kop = s.find(_is_zonekop)
    if not kop:
        return []
    out: list = []
    lijsten: list = []
    for el in kop.find_all_next(["p", "h3", "h4", "h5", "ul"]):
        if el.name == "h3" and not _is_zonekop(el):
            break
        if any(el in lijst.descendants for lijst in lijsten):
            continue  # zit al in een verzamelde lijst
        if el.name == "ul":
            lijsten.append(el)
        out.append(el)
    return out


# De vier vaste kleuren van de Franse kaarten (gemeten op de kaarten van Cambodja, Turkije en Japan).
_KAARTKLEUREN = {
    "rouge": (220, 10, 20),
    "orange": (245, 150, 60),
    "jaune": (245, 245, 170),
    "vert": (190, 210, 110),
}
_MAX_AFSTAND = 40  # pixels verder van alle vier de kleuren weg zijn zee, buurlanden, tekst
_MIN_AANDEEL = 0.02  # minder dan 2% van de kaart in een van de vier kleuren: niet betrouwbaar


def kaart_url(html: str) -> str | None:
    """De kaartafbeelding onder 'Zones de vigilance'."""
    mk = _ZONE_KOP.search(html)
    i = mk.start() if mk else -1
    m = re.search(r'<img[^>]*\bsrc="([^"]+)"', html[i : i + 5000]) if i >= 0 else None
    return urljoin(BASIS, m.group(1)) if m else None


def kaartkleur(afbeelding: bytes) -> tuple[str | None, dict[str, float]]:
    """De kleur met het grootste oppervlak op de kaart: de kleur voor het grootste deel van het land.

    Telt alleen pixels die dicht bij een van de vier vaste kaartkleuren liggen; zee, buurlanden,
    plaatsnamen en de titelbalk vallen daarbuiten. De legenda telt mee, maar is klein.
    """
    from io import BytesIO

    from PIL import Image

    im = Image.open(BytesIO(afbeelding)).convert("RGB")
    im.thumbnail((400, 400))
    telling = dict.fromkeys(_KAARTKLEUREN, 0)
    ruw = im.tobytes()
    pixels = list(zip(ruw[0::3], ruw[1::3], ruw[2::3]))
    for r, g, b in pixels:
        beste, afstand = None, _MAX_AFSTAND**2
        for kleur, (kr, kg, kb) in _KAARTKLEUREN.items():
            d = (r - kr) ** 2 + (g - kg) ** 2 + (b - kb) ** 2
            if d < afstand:
                beste, afstand = kleur, d
        if beste:
            telling[beste] += 1
    aandelen = {k: n / len(pixels) for k, n in telling.items()}
    kleur = max(aandelen, key=aandelen.get)
    return (kleur if aandelen[kleur] >= _MIN_AANDEEL else None), aandelen


_KAART_TOELICHTING = (
    "Frankrijk noemt de kleur voor de rest van het land alleen op de kaart. Afgelezen van de kaart: "
    "de kleur met het grootste oppervlak."
)


@lru_cache(maxsize=1)
def index() -> dict[str, str]:
    html = http.text(WEB)
    slugs = set(re.findall(r"/fr/information-par-pays/([a-z0-9-]+)/", html))
    return {s: PAD.format(slug=s) for s in slugs}


_OOK_OP_KAART = 0.002  # vanaf 0,2% van de kaart telt een strengere kleur als gebied (de legenda is kleiner)


def parse(
    html: str, iso: str, url: str, kaart: str | None = None, aandelen: dict[str, float] | None = None
) -> Advies:
    """kaart/aandelen: uitkomst van kaartkleur() voor de kaartafbeelding, als die er is."""
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
    #    Soms staat die net onder de volgende kop ('Risques et recommandations'): kijk dan in de eerste
    #    twee alinea's ná 'Zones de vigilance'.
    kandidaten = elementen
    if not any(e.name == "p" and tekst(e) for e in elementen):
        kop = s.find(_is_zonekop)
        kandidaten = [p for p in (kop.find_all_next("p", limit=2) if kop else []) if tekst(p)]
        if kandidaten:
            adv.brontekst = " ".join(tekst(p) for p in kandidaten)
    for e in kandidaten:
        if e.name not in ("p", "ul"):
            continue
        for zin in re.split(r"(?<=[.!?])\s+", tekst(e)):
            if kleur := _kleur_heel_land(zin, iso):
                adv.landelijk = niveau("fr", kleur)
                break
        if adv.landelijk:
            break

    # 2. Koppen per kleur ('Zones formellement déconseillées (rouge sur la carte)'), soms met per gebied
    #    een subkop zonder kleur ('Lunda Sul et Lunda Norte'): die hoort bij de kleur van de kop erboven.
    ruw: list[dict] = []
    kleur_nu: str | None = None
    huidig: dict | None = None
    for e in elementen:
        # Een kop: h4/h5, of een alinea die alleen vetgedrukte tekst bevat.
        is_kop = e.name in ("h4", "h5") or (
            e.name == "p" and e.find("strong") is not None and tekst(e.find("strong")) == tekst(e)
        )
        if is_kop:
            kop = tekst(e)
            kleur = _kleur_van(kop) if re.match(r"(?:zones?|r[ée]gions?|parties?)\b", kop, re.IGNORECASE) else None
            heel = bool(_HEEL_LAND.search(kop)) and _kleur_van(kop) is not None
            if heel:
                kleur = _kleur_van(kop)
            if kleur:
                kleur_nu = kleur
                huidig = {"kleur": kleur, "naam": "", "teksten": [], "kop": kop, "heel": heel}
                ruw.append(huidig)
            elif kleur_nu and e.name != "h4":
                huidig = {"kleur": kleur_nu, "naam": kop.rstrip(" :"), "teksten": [], "kop": kop, "heel": False}
                ruw.append(huidig)
            else:
                kleur_nu, huidig = None, None
        elif huidig is not None and tekst(e):
            huidig["teksten"].append(tekst(e))
    # Een kleurkop zonder eigen tekst, gevolgd door subkoppen in dezelfde kleur, is zelf geen gebied.
    secties: list[tuple[str, str]] = []
    namen: dict[int, str] = {}
    for i, r in enumerate(ruw):
        t = " ".join(r["teksten"])
        volgende = ruw[i + 1] if i + 1 < len(ruw) else None
        if not t and not r["naam"] and volgende and volgende["naam"] and volgende["kleur"] == r["kleur"]:
            continue
        if r["heel"]:
            t = f"{r['kop']} {t}".strip()  # 'Le reste du pays est en vigilance renforcée (en jaune) ...'
        if r["naam"]:
            namen[len(secties)] = r["naam"]
        secties.append((r["kleur"], t or r["kop"]))

    secties_oud = list(secties)  # om namen terug te vinden nadat secties zijn weggefilterd
    if not adv.landelijk and kaart:
        # Geen zin over het hele land: de kaart is de bron. Gebieden in dezelfde kleur wijken niet af.
        adv.landelijk = replace(niveau("fr", kaart), toelichting=_KAART_TOELICHTING)
        secties = [(k, t) for k, t in secties if k != kaart]
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
        naam_gebied = next((n for i, n in namen.items() if secties_oud[i] == (kleur, t)), "")
        adv.gebieden.append(Gebied(naam_gebied or t[:300], niveau("fr", kleur), brontekst=t))
    if adv.landelijk and adv.landelijk.kleur:
        # Een gebied in dezelfde kleur als het land ('Le reste du pays ...') wijkt niet af.
        adv.gebieden = [g for g in adv.gebieden if g.niveau.kleur != adv.landelijk.kleur]

    if adv.landelijk and aandelen and adv.landelijk.kleur and adv.landelijk.toelichting == _KAART_TOELICHTING:
        # Alleen als de basiskleur van de kaart komt: een zin in de tekst over het hele land is leidend.
        # Staat er op de kaart een strengere kleur die de tekst niet als gebied noemt? Dan zeggen we dat.
        basis = adv.landelijk.kleur.ernst
        genoemd = {g.niveau.kleur for g in adv.gebieden}
        missend = [
            k for k, a in aandelen.items()
            if a >= _OOK_OP_KAART and _ERNST[k] > basis and niveau("fr", k).kleur not in genoemd
        ]
        if missend:
            namen = " en ".join(niveau("fr", k).kleur.value for k in sorted(missend, key=_ERNST.get, reverse=True))
            adv.melding = (
                f"Op de kaart staan ook gebieden in {namen} die niet automatisch uit de tekst zijn "
                "herkend. Bekijk de kaart via de link."
            )

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
    kaart = None
    if (k_url := kaart_url(html)) is not None:
        try:
            kaart, aandelen = kaartkleur(http.get(k_url).content)
        except Exception:  # noqa: BLE001 - zonder kaart valt parse terug op de tekst
            kaart, aandelen = None, None
    else:
        aandelen = None
    return parse(html, iso, url, kaart=kaart, aandelen=aandelen)


BRON = Bron("fr", "Frankrijk", "🇫🇷", "fr", WEB, _ophalen=ophalen)
