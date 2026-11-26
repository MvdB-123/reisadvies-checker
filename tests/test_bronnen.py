"""Parsers testen op vastgelegde pagina's (stand 19-11-2026), zonder netwerk.

Fixtures vernieuwen: zie tests/README.md. De verwachte waarden hieronder zijn met de hand
gecontroleerd tegen de bronpagina's van die datum.
"""

from __future__ import annotations

import gzip
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from reisadvies.model import Kleur, Soort, Status
from reisadvies.sources import at, au, ca, de, dk, fr, ie, nl, se, uk, us

F = Path(__file__).parent / "fixtures"


def lees(naam: str) -> str:
    return gzip.decompress((F / f"{naam}.gz").read_bytes()).decode("utf-8")


def kleuren(adv):
    return sorted({g.niveau.kleur.value for g in adv.gebieden if g.niveau.kleur})


# ---------- Nederland ----------


def test_nl_turkije_regionaal():
    a = nl.parse(lees("nl_TR.html"), "TR", "u")
    assert a.status == Status.OK
    assert a.landelijk.kleur == Kleur.GEEL and a.landelijk.soort == Soort.LETTERLIJK
    assert a.gewijzigd_op == "2026-10-16"
    assert kleuren(a) == ["oranje", "rood"]
    assert any("Syrië" in g.omschrijving for g in a.gebieden)


def test_nl_oekraine_heel_land_rood():
    a = nl.parse(lees("nl_UA.html"), "UA", "u")
    assert a.landelijk.kleur == Kleur.ROOD
    assert a.gewijzigd_op == "2026-10-20"


# ---------- Verenigd Koninkrijk ----------


def test_uk_turkije_geen_groen_geel_onderscheid():
    a = uk.parse(json.loads(lees("uk_TR.json")), "TR")
    assert a.landelijk.kleur is None and a.landelijk.soort == Soort.BESTAAT_NIET
    assert [g.niveau.kleur for g in a.gebieden] == [Kleur.ROOD]
    assert "Syria" in a.gebieden[0].omschrijving
    assert "delen van het land" not in a.landelijk.toelichting  # gebieden staan in de kolom ernaast


def test_uk_oekraine_gebieden_met_lijsten():
    a = uk.parse(json.loads(lees("uk_UA.json")), "UA")
    namen = [g.omschrijving for g in a.gebieden]
    assert "Crimea" in namen
    assert any(n.startswith("All parts:") and "Lviv" in n for n in namen)
    assert kleuren(a) == ["oranje", "rood"]


# ---------- Frankrijk ----------


def test_fr_turkije_laagste_kleur_is_afgeleid():
    a = fr.parse(lees("fr_TR.html"), "TR", "u")
    assert a.landelijk.kleur == Kleur.GEEL
    assert a.landelijk.soort == Soort.AFGELEID  # rest van het land staat alleen op de kaart
    assert kleuren(a) == ["oranje", "rood"]
    assert a.gewijzigd_op == "2026-03-23"


def test_fr_oekraine_kop_zonder_kaartkleur():
    a = fr.parse(lees("fr_UA.html"), "UA", "u")
    assert a.landelijk.kleur == Kleur.ROOD


def test_fr_israel_landnaam_in_zin():
    """'Il demeure déconseillé aux ressortissants français, sauf pour des raisons impératives, de se
    rendre en Israël.' -> landelijk oranje. De gebieden staan onder vrije koppen en tellen niet."""
    a = fr.parse(lees("fr_IL.html"), "IL", "u")
    assert a.landelijk.kleur == Kleur.ORANJE and a.landelijk.soort == Soort.LETTERLIJK
    assert "Golan" in a.brontekst


def test_fr_vrije_tekst_wordt_niet_geinterpreteerd():
    html = (
        "<h3>Zones de vigilance</h3><p>Les voyages non essentiels vers l’île sont déconseillés.</p>"
        "<h3>Risques</h3>"
    )
    a = fr.parse(html, "CU", "u")
    assert a.landelijk is None and "vrije tekst" in a.melding


# ---------- Duitsland ----------


def test_de_oekraine_reisewarnung():
    a = de.parse("201946", json.loads(lees("de_UA.json")), "UA")
    assert a.landelijk.kleur == Kleur.ROOD and a.landelijk.bronlabel.startswith("Reisewarnung")
    assert a.url.endswith("/201946")


