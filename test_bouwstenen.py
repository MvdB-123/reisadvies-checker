"""Tests voor de lastige stukjes. Draaien zonder internet.

Elke test hier komt voort uit iets dat tijdens het bouwen daadwerkelijk misging.
Ze bewaken dus geen bedachte gevallen maar echte valkuilen in de bronteksten.

    python3 -m unittest test_bouwstenen -v
"""

import json
import unittest
from pathlib import Path

from bronnen import de, fr, nl, vk, vs
from bronnen.gedeeld import citaat, normaliseer, zinnen

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


class Zinsgrenzen(unittest.TestCase):
    def test_afkorting_breekt_de_zin_niet(self):
        """'bzw.' knipte de waarschuwing los van het gebied waar hij over ging."""
        tekst = ("Vor Reisen in die folgenden Provinzen bzw. der Nutzung der "
                 "genannten Straßen wird gewarnt. Weitere Hinweise folgen.")
        self.assertEqual(len(zinnen(tekst)), 2)
        self.assertIn("bzw. der Nutzung", zinnen(tekst)[0])

    def test_afkorting_met_hoofdletter_breekt_de_zin_niet(self):
        """'St. Louis' en 'U.S. citizens' kapten een gebiedsnaam af."""
        self.assertEqual(len(zinnen("Reconsider travel to: St. Louis Park. Klaar.")), 2)
        self.assertEqual(len(zinnen("Travel to Japan, U.S. citizens beware. Klaar.")), 2)

    def test_gewone_zinnen_worden_wel_gesplitst(self):
        self.assertEqual(len(zinnen("Eerste zin. Tweede zin. Derde zin.")), 3)


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

    def test_bijwoorden_tussen_von_en_reisen(self):
        """'Von nicht notwendigen Reisen … wird abgeraten' is een reisadvies."""
        tekst = ("Von nicht notwendigen Reisen in alle anderen Regionen Tschads "
                 "wird abgeraten.")
        self.assertEqual(len(de._zinnen_met_waarschuwing(tekst)), 1)

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

    def test_officiele_lange_naam_telt_als_het_land(self):
        """De pagina schrijft 'Brunei Darussalam' waar ons register 'Brunei' zegt."""
        self.assertTrue(nl._gaat_over_heel_land(
            "De kleurcode van het reisadvies voor Brunei Darussalam is geel.",
            "Brunei", "brunei darussalam"))
        self.assertTrue(nl._gaat_over_heel_land(
            "De kleurcode van het reisadvies voor Hongkong SAR is geel.", "Hongkong"))

    def test_grensgebied_tussen_twee_landen_is_geen_landniveau(self):
        self.assertFalse(nl._gaat_over_heel_land(
            "De kleurcode is ook oranje voor het grensgebied tussen Thailand "
            "en Myanmar.", "Thailand"))

    def test_lidwoord_voor_de_landsnaam(self):
        self.assertTrue(nl._gaat_over_heel_land(
            "De kleurcode van het reisadvies voor de Bahama\u2019s is geel.", "Bahama\u2019s"))

    def test_bijwoord_tussen_geldt_en_kleurcode(self):
        self.assertEqual(
            nl._doelwit("Voor de Koerdistan Regio Irak en de zuidelijke provincies "
                        "geldt grotendeels kleurcode oranje."),
            "de Koerdistan Regio Irak en de zuidelijke provincies")

    def test_gebiedsnaam_zonder_kleur_erachter(self):
        self.assertEqual(
            nl._gebied_uit("De kleurcode van het reisadvies voor het zuidoosten "
                           "van Fukushima is rood."),
            "het zuidoosten van Fukushima")


class AmerikaanseTeksten(unittest.TestCase):
    def test_kopje_voor_de_samenvatting_valt_weg(self):
        zinnen = vs._schone_zinnen("Advisory summary Do not travel to Ukraine for any reason.")
        self.assertEqual(zinnen[0], "Do not travel to Ukraine for any reason.")

    def test_vage_gebiedsaanduiding_wordt_overgeslagen(self):
        gebieden = vs._gebieden(["Do Not Travel to: these regions."], "", "Ukraine")
        self.assertEqual(gebieden, [])

    def test_landniveau_keert_niet_terug_als_gebied(self):
        """'Do not travel to Mali for any reason' is het land, geen gebied."""
        self.assertEqual(
            vs._gebieden(["Do not travel to Mali for any reason."], "", "Mali"), [])

    def test_zonder_dubbele_punt_is_het_geen_gebiedsopsomming(self):
        self.assertEqual(
            vs._gebieden(["Do not travel to Iraq due to terrorism."], "", "Iraq"), [])

    def test_gebied_met_reden_blijft_staan(self):
        gebieden = vs._gebieden(["Do Not Travel to: Arauca department due to crime."],
                                "", "Colombia")
        self.assertEqual(len(gebieden), 1)
        self.assertEqual(gebieden[0]["label"], "4")


class BritseUitspraken(unittest.TestCase):
    def test_twee_niveaus_in_een_zin(self):
        """Kenia zet beide niveaus achter elkaar zonder punt ertussen."""
        zin = ("FCDO advises against all travel to: Mandera County Lamu County "
               "FCDO advises against all but essential travel to: Garissa Town")
        treffers = list(vk.UITSPRAAK.finditer(zin))
        self.assertEqual(len(treffers), 2)
        self.assertEqual(treffers[0].group(1).lower(), "all travel")
        self.assertEqual(treffers[1].group(1).lower(), "all but essential travel")

    def test_dubbele_punt_na_to(self):
        self.assertTrue(vk.UITSPRAAK.search("all but essential travel to: Garissa"))

    def test_dubbele_punt_na_against(self):
        self.assertTrue(vk.ADVIESZIN.search("FCDO advises against: all travel to x"))

    def test_kopje_zonder_niveau_telt_niet_als_advies(self):
        self.assertFalse(vk.ADVIESZIN.search("Areas where FCDO advises against travel"))

    def test_land_als_geheel_versus_gebied(self):
        self.assertTrue(vk._is_heel_land("Afghanistan", "afghanistan"))
        self.assertTrue(vk._is_heel_land("the whole of the Mali due to unrest", "mali"))
        self.assertFalse(vk._is_heel_land("the north of Afghanistan", "afghanistan"))


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
