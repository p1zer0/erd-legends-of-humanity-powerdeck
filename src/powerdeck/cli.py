"""Kommandozeile: python3 -m powerdeck [...]"""

import argparse
import json
import sys
from pathlib import Path

from . import deck
from .config import DEFAULT_OUT


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="powerdeck",
        description="Baut cards.json für das ERD-Kartenspiel aus offenen Datenquellen.")
    parser.add_argument("--only", help="nur Personen, deren Name diesen Text enthält")
    parser.add_argument("--limit", type=int, help="nur die ersten N Personen")
    parser.add_argument("--no-gdelt", action="store_true",
                        help="GDELT überspringen: schnell, aber ohne Polarisierung")
    standard = DEFAULT_OUT.relative_to(DEFAULT_OUT.parents[1])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"Zielpfad (Standard: {standard})")
    return parser.parse_args(argv)


def report(result):
    """Was nach dem Lauf wichtig ist: Warnungen zuerst, dann das Ranking."""
    cards = result["cards"]
    warned = [c for c in cards if c["warnungen"]]
    if warned:
        print(f"\n{len(warned)} Karten mit Hinweisen:", file=sys.stderr)
        for card in warned:
            for warning in card["warnungen"]:
                print(f"  {card['name']}: {warning}", file=sys.stderr)

    print("\nTop 10:", file=sys.stderr)
    for card in cards[:10]:
        spread = (card.get("berichterstattung") or {}).get("verteilung_prozent", {})
        spectrum = f"L{spread.get('links', 0)}/M{spread.get('mitte', 0)}/R{spread.get('rechts', 0)}"
        print(f"  {card['macht']:>3}  {card['name']:<28} {spectrum}", file=sys.stderr)


def main(argv=None):
    args = parse_args(argv)
    roster, bias_table, state_table = deck.load_inputs()
    persons = deck.select(roster["persons"], args.only, args.limit)
    if not persons:
        print("Keine Person im Roster gefunden.", file=sys.stderr)
        return 1

    print(f"PowerDeck: {len(persons)} Karten werden gebaut", file=sys.stderr)

    def progress(index, total, name):
        print(f"  [{index}/{total}] {name}", file=sys.stderr, flush=True)

    result = deck.build(persons, bias_table, state_table,
                        use_gdelt=not args.no_gdelt, on_person=progress)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"\n{result['kartenzahl']} Karten -> {args.out}", file=sys.stderr)
    report(result)
    return 0