def test_de_turkije_geen_waarschuwing():
    a = de.parse("201962", json.loads(lees("de_TR.json")), "TR")
    assert a.landelijk.kleur is None and a.landelijk.soort == Soort.BESTAAT_NIET
    assert a.gewijzigd_op == "2026-11-06"


# ---------- Zweden ----------


def test_se_turkije_alleen_gebieden():
    a = se.parse(lees("se_TR.html"), "TR", "u")
    assert a.landelijk.kleur is None  # geen avrådan voor heel Turkije
    assert kleuren(a) == ["oranje", "rood"]
    assert a.gewijzigd_op == "2022-03-28"  # besluit over de avrådan


def test_se_oekraine_ovriga_delar_is_landelijk():
    a = se.parse(lees("se_UA.html"), "UA", "u")
    assert a.landelijk.kleur == Kleur.ROOD
    assert [g.niveau.kleur for g in a.gebieden] == [Kleur.ORANJE]
    assert "Lviv" in a.gebieden[0].omschrijving


# ---------- Denemarken ----------


def test_dk_turkije_balken():
    a = dk.parse(lees("dk_TR.html"), "TR", "u")
    assert a.landelijk.kleur == Kleur.GEEL
    assert kleuren(a) == ["oranje", "rood"]
    assert a.gewijzigd_op == "2026-06-17"


def test_dk_oekraine():
    assert dk.parse(lees("dk_UA.html"), "UA", "u").landelijk.kleur == Kleur.ROOD


# ---------- Oostenrijk ----------


def test_at_turkije_rest_des_landes():
    a = at.parse(lees("at_TR.html"), "TR", "u")
    assert a.landelijk.kleur == Kleur.GEEL
    assert kleuren(a) == ["oranje", "rood"]
    assert a.gewijzigd_op == "2026-10-23"


def test_at_oekraine():
    assert at.parse(lees("at_UA.html"), "UA", "u").landelijk.kleur == Kleur.ROOD


# ---------- Verenigde Staten ----------


def test_us_turkije_level2_met_gebied():
    a = us.parse(ET.fromstring(lees("us_TR.xml")), "TR")
    assert a.landelijk.kleur == Kleur.GEEL
    assert [g.niveau.kleur for g in a.gebieden] == [Kleur.ROOD]
    assert a.gewijzigd_op is not None


def test_us_oekraine_level4():
    a = us.parse(ET.fromstring(lees("us_UA.xml")), "UA")
    assert a.landelijk.kleur == Kleur.ROOD
    assert a.gewijzigd_op == "2026-08-28"


# ---------- Canada ----------


def test_ca_turkije():
    a = ca.parse(lees("ca_TR.html"), "TR", "u", "2026-09-29 10:00")
    assert a.landelijk.kleur == Kleur.GEEL
    assert {g.omschrijving for g in a.gebieden} == {"Borders with Iraq and Syria", "Southeastern provinces"}
    assert a.gewijzigd_op == "2026-09-29"


def test_ca_oekraine():
    assert ca.parse(lees("ca_UA.html"), "UA", "u").landelijk.kleur == Kleur.ROOD


# ---------- Algemeen ----------


def test_een_kapotte_bron_breekt_het_overzicht_niet():
    from reisadvies.sources.base import Bron

    def stuk(iso):
        raise RuntimeError("kapot")

    a = Bron("xx", "Test", "", "en", "https://x", _ophalen=stuk).haal("TR")
    assert a.status == Status.FOUT and "kapot" in a.melding


# ---------- Regressie: brede steekproef 19-11-2026 ----------


def test_at_regionaal_hoogste_niveau_wordt_nooit_landelijk():
    """Zijbalk 'Sicherheitsstufe 4 (regional)' mag India niet landelijk rood maken."""
    a = at.parse(lees("at_IN.html"), "IN", "u")
    assert a.landelijk.kleur == Kleur.GEEL
    assert kleuren(a) == ["oranje", "rood"]
    assert a.gebieden[0].omschrijving.startswith("Regionale Reisewarnung")


def test_fr_zin_over_heel_land():
    assert fr.parse(lees("fr_SY.html"), "SY", "u").landelijk.kleur == Kleur.ROOD


def test_fr_eerstgenoemde_kleur_telt():
    """'vigilance normale ( vert ), à l'exception de ... ( jaune )' -> groen."""
    a = fr.parse(lees("fr_CN.html"), "CN", "u")
    assert a.landelijk.kleur == Kleur.GROEN and a.landelijk.soort == Soort.LETTERLIJK


