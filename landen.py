"""Bouwt het landenregister: koppelt de landaanduiding van elke bron aan één land.

Elke overheid noemt hetzelfde land anders — 'thailand', 'thailande', 'Thailand', 'TH'.
Dit script legt die koppeling één keer vast in data/landen.json, zodat het ophalen
zelf daar niets meer over hoeft uit te zoeken. Draait los van de dagelijkse ophaalronde:
alleen als er een land bijkomt of een site zijn adressen verandert.
"""

import html
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from bronnen.gedeeld import haal_json, haal_tekst

HIER = Path(__file__).parent
UITVOER = HIER / "data" / "landen.json"

NAMENLIJST = (
    "https://raw.githubusercontent.com/mledoze/countries/master/dist/"
    "countries-unescaped.json"
)
NL_SITEMAP = "https://www.nederlandwereldwijd.nl/reisadvies/sitemap.xml"
VK_INDEX = "https://www.gov.uk/api/content/foreign-travel-advice"
FR_INDEX = "https://www.diplomatie.gouv.fr/fr/conseils-aux-voyageurs"
DE_OPENDATA = "https://www.auswaertiges-amt.de/opendata/travelwarning"
VS_RSS = "https://travel.state.gov/_res/rss/TAsTWs.xml"

# Woorden die in de ene taal wel en de andere niet in de landsnaam staan.
LIDWOORDEN = {
    "de", "het", "den", "der", "die", "das", "la", "le", "les", "el", "los",
    "the", "of", "and", "en", "und", "et", "du", "des", "di", "da", "van",
    "republiek", "republic", "republique", "republik",
}

# Landen waar geen enkele naamvariant overeenkomt. Met de hand vastgesteld en
# nagelopen tegen de bronpagina; de reden staat erbij zodat een opvolger het kan
# narekenen. Een waarde met meerdere codes betekent: die overheid behandelt deze
# landen op één pagina.
UITZONDERINGEN = {
    # Nederland
    "belaruswitrusland": ["BY"],
    "congodemocratische": ["CD"],
    "kaaimaneilanden": ["KY"],
    "macausar": ["MO"],
    "spitsbergen": ["SJ"],          # Spitsbergen valt onder Svalbard en Jan Mayen
    "tokelaueilanden": ["TK"],
    "zuidsudan": ["SS"],
    "bonaire": ["BQ"],              # zie OVERSLAAN voor Saba en Sint-Eustatius
    # Verenigd Koninkrijk
    "stvincentgrenadines": ["VC"],
    "stmaarten": ["SX"],
    "pitcairnisland": ["PN"],
    "antarcticabritishantarcticterritory": ["AQ"],
    "cookislandstokelauniue": ["CK", "TK", "NU"],
    "stmartinstbarthelemy": ["MF", "BL"],
    "bonairesteustatiussaba": ["BQ"],
    # Frankrijk
    "guineebissao": ["GW"],
    "ilesfidji": ["FJ"],
    "kirghizstan": ["KG"],
    "palaos": ["PW"],
    "saintehelene": ["SH"],
    "vaticansaintsiege": ["VA"],
    "israelterritoirespalestiniens": ["IL", "PS"],
    "israelpalestine": ["IL", "PS"],
    # Verenigde Staten
    "mexicotraveladvisory": ["MX"],
    "gaza": ["PS"],
    "westbank": ["PS"],
}

# Bronpagina's die geen land zijn, of die zo veel landen bundelen dat er geen
# zinnig advies per land uit te halen is. Bewust overgeslagen, niet vergeten.
OVERSLAAN = {
    "arctique", "europe",                       # Frankrijk: regiopagina's
    "mainlandchinahongkongmacauseesummaries",   # VS: verwijspagina zonder niveau
    "frenchwestindies",                         # VS: bundelt vier gebieden
    # Nederland publiceert Bonaire, Saba en Sint-Eustatius apart, maar de andere
    # overheden kennen alleen het gezamenlijke Caribisch Nederland (BQ). We volgen
    # Bonaire; de twee andere zouden hetzelfde vakje overschrijven.
    "saba", "sinteustatius",
}


