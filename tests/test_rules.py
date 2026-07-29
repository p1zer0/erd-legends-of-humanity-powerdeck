"""Tests der Spielregeln – die Stelle, an der die Aussage des Spiels steht."""

import random
import unittest

from powerdeck.game import rules
from powerdeck.game.cards import Karte
from powerdeck.game.rules import Seite, Zug

KEIN_ZUFALL = random.Random(0)


def karte(name, faction="staat", **stats):
    voll = dict.fromkeys(rules.ANGRIFF + rules.ESKALATION + rules.PASSIV, 0)
    voll.update(stats)
    return Karte(id=name, name=name, faction=faction, macht=50, stats=voll)


def ohne_chaos():
    """Ein Würfel, der nie kippt – für Tests der reinen Vergleichslogik."""
    class Nie(random.Random):
        def random(self):
            return 1.0
    return Nie()


def immer_chaos():
    class Immer(random.Random):
        def random(self):
            return 0.0
    return Immer()


class KonterRad(unittest.TestCase):
    def test_jede_angriffsdimension_hat_genau_einen_konter(self):
        self.assertEqual(set(rules.KONTER), set(rules.ANGRIFF))
        for angriff, konter in rules.KONTER.items():
            self.assertIn(konter, rules.ANGRIFF)
            self.assertNotEqual(angriff, konter)

    def test_das_rad_ist_geschlossen(self):
        # Von jeder Dimension aus erreicht man über Konter alle vier – ein Kreis,
        # keine Sackgasse. Sonst gäbe es eine Dimension, die niemand kontert.
        besucht, aktuell = [], "kapital"
        for _ in range(len(rules.ANGRIFF)):
            besucht.append(aktuell)
            aktuell = rules.KONTER[aktuell]
        self.assertEqual(aktuell, "kapital")
        self.assertEqual(set(besucht), set(rules.ANGRIFF))

    def test_verteidigung_darf_gleiche_oder_konternde_dimension(self):
        self.assertEqual(set(rules.erlaubte_verteidigung("kapital")), {"kapital", "narrativ"})

    def test_ungueltige_verteidigung_wird_abgelehnt(self):
        a, b = Seite("A"), Seite("B")
        with self.assertRaises(ValueError):
            rules.resolve(Zug(karte("X", kapital=50), "kapital"),
                          Zug(karte("Y", compute=99), "compute"), a, b, KEIN_ZUFALL)


class Vergleich(unittest.TestCase):
    def test_hoeherer_wert_gewinnt(self):
        ergebnis = rules.resolve(Zug(karte("A", kapital=60), "kapital"),
                                 Zug(karte("B", kapital=40), "kapital"),
                                 Seite("A"), Seite("B"), ohne_chaos())
        self.assertEqual(ergebnis.gewinner, "angriff")

    def test_konter_schlaegt_starken_angriff(self):
        # Narrativ kontert Kapital: ein schwacher Kapitalwert ist irrelevant,
        # verglichen wird 90 Narrativ gegen 60 Kapital.
        ergebnis = rules.resolve(Zug(karte("Konzern", kapital=60), "kapital"),
                                 Zug(karte("Bewegung", narrativ=90), "narrativ"),
                                 Seite("A"), Seite("B"), ohne_chaos())
        self.assertEqual(ergebnis.gewinner, "verteidigung")

    def test_gleichstand_geht_an_den_angreifer(self):
        ergebnis = rules.resolve(Zug(karte("A", kapital=50), "kapital"),
                                 Zug(karte("B", kapital=50), "kapital"),
                                 Seite("A"), Seite("B"), ohne_chaos())
        self.assertEqual(ergebnis.gewinner, "angriff")

    def test_zivilgesellschaft_haelt_das_wort_bei_gleichstand(self):
        ergebnis = rules.resolve(
            Zug(karte("Staat", faction="staat", narrativ=50), "narrativ"),
            Zug(karte("NGO", faction="zivil", narrativ=50), "narrativ"),
            Seite("A"), Seite("B"), ohne_chaos())
        self.assertEqual(ergebnis.gewinner, "verteidigung")


class Polarisierung(unittest.TestCase):
    def test_schuetzt_gegen_narrativ(self):
        # 40 Narrativ + 40 Polarisierung/2 = 60 schlägt einen Angriff mit 50.
        ergebnis = rules.resolve(
            Zug(karte("Presse", narrativ=50), "narrativ"),
            Zug(karte("Populist", narrativ=40, polarisierung=40), "narrativ"),
            Seite("A"), Seite("B"), ohne_chaos())
        self.assertEqual(ergebnis.gewinner, "verteidigung")
        self.assertEqual(ergebnis.verteidigungswert, 60)

    def test_schuetzt_nicht_gegen_andere_dimensionen(self):
        ergebnis = rules.resolve(
            Zug(karte("Bank", kapital=50), "kapital"),
            Zug(karte("Populist", kapital=40, polarisierung=90), "kapital"),
            Seite("A"), Seite("B"), ohne_chaos())
        self.assertEqual(ergebnis.verteidigungswert, 40)


