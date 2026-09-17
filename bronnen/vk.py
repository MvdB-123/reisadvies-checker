"""Verenigd Koninkrijk — Foreign, Commonwealth & Development Office.

GOV.UK geeft het niveau gestructureerd mee in 'alert_status'; de onderbouwing
staat in het onderdeel 'Warnings and insurance' van dezelfde pagina.
"""

import re

from .gedeeld import OphaalFout, citaat, haal_json, normaliseer, plat, zinnen

API = "https://www.gov.uk/api/content/foreign-travel-advice/{slug}"
PAGINA = "https://www.gov.uk/foreign-travel-advice/{slug}"

# De zin waarmee het FCDO een advies uitspreekt. Kopjes lopen in de platte tekst
# door in de zin eronder, dus we knippen het citaat op 'FCDO advises'.
ADVIESZIN = re.compile(
    r"FCDO\s+advises\s+against:?\s+(?:all\s+but\s+essential\s+travel|all\s+travel)",
    re.IGNORECASE)

# Eén losse uitspraak: een niveau plus het gebied waar het voor geldt. Ze staan
# niet altijd in een eigen zin — Saoedi-Arabië zet er twee achter elkaar:
# "FCDO advises against: all travel to within 10km of the border with Yemen
#  all but essential travel to a..." — en soms staat er een dubbele punt met
# een opsomming achter ("travel to: Garissa Town Tana River County ...").
UITSPRAAK = re.compile(
    r"\b(all\s+but\s+essential\s+travel|all\s+travel)\s+to:?\s+", re.IGNORECASE)
HEEL_LAND = re.compile(r"\bthe\s+whole\s+(?:of|country)\b", re.IGNORECASE)



def haal_alles(register, alleen=None):
    resultaat = {}
    for land in register:
        slug = land.get("vk_slug")
        if not slug or (alleen is not None and land["iso2"] not in alleen):
            continue
        resultaat[land["iso2"]] = _haal_land(slug)
    return resultaat