def normaliseer(tekst):
    """Maakt namen vergelijkbaar: zonder accenten, leestekens en lidwoorden."""
    if not tekst:
        return ""
    tekst = unicodedata.normalize("NFKD", str(tekst))
    tekst = "".join(t for t in tekst if not unicodedata.combining(t))
    tekst = tekst.lower().replace("&", " en ")
    woorden = [w for w in re.split(r"[^a-z0-9]+", tekst) if w and w not in LIDWOORDEN]
    return "".join(woorden)


def bouw_naamindex(landen):
    """Alle bekende schrijfwijzen van elk land -> ISO2."""
    index = {}

    def voeg_toe(naam, iso2):
        sleutel = normaliseer(naam)
        # Eerste treffer wint: de officiële lijst gaat voor op bijnamen.
        if sleutel and sleutel not in index:
            index[sleutel] = iso2

    for land in landen:
        iso2 = land.get("cca2")
        if not iso2:
            continue
        naam = land.get("name", {})
        voeg_toe(naam.get("common"), iso2)
        voeg_toe(naam.get("official"), iso2)
        for taal in ("nld", "fra", "deu", "spa", "por", "ita"):
            vertaling = land.get("translations", {}).get(taal) or {}
            voeg_toe(vertaling.get("common"), iso2)
            voeg_toe(vertaling.get("official"), iso2)
        for variant in land.get("altSpellings", []):
            voeg_toe(variant, iso2)
        # Codes buiten de lidwoordenfilter om: 'ET' en 'LA' zijn Ethiopië en Laos,
        # geen Franse en Spaanse lidwoorden.
        index.setdefault(iso2.lower(), iso2)
        if land.get("cca3"):
            index.setdefault(land["cca3"].lower(), iso2)
    return index


def zoek_iso2(naam, index):
    """Geeft de lijst ISO2-codes waar deze bronaanduiding bij hoort."""
    rauw = re.sub(r"[^a-z0-9]+", "", str(naam or "").lower())
    if len(rauw) in (2, 3) and rauw in index:
        return [index[rauw]]
    sleutel = normaliseer(naam)
    if sleutel in OVERSLAAN:
        return []
    if sleutel in UITZONDERINGEN:
        return list(UITZONDERINGEN[sleutel])
    gevonden = index.get(sleutel)
    return [gevonden] if gevonden else []


def haal_namenlijst():
    """Landnamen in het Nederlands, Frans, Duits en Engels, met ISO-code."""
    return haal_json(NAMENLIJST)


def haal_nl_slugs():
    """Nederland publiceert zijn reisadviezen in een eigen sitemap."""
    xml = haal_tekst(NL_SITEMAP)
    return sorted(set(re.findall(
        r"<loc>https://www\.nederlandwereldwijd\.nl/reisadvies/([a-z0-9-]+)</loc>", xml)))


def haal_vk_slugs():
    """De GOV.UK-koppeling geeft alle landen als onderliggende pagina's."""
    gegevens = haal_json(VK_INDEX)
    uit = {}
    for kind in gegevens.get("links", {}).get("children", []):
        pad = kind.get("base_path", "")
        titel = kind.get("title", "")
        slug = pad.rsplit("/", 1)[-1]
        if slug:
            # 'Thailand travel advice' -> 'Thailand'
            uit[slug] = re.sub(r"\s+travel advice$", "", titel).strip()
    return uit


def haal_fr_slugs():
    """Frankrijk noemt zijn landpagina's alleen in de sitemap, niet in een index."""
    index = haal_tekst("https://www.diplomatie.gouv.fr/sitemap.xml")
    slugs = set()
    for deel in re.findall(r"<loc>([^<]+)</loc>", index):
        try:
            xml = haal_tekst(deel)
        except OphaalFout:
            continue
        slugs.update(re.findall(r"/fr/information-par-pays/([a-z0-9-]+)", xml))
    # De index bevat ook niet-landen.
    slugs -= {"alertes", "dernieres-minutes", "conseils-par-pays-destination"}
    return sorted(slugs)


def haal_de_landen():
    """Duitsland levert alle landen in één keer, met ISO-code."""
    antwoord = haal_json(DE_OPENDATA).get("response", {})
    uit = {}
    for sleutel, item in antwoord.items():
        if not isinstance(item, dict) or "countryCode" not in item:
            continue
        uit[item["countryCode"]] = {
            "id": sleutel,
            "naam": item.get("countryName", ""),
        }
    return uit


