"""Karten und Decks – die Brücke zwischen Datenschicht und Spiel.

Die Spielschicht liest ausschließlich die fertige cards.json. Sie kennt weder
Wikidata noch GDELT. Diese Grenze ist Absicht: das Spiel muss auch dann laufen,
wenn keine Datenquelle erreichbar ist.
"""

import json
from dataclasses import dataclass

# Ein Deck hat feste Größe, und die Summe der Machtwerte ist gedeckelt.
# Dadurch ist `macht` das, was es sein soll: ein Preis, keine Siegbedingung.
DECKGROESSE = 8
MACHT_BUDGET = 420


@dataclass(frozen=True)
class Karte:
    id: str
    name: str
    faction: str
    macht: int
    stats: dict
    beschreibung: str = ""
    quellen: dict = None

    @classmethod
    def from_json(cls, roh):
        return cls(
            id=roh["id"],
            name=roh["name"],
            faction=roh["faction"],
            macht=roh["macht"],
            stats=dict(roh["stats"]),
            beschreibung=roh.get("beschreibung") or "",
            quellen=roh.get("quellen") or {},
        )


class DeckFehler(ValueError):
    """Ein Deck verstößt gegen die Bauregeln."""


@dataclass
class Deck:
    name: str
    karten: list

    def pruefen(self, groesse=DECKGROESSE, budget=MACHT_BUDGET):
        if len(self.karten) != groesse:
            raise DeckFehler(f"{self.name}: {len(self.karten)} Karten, erlaubt sind {groesse}")
        kosten = sum(k.macht for k in self.karten)
        if kosten > budget:
            raise DeckFehler(f"{self.name}: Machtbudget überschritten ({kosten} > {budget})")
        ids = [k.id for k in self.karten]
        if len(ids) != len(set(ids)):
            raise DeckFehler(f"{self.name}: doppelte Karten im Deck")
        return self

    @property
    def kosten(self):
        return sum(k.macht for k in self.karten)


def lade_karten(pfad):
    """Karten aus einer cards.json lesen."""
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    return [Karte.from_json(k) for k in daten["cards"]]


def deck_bauen(karten, name, groesse=DECKGROESSE, budget=MACHT_BUDGET, wuerfel=None):
    """Ein zulässiges Deck zusammenstellen.

    Bewusst gierig von unten: teure Karten sind selten leistbar, und genau
    deshalb sind schwache Karten spielbar statt Beiwerk.
    """
    vorrat = list(karten)
    if wuerfel:
        wuerfel.shuffle(vorrat)
    else:
        vorrat.sort(key=lambda k: k.macht)

    gewaehlt, kosten = [], 0
    for karte in vorrat:
        if len(gewaehlt) == groesse:
            break
        if kosten + karte.macht <= budget:
            gewaehlt.append(karte)
            kosten += karte.macht

    if len(gewaehlt) < groesse:
        raise DeckFehler(
            f"{name}: nur {len(gewaehlt)} von {groesse} Karten passen ins Budget {budget}")
    return Deck(name=name, karten=gewaehlt).pruefen(groesse, budget)
