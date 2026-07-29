"""Tests der Partie-Zustandsmaschine und des Deckbaus."""

import random
import unittest
from pathlib import Path

from powerdeck.game import battle, cards, rules
from powerdeck.game.bot import Bot
from powerdeck.game.rules import Zug

FIXTURE = Path(__file__).parent / "fixtures" / "cards_test.json"


def zwei_decks(seed=1):
    alle = cards.lade_karten(FIXTURE)
    wuerfel = random.Random(seed)
    deck_a = cards.deck_bauen(alle, "A", wuerfel=wuerfel)
    rest = [k for k in alle if k not in deck_a.karten]
    deck_b = cards.deck_bauen(rest, "B", wuerfel=wuerfel)
    return deck_a, deck_b


class Deckbau(unittest.TestCase):
    def test_deck_haelt_groesse_und_budget(self):
        deck_a, deck_b = zwei_decks()
        for deck in (deck_a, deck_b):
            self.assertEqual(len(deck.karten), cards.DECKGROESSE)
            self.assertLessEqual(deck.kosten, cards.MACHT_BUDGET)

    def test_decks_teilen_keine_karte(self):
        deck_a, deck_b = zwei_decks()
        self.assertFalse({k.id for k in deck_a.karten} & {k.id for k in deck_b.karten})

    def test_doppelte_karte_wird_abgelehnt(self):
        alle = cards.lade_karten(FIXTURE)
        deck = cards.Deck("Doppelt", [alle[0]] * cards.DECKGROESSE)
        with self.assertRaises(cards.DeckFehler):
            deck.pruefen()

    def test_budget_begrenzt_die_teuersten_karten(self):
        alle = sorted(cards.lade_karten(FIXTURE), key=lambda k: -k.macht)
        teuer = cards.Deck("Nur teuer", alle[:cards.DECKGROESSE])
        if teuer.kosten > cards.MACHT_BUDGET:
            with self.assertRaises(cards.DeckFehler):
                teuer.pruefen()
        else:
            self.skipTest("Testkarten sind zu billig, um das Budget zu sprengen")

    def test_zu_kleines_budget_meldet_klar(self):
        alle = cards.lade_karten(FIXTURE)
        with self.assertRaises(cards.DeckFehler):
            cards.deck_bauen(alle, "Zu klein", budget=10)


class Partieverlauf(unittest.TestCase):
    def setUp(self):
        self.deck_a, self.deck_b = zwei_decks()
        self.partie = battle.Partie(self.deck_a, self.deck_b, seed=5)

    def test_karten_gelten_nur_eine_runde(self):
        angriff = Zug(self.partie.hand("a")[0], "kapital")
        verteidigung = Zug(self.partie.hand("b")[0], "kapital")
        self.partie.runde_spielen(angriff, verteidigung)

        self.assertNotIn(angriff.karte, self.partie.hand("a"))
        self.assertNotIn(verteidigung.karte, self.partie.hand("b"))
        gueltig, grund = self.partie.zug_gueltig("a", angriff.karte, "kapital")
        self.assertFalse(gueltig)
        self.assertIn("bereits gespielt", grund)

    def test_eskalation_nur_einmal(self):
        karte = self.partie.hand("a")[0]
        self.partie.runde_spielen(Zug(karte, "nuklear"),
                                  Zug(self.partie.hand("b")[0], "nuklear"))
        naechste = self.partie.hand("a")[0]
        gueltig, grund = self.partie.zug_gueltig("a", naechste, "nuklear")
        self.assertFalse(gueltig)
        self.assertIn("schon eingesetzt", grund)

    def test_ungueltige_verteidigungsdimension(self):
        karte = self.partie.hand("b")[0]
        gueltig, _ = self.partie.zug_gueltig("b", karte, "compute", angriff=False,
                                             angriffsdimension="kapital")
        self.assertFalse(gueltig)

    def test_partie_endet_und_kennt_den_sieger(self):
        bot_a, bot_b = Bot("a", self.partie), Bot("b", self.partie)
        angreifer = "a"
        while not self.partie.vorbei:
            angriff = (bot_a if angreifer == "a" else bot_b).angriff()
            verteidigung = (bot_b if angreifer == "a" else bot_a).verteidigung(angriff.dimension)
            self.partie.runde_spielen(angriff, verteidigung, angreifer=angreifer)
            angreifer = "b" if angreifer == "a" else "a"

        self.assertTrue(self.partie.vorbei)
        self.assertLessEqual(self.partie.runde, 5)
        self.assertIn(self.partie.sieger, ("A", "B", None))
        self.assertIn("Sieger", self.partie.protokoll())

    def test_nach_dem_ende_geht_nichts_mehr(self):
        while not self.partie.vorbei:
            self.partie.runde_spielen(Zug(self.partie.hand("a")[0], "kapital"),
                                      Zug(self.partie.hand("b")[0], "kapital"))
        with self.assertRaises(RuntimeError):
            self.partie.runde_spielen(Zug(self.deck_a.karten[0], "kapital"),
                                      Zug(self.deck_b.karten[0], "kapital"))

    def test_gleicher_seed_gleicher_verlauf(self):
        def lauf():
            deck_a, deck_b = zwei_decks()
            partie = battle.Partie(deck_a, deck_b, seed=99)
            bot_a, bot_b = Bot("a", partie), Bot("b", partie)
            while not partie.vorbei:
                angriff = bot_a.angriff()
                partie.runde_spielen(angriff, bot_b.verteidigung(angriff.dimension))
            return partie.protokoll()

        self.assertEqual(lauf(), lauf())