def haal_vs_landen():
    """De Amerikaanse RSS bevat elk land als 'Land - Level N: ...'."""
    xml = haal_tekst(VS_RSS)
    namen = set()
    for titel in re.findall(r"<title>([^<]+)</title>", xml):
        titel = html.unescape(titel)
        treffer = re.match(r"^(.*?)\s+-\s+Level\s+[1-4]\b", titel.strip())
        if treffer:
            namen.add(treffer.group(1).strip())
    return sorted(namen)


def bouw_register():
    print("Landnamen ophalen…", flush=True)
    namenlijst = haal_namenlijst()
    index = bouw_naamindex(namenlijst)

    nederlands = {}
    for land in namenlijst:
        iso2 = land.get("cca2")
        vertaling = land.get("translations", {}).get("nld") or {}
        nederlands[iso2] = vertaling.get("common") or land.get("name", {}).get("common")

    print("Bronlijsten ophalen…", flush=True)
    nl_slugs = haal_nl_slugs()
    vk_slugs = haal_vk_slugs()
    fr_slugs = haal_fr_slugs()
    de_landen = haal_de_landen()
    vs_namen = haal_vs_landen()
    print(f"  NL {len(nl_slugs)} · VK {len(vk_slugs)} · FR {len(fr_slugs)} · "
          f"DE {len(de_landen)} · VS {len(vs_namen)}", flush=True)

    register = {}
    niet_gekoppeld = {"nl": [], "vk": [], "fr": [], "de": [], "vs": []}

    def regel(iso2):
        return register.setdefault(iso2, {
            "iso2": iso2,
            "naam": nederlands.get(iso2) or iso2,
            "nl_slug": None, "vk_slug": None, "fr_slug": None,
            "de_iso2": None, "vs_naam": None,
        })

    for slug in nl_slugs:
        codes = zoek_iso2(slug, index)
        for iso2 in codes:
            regel(iso2)["nl_slug"] = slug
        if not codes and normaliseer(slug) not in OVERSLAAN:
            niet_gekoppeld["nl"].append(slug)

    for slug, titel in vk_slugs.items():
        codes = zoek_iso2(titel, index) or zoek_iso2(slug, index)
        for iso2 in codes:
            regel(iso2)["vk_slug"] = slug
        if not codes and normaliseer(slug) not in OVERSLAAN:
            niet_gekoppeld["vk"].append(f"{slug} ({titel})")

    for slug in fr_slugs:
        codes = zoek_iso2(slug, index)
        for iso2 in codes:
            regel(iso2)["fr_slug"] = slug
        if not codes and normaliseer(slug) not in OVERSLAAN:
            niet_gekoppeld["fr"].append(slug)

    for iso2, gegevens in de_landen.items():
        if zoek_iso2(iso2, index):
            regel(iso2)["de_iso2"] = iso2
        else:
            niet_gekoppeld["de"].append(f"{iso2} ({gegevens['naam']})")

    for naam in vs_namen:
        codes = zoek_iso2(naam, index)
        for iso2 in codes:
            regel(iso2)["vs_naam"] = naam
        if not codes and normaliseer(naam) not in OVERSLAAN:
            niet_gekoppeld["vs"].append(naam)

    landen = sorted(register.values(), key=lambda r: r["naam"])
    return landen, niet_gekoppeld


def main():
    landen, niet_gekoppeld = bouw_register()

    totaal = len(landen)
    print(f"\n{totaal} landen in het register.")
    for bron in ("nl", "vk", "fr", "de", "vs"):
        sleutel = {"nl": "nl_slug", "vk": "vk_slug", "fr": "fr_slug",
                   "de": "de_iso2", "vs": "vs_naam"}[bron]
        aantal = sum(1 for land in landen if land[sleutel])
        print(f"  {bron.upper()}: {aantal} gekoppeld, "
              f"{len(niet_gekoppeld[bron])} niet herkend")

    for bron, lijst in niet_gekoppeld.items():
        if lijst:
            print(f"\nNiet herkend bij {bron.upper()} ({len(lijst)}):")
            for naam in lijst:
                print(f"  - {naam}")

    UITVOER.parent.mkdir(exist_ok=True)
    UITVOER.write_text(json.dumps({
        "gegenereerd_op": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "landen": landen,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nGeschreven naar {UITVOER}")
    return 0 if totaal else 1


if __name__ == "__main__":
    sys.exit(main())
