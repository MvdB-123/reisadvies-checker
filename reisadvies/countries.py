"""Landen: ISO-codes, namen per taal (uit CLDR via Babel) en het koppelen aan bronnamen.

Elke overheid gebruikt eigen namen en slugs (‘tyrkiet’, ‘turquie’, ‘Türkiye’). We koppelen
door de genormaliseerde naam van de bron te vergelijken met de CLDR-namen in de taal van de
bron, aangevuld met de aliassen hieronder voor afwijkingen die CLDR niet kent.
"""

from __future__ import annotations

import re
import unicodedata
from functools import cache

from babel import Locale

# Aanvullende namen per taal, voor gevallen waar een bron afwijkt van CLDR.
# Sleutel: ISO-code, waarde: namen (worden genormaliseerd).
ALIASSEN: dict[str, dict[str, list[str]]] = {
    "en": {
        "TR": ["Turkey", "Turkiye"],
        "CI": ["Cote d'Ivoire", "Ivory Coast"],
        "CZ": ["Czech Republic"],
        "MM": ["Burma"],
        "CD": ["Democratic Republic of the Congo", "Congo (Kinshasa)", "DR Congo"],
        "CG": ["Republic of the Congo", "Congo (Brazzaville)", "Congo"],
        "KP": ["North Korea", "Democratic People's Republic of Korea"],
        "KR": ["South Korea", "Republic of Korea"],
        "PS": [
            "Israel, the West Bank and Gaza",
            "The Occupied Palestinian Territories",
            "West Bank and Gaza",
            "Israel and Palestine",
            "Israel, The West Bank and Gaza",
        ],
        "IL": ["Israel and Palestine", "Israel, The West Bank and Gaza", "Israel, the West Bank and Gaza"],
        "VA": ["Holy See", "Vatican City"],
        "MK": ["North Macedonia"],
        "SZ": ["Eswatini", "Swaziland"],
        "CV": ["Cabo Verde", "Cape Verde"],
        "TL": ["Timor-Leste", "East Timor"],
        "GM": ["The Gambia", "Gambia"],
        "BS": ["The Bahamas", "Bahamas"],
        "US": ["USA", "United States of America"],
        "GB": ["United Kingdom", "UK"],
        "FM": ["Micronesia"],
        "ST": ["Sao Tome and Principe"],
        "KN": ["St Kitts and Nevis", "Saint Kitts and Nevis"],
        "LC": ["St Lucia", "Saint Lucia"],
        "VC": ["St Vincent and the Grenadines", "Saint Vincent and the Grenadines"],
        "BL": ["St Barthelemy", "Saint Barthelemy"],
        "MF": ["St Martin", "Saint Martin"],
        "PM": ["St Pierre and Miquelon", "Saint Pierre and Miquelon"],
        "SH": ["St Helena, Ascension and Tristan da Cunha", "Saint Helena"],
        "HK": ["Hong Kong"],
        "MO": ["Macao", "Macau"],
        "BA": ["Bosnia and Herzegovina", "Bosnia-Herzegovina"],
        "VN": ["Vietnam"],
        "LA": ["Laos"],
        "RU": ["Russia"],
        "SY": ["Syria"],
        "IR": ["Iran"],
        "MD": ["Moldova"],
        "BN": ["Brunei"],
        "BO": ["Bolivia"],
        "VE": ["Venezuela"],
        "TZ": ["Tanzania"],
        "CW": ["Curacao"],
    },
    "nl": {
        "PS": ["Palestijnse Gebieden"],
        "CD": ["Congo (Democratische Republiek)", "Democratische Republiek Congo"],
        "CG": ["Congo (Republiek)", "Republiek Congo"],
        "US": ["Verenigde Staten van Amerika"],
        "MK": ["Noord-Macedonie"],
        "CZ": ["Tsjechie"],
    },
    "de": {
        "CD": ["Kongo, Demokratische Republik", "Demokratische Republik Kongo"],
        "CG": ["Kongo, Republik", "Republik Kongo"],
        "KR": ["Korea, Republik", "Republik Korea", "Suedkorea"],
        "KP": ["Korea, Demokratische Volksrepublik", "Nordkorea"],
        "PS": ["Palaestinensische Gebiete"],
        "US": ["USA", "Vereinigte Staaten"],
        "CI": ["Cote d'Ivoire", "Elfenbeinkueste"],
        "VA": ["Heiliger Stuhl", "Vatikanstadt"],
    },
    "fr": {
        "US": ["Etats-Unis", "Etats Unis"],
        "PS": ["Israel et Territoires palestiniens", "Territoires palestiniens", "Israel Palestine"],
        "IL": ["Israel et Territoires palestiniens", "Israel Palestine"],
        "CD": ["Republique democratique du Congo", "RDC"],
        "CG": ["Congo"],
    },
    "da": {
        "PS": ["De palaestinensiske omraader", "Palaestina"],
        "CD": ["Den Demokratiske Republik Congo", "DR Congo"],
        "CG": ["Republikken Congo", "Congo"],
        "US": ["USA"],
        "CI": ["Elfenbenskysten"],
    },
    "sv": {
        "PS": ["Palestina"],
        "CD": ["Demokratiska republiken Kongo", "Kongo-Kinshasa"],
        "CG": ["Republiken Kongo", "Kongo-Brazzaville"],
        "US": ["USA"],
    },
}


