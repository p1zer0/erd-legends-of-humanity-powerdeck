"""Der Verbesserungs-Loop – erreichbar über `python3 -m powerdeck loop`.

Zwei Betriebsarten:

    python3 -m powerdeck loop                    alle Aufgaben, Vorschläge schreiben
    python3 -m powerdeck loop --anwenden <datei> einen Vorschlag übernehmen

Die Trennung ist der Kern: Der Loop läuft, so oft er will, und produziert
Vorschläge. Übernommen wird nur, was jemand gelesen hat.
"""

import argparse
import sys
from pathlib import Path

from ..pipeline.config import ROOT
from . import proposals
from .tasks import AUFGABEN

VORSCHLAGSORDNER = ROOT / "proposals"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="powerdeck loop",
        description="Sucht Verbesserungen und schlägt sie vor – ohne selbst zu schreiben.")
    parser.add_argument("--aufgabe", choices=sorted(AUFGABEN),
                        help="nur diese eine Aufgabe laufen lassen")
    parser.add_argument("--ordner", type=Path, default=VORSCHLAGSORDNER,
                        help="wohin die Vorschläge geschrieben werden")
    parser.add_argument("--anwenden", type=Path,
                        help="einen Vorschlag (JSON) in die Zieldatei einarbeiten")
    parser.add_argument("--bestaetigt", action="store_true",
                        help="prüfpflichtige Vorschläge übernehmen – nach dem Lesen")
    return parser.parse_args(argv)


def anwenden(args):
    vorschlag = proposals.laden(args.anwenden)
    try:
        anzahl = proposals.anwenden(vorschlag, ROOT, bestaetigt=args.bestaetigt)
    except PermissionError as fehler:
        print(f"{fehler}\n", file=sys.stderr)
        print(f"Erst lesen: {args.anwenden.with_suffix('.md')}", file=sys.stderr)
        return 2
    print(f"{anzahl} Einträge übernommen in {vorschlag.datei}")
    if anzahl:
        print("Nicht vergessen: Platzhalter ersetzen, dann `make test`.")
    return 0


def main(argv=None):
    args = parse_args(argv)
    if args.anwenden:
        return anwenden(args)

    namen = [args.aufgabe] if args.aufgabe else sorted(AUFGABEN)
    print(f"Verbesserungs-Loop: {len(namen)} Aufgaben\n", file=sys.stderr)

    geschrieben = []
    for name in namen:
        funktion, beschreibung = AUFGABEN[name]
        print(f"  {name}: {beschreibung}", file=sys.stderr, flush=True)
        try:
            vorschlag = funktion()
        except Exception as fehler:  # eine Aufgabe darf den Loop nicht kippen
            print(f"    fehlgeschlagen: {fehler}", file=sys.stderr)
            continue
        if vorschlag is None:
            print("    nichts zu tun", file=sys.stderr)
            continue
        pfad = proposals.speichern(vorschlag, args.ordner)
        geschrieben.append((vorschlag, pfad))
        marke = " [prüfpflichtig]" if vorschlag.prueffplicht else ""
        print(f"    -> {vorschlag.titel}{marke}", file=sys.stderr)

    if not geschrieben:
        print("\nKeine Vorschläge. Das ist ein gutes Ergebnis.", file=sys.stderr)
        return 0

    print(f"\n{len(geschrieben)} Vorschläge in {args.ordner}:", file=sys.stderr)
    for _, pfad in geschrieben:
        print(f"  {pfad.with_suffix('.md').name}", file=sys.stderr)
    print("\nLesen, entscheiden, dann:", file=sys.stderr)
    print(f"  python3 -m powerdeck loop --anwenden {geschrieben[0][1]}", file=sys.stderr)
    return 0
