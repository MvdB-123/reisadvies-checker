"""Tests voor de lastige stukjes. Draaien zonder internet.

Elke test hier komt voort uit iets dat tijdens het bouwen daadwerkelijk misging.
Ze bewaken dus geen bedachte gevallen maar echte valkuilen in de bronteksten.

    python3 -m unittest test_bouwstenen -v
"""

import json
import unittest
from pathlib import Path

from bronnen import de, fr, nl, vs
from bronnen.gedeeld import citaat, normaliseer, plat

HIER = Path(__file__).parent


class Citaten(unittest.TestCase):
    def test_korte_tekst_blijft_heel(self):
        self.assertEqual(citaat("Reis niet naar Mali."), "Reis niet naar Mali.")

    def test_lange_tekst_kapt_af_op_zinsgrens(self):
        lang = "Eerste zin. " + "Daarna volgt een lange zin die doorloopt. " * 12
        uit = citaat(lang)
        self.assertLess(len(uit), 340)
        self.assertTrue(uit.endswith("[…]"))

    def test_kapt_niet_vlak_voor_een_ontkenning(self):
        """Afkappen na 'reis' maar voor 'niet' zou de strekking omdraaien."""
        tekst = ("Het gebied rond de grens is rustig gebleven dit seizoen en er zijn "
                 "geen incidenten gemeld door de autoriteiten ter plaatse. Reis niet "
                 "naar het noorden van het land want daar is het gevaarlijk.")
        uit = citaat(tekst, max_tekens=len(tekst.split("Reis niet")[0]) + 5)
        self.assertNotRegex(uit.lower(), r"\breis\s*\[")
        self.assertNotRegex(uit.lower(), r"\bniet\s*\[")


class Landsnamen(unittest.TestCase):
    def test_schrijfwijzen_vallen_samen(self):
        """De Amerikaanse feed gebruikt beide schrijfwijzen door elkaar."""
        self.assertEqual(normaliseer("São Tomé and Príncipe"),
                         normaliseer("Sao Tome and Principe"))

    def test_lidwoorden_tellen_niet_mee(self):
        self.assertEqual(normaliseer("Republic of the Congo"), normaliseer("Congo"))


class DuitseZinnen(unittest.TestCase):
    def test_reiswaarschuwing_wordt_herkend(self):
        tekst = "Aktuelles Vor Reisen nach Mali wird gewarnt. Weitere Hinweise folgen."
        self.assertEqual(de._zinnen_met_waarschuwing(tekst),
                         ["Vor Reisen nach Mali wird gewarnt."])

    def test_drugswaarschuwing_telt_niet_mee(self):
        """Duits gebruikt dezelfde formulering voor niet-reisgerelateerde zaken."""
        tekst = ("Vor Erwerb, Besitz und Konsum von Rauschgiften aller Art wird "
                 "dringend abgeraten.")
        self.assertEqual(de._zinnen_met_waarschuwing(tekst), [])

    def test_kopje_lift_niet_mee_in_het_citaat(self):
        tekst = "Siehe Aktuelles Vor Reisen in die Provinz Cabo Delgado wird gewarnt."
        self.assertEqual(de._zinnen_met_waarschuwing(tekst)[0],
                         "Vor Reisen in die Provinz Cabo Delgado wird gewarnt.")


class NederlandseKleurcodes(unittest.TestCase):
    def test_toekenning_aan_heel_land(self):
        self.assertTrue(nl._gaat_over_heel_land(
            "Voor de rest van Thailand geldt kleurcode geel.", "Thailand"))
        self.assertTrue(nl._gaat_over_heel_land(
            "De kleurcode van het reisadvies voor Mali is rood.", "Mali"))

    def test_toekenning_aan_een_gebied_is_geen_landniveau(self):
        self.assertFalse(nl._gaat_over_heel_land(
            "Kleurcode oranje geldt voor de strook van 5 tot 20 kilometer.", "Thailand"))

    def test_algemene_uitleg_is_geen_toekenning(self):
        for zin in ("Wat uw situatie ook is: reis niet naar gebieden met kleurcode rood.",
                    "U kunt reizen naar gebieden met kleurcode groen."):
            self.assertRegex(zin, nl.UITLEG.pattern)

    def test_gebiedsnaam_zonder_kleur_erachter(self):
        self.assertEqual(
            nl._gebied_uit("De kleurcode van het reisadvies voor het zuidoosten "
                           "van Fukushima is rood."),
            "het zuidoosten van Fukushima")


class AmerikaanseTeksten(unittest.TestCase):
    def test_kopje_voor_de_samenvatting_valt_weg(self):
        zinnen = vs._zinnen("Advisory summary Do not travel to Ukraine for any reason.")
        self.assertEqual(zinnen[0], "Do not travel to Ukraine for any reason.")

    def test_vage_gebiedsaanduiding_wordt_overgeslagen(self):
        gebieden = vs._gebieden(["Do Not Travel to: these regions."])
        self.assertEqual(gebieden, [])

    def test_gebied_met_reden_blijft_staan(self):
        gebieden = vs._gebieden(["Do Not Travel to: Arauca department due to crime."])
        self.assertEqual(len(gebieden), 1)
        self.assertEqual(gebieden[0]["label"], "4")


class FranseZones(unittest.TestCase):
    def test_heel_grondgebied_wordt_als_landniveau_herkend(self):
        self.assertTrue(fr.HEEL_LAND.search(
            "L’ensemble du territoire est classé en zone rouge."))

    def test_gewone_zone_is_geen_landniveau(self):
        self.assertFalse(fr.HEEL_LAND.search(
            "À l’extrême-sud, les voyages sont formellement déconseillés."))


class Mappingtabel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping = json.loads((HIER / "mapping.json").read_text(encoding="utf-8"))

    def test_elk_label_wijst_naar_een_bestaande_kleur(self):
        kleuren = set(self.mapping["kleuren"])
        for bron, regels in self.mapping["bronnen"].items():
            for label, info in regels["labels"].items():
                with self.subTest(bron=bron, label=label):
                    self.assertIn(info["kleur"], kleuren)
                    self.assertIn(info["type"], ("letterlijk", "afgeleid"))
                    self.assertTrue(info["onderbouwing"].strip())

    def test_onbekend_label_wordt_niet_geraden(self):
        import bouw
        uit = bouw.pas_mapping_toe(
            "de",
            {"gelukt": True, "landniveau": {"label": "nieuwSoortWaarschuwing",
                                            "citaat": "x"}, "gebieden": []},
            self.mapping)
        self.assertIsNone(uit["landniveau"]["kleur"])
        self.assertEqual(uit["landniveau"]["type"], "niet in de mappingtabel")


if __name__ == "__main__":
    unittest.main()
