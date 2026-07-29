"""Der Herzschlag: läuft weiter, bis jemand ihn stoppt.

Ein Schlag besteht aus vier Schritten:

  1. Daten auffrischen      Deck neu bauen, wenn es alt ist
  2. Lücken suchen          die Aufgaben aus tasks.py
  3. Einordnen              unbekannte Medien, mit Konsens mehrerer Modelle
  4. Berichten              Journal schreiben, Vorschläge ablegen

Was einig ist, wird übernommen. Was strittig ist, geht an einen Menschen.
Aussagen über Personen gehen immer an einen Menschen.

Gestoppt wird über eine Datei (`.heartbeat-stop`), über SIGTERM oder mit
Strg-C. Der laufende Schlag wird dabei zu Ende gebracht, damit nichts halb
geschrieben liegen bleibt.
"""

import json
import signal
import sys
import time
from datetime import datetime, timezone

from ..pipeline.config import BIAS_FILE, DEFAULT_OUT, ROOT
from . import agent, classify, proposals
from .tasks import AUFGABEN, unbekannte_domains

STOPPDATEI = ROOT / ".heartbeat-stop"
JOURNAL = ROOT / "heartbeat.jsonl"
VORSCHLAEGE = ROOT / "proposals"

# Wie viele Domains pro Schlag eingeordnet werden. Klein halten: lieber jede
# Stunde zehn belastbare als einmal zweihundert schnelle.
DOMAINS_PRO_SCHLAG = 10

# Ab diesem Alter in Stunden gilt das Deck als alt.
DECK_MAX_ALTER = 20


