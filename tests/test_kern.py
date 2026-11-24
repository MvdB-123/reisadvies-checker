from __future__ import annotations

from datetime import UTC, datetime

from reisadvies.countries import koppel, zoek
from reisadvies.mapping import MAPPING, niveau
from reisadvies.model import Advies, Gebied, Kleur, Soort, Status
from reisadvies.report import render, samenvatting
from reisadvies.sources import BRONNEN
from reisadvies.sources.base import datum


def test_zoek_land():
    assert zoek("Turkije") == zoek("turkey") == zoek("TR") == "TR"
    assert zoek("Ivoorkust") == "CI"
    assert zoek("Kosovo") == "XK"
    assert zoek("Verenigde Staten") == "US"
    assert zoek("Atlantis") is None


def test_koppel_varianten():
    assert koppel("TR", "de", {"tuerkei": 1}) == 1
    assert koppel("TL", "da", {"oesttimor": 2}) == 2
    assert koppel("TT", "en", {"Trinidad and Tobago": 3}) == 3
    assert koppel("GM", "en", {"Gambia, The": 4}) == 4
    assert koppel("MM", "en", {"Myanmar": 5}) == 5


def test_volledige_naam_wint_van_variant():
    kandidaten = {"Congo": "CG", "Democratic Republic of the Congo": "CD"}
    assert koppel("CD", "en", kandidaten) == "CD"
    assert koppel("CG", "en", kandidaten) == "CG"


def test_datum():
    assert datum("Laatst gewijzigd op: 20-10-2026") == "2026-10-20"
    assert datum("17.06.2026 Kl. 09.57") == "2026-06-17"
    assert datum("15 septembre 2026") == "2026-09-15"
    assert datum("02 nov. 2026, 15.40") == "2026-11-02"
    assert datum("Fri, 29 May 2026") == "2026-05-29"


def test_mappingtabel_volledig_en_consistent():
    assert set(MAPPING) == set(BRONNEN)
    for bron, tabel in MAPPING.items():
        for sleutel, n in tabel.items():
            if n.soort == Soort.BESTAAT_NIET:
                assert n.kleur is None, (bron, sleutel)
            else:
                assert n.kleur is not None, (bron, sleutel)
            assert n.bronlabel and n.vertaling


def test_niveau_is_kopie():
    n = niveau("uk", "geen")
    n.toelichting += "x"
    assert not MAPPING["uk"]["geen"].toelichting.endswith("x")


def _adv(bron, kleur_sleutel, status=Status.OK, gebieden=()):
    a = Advies(bron, "TR", status)
    if kleur_sleutel:
        a.landelijk = niveau(bron, kleur_sleutel)
    a.gebieden = list(gebieden)
    return a


def test_samenvatting():
    adviezen = [
        _adv("nl", "geel"),
        _adv("uk", "geen", gebieden=[Gebied("grens", niveau("uk", "avoid_all"))]),
        _adv("ca", "non_essential"),
        _adv("us", "1"),
        _adv("dk", "ekstra_forsigtig"),
        _adv("ie", None, Status.HANDMATIG),
    ]
    s = samenvatting(adviezen)
    assert s["nl_kleur"] == Kleur.GEEL
    assert s["strenger"] == ["Canada"]
    assert s["milder"] == ["Verenigde Staten"]
    assert s["gelijk"] == ["Denemarken"]
    assert s["geen_kleur"] == ["Verenigd Koninkrijk"]
    assert s["niet_beschikbaar"] == ["Ierland"]
    assert s["strengere_gebieden"] == ["Verenigd Koninkrijk"]


def test_render_toont_handmatig_nooit_leeg():
    adviezen = [_adv("nl", "geel"), _adv("ie", None, Status.HANDMATIG)]
    adviezen[1].melding = "Handmatig nalopen."
    adviezen[1].url = "https://www.ireland.ie/"
    html = render("TR", adviezen, nu=datetime(2026, 11, 19, 12, tzinfo=UTC))
    assert "Turkije" in html
    assert "géén &#34;geen risico&#34;" in html or 'géén "geen risico"' in html
    assert "https://www.ireland.ie/" in html


def test_deepl_link_en_citaat():
    from reisadvies.report import citaat, deepl_link

    assert deepl_link("Hej världen", "sv") == "https://www.deepl.com/translator#sv/nl/Hej%20v%C3%A4rlden"
    lang = "Eerste zin. " + "woord " * 100
    assert citaat(lang).endswith("…") and citaat("Kort.") == "Kort."


def test_geen_datum_geeft_onzeker_en_oud_geeft_waarschuwing():
    from datetime import UTC, datetime

    from reisadvies.mapping import niveau
    from reisadvies.model import Advies, Status
    from reisadvies.report import render

    nu = datetime(2026, 11, 24, tzinfo=UTC)
    zonder = Advies("dk", "TR", Status.OK, landelijk=niveau("se", "geen"))
    oud = Advies("at", "TR", Status.OK, landelijk=niveau("se", "geen"), gewijzigd_op="2024-01-01")
    h = render("TR", [zonder, oud], nu)
    assert "Onzeker – niet vast te stellen" in h
    assert "niet gewijzigd" in h
