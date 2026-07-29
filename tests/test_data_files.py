"""Prüft die Datendateien – sie sind der Teil, der von Hand gepflegt wird."""

import json
import unittest

from powerdeck.config import BIAS_FILE, ROSTER_FILE, WEIGHTS
from powerdeck.deck import finalize

HARD_KEYS = {"militaer", "nuklear", "daten", "compute", "kapital_override"}


class Roster(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = json.loads(ROSTER_FILE.read_text(encoding="utf-8"))
        cls.persons = cls.roster["persons"]

    def test_namen_sind_eindeutig(self):
        namen = [p["name"] for p in self.persons]
        self.assertEqual(len(namen), len(set(namen)))

    def test_jede_person_hat_fraktion_und_begruendung(self):
        for person in self.persons:
            with self.subTest(person=person["name"]):
                self.assertIn(person["faction"], self.roster["factions"])
                self.assertTrue(person.get("note"), "note begründet die Hartwerte")

    def test_hartwerte_sind_bekannt_und_im_bereich(self):
        for person in self.persons:
            for key, value in person.get("hard", {}).items():
                with self.subTest(person=person["name"], key=key):
                    self.assertIn(key, HARD_KEYS)
                    self.assertGreaterEqual(value, 0)
                    self.assertLessEqual(value, 100)

    def test_alle_fraktionen_sind_besetzt(self):
        besetzt = {p["faction"] for p in self.persons}
        self.assertEqual(besetzt, set(self.roster["factions"]))


class BiasTabelle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(BIAS_FILE.read_text(encoding="utf-8"))

    def test_bias_werte_liegen_zwischen_minus_zwei_und_zwei(self):
        for domain, value in self.sources["bias"].items():
            with self.subTest(domain=domain):
                self.assertGreaterEqual(value, -2)
                self.assertLessEqual(value, 2)

    def test_domains_sind_kleingeschrieben_und_ohne_www(self):
        for domain in list(self.sources["bias"]) + list(self.sources["state"]):
            with self.subTest(domain=domain):
                self.assertEqual(domain, domain.lower())
                self.assertFalse(domain.startswith("www."))

    def test_keine_domain_ist_gleichzeitig_staatsnah_und_eingeordnet(self):
        self.assertFalse(set(self.sources["bias"]) & set(self.sources["state"]))


class Finalize(unittest.TestCase):
    def test_baut_ein_deck_ohne_netz(self):
        rows = [
            {"name": "A", "faction": "staat", "warnings": [], "hard": {"militaer": 50},
             "_attention": {"mittel": 1000.0, "cv": 0.2, "spike": 2.0}, "_gdelt_total": 500,
             "_coverage": {"bias_mittelwert": 1.0, "bias_streuung": 0.5,
                           "verteilung_prozent": {}}},
            {"name": "B", "faction": "tech", "warnings": [], "hard": {"compute": 90},
             "_attention": {"mittel": 10.0, "cv": 0.9, "spike": 8.0}, "_gdelt_total": 5,
             "_coverage": {"bias_mittelwert": 0.0, "bias_streuung": 0.1,
                           "verteilung_prozent": {}}},
        ]
        deck = finalize(rows)

        self.assertEqual(deck["kartenzahl"], 2)
        self.assertEqual(set(deck["cards"][0]["stats"]), set(WEIGHTS))
        # A ist präsenter, B unberechenbarer
        by_name = {c["name"]: c for c in deck["cards"]}
        self.assertGreater(by_name["A"]["stats"]["narrativ"], by_name["B"]["stats"]["narrativ"])
        self.assertGreater(by_name["B"]["stats"]["chaos"], by_name["A"]["stats"]["chaos"])
        # absteigend nach Macht sortiert
        machtwerte = [c["macht"] for c in deck["cards"]]
        self.assertEqual(machtwerte, sorted(machtwerte, reverse=True))

    def test_karte_ohne_livedaten_kippt_nicht(self):
        deck = finalize([{"name": "Ausfall", "faction": "staat",
                          "warnings": ["kein Netz"], "hard": {}}])
        self.assertEqual(deck["cards"][0]["stats"]["narrativ"], 0)
        self.assertEqual(deck["cards"][0]["warnungen"], ["kein Netz"])


if __name__ == "__main__":
    unittest.main()