def test_dk_geen_rejsevejledning():
    a = dk.parse(lees("dk_SY.html"), "SY", "u")
    assert a.status == Status.NIET_GEVONDEN


def test_dk_resten_af_landet_is_landelijk():
    a = dk.parse(lees("dk_PK.html"), "PK", "u")
    assert a.landelijk.kleur == Kleur.ORANJE
    assert kleuren(a) == ["rood"]


def test_uk_gebieden_onder_regiokoppen():
    a = uk.parse(json.loads(lees("uk_TH.json")), "TH")
    assert len(a.gebieden) >= 2
    assert all(g.niveau.kleur == Kleur.ORANJE for g in a.gebieden)
    assert any("Pattani" in g.omschrijving for g in a.gebieden)


def test_nl_kleurcode_voor_het_reisadvies():
    assert nl.parse(lees("nl_ZA.html"), "ZA", "u").landelijk.kleur == Kleur.GEEL


@pytest.mark.parametrize(
    ("zin", "kleur"),
    [
        (
            (
                "À l’exception des zones formellement déconseillées et déconseillées sauf raison impérative, "
                "le reste du territoire kényan est placé en vigilance renforcée."
            ),
            "jaune",
        ),
        (
            (
                "Dans le contexte de la guerre, il est formellement déconseillé de se rendre dans l’ensemble "
                "du territoire de la Russie."
            ),
            "rouge",
        ),
        (
            "L’ensemble du territoire chinois est placé en vigilance normale ( vert ), à l’exception de ( jaune ).",
            "vert",
        ),
        ("Le reste du territoire est déconseillé sauf raison impérative (en orange sur la carte).", "orange"),
        ("Le reste du pays est en vigilance renforcée.", "jaune"),
        ("Il est formellement déconseillé de se rendre dans le nord.", None),  # geen heel-land-zin
    ],
)
def test_fr_kleur_heel_land(zin, kleur):
    assert fr._kleur_heel_land(zin) == kleur


# ---------- Nederland via de open-data-API ----------


def _nl_api(iso):
    data = json.loads(lees(f"nl_api_{iso}.json"))
    return nl.parse(nl.api_html(data), iso, data["canonical"])


def test_nl_api_turkije():
    a = _nl_api("TR")
    assert a.landelijk.kleur == Kleur.GEEL
    assert a.gewijzigd_op == "2026-10-16"
    assert len(a.gebieden) == 4 and kleuren(a) == ["oranje", "rood"]


def test_nl_api_tips_zijn_geen_gebieden():
    """Onder 'Oranje: alleen noodzakelijke reizen' staan ook tips in lijsten; alleen de lijst na
    'Voor de volgende gebieden geldt kleurcode oranje:' telt."""
    a = _nl_api("TH")
    assert all("Blijf niet langer" not in g.omschrijving for g in a.gebieden)
    assert len(a.gebieden) == 5 and kleuren(a) == ["oranje", "rood"]
    # de rode strook staat alleen in 'In het kort' ('De kleurcode van het reisadvies is rood voor de strook ...')
    assert any(g.niveau.kleur == Kleur.ROOD and "5 kilometer" in g.omschrijving for g in a.gebieden)


def test_nl_api_zin_als_lijstitem():
    a = _nl_api("VE")
    assert a.landelijk.kleur == Kleur.ORANJE
    assert len(a.gebieden) == 6 and kleuren(a) == ["rood"]


# ---------- Duitsland: afraden staat alleen in de tekst ----------


def test_de_israel_afraden_zonder_vlag():
    """Geen vlag in de API, maar 'Von Reisen in andere Landesteile Israels ... wird abgeraten'."""
    v = json.loads(lees("de_IL.json"))
    assert not v["warning"] and not v["partialWarning"]
    a = de.parse("203814", v, "IL")
    assert a.landelijk.kleur == Kleur.ORANJE and a.landelijk.soort == Soort.AFGELEID
    assert any(g.niveau.kleur == Kleur.ROOD and "Gaza" in g.omschrijving for g in a.gebieden)
    assert all(g.niveau.kleur != Kleur.ORANJE for g in a.gebieden)  # zelfde kleur als het land weg


def test_de_nigeria_niet_genannte_gebiete_is_landelijk():
    a = de.parse("205788", json.loads(lees("de_NG.json")), "NG")
    assert a.landelijk.kleur == Kleur.ORANJE
    assert kleuren(a) == ["rood"]


