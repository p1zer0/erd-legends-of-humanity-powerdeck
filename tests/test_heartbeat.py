"""Tests für Herzschlag und Konsens-Einordnung.

Kein Netz, kein Modell: die Anbieter werden ersetzt. Geprüft wird die Logik,
die entscheidet, was ohne Menschen übernommen werden darf.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from powerdeck.loop import agent, classify, heartbeat


def stimme(domain, kategorie="bias", wert=0.0, sicherheit=0.9, land=None):
    eintrag = {"domain": domain, "kategorie": kategorie, "sicherheit": sicherheit,
               "begruendung": "Testbegründung"}
    if kategorie == "staat":
        eintrag["land"] = land or "Testland"
    else:
        eintrag["wert"] = wert
    return eintrag


def runden(*antworten):
    """Ersetzt _frage_einordnung: gibt der Reihe nach vorbereitete Runden zurück."""
    aufrufe = {"n": 0}

    def gefaelscht(domains, anbieter_index):
        i = aufrufe["n"]
        aufrufe["n"] += 1
        if i >= len(antworten):
            raise agent.KeinAnbieter("keine weitere Antwort vorbereitet")
        return {e["domain"]: e for e in antworten[i]}, f"anbieter-{i}"

    return gefaelscht


class Konsens(unittest.TestCase):
    def test_einigkeit_wird_uebernommen(self):
        with mock.patch.object(classify, "_frage_einordnung",
                               runden([stimme("a.example", wert=-1.0)],
                                      [stimme("a.example", wert=-1.2)])):
            einig, strittig = classify.einordnen(["a.example"], noetig=2, toleranz=0.75)
        self.assertIn("a.example", einig)
        self.assertAlmostEqual(einig["a.example"]["wert"], -1.1, places=2)
        self.assertEqual(strittig, {})

    def test_abweichung_ueber_toleranz_ist_strittig(self):
        with mock.patch.object(classify, "_frage_einordnung",
                               runden([stimme("b.example", wert=-1.5)],
                                      [stimme("b.example", wert=1.5)])):
            einig, strittig = classify.einordnen(["b.example"], noetig=2, toleranz=0.75)
        self.assertEqual(einig, {})
        self.assertIn("b.example", strittig)
        self.assertEqual(len(strittig["b.example"]), 2)

    def test_uneinige_kategorie_ist_strittig(self):
        with mock.patch.object(classify, "_frage_einordnung",
                               runden([stimme("c.example", kategorie="staat")],
                                      [stimme("c.example", wert=0.0)])):
            einig, strittig = classify.einordnen(["c.example"], noetig=2)
        self.assertEqual(einig, {})
        self.assertIn("c.example", strittig)

    def test_unsicherheit_verhindert_uebernahme(self):
        """Sagt ein Modell 'kenne ich nicht', wird nichts übernommen."""
        with mock.patch.object(classify, "_frage_einordnung",
                               runden([stimme("d.example", wert=0.0, sicherheit=0.2)],
                                      [stimme("d.example", wert=0.0, sicherheit=0.9)])):
            einig, strittig = classify.einordnen(["d.example"], noetig=2)
        self.assertEqual(einig, {})
        self.assertIn("d.example", strittig)

    def test_staatsmedien_brauchen_dasselbe_land(self):
        with mock.patch.object(classify, "_frage_einordnung",
                               runden([stimme("e.example", kategorie="staat", land="Russland")],
                                      [stimme("e.example", kategorie="staat", land="Russland")])):
            einig, _ = classify.einordnen(["e.example"], noetig=2)
        self.assertEqual(einig["e.example"]["kategorie"], "staat")
        self.assertEqual(einig["e.example"]["land"], "Russland")

    def test_widersprechende_laender_sind_strittig(self):
        with mock.patch.object(classify, "_frage_einordnung",
                               runden([stimme("f.example", kategorie="staat", land="China")],
                                      [stimme("f.example", kategorie="staat", land="Iran")])):
            einig, strittig = classify.einordnen(["f.example"], noetig=2)
        self.assertEqual(einig, {})
        self.assertIn("f.example", strittig)

    def test_zu_wenige_antworten_uebernehmen_nichts(self):
        """Fällt ein Anbieter aus, fehlt eine Stimme – dann passiert nichts."""
        with mock.patch.object(classify, "_frage_einordnung",
                               runden([stimme("g.example", wert=0.0)])):
            einig, strittig = classify.einordnen(["g.example"], noetig=2)
        self.assertEqual(einig, {})
        self.assertEqual(strittig, {})

    def test_konsens_null_schaltet_ab(self):
        einig, strittig = classify.einordnen(["h.example"], noetig=0)
        self.assertEqual((einig, strittig), ({}, {}))


class Uebernehmen(unittest.TestCase):
    def test_bestehende_einordnung_bleibt(self):
        with tempfile.TemporaryDirectory() as ordner:
            datei = Path(ordner) / "bias.json"
            datei.write_text(json.dumps({"bias": {"alt.example": -1.5}, "state": {}}),
                             encoding="utf-8")
            with mock.patch.object(classify, "BIAS_FILE", datei):
                anzahl = classify.uebernehmen({
                    "alt.example": {"kategorie": "bias", "wert": 2.0},
                    "neu.example": {"kategorie": "bias", "wert": 0.5},
                })
            daten = json.loads(datei.read_text())
        self.assertEqual(anzahl, 1)
        self.assertEqual(daten["bias"]["alt.example"], -1.5)  # unangetastet
        self.assertEqual(daten["bias"]["neu.example"], 0.5)

    def test_staatsmedien_landen_im_richtigen_abschnitt(self):
        with tempfile.TemporaryDirectory() as ordner:
            datei = Path(ordner) / "bias.json"
            datei.write_text(json.dumps({"bias": {}, "state": {}}), encoding="utf-8")
            with mock.patch.object(classify, "BIAS_FILE", datei):
                classify.uebernehmen({"x.example": {"kategorie": "staat", "land": "China"}})
            daten = json.loads(datei.read_text())
        self.assertEqual(daten["state"]["x.example"], "China")
        self.assertNotIn("x.example", daten["bias"])


class Herzschlag(unittest.TestCase):
    """Der Herzschlag wird ohne Aufgaben und ohne Netz gefahren – geprüft wird
    der Ablauf, nicht die Datenquellen."""

    def setUp(self):
        self.stille = contextlib.redirect_stderr(io.StringIO())
        self.stille.__enter__()
        self.ohne_aufgaben = mock.patch.object(heartbeat, "AUFGABEN", {})
        self.ohne_aufgaben.start()

    def tearDown(self):
        self.ohne_aufgaben.stop()
        self.stille.__exit__(None, None, None)

    def test_trockenlauf_schreibt_nichts(self):
        with tempfile.TemporaryDirectory() as ordner:
            journal = Path(ordner) / "journal.jsonl"
            with mock.patch.object(heartbeat, "JOURNAL", journal), \
                 mock.patch.object(heartbeat, "VORSCHLAEGE", Path(ordner) / "p"), \
                 mock.patch.object(heartbeat, "STOPPDATEI", Path(ordner) / "stop"):
                herz = heartbeat.Herzschlag(intervall=1, trocken=True)
                herz.laufen(max_schlaege=1)
                self.assertFalse((Path(ordner) / "p").exists())
                self.assertTrue(journal.exists())

    def test_kaputter_schlag_beendet_den_herzschlag_nicht(self):
        """Der ganze Punkt: er läuft weiter, bis jemand ihn stoppt."""
        with tempfile.TemporaryDirectory() as ordner, \
             mock.patch.object(heartbeat, "JOURNAL", Path(ordner) / "j.jsonl"), \
             mock.patch.object(heartbeat, "STOPPDATEI", Path(ordner) / "stop"):
            herz = heartbeat.Herzschlag(intervall=1, trocken=True)
            with mock.patch.object(herz, "deck_auffrischen",
                                   side_effect=RuntimeError("kaputt")):
                herz.laufen(max_schlaege=2)
            self.assertEqual(herz.schlag, 2)
            journal = (Path(ordner) / "j.jsonl").read_text(encoding="utf-8")
            self.assertIn("kaputt", journal)

    def test_stoppdatei_beendet_den_lauf(self):
        with tempfile.TemporaryDirectory() as ordner:
            stopp = Path(ordner) / "stop"
            with mock.patch.object(heartbeat, "JOURNAL", Path(ordner) / "j.jsonl"), \
                 mock.patch.object(heartbeat, "STOPPDATEI", stopp):
                herz = heartbeat.Herzschlag(intervall=1, trocken=True)
                original = herz.ein_schlag

                def schlag_dann_stopp():
                    original()
                    stopp.touch()

                with mock.patch.object(herz, "ein_schlag", schlag_dann_stopp):
                    herz.laufen()
            self.assertEqual(herz.schlag, 1)
            self.assertFalse(stopp.exists())  # aufgeräumt


class Anbieterkaskade(unittest.TestCase):
    def test_platzhalter_ohne_umgebungsvariable_wird_uebersprungen(self):
        with tempfile.TemporaryDirectory() as ordner:
            datei = Path(ordner) / "agents.json"
            datei.write_text(json.dumps({"anbieter": [
                {"name": "fehlt", "url": "u", "modell": "m", "schluessel": "${GIBT_ES_NICHT_XYZ}"},
                {"name": "lokal", "url": "u", "modell": "m", "schluessel": ""},
            ]}), encoding="utf-8")
            with mock.patch.object(agent, "KONFIG", datei):
                namen = [a["name"] for a in agent.lade_anbieter()]
        self.assertEqual(namen, ["lokal"])

    def test_inaktive_anbieter_zaehlen_nicht(self):
        with tempfile.TemporaryDirectory() as ordner:
            datei = Path(ordner) / "agents.json"
            datei.write_text(json.dumps({"anbieter": [
                {"name": "aus", "aktiv": False, "url": "u", "modell": "m", "schluessel": ""},
            ]}), encoding="utf-8")
            with mock.patch.object(agent, "KONFIG", datei):
                self.assertFalse(agent.verfuegbar())

    def test_ohne_konfiguration_kein_absturz(self):
        with tempfile.TemporaryDirectory() as ordner, \
             mock.patch.object(agent, "KONFIG", Path(ordner) / "gibtsnicht.json"):
            self.assertEqual(agent.lade_anbieter(), [])
            self.assertFalse(agent.verfuegbar())


if __name__ == "__main__":
    unittest.main()
