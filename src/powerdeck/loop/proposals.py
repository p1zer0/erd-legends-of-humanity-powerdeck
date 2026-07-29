"""Vorschläge: das Format, in dem der Loop Verbesserungen liefert.

Ein Vorschlag ist kein Commit. Er ist eine begründete, belegte Änderung an einer
Datendatei, die ein Mensch annehmen oder verwerfen kann. Das ist die einzige
Stelle im Projekt, an der Automatik auf gepflegte Inhalte trifft – deshalb hat
sie ein eigenes Format und einen eigenen Test.

Warum kein Auto-Commit: Das Projekt verspricht, dass jede Zahl eine Quelle hat.
Ein System, das unbeaufsichtigt Aussagen über namentlich genannte lebende
Menschen schreibt, kann dieses Versprechen nicht halten – ein einziger falscher
Wert kostet die Glaubwürdigkeit aller anderen.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

# Änderungen an diesen Dateien betreffen Aussagen über reale Personen.
# Sie sind immer prüfpflichtig, egal wie gut der Beleg aussieht.
PRUEFPFLICHTIG = {"data/roster.json"}


@dataclass
class Vorschlag:
    """Eine vorgeschlagene Änderung an genau einer Datei."""

    aufgabe: str                    # welche Loop-Aufgabe ihn erzeugt hat
    datei: str                      # Pfad relativ zum Repo
    titel: str
    begruendung: str
    eintraege: dict = field(default_factory=dict)   # was ergänzt werden soll
    belege: list = field(default_factory=list)      # URLs, die das stützen
    hinweise: list = field(default_factory=list)    # was ein Mensch prüfen muss
    erzeugt_am: str = ""

    def __post_init__(self):
        if not self.erzeugt_am:
            self.erzeugt_am = date.today().isoformat()

    @property
    def prueffplicht(self):
        return self.datei in PRUEFPFLICHTIG

    def als_markdown(self):
        zeilen = [
            f"# {self.titel}",
            "",
            f"**Aufgabe:** `{self.aufgabe}`  ",
            f"**Datei:** `{self.datei}`  ",
            f"**Erzeugt:** {self.erzeugt_am}",
            "",
            "## Begründung",
            "",
            self.begruendung,
            "",
            f"## Vorgeschlagene Einträge ({len(self.eintraege)})",
            "",
            "```json",
            json.dumps(self.eintraege, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
        if self.belege:
            zeilen += ["## Belege", ""] + [f"- {b}" for b in self.belege] + [""]
        if self.hinweise:
            zeilen += ["## Vor dem Übernehmen prüfen", ""] + \
                      [f"- [ ] {h}" for h in self.hinweise] + [""]
        if self.prueffplicht:
            zeilen += [
                "> **Prüfpflichtig.** Diese Datei enthält Aussagen über reale "
                "Personen und Organisationen. Nicht ungelesen übernehmen.",
                "",
            ]
        return "\n".join(zeilen)


def speichern(vorschlag, ordner):
    """Vorschlag als JSON (maschinenlesbar) und Markdown (für Menschen)."""
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    basis = f"{vorschlag.erzeugt_am}-{vorschlag.aufgabe}"
    json_pfad = ordner / f"{basis}.json"
    json_pfad.write_text(json.dumps(asdict(vorschlag), ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    (ordner / f"{basis}.md").write_text(vorschlag.als_markdown(), encoding="utf-8")
    return json_pfad


def laden(pfad):
    daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    return Vorschlag(**daten)


def anwenden(vorschlag, wurzel, bestaetigt=False):
    """Einen Vorschlag in die Zieldatei einarbeiten.

    Prüfpflichtige Dateien verlangen ein ausdrückliches `bestaetigt=True`.
    Diese Prüfung sitzt absichtlich hier und nicht in der CLI: sie soll auch
    dann greifen, wenn der Loop später von einem anderen Programm aufgerufen wird.
    """
    if vorschlag.prueffplicht and not bestaetigt:
        raise PermissionError(
            f"{vorschlag.datei} ist prüfpflichtig – Vorschlag muss ausdrücklich "
            f"bestätigt werden (--bestaetigt).")

    # Zieltyp zuerst prüfen: ein unbekanntes Ziel soll klar scheitern,
    # nicht an einer fehlenden Datei.
    if not vorschlag.datei.endswith(("bias_sources.json", "roster.json")):
        raise ValueError(f"Unbekanntes Ziel: {vorschlag.datei}")

    ziel = Path(wurzel) / vorschlag.datei
    daten = json.loads(ziel.read_text(encoding="utf-8"))

    if vorschlag.datei.endswith("bias_sources.json"):
        neu = {k: v for k, v in vorschlag.eintraege.items() if k not in daten["bias"]}
        daten["bias"].update(neu)
        daten["bias"] = dict(sorted(daten["bias"].items()))
        geaendert = len(neu)
    elif vorschlag.datei.endswith("roster.json"):
        bekannt = {p["name"] for p in daten["persons"]}
        neu = [p for p in vorschlag.eintraege.values() if p["name"] not in bekannt]
        daten["persons"].extend(neu)
        geaendert = len(neu)

    ziel.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return geaendert