# Aanvullingen uit de dekkingscontrole (scripts/dekking.py), november 2026.
_EXTRA: dict[str, dict[str, list[str]]] = {
    "nl": {
        "BS": ["Bahamas"],
        "BY": ["Belarus Wit-Rusland", "Wit-Rusland"],
        "BQ": ["Bonaire"],
        "BN": ["Brunei Darussalam"],
        "CG": ["Congo de Republiek"],
        "HK": ["Hongkong"],
        "MO": ["Macau SAR", "Macau"],
        "FM": ["Micronesie"],
        "SJ": ["Spitsbergen"],
        "SD": ["Sudan"],
        "TK": ["Tokelau-eilanden"],
        "UG": ["Uganda"],
        "SS": ["Zuid-Sudan"],
    },
    "en": {
        "FM": ["Federated States of Micronesia", "Micronesia (FSM)"],
        "PS": ["Palestine", "Gaza", "The West Bank"],
        "PN": ["Pitcairn Island"],
        "KG": ["The Kyrgyz Republic", "Kyrgyz Republic"],
        "CG": ["Republic of Congo"],
        "NR": ["Naoero"],
        "CD": ["Democratic Republic of Congo"],
        "MP": ["Northern Marianas"],
        "PM": ["Saint-Pierre-et-Miquelon"],
        "VI": ["Virgin Islands (U.S.)", "US Virgin Islands"],
        "BQ": ["Bonaire"],
        "MF": ["French Saint Martin"],
    },
    "fr": {
        "MM": ["Birmanie"],
        "GW": ["Guinee-Bissao"],
        "HK": ["Hong-Kong"],
        "FJ": ["Iles Fidji"],
        "MO": ["Macao"],
        "PW": ["Republique des Palaos"],
        "CZ": ["Republique tcheque"],
        "VN": ["Vietnam"],
    },
    "da": {"KP": ["Nordkorea", "Nord-Korea"], "TW": ["Taiwan", "Taipei"], "TL": ["Østtimor"]},
    "de": {
        "HK": ["Hongkong"],
        "MO": ["Macao"],
        "CG": ["Kongo"],
        "MD": ["Moldau"],
        "PS": ["Palaestina", "Palästinensisches Gebiet"],
        "RU": ["Russische Foederation", "Russische Föderation"],
        "TW": ["Taiwan Chinesisches Taipei", "Taiwan"],
        "CZ": ["Tschechische Republik"],
        "PR": ["Puerto Rico"],
        "VI": ["US Virgin Islands"],
    },
}
for _taal, _tabel in _EXTRA.items():
    for _iso, _namen in _tabel.items():
        ALIASSEN.setdefault(_taal, {}).setdefault(_iso, []).extend(_namen)