class Herzschlag:
    def __init__(self, intervall=3600, konsens=2, toleranz=0.75, trocken=False):
        self.intervall = intervall
        self.konsens = konsens
        self.toleranz = toleranz
        self.trocken = trocken
        self.laeuft = True
        self.schlag = 0
        signal.signal(signal.SIGTERM, self._stoppen)
        signal.signal(signal.SIGINT, self._stoppen)

    def _stoppen(self, *_):
        if self.laeuft:
            self.log("Stoppsignal erhalten – laufender Schlag wird beendet")
        self.laeuft = False

    # ------------------------------------------------------------- Ausgabe

    def log(self, text, **felder):
        zeit = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"  {text}", file=sys.stderr, flush=True)
        eintrag = {"zeit": zeit, "schlag": self.schlag, "text": text, **felder}
        with JOURNAL.open("a", encoding="utf-8") as datei:
            datei.write(json.dumps(eintrag, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------ Schritte

    def deck_auffrischen(self):
        """Nur bauen, wenn die Daten alt sind – die Quellen sollen nicht leiden."""
        if DEFAULT_OUT.exists():
            alter = (time.time() - DEFAULT_OUT.stat().st_mtime) / 3600
            if alter < DECK_MAX_ALTER:
                self.log(f"Deck ist {alter:.0f} h alt – kein Neubau nötig")
                return
        if self.trocken:
            self.log("Deck wäre neu zu bauen (Trockenlauf)")
            return

        from ..pipeline import build as pipeline
        self.log("Deck wird neu gebaut")
        roster, bias, staat = pipeline.load_inputs()
        ergebnis = pipeline.build(roster["persons"], bias, staat)
        DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_OUT.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        warnungen = sum(1 for c in ergebnis["cards"] if c["warnungen"])
        self.log(f"Deck gebaut: {ergebnis['kartenzahl']} Karten, "
                 f"{warnungen} mit Hinweisen",
                 karten=ergebnis["kartenzahl"], warnungen=warnungen)

    def luecken_suchen(self):
        neu = 0
        for name, (funktion, _) in sorted(AUFGABEN.items()):
            try:
                vorschlag = funktion()
            except Exception as fehler:
                self.log(f"Aufgabe {name} fehlgeschlagen: {fehler}")
                continue
            if vorschlag is None:
                continue
            if not self.trocken:
                proposals.speichern(vorschlag, VORSCHLAEGE)
            neu += 1
            self.log(f"Vorschlag: {vorschlag.titel}", aufgabe=name)
        if not neu:
            self.log("keine neuen Lücken gefunden")
        return neu

    def medien_einordnen(self):
        """Der einzige Schritt, der ohne Menschen in eine Datendatei schreibt.

        Erlaubt ist das, weil: mehrere unabhängige Modelle müssen übereinstimmen,
        bestehende Einträge werden nie überschrieben, jede Änderung ist ein
        Commit und damit umkehrbar – und es sind Aussagen über Redaktionen,
        nicht über Personen.
        """
        if not agent.verfuegbar():
            self.log("kein Modell konfiguriert – Einordnung übersprungen "
                     "(agents.example.json nach agents.json kopieren)")
            return 0

        offen = [d for d, _ in unbekannte_domains(mindestens=2)][:DOMAINS_PRO_SCHLAG]
        if not offen:
            self.log("alle bekannten Medien sind eingeordnet")
            return 0

        einig, strittig = classify.einordnen(offen, self.konsens, self.toleranz,
                                             protokoll=self.log)

        if strittig and not self.trocken:
            proposals.speichern(proposals.Vorschlag(
                aufgabe="einordnung-strittig",
                datei="data/bias_sources.json",
                titel=f"{len(strittig)} Quellen: die Modelle sind sich uneinig",
                begruendung=(
                    "Bei diesen Quellen wichen die unabhängigen Einschätzungen "
                    "voneinander ab oder waren unsicher. Uneinigkeit ist hier die "
                    "interessantere Information: sie zeigt, wo die Einordnung "
                    "tatsächlich strittig ist. Bitte von Hand entscheiden."),
                eintraege=strittig,
                hinweise=[f"{d}: " + " / ".join(
                    f"{s['anbieter']} sagt {s.get('kategorie')} {s.get('wert', '')}"
                    for s in stimmen) for d, stimmen in strittig.items()],
            ), VORSCHLAEGE)

        if self.trocken:
            self.log(f"würde {len(einig)} Quellen übernehmen (Trockenlauf)")
            return 0

        anzahl = classify.uebernehmen(einig)
        self.log(f"{anzahl} Quellen eingeordnet, {len(strittig)} strittig "
                 f"an Menschen abgegeben",
                 uebernommen=anzahl, strittig=len(strittig))
        return anzahl

    def abdeckung(self):
        """Die eine Zahl, an der Fortschritt sichtbar wird."""
        daten = json.loads(BIAS_FILE.read_text(encoding="utf-8"))
        return len(daten["bias"]) + len(daten["state"])

    # -------------------------------------------------------------- Ablauf

    def ein_schlag(self):
        self.schlag += 1
        vorher = self.abdeckung()
        print(f"\n--- Schlag {self.schlag} ---", file=sys.stderr)

        self.deck_auffrischen()
        self.luecken_suchen()
        self.medien_einordnen()

        nachher = self.abdeckung()
        self.log(f"Schlag {self.schlag} fertig: {nachher} eingeordnete Quellen "
                 f"({nachher - vorher:+d})", quellen=nachher, zuwachs=nachher - vorher)

    def laufen(self, max_schlaege=None):
        if STOPPDATEI.exists():
            STOPPDATEI.unlink()
        self.log(f"Herzschlag gestartet, Intervall {self.intervall} s, "
                 f"Konsens {self.konsens}")

        while self.laeuft:
            try:
                self.ein_schlag()
            except Exception as fehler:
                # Ein kaputter Schlag beendet den Herzschlag nicht. Er soll
                # laufen, bis jemand ihn stoppt – das ist der ganze Punkt.
                self.log(f"Schlag fehlgeschlagen: {type(fehler).__name__}: {fehler}")

            if max_schlaege and self.schlag >= max_schlaege:
                self.log(f"{max_schlaege} Schläge erreicht – Ende")
                break

            wartet = 0
            while self.laeuft and wartet < self.intervall:
                if STOPPDATEI.exists():
                    self.log("Stoppdatei gefunden")
                    STOPPDATEI.unlink()
                    self.laeuft = False
                    break
                time.sleep(min(5, self.intervall - wartet))
                wartet += 5

        self.log(f"Herzschlag beendet nach {self.schlag} Schlägen")
        return 0


def stoppen():
    """Von außen: dem laufenden Herzschlag sagen, dass Schluss ist."""
    STOPPDATEI.touch()
    print(f"Stoppsignal abgelegt: {STOPPDATEI}", file=sys.stderr)
    print("Der laufende Schlag wird noch zu Ende gebracht.", file=sys.stderr)
    return 0


def journal_zeigen(zeilen=20):
    if not JOURNAL.exists():
        print("Noch kein Journal – der Herzschlag lief nie.", file=sys.stderr)
        return 0
    eintraege = JOURNAL.read_text(encoding="utf-8").strip().split("\n")
    for zeile in eintraege[-zeilen:]:
        eintrag = json.loads(zeile)
        print(f"{eintrag['zeit']}  [{eintrag['schlag']:>3}]  {eintrag['text']}")
    return 0


# ------------------------------------------------------------------ CLI

def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        prog="powerdeck heartbeat",
        description="Läuft weiter und entwickelt das Projekt fort, bis du ihn stoppst.")
    parser.add_argument("--intervall", type=int, default=3600,
                        help="Sekunden zwischen zwei Schlägen (Standard 3600)")
    parser.add_argument("--konsens", type=int, default=None,
                        help="wie viele Modelle einer Einordnung zustimmen müssen")
    parser.add_argument("--schlaege", type=int, default=None,
                        help="nach so vielen Schlägen aufhören (Standard: nie)")
    parser.add_argument("--trocken", action="store_true",
                        help="alles durchrechnen, nichts schreiben")
    parser.add_argument("--stop", action="store_true",
                        help="einem laufenden Herzschlag sagen, dass Schluss ist")
    parser.add_argument("--journal", type=int, nargs="?", const=20, default=None,
                        help="die letzten N Journaleinträge zeigen")
    args = parser.parse_args(argv)

    if args.stop:
        return stoppen()
    if args.journal is not None:
        return journal_zeigen(args.journal)

    konsens, toleranz = args.konsens, 0.75
    if agent.KONFIG.exists():
        einstellungen = json.loads(agent.KONFIG.read_text(encoding="utf-8")).get("konsens", {})
        konsens = konsens if konsens is not None else einstellungen.get("noetig", 2)
        toleranz = einstellungen.get("toleranz", 0.75)
    konsens = 2 if konsens is None else konsens

    herz = Herzschlag(intervall=args.intervall, konsens=konsens,
                      toleranz=toleranz, trocken=args.trocken)
    return herz.laufen(max_schlaege=args.schlaege)