class Balance(unittest.TestCase):
    """Balance ist eine Behauptung, bis sie gemessen ist."""

    def _turnier(self, partien=120):
        siege = {"a": 0, "b": 0, "unentschieden": 0}
        for seed in range(partien):
            deck_a, deck_b = zwei_decks(seed=seed)
            partie = battle.Partie(deck_a, deck_b, seed=seed)
            bot_a, bot_b = Bot("a", partie), Bot("b", partie)
            angreifer = "a"
            while not partie.vorbei:
                angriff = (bot_a if angreifer == "a" else bot_b).angriff()
                verteidigung = (bot_b if angreifer == "a" else bot_a).verteidigung(
                    angriff.dimension)
                partie.runde_spielen(angriff, verteidigung, angreifer=angreifer)
                angreifer = "b" if angreifer == "a" else "a"
            sieger = partie.sieger
            siege["a" if sieger == "A" else "b" if sieger == "B" else "unentschieden"] += 1
        return siege

    def test_der_erste_zug_entscheidet_nicht_die_partie(self):
        siege = self._turnier()
        entschieden = siege["a"] + siege["b"]
        self.assertGreater(entschieden, 0)
        anteil_a = siege["a"] / entschieden
        # Wer zuerst angreift, hat einen Vorteil – er darf aber nicht zum
        # Selbstläufer werden. Alles jenseits von 70 % wäre kaputt.
        self.assertLess(anteil_a, 0.70, f"Startvorteil zu groß: {siege}")
        self.assertGreater(anteil_a, 0.30, f"Startnachteil zu groß: {siege}")

    def test_alle_angriffsdimensionen_kommen_vor(self):
        """Wird eine Dimension nie gespielt, ist sie tote Regel."""
        genutzt = set()
        for seed in range(40):
            deck_a, deck_b = zwei_decks(seed=seed)
            partie = battle.Partie(deck_a, deck_b, seed=seed)
            bot_a, bot_b = Bot("a", partie), Bot("b", partie)
            while not partie.vorbei:
                angriff = bot_a.angriff()
                genutzt.add(angriff.dimension)
                partie.runde_spielen(angriff, bot_b.verteidigung(angriff.dimension))
        fehlend = set(rules.ANGRIFF) - genutzt
        self.assertFalse(fehlend, f"nie angegriffene Dimensionen: {fehlend}")


if __name__ == "__main__":
    unittest.main()
