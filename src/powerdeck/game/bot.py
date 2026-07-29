"""Ein einfacher Gegner – gut genug, um das Spielgefühl zu prüfen.

Der Bot rechnet nicht voraus. Er spielt die Dimension, in der seine beste Karte
am deutlichsten über dem Durchschnitt des Gegnerdecks liegt. Das reicht, um zu
erkennen, ob eine Karte zu stark ist: gegen einen simplen Gegner darf keine
Strategie durchgehend gewinnen.
"""

import statistics

from . import rules
from .rules import Zug


def _deckschnitt(deck, dimension):
    werte = [k.stats.get(dimension, 0) for k in deck.karten]
    return statistics.fmean(werte) if werte else 0.0


class Bot:
    def __init__(self, seite, partie, name="Bot"):
        self.seite = seite
        self.partie = partie
        self.name = name

    def _zustand(self):
        return self.partie.a if self.seite == "a" else self.partie.b

    def _gegnerdeck(self):
        return self.partie.deck_b if self.seite == "a" else self.partie.deck_a

    def angriff(self):
        """Karte und Dimension mit dem größten Vorsprung gegenüber dem Gegnerschnitt."""
        gegner = self._gegnerdeck()
        zustand = self._zustand()
        moeglich = list(rules.ANGRIFF)
        moeglich += [d for d in rules.ESKALATION if rules.eskalation_erlaubt(zustand, d)]

        bester, bester_vorsprung = None, float("-inf")
        for karte in self.partie.hand(self.seite):
            for dimension in moeglich:
                vorsprung = karte.stats.get(dimension, 0) - _deckschnitt(gegner, dimension)
                # Eskalation kostet – nur einsetzen, wenn sie deutlich trägt.
                if dimension in rules.ESKALATION:
                    vorsprung -= 20
                if vorsprung > bester_vorsprung:
                    bester, bester_vorsprung = Zug(karte, dimension), vorsprung
        return bester

    def verteidigung(self, angriffsdimension):
        """Die Antwort mit dem höchsten effektiven Wert."""
        bester, bester_wert = None, float("-inf")
        for karte in self.partie.hand(self.seite):
            for dimension in rules.erlaubte_verteidigung(angriffsdimension):
                if dimension in rules.ESKALATION and not rules.eskalation_erlaubt(
                        self._zustand(), dimension):
                    continue
                wert = karte.stats.get(dimension, 0)
                if angriffsdimension == "narrativ" and dimension == "narrativ":
                    wert += karte.stats.get("polarisierung", 0) * rules.POLARISIERUNGS_SCHUTZ
                if wert > bester_wert:
                    bester, bester_wert = Zug(karte, dimension), wert
        return bester
