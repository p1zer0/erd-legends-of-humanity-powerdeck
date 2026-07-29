"""Die Partie: Zustandsmaschine über mehrere Runden.

Der gesamte Verlauf hängt an einem Seed. Zwei Spieler mit denselben Zügen und
demselben Seed kommen zwingend zum selben Ergebnis – Voraussetzung dafür, dass
eine Partie später serverseitig nachgerechnet werden kann, statt dem Client zu
glauben.
"""

import random
from dataclasses import dataclass, field

from . import rules


@dataclass
class Partie:
    deck_a: object
    deck_b: object
    seed: int = 0
    runden: int = 5

    def __post_init__(self):
        self.wuerfel = random.Random(self.seed)
        self.a = rules.Seite(name=self.deck_a.name)
        self.b = rules.Seite(name=self.deck_b.name)
        self.runde = 0
        self.verlauf = []
        self.gespielt_a = set()
        self.gespielt_b = set()

    # -------------------------------------------------------------- Zustand

    @property
    def vorbei(self):
        noetig = self.runden // 2 + 1
        return (self.runde >= self.runden
                or self.a.punkte >= noetig or self.b.punkte >= noetig)

    @property
    def sieger(self):
        if not self.vorbei:
            return None
        if self.a.punkte == self.b.punkte:
            return None
        return self.a.name if self.a.punkte > self.b.punkte else self.b.name

    def hand(self, seite):
        """Noch nicht gespielte Karten. Jede Karte gilt genau eine Runde."""
        deck, gespielt = ((self.deck_a, self.gespielt_a) if seite == "a"
                          else (self.deck_b, self.gespielt_b))
        return [k for k in deck.karten if k.id not in gespielt]

    # ---------------------------------------------------------------- Zug

    def zug_gueltig(self, seite, karte, dimension, angriff=True, angriffsdimension=None):
        """Prüft einen Zug, ohne ihn auszuführen – dieselbe Prüfung nutzt der Server."""
        if karte not in self.hand(seite):
            return False, "Karte wurde bereits gespielt"
        zustand = self.a if seite == "a" else self.b
        if dimension in rules.ESKALATION and not rules.eskalation_erlaubt(zustand, dimension):
            return False, f"{dimension} wurde in dieser Partie schon eingesetzt"
        if angriff:
            if dimension not in rules.ANGRIFF + rules.ESKALATION:
                return False, f"{dimension} ist keine Angriffsdimension"
        elif dimension not in rules.erlaubte_verteidigung(angriffsdimension):
            return False, f"{dimension} ist keine gültige Antwort auf {angriffsdimension}"
        return True, ""

    def runde_spielen(self, angriff, verteidigung, angreifer="a"):
        """Eine Runde ausführen und den Zustand fortschreiben."""
        if self.vorbei:
            raise RuntimeError("Die Partie ist beendet")

        seite_a = self.a if angreifer == "a" else self.b
        seite_b = self.b if angreifer == "a" else self.a

        ergebnis = rules.resolve(angriff, verteidigung, seite_a, seite_b, self.wuerfel)

        if angreifer == "a":
            self.gespielt_a.add(angriff.karte.id)
            self.gespielt_b.add(verteidigung.karte.id)
        else:
            self.gespielt_b.add(angriff.karte.id)
            self.gespielt_a.add(verteidigung.karte.id)

        gewinner_seite = seite_a if ergebnis.gewinner == "angriff" else seite_b
        gewinner_seite.punkte += 1

        self.runde += 1
        self.verlauf.append(Runde(
            nummer=self.runde,
            angreifer=seite_a.name,
            angriff=angriff,
            verteidigung=verteidigung,
            ergebnis=ergebnis,
            gewinner=gewinner_seite.name,
            stand=(self.a.punkte, self.b.punkte),
        ))
        return self.verlauf[-1]

    def protokoll(self):
        """Der ganze Verlauf als lesbarer Text – für Log, Replay und Nachweis."""
        zeilen = []
        for runde in self.verlauf:
            zeilen.append(f"Runde {runde.nummer} – Angriff: {runde.angreifer}")
            zeilen.extend("  " + z for z in runde.ergebnis.protokoll)
            zeilen.append(f"  -> {runde.gewinner} gewinnt die Runde "
                          f"(Stand {runde.stand[0]}:{runde.stand[1]})")
        if self.vorbei:
            zeilen.append(f"Sieger: {self.sieger or 'unentschieden'}")
        return "\n".join(zeilen)


@dataclass
class Runde:
    nummer: int
    angreifer: str
    angriff: object
    verteidigung: object
    ergebnis: object
    gewinner: str
    stand: tuple = field(default=(0, 0))
