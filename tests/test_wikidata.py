"""Tests der Wikidata-Auswertung gegen eine gekürzte echte Entity."""

import json
import unittest
from pathlib import Path

from powerdeck.sources import wikidata

FIXTURE = Path(__file__).parent / "fixtures" / "entity_example.json"


class Extract(unittest.TestCase):
    def setUp(self):
        self.entity = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.info = wikidata.extract(self.entity)

    def test_nimmt_das_juengste_vermoegen(self):
        self.assertEqual(self.info["net_worth_usd"], 5e10)
        self.assertEqual(self.info["net_worth_year"], "2024")

    def test_beendete_aemter_zaehlen_nicht(self):
        positions = self.info["_position_qids"]
        self.assertIn("Q100", positions)      # laufend
        self.assertNotIn("Q101", positions)   # hat ein Enddatum
        self.assertIn("Q200", positions)      # CEO-Rolle

    def test_bildlink_und_lizenzseite(self):
        self.assertIn("Beispiel_Bild.jpg", self.info["image_url"])
        self.assertTrue(self.info["image_license_page"].endswith("Beispiel_Bild.jpg"))

    def test_wikipedia_titel(self):
        self.assertEqual(self.info["enwiki"], "Example Person")
        self.assertEqual(self.info["dewiki"], "Beispielperson")

    def test_lebende_person_erzeugt_keine_warnung(self):
        self.assertEqual(self.info["warnings"], [])

    def test_todesdatum_erzeugt_warnung(self):
        self.entity["claims"]["P570"] = [
            {"mainsnak": {"datavalue": {"value": {"time": "+2026-02-28T00:00:00Z"}}}}]
        info = wikidata.extract(self.entity)
        self.assertEqual(len(info["warnings"]), 1)
        self.assertIn("2026-02-28", info["warnings"][0])

    def test_vermoegen_in_euro_wird_umgerechnet(self):
        self.entity["claims"]["P2218"] = [{
            "mainsnak": {"datavalue": {"value": {
                "amount": "+1000000000",
                "unit": "http://www.wikidata.org/entity/Q4916"}}}}]
        info = wikidata.extract(self.entity)
        self.assertGreater(info["net_worth_usd"], 1e9)


class RoleConfirmed(unittest.TestCase):
    def test_findet_rolle_in_aemtern(self):
        self.assertTrue(wikidata.role_confirmed(
            "prime minister", ["Prime Minister of Beispielland"], ""))

    def test_findet_rolle_in_beschreibung(self):
        self.assertTrue(wikidata.role_confirmed(
            "chief executive officer", [], "chief executive officer of Beispiel AG"))

    def test_meldet_fehlende_rolle(self):
        self.assertFalse(wikidata.role_confirmed(
            "president", ["Senator"], "American politician"))

    def test_ohne_erwartung_immer_bestaetigt(self):
        self.assertTrue(wikidata.role_confirmed("", [], ""))


if __name__ == "__main__":
    unittest.main()
