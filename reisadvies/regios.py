"""Indeling van landen in regio's, voor het filter op de startpagina.

Gebaseerd op de VN-indeling (M49), met 'Midden-Oosten' apart en 'Centraal-Azië en Kaukasus' samen.
Een land hoort bij één regio; de regio's van Afrika horen daarnaast bij 'Afrika' (het geheel).
Landen die nergens bij horen (Antarctica en onbewoonde gebieden) komen onder 'Overig'.
"""

from __future__ import annotations

REGIOS: dict[str, tuple[str, str]] = {
    # sleutel: (naam, ISO-codes)
    "midden-oosten": ("Midden-Oosten", "AE BH IL IQ IR JO KW LB OM PS QA SA SY TR YE"),
    "europa": (
        "Europa",
        "AD AL AT AX BA BE BG BY CH CY CZ DE DK EE ES FI FO FR GB GG GI GR HR HU IE IM IS IT JE LI LT LU LV MC MD ME "
        "MK MT NL NO PL PT RO RS RU SE SI SJ SK SM UA VA XK",
    ),
    "centraal-azie": ("Centraal-Azië en Kaukasus", "AM AZ GE KG KZ TJ TM UZ"),
    "oost-azie": ("Oost-Azië", "CN HK JP KP KR MN MO TW"),
    "zuid-azie": ("Zuid-Azië", "AF BD BT IN LK MV NP PK"),
    "zuidoost-azie": ("Zuidoost-Azië", "BN ID KH LA MM MY PH SG TH TL VN"),
    "oceanie": (
        "Oceanië",
        "AS AU CC CK CX FJ FM GU KI MH MP NC NF NR NU NZ PF PG PN PW SB TK TO TV UM VU WF WS",
    ),
    "noord-amerika": ("Noord-Amerika", "BM CA GL PM US"),
    "midden-amerika": ("Midden-Amerika", "BZ CR GT HN MX NI PA SV"),
    "caribisch": (
        "Caribisch gebied",
        "AG AI AW BB BL BQ BQ-BO BQ-SA BQ-SE BS CU CW DM DO GD GP HT JM KN KY LC MF MQ MS PR SX TC TT VC VG VI",
    ),
    "zuid-amerika": ("Zuid-Amerika", "AR BO BR CL CO EC FK GF GY PE PY SR UY VE"),
    "afrika-noord": ("Noord-Afrika", "DZ EG EH LY MA SD TN"),
    "afrika-west": ("West-Afrika", "BF BJ CI CV GH GM GN GW LR ML MR NE NG SH SL SN TG"),
    "afrika-centraal": ("Centraal-Afrika", "AO CD CF CG CM GA GQ ST TD"),
    "afrika-oost": ("Oost-Afrika", "BI DJ ER ET KE KM MG MU MW MZ RE RW SC SO SS TZ UG YT ZM ZW"),
    "afrika-zuid": ("Zuidelijk Afrika", "BW LS NA SZ ZA"),
    "overig": ("Overig", "AQ BV GS HM IO TF"),
}

AFRIKA = [k for k in REGIOS if k.startswith("afrika-")]
_ISO_NAAR_REGIO = {iso: sleutel for sleutel, (_, codes) in REGIOS.items() for iso in codes.split()}


def regios_van(iso: str) -> list[str]:
    """De regio('s) van een land: de eigen regio, en voor Afrika ook 'afrika' (het geheel)."""
    sleutel = _ISO_NAAR_REGIO.get(iso)
    if sleutel is None:
        return ["overig"]
    return [sleutel, "afrika"] if sleutel in AFRIKA else [sleutel]


def opties() -> list[tuple[str, str, bool]]:
    """(sleutel, naam, ingesprongen) voor het keuzemenu; Afrika als geheel met zijn delen eronder."""
    uit: list[tuple[str, str, bool]] = []
    for sleutel, (naam, _) in REGIOS.items():
        if sleutel == "afrika-noord":
            uit.append(("afrika", "Afrika (alle)", False))
        uit.append((sleutel, naam, sleutel in AFRIKA))
    return uit
