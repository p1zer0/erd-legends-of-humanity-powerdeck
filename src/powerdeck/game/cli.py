"""Partie im Terminal – erreichbar über `python3 -m powerdeck play`.

Kein Ersatz für einen Client, sondern das Werkzeug, um zu prüfen, ob sich die
Regeln gut anfühlen, bevor irgendeine Oberfläche gebaut wird.
"""

import argparse
import random
import sys
from pathlib import Path

from ..pipeline.config import DEFAULT_OUT
from . import battle, cards, rules
from .bot import Bot
from .rules import Zug


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="powerdeck play",
        description="Eine Partie PowerDeck im Terminal.")
    parser.add_argument("--cards", default=DEFAULT_OUT, help="Pfad zu cards.json")
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed für einen reproduzierbaren Verlauf")
    parser.add_argument("--auto", action="store_true", help="Bot gegen Bot, nur zuschauen")
    parser.add_argument("--runden", type=int, default=5, help="Rundenzahl (Standard 5)")
    return parser.parse_args(argv)


def karte_zeile(karte, index=None):
    werte = " ".join(f"{d[:4]}{karte.stats.get(d, 0):>4}"
                     for d in rules.ANGRIFF + rules.ESKALATION + rules.PASSIV)
    kopf = f"  [{index}] " if index is not None else "  "
    return f"{kopf}{karte.name:<24} {karte.faction:<8} Macht {karte.macht:>3}   {werte}"


def frage(prompt, optionen):
    """Eingabe erzwingen, bis sie gültig ist. Leere Eingabe nimmt die erste Option."""
    while True:
        roh = input(f"{prompt} [{'/'.join(optionen)}]: ").strip().lower()
        if not roh:
            return optionen[0]
        for option in optionen:
            if option.lower().startswith(roh):
                return option
        print("  Bitte eine der genannten Optionen.")


def mensch_angriff(partie, seite):
    hand = partie.hand(seite)
    print("\nDeine Hand:")
    for i, karte in enumerate(hand):
        print(karte_zeile(karte, i))

    while True:
        try:
            index = int(input(f"Karte wählen [0-{len(hand) - 1}]: ").strip() or "0")
            karte = hand[index]
            break
        except (ValueError, IndexError):
            print("  Ungültige Nummer.")

    zustand = partie.a if seite == "a" else partie.b
    moeglich = list(rules.ANGRIFF)
    moeglich += [d for d in rules.ESKALATION if rules.eskalation_erlaubt(zustand, d)]
    dimension = frage("Dimension", moeglich)
    return Zug(karte, dimension)


def mensch_verteidigung(partie, seite, angriffsdimension):
    hand = partie.hand(seite)
    print(f"\nAngriff auf {angriffsdimension}. Deine Hand:")
    for i, karte in enumerate(hand):
        print(karte_zeile(karte, i))

    while True:
        try:
            index = int(input(f"Karte wählen [0-{len(hand) - 1}]: ").strip() or "0")
            karte = hand[index]
            break
        except (ValueError, IndexError):
            print("  Ungültige Nummer.")

    moeglich = list(rules.erlaubte_verteidigung(angriffsdimension))
    dimension = moeglich[0] if len(moeglich) == 1 else frage("Antwort", moeglich)
    return Zug(karte, dimension)


def main(argv=None):
    args = parse_args(argv)
    pfad = args.cards if hasattr(args.cards, "read_text") else Path(args.cards)
    if not pfad.exists():
        print(f"Keine Karten unter {pfad}. Erst `make deck` oder `make deck-fast` laufen lassen.",
              file=sys.stderr)
        return 1

    alle = cards.lade_karten(pfad)
    seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    wuerfel = random.Random(seed)

    deck_a = cards.deck_bauen(alle, "Du" if not args.auto else "Bot A", wuerfel=wuerfel)
    deck_b = cards.deck_bauen([k for k in alle if k not in deck_a.karten],
                              "Bot B" if args.auto else "Bot", wuerfel=wuerfel)
    partie = battle.Partie(deck_a, deck_b, seed=seed, runden=args.runden)

    print(f"PowerDeck – Seed {seed}, {args.runden} Runden\n")
    for deck in (deck_a, deck_b):
        print(f"{deck.name} (Machtkosten {deck.kosten}):")
        for karte in deck.karten:
            print(karte_zeile(karte))
        print()

    bot_a = Bot("a", partie, deck_a.name)
    bot_b = Bot("b", partie, deck_b.name)
    angreifer = "a"

    while not partie.vorbei:
        print(f"--- Runde {partie.runde + 1} ---")
        if angreifer == "a":
            angriff = bot_a.angriff() if args.auto else mensch_angriff(partie, "a")
            verteidigung = bot_b.verteidigung(angriff.dimension)
        else:
            angriff = bot_b.angriff()
            verteidigung = (bot_a.verteidigung(angriff.dimension) if args.auto
                            else mensch_verteidigung(partie, "a", angriff.dimension))
            print(f"\n{deck_b.name} greift an: {angriff.karte.name} auf {angriff.dimension}")

        runde = partie.runde_spielen(angriff, verteidigung, angreifer=angreifer)
        for zeile in runde.ergebnis.protokoll:
            print("  " + zeile)
        print(f"  -> {runde.gewinner} gewinnt "
              f"(Stand {runde.stand[0]}:{runde.stand[1]})\n")
        angreifer = "b" if angreifer == "a" else "a"

    print(f"Sieger: {partie.sieger or 'unentschieden'}")
    return 0