class Eskalation(unittest.TestCase):
    def test_nuklear_kostet_dauerhaft_narrativ(self):
        a = Seite("A")
        rules.resolve(Zug(karte("Staat", nuklear=80), "nuklear"),
                      Zug(karte("Anderer", nuklear=10), "nuklear"),
                      a, Seite("B"), ohne_chaos())
        self.assertEqual(a.narrativ_faktor, rules.NUKLEAR_NARRATIV_REST)
        self.assertIn("nuklear", a.eskalation_genutzt)

    def test_narrativ_malus_wirkt_in_spaeteren_runden(self):
        a = Seite("A")
        a.narrativ_faktor = 0.5
        ergebnis = rules.resolve(Zug(karte("Staat", narrativ=80), "narrativ"),
                                 Zug(karte("Presse", narrativ=50), "narrativ"),
                                 a, Seite("B"), ohne_chaos())
        self.assertEqual(ergebnis.angriffswert, 40)
        self.assertEqual(ergebnis.gewinner, "verteidigung")

    def test_nuklear_ist_nur_durch_nuklear_zu_beantworten(self):
        self.assertEqual(rules.erlaubte_verteidigung("nuklear"), ("nuklear",))

    def test_compute_wird_durch_militaer_gekontert(self):
        self.assertEqual(set(rules.erlaubte_verteidigung("compute")), {"compute", "militaer"})

    def test_zivilgesellschaft_daempft_eskalation(self):
        ergebnis = rules.resolve(
            Zug(karte("Staat", nuklear=80), "nuklear"),
            Zug(karte("ICAN", faction="zivil", nuklear=30), "nuklear"),
            Seite("A"), Seite("B"), ohne_chaos())
        self.assertEqual(ergebnis.angriffswert, 40)  # halbiert
        self.assertEqual(ergebnis.gewinner, "angriff")

    def test_eskalation_nur_einmal_pro_partie(self):
        a = Seite("A")
        a.eskalation_genutzt.add("nuklear")
        self.assertFalse(rules.eskalation_erlaubt(a, "nuklear"))
        self.assertTrue(rules.eskalation_erlaubt(a, "compute"))


class Chaos(unittest.TestCase):
    def test_kippt_die_runde(self):
        ergebnis = rules.resolve(Zug(karte("Stark", kapital=90), "kapital"),
                                 Zug(karte("Wild", kapital=10, chaos=100), "kapital"),
                                 Seite("A"), Seite("B"), immer_chaos())
        self.assertTrue(ergebnis.chaos_umschlag)
        self.assertEqual(ergebnis.gewinner, "verteidigung")

    def test_ohne_chaoswert_kein_umschlag(self):
        ergebnis = rules.resolve(Zug(karte("Stark", kapital=90), "kapital"),
                                 Zug(karte("Brav", kapital=10, chaos=0), "kapital"),
                                 Seite("A"), Seite("B"), immer_chaos())
        self.assertFalse(ergebnis.chaos_umschlag)

    def test_gleicher_seed_gleiches_ergebnis(self):
        def lauf():
            return rules.resolve(Zug(karte("A", kapital=60), "kapital"),
                                 Zug(karte("B", kapital=50, chaos=80), "kapital"),
                                 Seite("A"), Seite("B"), random.Random(42)).gewinner
        self.assertEqual(lauf(), lauf())


class KeineDominanteKarte(unittest.TestCase):
    def test_jede_dimension_hat_eine_antwort(self):
        """Der Kern der Gestaltung: keine Angriffsdimension ist unbeantwortbar."""
        for dimension in rules.ANGRIFF + rules.ESKALATION:
            with self.subTest(dimension=dimension):
                self.assertTrue(rules.erlaubte_verteidigung(dimension))

    def test_spezialist_schlaegt_allrounder_in_seiner_dimension(self):
        """Breite schützt nicht: wer überall 60 hat, verliert gegen 90 an der
        richtigen Stelle. Das ist der Grund, warum schwache Karten spielbar sind."""
        allrounder = karte("Allrounder", kapital=60, militaer=60, daten=60, narrativ=60)
        spezialist = karte("Bewegung", faction="zivil", narrativ=90)
        ergebnis = rules.resolve(Zug(allrounder, "kapital"), Zug(spezialist, "narrativ"),
                                 Seite("A"), Seite("B"), ohne_chaos())
        self.assertEqual(ergebnis.gewinner, "verteidigung")

    def test_derselbe_allrounder_gewinnt_die_dimension_ohne_konter(self):
        allrounder = karte("Allrounder", kapital=60, militaer=60, daten=60, narrativ=60)
        spezialist = karte("Bewegung", faction="zivil", narrativ=90)
        # Greift er stattdessen Daten an, kann die Bewegung nur mit Militär
        # antworten – und hat dort nichts.
        ergebnis = rules.resolve(Zug(allrounder, "daten"), Zug(spezialist, "militaer"),
                                 Seite("A"), Seite("B"), ohne_chaos())
        self.assertEqual(ergebnis.gewinner, "angriff")


if __name__ == "__main__":
    unittest.main()
