"""Tests des Verbesserungs-Loops.

Der wichtigste Test hier ist der, der beweist, dass der Loop **nicht** ungefragt
in Aussagen über reale Personen schreibt.
"""

import json
import tempfile
import unittest
from pathlib import Path

from powerdeck.loop import proposals
from powerdeck.loop.proposals import Vorschlag
from powerdeck.loop.tasks import unbekannte_domains


def bias_vorschlag(**kwargs):
    standard = {
        "aufgabe": "bias-luecken",
        "datei": "data/bias_sources.json",
        "titel": "Test",
        "begruendung": "weil",
        "eintraege": {"neu.example": 0.0},
    }
    standard.update(kwargs)
    return Vorschlag(**standard)


class Pruefpflicht(unittest.TestCase):
    def test_roster_ist_pruefpflichtig(self):
        self.assertTrue(bias_vorschlag(datei="data/roster.json").prueffplicht)

    def test_bias_tabelle_ist_es_nicht(self):
        self.assertFalse(bias_vorschlag().prueffplicht)

    def test_roster_kann_nicht_unbestaetigt_geschrieben_werden(self):
        vorschlag = bias_vorschlag(datei="data/roster.json",
                                   eintraege={"Q1": {"name": "Jemand"}})
        with tempfile.TemporaryDirectory() as ordner:
            wurzel = Path(ordner)
            (wurzel / "data").mkdir()
            (wurzel / "data" / "roster.json").write_text(
                json.dumps({"factions": {}, "persons": []}), encoding="utf-8")
            with self.assertRaises(PermissionError):
                proposals.anwenden(vorschlag, wurzel)
            # Die Datei bleibt unangetastet
            daten = json.loads((wurzel / "data" / "roster.json").read_text())
            self.assertEqual(daten["persons"], [])

    def test_mit_bestaetigung_wird_geschrieben(self):
        vorschlag = bias_vorschlag(datei="data/roster.json",
                                   eintraege={"Q1": {"name": "Jemand"}})
        with tempfile.TemporaryDirectory() as ordner:
            wurzel = Path(ordner)
            (wurzel / "data").mkdir()
            (wurzel / "data" / "roster.json").write_text(
                json.dumps({"factions": {}, "persons": []}), encoding="utf-8")
            anzahl = proposals.anwenden(vorschlag, wurzel, bestaetigt=True)
            self.assertEqual(anzahl, 1)


class Anwenden(unittest.TestCase):
    def _wurzel(self, ordner, bias=None):
        wurzel = Path(ordner)
        (wurzel / "data").mkdir()
        (wurzel / "data" / "bias_sources.json").write_text(
            json.dumps({"bias": bias or {"alt.example": 1.0}, "state": {}}),
            encoding="utf-8")
        return wurzel

    def test_ergaenzt_neue_domains(self):
        with tempfile.TemporaryDirectory() as ordner:
            wurzel = self._wurzel(ordner)
            anzahl = proposals.anwenden(bias_vorschlag(), wurzel)
            daten = json.loads((wurzel / "data" / "bias_sources.json").read_text())
            self.assertEqual(anzahl, 1)
            self.assertIn("neu.example", daten["bias"])
            self.assertEqual(daten["bias"]["alt.example"], 1.0)

    def test_ueberschreibt_bestehende_einordnung_nicht(self):
        """Handarbeit gewinnt gegen Automatik – immer."""
        with tempfile.TemporaryDirectory() as ordner:
            wurzel = self._wurzel(ordner, bias={"neu.example": -1.5})
            anzahl = proposals.anwenden(bias_vorschlag(), wurzel)
            daten = json.loads((wurzel / "data" / "bias_sources.json").read_text())
            self.assertEqual(anzahl, 0)
            self.assertEqual(daten["bias"]["neu.example"], -1.5)

    def test_unbekanntes_ziel_wird_abgelehnt(self):
        with tempfile.TemporaryDirectory() as ordner:
            wurzel = Path(ordner)
            with self.assertRaises(ValueError):
                proposals.anwenden(bias_vorschlag(datei="data/irgendwas.json"), wurzel)


class Speichern(unittest.TestCase):
    def test_json_und_markdown_landen_nebeneinander(self):
        with tempfile.TemporaryDirectory() as ordner:
            pfad = proposals.speichern(bias_vorschlag(), ordner)
            self.assertTrue(pfad.exists())
            self.assertTrue(pfad.with_suffix(".md").exists())
            zurueck = proposals.laden(pfad)
            self.assertEqual(zurueck.eintraege, {"neu.example": 0.0})

    def test_markdown_warnt_bei_pruefpflicht(self):
        text = bias_vorschlag(datei="data/roster.json").als_markdown()
        self.assertIn("Prüfpflichtig", text)

    def test_markdown_enthaelt_belege_und_hinweise(self):
        text = bias_vorschlag(belege=["https://beispiel.example"],
                              hinweise=["Wert ersetzen"]).als_markdown()
        self.assertIn("https://beispiel.example", text)
        self.assertIn("[ ] Wert ersetzen", text)


class DomainSammlung(unittest.TestCase):
    def test_laeuft_ohne_cache_durch(self):
        """Ohne Cache gibt es nichts zu melden – und keinen Absturz."""
        self.assertIsInstance(unbekannte_domains(mindestens=10**9), list)


if __name__ == "__main__":
    unittest.main()
