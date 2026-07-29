"""Gemeinsamer Einstieg: `python3 -m powerdeck <befehl>`."""

import sys

BEFEHLE = {
    "deck": ("powerdeck.pipeline.cli", "cards.json aus offenen Datenquellen bauen"),
    "play": ("powerdeck.game.cli", "eine Partie im Terminal spielen"),
    "loop": ("powerdeck.loop.cli", "Verbesserungen suchen und vorschlagen"),
    "heartbeat": ("powerdeck.loop.heartbeat", "dauerhaft weiterentwickeln, bis du stoppst"),
}


def hilfe():
    print("Aufruf: python3 -m powerdeck <befehl> [optionen]\n")
    print("Befehle:")
    for name, (_, beschreibung) in BEFEHLE.items():
        print(f"  {name:<10} {beschreibung}")
    print("\n  python3 -m powerdeck <befehl> --help  zeigt die Optionen")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        hilfe()
        return 0
    befehl, rest = argv[0], argv[1:]
    if befehl not in BEFEHLE:
        print(f"Unbekannter Befehl: {befehl}\n", file=sys.stderr)
        hilfe()
        return 1
    modul = __import__(BEFEHLE[befehl][0], fromlist=["main"])
    return modul.main(rest)