def _haal_land(slug):
    uit = {
        "gelukt": False, "bron_url": PAGINA.format(slug=slug), "gewijzigd_op": None,
        "landniveau": None, "gebieden": [], "opmerking": None,
    }
    try:
        gegevens = haal_json(API.format(slug=slug))
    except OphaalFout as fout:
        uit["opmerking"] = f"Niet opgehaald: {fout}"
        return uit

    uit["gelukt"] = True
    uit["gewijzigd_op"] = (gegevens.get("public_updated_at") or "")[:10] or None
    details = gegevens.get("details", {})
    niveaus = details.get("alert_status") or []

    if not niveaus:
        # Het VK publiceert alleen negatieve adviezen. Zwijgen betekent hier:
        # geen advies tegen reizen. Dat expliciet tonen is eerlijker dan een leeg
        # vakje, dat leest als 'niet opgehaald'.
        # Geen enkel advies: het VK maakt dan ook geen kaart voor dit land.
        uit["landniveau"] = {"label": "geen_advies_land", "citaat": ""}
        return uit

    waarschuwingen = []
    for onderdeel in details.get("parts", []):
        if onderdeel.get("slug") == "warnings-and-insurance":
            waarschuwingen = zinnen(plat(onderdeel.get("body", "")))
            break

    # Het niveau leiden we af uit de tekst zelf en niet uit alert_status: het VK
    # schrijft lang niet altijd 'the whole of', en soms wijkt de tekst af van het
    # gestructureerde veld. alert_status blijft het vangnet.
    #
    # Eén zin kan meerdere uitspraken bevatten: bij Kenia staan 'all travel to'
    # en 'all but essential travel to' achter elkaar zonder punt ertussen. Elk
    # citaat begint daarom bij zijn eigen 'FCDO advises against' en loopt tot de
    # volgende uitspraak, zodat het letterlijk en op zichzelf leesbaar blijft.
    landsnaam = normaliseer(slug.replace("-", " "))
    geduid = []
    for zin in waarschuwingen:
        inleidingen = list(ADVIESZIN.finditer(zin))
        if not inleidingen:
            continue
        uitspraken = list(UITSPRAAK.finditer(zin))
        for nummer, treffer in enumerate(uitspraken):
            grens = (uitspraken[nummer + 1].start() if nummer + 1 < len(uitspraken)
                     else len(zin))
            doeltekst = zin[treffer.end():grens].strip(" .,;:")
            if not doeltekst:
                continue
            eerder = [i.start() for i in inleidingen if i.start() <= treffer.start()]
            citaattekst = zin[(eerder[-1] if eerder else treffer.start()):grens]
            zwaar = treffer.group(1).lower().strip() == "all travel"
            heel = _is_heel_land(doeltekst, landsnaam)
            label = ("avoid_all_travel" if zwaar
                     else "avoid_all_but_essential_travel") \
                + ("_to_whole_country" if heel else "_to_parts")
            geduid.append((label, citaattekst.strip(), doeltekst, heel))

    for label, tekst, _doel, heel in geduid:
        if heel and not uit["landniveau"]:
            uit["landniveau"] = {"label": label, "citaat": citaat(tekst)}

    # Loopt een kopje door in de zin ("…all but essential travel to Cuba Protests
    # in Cuba The ongoing situation…"), dan herkennen we het land niet exact.
    # Zegt alert_status dat het om het hele land gaat, dan geeft dat de doorslag.
    if not uit["landniveau"] and any(n.endswith("_to_whole_country") for n in niveaus):
        for label, tekst, doeltekst, _heel in geduid:
            if normaliseer(doeltekst).startswith(landsnaam):
                heel_label = next(n for n in niveaus if n.endswith("_to_whole_country"))
                uit["landniveau"] = {"label": heel_label, "citaat": citaat(tekst)}
                break

    for label, tekst, doeltekst, heel in geduid:
        # Zinnen die het land zelf noemen herhalen het landniveau; dat is geen
        # apart gebied.
        if heel or normaliseer(doeltekst).startswith(landsnaam):
            continue
        if uit["landniveau"] and citaat(tekst) == uit["landniveau"]["citaat"]:
            continue
        uit["gebieden"].append({
            "label": label,
            "gebied": citaat(doeltekst, 200),
            "citaat": citaat(tekst),
        })

    # Staat er in alert_status een niveau waar geen tekst bij te vinden is, dan
    # melden we dat met zoveel woorden. Geen kleurcode zonder bron, maar ook
    # niet stilzwijgend weglaten wat het VK wél zegt.
    gebruikt = {label for label, *_ in geduid}
    if uit["landniveau"]:
        gebruikt.add(uit["landniveau"]["label"])
    gebruikt.update(g["label"] for g in uit["gebieden"])
    # Gelden alle adviezen alleen voor delen van het land, dan is de rest op hun
    # kaart groen: het VK kleurt precies de gebieden die het afraadt, en maakt
    # helemaal geen kaart voor een land zonder advies. De rest is dus per
    # definitie het gebied waartegen niets is geadviseerd.
    if not uit["landniveau"] and uit["gebieden"]:
        uit["landniveau"] = {"label": "geen_advies_rest", "citaat": ""}

    ontbreekt = [n for n in niveaus if n not in gebruikt]
    if ontbreekt:
        uit["opmerking"] = (
            "Het VK vermeldt in zijn gegevens ook: "
            + ", ".join(sorted(ontbreekt))
            + ". De bijbehorende tekst staat niet in het onderdeel dat wij lezen; "
            "zie de bronpagina."
        )
    return uit


def _is_heel_land(doeltekst, landsnaam):
    """Gaat dit advies over het land als geheel, of over een gebied erbinnen?"""
    if HEEL_LAND.search(doeltekst):
        return True
    doel = normaliseer(doeltekst)
    if not doel or not landsnaam:
        return False
    # 'Afghanistan.' telt; 'Afghanistan, even if you are part of a tour group'
    # is dezelfde uitspraak met een staart, en 'the north of Afghanistan' niet.
    return doel == landsnaam


def _gebied_uit(zin):
    """Haalt het stuk na 'travel to' uit de advieszin; dat benoemt het gebied."""
    treffer = re.search(r"\btravel\s+to\s+(.*)", zin, re.IGNORECASE)
    return treffer.group(1).strip() if treffer else zin