def test_de_verwijzing_naar_ander_land_telt_niet():
    v = {
        "countryName": "Russische Föderation",
        "warning": True,
        "content": (
            "<p>Vor Reisen in die Russische Föderation wird gewarnt.</p>"
            "<p>Vor Reisen nach Belarus wird gewarnt, siehe Reise- und Sicherheitshinweise Belarus.</p>"
        ),
    }
    a = de.parse("1", v, "RU")
    assert a.landelijk.kleur == Kleur.ROOD and a.gebieden == []


# ---------- Zweden via regeringen.se ----------


def _se_rg(iso):
    return se.parse_regeringen(lees(f"se_rg_{iso}.html"), iso, "u")


def test_se_lijst_alle_namen_gekoppeld():
    """Een naam op UD's lijst die niet gekoppeld wordt, zou 'geen avrådan' opleveren."""
    from unittest import mock

    from reisadvies.countries import alle_landen, koppel

    with mock.patch.object(se.http, "text", return_value=lees("se_lijst.html")):
        se.ud_index.cache_clear()
        ix = se.ud_index()
    se.ud_index.cache_clear()
    gekoppeld = {koppel(iso, "sv", ix) for iso in alle_landen()} - {None}
    assert set(ix.values()) <= gekoppeld


def test_se_rusland_naam_met_haakjes_is_heel_land():
    assert _se_rg("RU").landelijk.kleur == Kleur.ROOD


def test_se_israel_ovriga_is_landelijk():
    a = _se_rg("IL")
    assert a.landelijk.kleur == Kleur.ORANJE
    assert kleuren(a) == ["rood"]
    assert a.gewijzigd_op == "2026-08-20"


def test_se_gemengde_zin_eerste_niveau_telt():
    a = _se_rg("PS")
    assert [g.niveau.kleur for g in a.gebieden] == [Kleur.ROOD]


def test_se_opgeheven_avradan():
    a = _se_rg("AE")
    assert a.landelijk.kleur is None and a.gebieden == []


def test_se_oekraine_mildere_gebieden_blijven():
    a = _se_rg("UA")
    assert a.landelijk.kleur == Kleur.ROOD
    assert kleuren(a) == ["oranje"]


@pytest.mark.parametrize(
    ("zin", "iso", "kleur"),
    [
        ("La totalité du territoire est formellement déconseillée.", "AF", "rouge"),
        ("Le territoire belge est placé en vigilance normale.", "BE", "vert"),
        (
            "L’ensemble du territoire iranien est placé en rouge sur la carte des conseils aux voyageurs.",
            "IR",
            "rouge",
        ),
        (
            "Il est déconseillé aux ressortissants français, sauf pour des raisons impératives, de se rendre au Koweït.",
            "KW",
            "orange",
        ),
    ],
)
def test_fr_meer_vaste_formuleringen(zin, iso, kleur):
    assert fr._kleur_heel_land(zin, iso) == kleur


def test_uk_brontekst_is_het_advies_niet_de_wijzigingsnotitie():
    a = uk.parse(json.loads(lees("uk_UA.json")), "UA")
    assert a.brontekst.startswith("FCDO advises against")
    assert "insurance" not in a.brontekst.lower()
    assert "Updated information" not in a.brontekst


def test_uk_oekraine_rest_van_het_land_is_landelijk_niveau():
    a = uk.parse(json.loads(lees("uk_UA.json")), "UA")
    assert a.landelijk.kleur and a.landelijk.kleur.value == "rood"
    assert not any("all other regions" in g.omschrijving for g in a.gebieden)
    assert any(g.niveau.kleur.value == "oranje" for g in a.gebieden)  # westelijke uitzonderingen


def test_uk_rest_van_een_regio_is_geen_landelijk_niveau():
    assert not uk._is_rest("the rest of the Savanes region", {"name": "Togo", "synonyms": []})
    assert uk._is_rest("the rest of Chad, including the capital", {"name": "Chad", "synonyms": []})


# ---------- Ierland (pagina's opgeslagen vanaf een kantoornetwerk, 25-11-2026) ----------


def test_ie_turkije_geel_met_rood_en_oranje_gebied():
    a = ie.parse(lees("ie_TR.html"), "TR", "x")
    assert a.landelijk.kleur == Kleur.GEEL and a.landelijk.soort == Soort.LETTERLIJK
    assert a.gewijzigd_op == "2026-09-30"  # 'Updated on', niet 'Still current at'
    assert kleuren(a) == ["oranje", "rood"]
    assert any("Hatay" in g.omschrijving for g in a.gebieden)