def normaliseer(s: str) -> str:
    """'Côte d’Ivoire' -> 'cote d ivoire'; 'tyrkiet/' -> 'tyrkiet'. Ook voor slugs."""
    s = s.replace("ß", "ss").replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
    s = s.replace("Æ", "Ae").replace("Ø", "Oe").replace("Å", "Aa")
    # Duitse umlaut-transcriptie (ue/oe/ae) en de varianten zonder: beide normaliseren naar a/o/u
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


_STOPWOORDEN = {"the", "and", "en", "et", "und", "og", "och", "de", "la", "le", "les", "l", "des", "du"}


def _varianten(s: str) -> set[str]:
    """Genormaliseerde varianten van een naam, zodat kleine verschillen niet uitmaken.

    - zonder lidwoorden/voegwoorden: 'Gambia, The' = 'Gambia'; 'Trinidad & Tobago' = 'Trinidad and Tobago'
    - zonder toevoeging tussen haakjes: 'Myanmar (Birma)' = 'Myanmar'
    - Duitse/Scandinavische transcripties: 'tuerkei' = 'türkei'; 'oesttimor' = 'østtimor'
    """
    basis = {s, re.sub(r"\([^)]*\)", " ", s)}
    vs: set[str] = set()
    for b in basis:
        n = " ".join(w for w in normaliseer(b.replace("&", " and ")).split() if w not in _STOPWOORDEN)
        if not n:
            continue
        vs.add(n)
        vs.add(re.sub(r"(?<=[aou])e", "", n))
        vs.add(n.replace("aa", "a").replace("oe", "o").replace("ae", "a"))
    return vs


@cache
def _locale(taal: str) -> Locale:
    return Locale(taal)


def alle_landen() -> list[str]:
    """Alle ISO 3166-1 alpha-2 codes die CLDR als land kent (geen regio's als '150')."""
    return sorted(
        c
        for c in _locale("en").territories
        if re.fullmatch(r"[A-Z]{2}", c) and c not in {"ZZ", "EU", "EZ", "UN", "QO", "XA", "XB"}
    )


def naam(iso: str, taal: str = "nl") -> str:
    return _locale(taal).territories.get(iso, iso)


@cache
def _sleutels(iso: str, taal: str) -> frozenset[str]:
    namen = [naam(iso, taal)] + ALIASSEN.get(taal, {}).get(iso, [])
    out: set[str] = set()
    for n in namen:
        out |= _varianten(n)
    return frozenset(out)


@cache
def _volledig(iso: str, taal: str) -> frozenset[str]:
    """Alleen de volledige genormaliseerde namen (zonder varianten)."""
    return frozenset(normaliseer(n) for n in [naam(iso, taal)] + ALIASSEN.get(taal, {}).get(iso, []))


def koppel(iso: str, taal: str, kandidaten: dict):
    """Zoek in {bronnaam_of_slug: waarde} de kandidaat die bij `iso` hoort, in taal `taal`.

    Eerst op volledige naam ('congo kinshasa'), pas daarna op varianten ('congo'), zodat een
    ingekorte variant nooit een exacte naam van een ander land wint. Geeft de waarde of None.
    """
    volledig = _volledig(iso, taal)
    for k, v in kandidaten.items():
        if normaliseer(k) in volledig:
            return v
    gezocht = _sleutels(iso, taal)
    for k, v in kandidaten.items():
        if _varianten(k) & gezocht:
            return v
    return None


@cache
def _zoektabel() -> dict[str, str]:
    tabel: dict[str, str] = {}
    for iso in alle_landen():
        for taal in ("nl", "en"):
            for k in _sleutels(iso, taal):
                tabel.setdefault(k, iso)
    return tabel


def zoek(invoer: str) -> str | None:
    """'TR', 'Turkije', 'turkey' -> 'TR'."""
    s = invoer.strip()
    if re.fullmatch(r"[A-Za-z]{2}", s) and s.upper() in alle_landen():
        return s.upper()
    for v in _varianten(s):
        if v in _zoektabel():
            return _zoektabel()[v]
    return None
