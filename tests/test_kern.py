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
    assert "Niet automatisch opgehaald" in html and 'niet "geen risico"' in html
    assert "https://www.ireland.ie/" in html


def test_deepl_link_en_citaat():
    from reisadvies.report import citaat, deepl_link

    assert deepl_link("Hej världen", "sv") == "https://www.deepl.com/translator#sv/nl/Hej%20v%C3%A4rlden"
    # '/' en '|' knippen de tekst af in DeepL tenzij ze een backslash voor zich hebben (M16/H26 werd 'M16')
    assert deepl_link("the M16/H26 road", "en").endswith("the%20M16%5C%2FH26%20road")
    assert "%5C%7C" in deepl_link("a | b", "en")
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



def test_wijzigingen_tussen_twee_rondes():
    from reisadvies.site import wijzigingen

    def rij(fr_kleur, fr_gebied, datum, ie_stand="letterlijk"):
        return {
            "iso": "TR",
            "naam": "Turkije",
            "bronnen": {
                "fr": {"kleur": fr_kleur, "stand": "letterlijk", "gebieden": 1, "strengste_gebied": fr_gebied, "gewijzigd": datum},
                "ie": {"kleur": "geel", "stand": ie_stand, "gebieden": 0, "strengste_gebied": 0, "gewijzigd": None},
            },
        }

    w = wijzigingen([rij("geel", 3, "2026-11-01", "handmatig")], [rij("oranje", 4, "2026-11-24")])
    assert w[0]["regels"] == ["Frankrijk: landelijk geel → oranje", "Frankrijk: strengste gebied oranje → rood"]
    assert wijzigingen([rij("geel", 3, "2026-11-01")], [rij("geel", 3, "2026-11-24")]) == []
    # Zelfde wijzigingsdatum: de overheid paste niets aan, het verschil komt van de tool zelf.
    assert wijzigingen([rij("geel", 0, "2026-11-01")], [rij("geel", 4, "2026-11-01")]) == []

def test_regios_dekken_alle_nederlandse_adviezen_en_afrika_is_het_geheel():
    from reisadvies.regios import REGIOS, regios_van

    assert regios_van("KE") == ["afrika-oost", "afrika"]
    assert regios_van("EG") == ["afrika-noord", "afrika"]
    assert regios_van("TR") == ["midden-oosten"] and regios_van("TH") == ["zuidoost-azie"]
    assert regios_van("BQ-BO") == ["caribisch"] and regios_van("QQ") == ["overig"]
    codes = [c for _, (_, codes) in REGIOS.items() for c in codes.split()]
    assert len(codes) == len(set(codes))  # een land hoort bij precies één regio


def test_gebiedregels_kort_boven_en_volledig_in_de_uitklapper():
    from reisadvies.model import Gebied
    from reisadvies.report import KORT_GEBIED, _gebiedregels

    a = _adv("de", "reisewarnung")
    lang = "die Region " + ", ".join(f"Gebied{n}" for n in range(40))
    a.gebieden = [
        Gebied("die Regionen Adamaoua und Nord", niveau("de", "abraten"), brontekst="Von Reisen in die Regionen Adamaoua und Nord wird abgeraten."),
        Gebied(lang, niveau("de", "teilreisewarnung"), brontekst=f"Vor Reisen in {lang} wird gewarnt."),
        Gebied("Nord", niveau("de", "abraten"), brontekst=""),
    ]
    regels = {r["naam"][:12]: r for r in _gebiedregels(a)}
    lang_r = regels[lang[:12]]
    assert lang_r["kort"].endswith("…") and len(lang_r["kort"]) <= KORT_GEBIED + 2
    assert lang_r["volledig"].startswith("Vor Reisen in die Region") and lang_r["meer"]
    assert regels["Nord"]["meer"] is False and regels["Nord"]["kort"] == "Nord"  # alleen een naam: niets uit te klappen
