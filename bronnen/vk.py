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
ADVIESZIN = re.compile(r"FCDO\s+advises\s+against\s+(all\s+but\s+essential\s+travel|all\s+travel)",
                       re.IGNORECASE)
HEEL_LAND = re.compile(r"\bthe\s+whole\s+(?:of|country)\b", re.IGNORECASE)
ZWAAR = re.compile(r"against\s+all\s+travel\b", re.IGNORECASE)
DOELWIT = re.compile(r"\btravel\s+to\s+(.*)", re.IGNORECASE)


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
        uit["opmerking"] = (
            "Het VK raadt geen reizen naar dit land af. Het VK geeft geen "
            "'veilig'-niveau af, dus dit is geen kleurcode."
        )
        return uit

    waarschuwingen = []
    for onderdeel in details.get("parts", []):
        if onderdeel.get("slug") == "warnings-and-insurance":
            waarschuwingen = zinnen(plat(onderdeel.get("body", "")))
            break

    # Alleen de zinnen waarin het FCDO daadwerkelijk een advies uitspreekt,
    # geknipt op 'FCDO advises' zodat het kopje erboven niet meelift. Staat de
    # formulering er twee keer in, dan is de eerste het kopje dat doorloopt.
    adviezen = []
    for zin in waarschuwingen:
        treffers = list(ADVIESZIN.finditer(zin))
        if treffers:
            adviezen.append(zin[treffers[-1].start():])

    # Het niveau leiden we af uit de zin zelf en niet uit alert_status: het VK
    # schrijft lang niet altijd 'the whole of', en soms wijkt de tekst af van
    # het gestructureerde veld. alert_status blijft het vangnet.
    landsnaam = normaliseer(slug.replace("-", " "))
    geduid = []
    for zin in sorted(adviezen, key=len):
        doel = DOELWIT.search(zin)
        doeltekst = doel.group(1).strip(" .") if doel else ""
        zwaar = bool(ZWAAR.search(zin))
        heel = _is_heel_land(doeltekst, landsnaam)
        label = ("avoid_all_travel" if zwaar else "avoid_all_but_essential_travel") \
            + ("_to_whole_country" if heel else "_to_parts")
        geduid.append((label, zin, doeltekst, heel))

    for label, zin, _doel, heel in geduid:
        if heel and not uit["landniveau"]:
            uit["landniveau"] = {"label": label, "citaat": citaat(zin)}

    # Loopt een kopje door in de zin ("…all but essential travel to Cuba Protests
    # in Cuba The ongoing situation…"), dan herkennen we het land niet exact.
    # Zegt alert_status dat het om het hele land gaat, dan geeft dat de doorslag.
    if not uit["landniveau"] and any(n.endswith("_to_whole_country") for n in niveaus):
        for label, zin, doeltekst, _heel in geduid:
            if normaliseer(doeltekst).startswith(landsnaam):
                heel_label = next(n for n in niveaus if n.endswith("_to_whole_country"))
                uit["landniveau"] = {"label": heel_label, "citaat": citaat(zin)}
                break

    for label, zin, doeltekst, heel in geduid:
        # Zinnen die het land zelf noemen zijn een herhaling van het landniveau,
        # geen apart gebied. Zonder doelgebied ("advises against all travel, to
        # leave these areas") wijst de zin niets aan en hoort hij er ook niet bij.
        if heel or not doeltekst or normaliseer(doeltekst).startswith(landsnaam):
            continue
        if uit["landniveau"] and citaat(zin) == uit["landniveau"]["citaat"]:
            continue
        uit["gebieden"].append({
            "label": label,
            "gebied": citaat(doeltekst or zin, 200),
            "citaat": citaat(zin),
        })

    # Staat er in alert_status een niveau waar geen zin bij gevonden is, dan
    # melden we dat wel, zonder citaat. Beter een vermelding zonder bewijs dan
    # een advies dat we stilzwijgend weglaten.
    gevonden = {label for label, *_ in geduid}
    for niveau in niveaus:
        if niveau in gevonden:
            continue
        if niveau.endswith("_to_whole_country") and not uit["landniveau"]:
            uit["landniveau"] = {"label": niveau, "citaat": ""}
        elif niveau.endswith("_to_parts") and not uit["gebieden"]:
            uit["gebieden"].append({
                "label": niveau, "gebied": "Zie de bronpagina", "citaat": "",
            })
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
