"""Verenigd Koninkrijk — Foreign, Commonwealth & Development Office.

GOV.UK geeft het niveau gestructureerd mee in 'alert_status'; de onderbouwing
staat in het onderdeel 'Warnings and insurance' van dezelfde pagina.
"""

import re

from .gedeeld import OphaalFout, citaat, haal_json, plat

API = "https://www.gov.uk/api/content/foreign-travel-advice/{slug}"
PAGINA = "https://www.gov.uk/foreign-travel-advice/{slug}"

# De zin waarmee het FCDO een advies uitspreekt. Kopjes lopen in de platte tekst
# door in de zin eronder, dus we knippen het citaat op 'FCDO advises'.
ADVIESZIN = re.compile(r"FCDO\s+advises\s+against\s+(all\s+but\s+essential\s+travel|all\s+travel)",
                       re.IGNORECASE)
HEEL_LAND = re.compile(r"\bthe\s+whole\s+(?:of|country)\b", re.IGNORECASE)


def _zinnen(tekst):
    return [z.strip() for z in re.split(r"(?<=[.!?])\s+", tekst) if z.strip()]


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

    zinnen = []
    for onderdeel in details.get("parts", []):
        if onderdeel.get("slug") == "warnings-and-insurance":
            zinnen = _zinnen(plat(onderdeel.get("body", "")))
            break

    # Alleen de zinnen waarin het FCDO daadwerkelijk een advies uitspreekt,
    # geknipt op 'FCDO advises' zodat het kopje erboven niet meelift.
    adviezen = []
    for zin in zinnen:
        # Staat de formulering er twee keer in, dan is de eerste het kopje dat in
        # de platte tekst doorloopt ("FCDO advises against all travel to Mali
        # FCDO advises against all travel to the whole of Mali…").
        treffers = list(ADVIESZIN.finditer(zin))
        if treffers:
            adviezen.append(zin[treffers[-1].start():])

    for niveau in niveaus:
        heel = niveau.endswith("_to_whole_country")
        zwaar = niveau.startswith("avoid_all_travel")
        passend = [
            zin for zin in adviezen
            if bool(HEEL_LAND.search(zin)) == heel
            and zin.lower().startswith("fcdo advises against all travel") == zwaar
        ]
        if heel:
            uit["landniveau"] = {
                "label": niveau,
                "citaat": citaat(passend[0]) if passend else "",
            }
        else:
            for zin in passend:
                uit["gebieden"].append({
                    "label": niveau,
                    "gebied": citaat(_gebied_uit(zin), 200),
                    "citaat": citaat(zin),
                })
            if not passend:
                uit["gebieden"].append({
                    "label": niveau, "gebied": "Zie de bronpagina", "citaat": "",
                })
    return uit


def _gebied_uit(zin):
    """Haalt het stuk na 'travel to' uit de advieszin; dat benoemt het gebied."""
    treffer = re.search(r"\btravel\s+to\s+(.*)", zin, re.IGNORECASE)
    return treffer.group(1).strip() if treffer else zin