def test_ie_israel_oranje_en_strongly_advised_is_afgeleid():
    a = ie.parse(lees("ie_IL.html"), "IL", "x")
    assert a.landelijk.kleur == Kleur.ORANJE
    assert len(a.gebieden) == 3
    assert all(g.niveau.kleur == Kleur.ROOD and g.niveau.soort == Soort.AFGELEID for g in a.gebieden)


def test_ie_oekraine_rood_hele_land_is_geen_gebied():
    a = ie.parse(lees("ie_UA.html"), "UA", "x")
    assert a.landelijk.kleur == Kleur.ROOD
    assert a.gebieden == []
    assert a.brontekst.startswith("The Department strongly advises against all travel to Ukraine")


# ---------- Australië ----------


def test_au_turkije_niveaus_en_updated_datum():
    a = au.parse(lees("au_TR.html"), "TR", "x")
    assert a.landelijk.kleur == Kleur.GEEL
    assert a.gewijzigd_op == "2026-10-30"  # 'Updated', niet 'Still current at' (25-11)
    assert kleuren(a) == ["oranje", "rood"]
    assert a.brontekst.startswith("Exercise a high degree of caution in Türkiye overall")


def test_au_israel_en_oekraine():
    il = au.parse(lees("au_IL.html"), "IL", "x")
    assert il.landelijk.kleur == Kleur.ORANJE and kleuren(il) == ["rood"]
    ua = au.parse(lees("au_UA.html"), "UA", "x")
    assert ua.landelijk.kleur == Kleur.ROOD and ua.gebieden == []


def test_ie_en_au_geblokkeerd_wordt_handmatig_nalopen(monkeypatch):
    from reisadvies import http

    def weiger(url):
        raise http.OphaalFout(f"{url}: HTTP 403", 403)

    monkeypatch.setattr(http, "text", weiger)
    for mod in (ie, au):
        mod.index.cache_clear()
        monkeypatch.setattr(mod, "_geblokkeerd", False)
        a = mod.ophalen("TR")
        assert a.status == Status.HANDMATIG and "cloud" in a.melding
        assert mod.ophalen("UA").status == Status.HANDMATIG  # tweede land: direct, zonder wachten
        mod.index.cache_clear()


# ---------- Frankrijk: kleur afgelezen van de kaart ----------


def _kaart(vlakken):
    """Testkaart: grijze achtergrond (buurlanden) met gekleurde vlakken {kleur: aandeel}."""
    from io import BytesIO

    from PIL import Image

    im = Image.new("RGB", (100, 100), (192, 192, 192))
    y = 0
    for kleur, aandeel in vlakken.items():
        h = round(aandeel * 100)
        im.paste(fr._KAARTKLEUREN[kleur], (0, y, 100, y + h))
        y += h
    buf = BytesIO()
    im.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def test_fr_kaartkleur_grootste_oppervlak():
    kleur, aandelen = fr.kaartkleur(_kaart({"jaune": 0.5, "rouge": 0.05}))
    assert kleur == "jaune" and aandelen["rouge"] > 0.02  # JPEG vervaagt de randen iets


def test_fr_kaart_geeft_basiskleur_en_meldt_ongenoemde_strengere_gebieden():
    from bs4 import BeautifulSoup  # noqa: F401 - parse leest een minimale pagina

    html = "<main><h2>Zones de vigilance</h2><p>Il est recommandé de faire preuve de prudence.</p></main>"
    a = fr.parse(html, "KH", "x", kaart="jaune", aandelen={"jaune": 0.4, "rouge": 0.03, "orange": 0, "vert": 0})
    assert a.landelijk.kleur == Kleur.GEEL and a.landelijk.bronlabel.startswith("Vigilance renforcée")
    assert "rood" in a.melding  # rood staat op de kaart, maar niet als gebied in de tekst


def test_us_citaat_zonder_werkwoord_wordt_zichtbaar_aangevuld():
    import xml.etree.ElementTree as ET

    item = ET.fromstring(
        "<item><title>Cambodia - Level 2: Exercise Increased Caution</title><pubDate>Mon, 15 Sep 2026 00:00:00 GMT</pubDate>"
        "<link>https://x</link><description><![CDATA[<p>in <b>Cambodia </b>due to <b>crime</b>, <b>unrest</b>.</p>]]></description></item>"
    )
    a = us.parse(item, "KH")
    assert a.brontekst == "[Exercise increased caution] in Cambodia due to crime, unrest."


