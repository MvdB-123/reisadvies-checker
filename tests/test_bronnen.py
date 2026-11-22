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
from reisadvies.sources import at, ca, de, dk, fr, nl, se, uk, us

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
    assert "delen van het land" in a.landelijk.toelichting


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


def test_fr_israel_vrije_tekst_wordt_niet_geinterpreteerd():
    a = fr.parse(lees("fr_IL.html"), "IL", "u")
    assert a.landelijk is None
    assert "vrije tekst" in a.melding
    assert "Golan" in a.brontekst


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


@pytest.mark.parametrize("bron", ["ie", "au"])
def test_handmatige_bronnen(bron):
    from reisadvies.sources import BRONNEN

    a = BRONNEN[bron].haal("TR")
    assert a.status == Status.HANDMATIG and a.url


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
    assert len(a.gebieden) == 4 and kleuren(a) == ["oranje"]


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