def test_se_belarus_avrada_infinitief_is_rood():
    """'beslutat om att avråda från alla resor' (infinitief) werd gemist en als 'Ingen avrådan' getoond."""
    html = (
        "<main><h1>Belarus - avrådan</h1>Publicerad 28 februari 2022 Med anledning av säkerhetsläget i regionen "
        "har Utrikesdepartementet den 28 februari 2022 beslutat om att avråda från alla resor till Belarus. "
        "Avrådan gäller tills vidare. Nivåer av avrådan</main>"
    )
    a = se.parse_regeringen(html, "BY", "u")
    assert a.landelijk.kleur == Kleur.ROOD


def test_se_avrada_zonder_herkend_niveau_is_nooit_geen_avradan():
    html = "<main>Publicerad 1 januari 2026 Avrådan gäller tills vidare. Nivåer av avrådan</main>"
    a = se.parse_regeringen(html, "XX", "u")
    assert a.landelijk is None and "niet automatisch herkend" in a.melding


# ---------- Herkenning uitgebreid na de controle van alle landen (26-11-2026) ----------


def test_fr_kop_en_zinvarianten_voor_het_hele_land():
    html = (
        "<main><h2>Zone de vigilance</h2><p>La vigilance est normale sur l’ensemble du territoire de l’Andorre.</p></main>"
    )
    assert fr.parse(html, "AD", "x").landelijk.kleur == Kleur.GROEN
    html = "<main><h2>Zones de vigilence</h2><p>L’ensemble de l’archipel est en vigilance renforcée.</p></main>"
    assert fr.parse(html, "BS", "x").landelijk.kleur == Kleur.GEEL
    html = "<main><h2>Zone de vigilance</h2><p>L'ensemble du territoire figure en vigilance normale.</p></main>"
    assert fr.parse(html, "AL", "x").landelijk.kleur == Kleur.GROEN


def test_at_andere_paginaopbouw_rest_van_het_land():
    html = (
        '<a>Sicherheitsstufe 2 (regional)</a>'
        '<div class="card panel border-red">Sicherheitsrisiko &nbsp;( Sicherheitsstufe 2 )&nbsp; in den Grenzgebieten '
        "zu Aserbaidschan. Es wird auf das Sicherheitsrisiko hingewiesen.</div>"
        '<div class="card panel border-mediumgray">Guter Sicherheitsstandard &nbsp;( Sicherheitsstufe 1 ) im Rest des Landes</div>'
    )
    a = at.parse(html, "AM", "x")
    assert a.landelijk.kleur == Kleur.GROEN and [g.niveau.kleur for g in a.gebieden] == [Kleur.GEEL]


def test_dk_hele_landnaam_en_hoofdletter_vi():
    html = (
        '<h1>VI har ingen rejsevejledning for Jamaica</h1>'
    )
    a = dk.parse(html, "JM", "x")
    assert a.status == Status.NIET_GEVONDEN


def test_uk_lijst_na_advises_against_met_rest_van_het_land():
    body = (
        "<h2>Areas where FCDO advises against travel</h2><p>FCDO advises against:</p>"
        "<ul><li>all travel to within 10km of the border with Yemen</li>"
        "<li>all but essential travel to the rest of Saudi Arabia</li></ul>"
        "<p>all travel to within 10km of the border with Yemen</p>"
    )
    data = {
        "base_path": "/foreign-travel-advice/saudi-arabia",
        "public_updated_at": "2026-11-01T00:00:00Z",
        "details": {
            "alert_status": ["avoid_all_travel_to_parts", "avoid_all_but_essential_travel_to_parts"],
            "country": {"name": "Saudi Arabia", "synonyms": []},
            "parts": [{"slug": "warnings-and-insurance", "body": body}],
        },
    }
    a = uk.parse(data, "SA")
    assert a.landelijk.kleur == Kleur.ORANJE
    assert [g.niveau.kleur for g in a.gebieden] == [Kleur.ROOD]


def test_de_aufenthalten_en_bzw_afkorting():
    v = {
        "countryName": "Japan",
        "partialWarning": True,
        "content": "<p>Sicherheit - Teilreisewarnung Vor Aufenthalten in von der Regierung ausgewiesenen "
        "evakuierten Gebieten bzw. Zonen um Fukushima wird gewarnt.</p>",
    }
    a = de.parse("1", v, "JP")
    assert any(g.niveau.kleur == Kleur.ROOD for g in a.gebieden) and not a.melding
