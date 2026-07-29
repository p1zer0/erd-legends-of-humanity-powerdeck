"""Medien einordnen – mit Konsens statt Vertrauen.

Die politische Einordnung einer Nachrichtenquelle ist die heikelste Zahl im
Projekt. Ein einzelnes Modell darf sie nicht setzen: Modelle sind bei genau
dieser Frage messbar unsicher und ziemlich selbstbewusst dabei.

Deshalb wird jede Domain **mehrfach unabhängig** gefragt. Übernommen wird nur,
worüber sich die Anbieter einig sind – gleiche Kategorie und Werte nah
beieinander. Alles andere geht als Vorschlag an einen Menschen, mit beiden
Einschätzungen nebeneinander. Uneinigkeit ist kein Fehler, sondern die
interessanteste Information: sie zeigt, wo die Einordnung wirklich strittig ist.
"""

import json
import statistics

from ..pipeline.config import BIAS_FILE
from . import agent

SYSTEM = """Du ordnest Nachrichtenquellen politisch ein, für ein Aufklärungsspiel
über Machtverhältnisse. Deine Einordnung wird veröffentlicht und muss belegbar sein.

Skala: -2 = deutlich links, -1 = links, 0 = Mitte, +1 = rechts, +2 = deutlich rechts.
Zwischenwerte sind erlaubt (z.B. -0.7).

Regeln:
- Beurteile die redaktionelle Linie, nicht einzelne Artikel.
- Staatlich kontrollierte oder staatsnahe Medien bekommen die Kategorie "staat"
  und KEINEN Links-Rechts-Wert. Sie passen nicht auf diese Achse.
- Reine Wirtschafts-, Sport- oder Fachdienste ohne politische Linie: 0 mit
  niedriger Sicherheit.
- Wenn du eine Quelle nicht kennst: sicherheit 0 und sag es. Rate nicht.
  Eine falsche Einordnung ist schlechter als keine.

Antworte ausschließlich mit JSON, ohne Fließtext drumherum:
{"eintraege": [{"domain": "...", "kategorie": "bias"|"staat", "wert": -2..2,
"land": "nur bei staat", "sicherheit": 0..1, "begruendung": "ein Satz"}]}"""


def _frage_einordnung(domains, anbieter_index):
    """Eine Runde Einordnung. anbieter_index verschiebt die Kaskade, damit
    zwei Durchläufe möglichst nicht denselben Anbieter erwischen."""
    alle = agent.lade_anbieter()
    if not alle:
        raise agent.KeinAnbieter("kein Anbieter konfiguriert")

    # Kaskade rotieren: Durchlauf 2 beginnt beim zweiten Anbieter
    gedreht = alle[anbieter_index % len(alle):] + alle[:anbieter_index % len(alle)]

    nachrichten = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "Ordne diese Quellen ein:\n" + "\n".join(domains)},
    ]

    fehler = []
    for eintrag in gedreht:
        try:
            roh = agent._anfrage(eintrag, nachrichten, max_tokens=2000, temperatur=0.1)
        except Exception as e:
            fehler.append(f"{eintrag['name']}: {type(e).__name__}")
            continue
        text = roh.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:]
        try:
            daten = json.loads(text.strip())
        except json.JSONDecodeError:
            fehler.append(f"{eintrag['name']}: kein JSON")
            continue
        return {e["domain"].lower(): e for e in daten.get("eintraege", [])}, eintrag["name"]

    raise agent.KeinAnbieter("; ".join(fehler))


def einordnen(domains, noetig=2, toleranz=0.75, protokoll=None):
    """Domains mehrfach einordnen lassen und nach Konsens trennen.

    Rückgabe: (einig, strittig)
      einig    – {domain: {"kategorie", "wert", "land", "begruendung", "stimmen"}}
      strittig – {domain: [alle Einzeleinschätzungen]}
    """
    if noetig < 1:
        return {}, {}

    runden = []
    for i in range(noetig):
        try:
            ergebnis, name = _frage_einordnung(domains, i)
            runden.append((name, ergebnis))
            if protokoll:
                protokoll(f"Einordnung {i + 1}/{noetig} von {name}: "
                          f"{len(ergebnis)} Quellen")
        except agent.KeinAnbieter as e:
            if protokoll:
                protokoll(f"Einordnung {i + 1}/{noetig} fehlgeschlagen: {e}")

    if len(runden) < noetig:
        return {}, {}  # ohne genug unabhängige Stimmen wird nichts übernommen

    einig, strittig = {}, {}
    for domain in domains:
        stimmen = [(name, r[domain]) for name, r in runden if domain in r]
        if len(stimmen) < noetig:
            continue

        kategorien = {s["kategorie"] for _, s in stimmen}
        sicher = all(s.get("sicherheit", 0) >= 0.5 for _, s in stimmen)

        if len(kategorien) > 1 or not sicher:
            strittig[domain] = [{"anbieter": n, **s} for n, s in stimmen]
            continue

        if kategorien == {"staat"}:
            laender = {s.get("land", "") for _, s in stimmen}
            if len(laender) == 1:
                einig[domain] = {"kategorie": "staat", "land": laender.pop(),
                                 "begruendung": stimmen[0][1].get("begruendung", ""),
                                 "stimmen": [n for n, _ in stimmen]}
            else:
                strittig[domain] = [{"anbieter": n, **s} for n, s in stimmen]
            continue

        werte = [float(s.get("wert", 0)) for _, s in stimmen]
        if max(werte) - min(werte) <= toleranz:
            einig[domain] = {"kategorie": "bias",
                             "wert": round(statistics.fmean(werte), 2),
                             "begruendung": stimmen[0][1].get("begruendung", ""),
                             "stimmen": [n for n, _ in stimmen]}
        else:
            strittig[domain] = [{"anbieter": n, **s} for n, s in stimmen]

    return einig, strittig


def uebernehmen(einig):
    """Konsens-Einordnungen in die Bias-Tabelle schreiben.

    Bestehende Einträge werden nie überschrieben – Handarbeit gewinnt gegen
    Automatik. Rückgabe: Anzahl tatsächlich ergänzter Domains.
    """
    daten = json.loads(BIAS_FILE.read_text(encoding="utf-8"))
    bekannt = set(daten["bias"]) | set(daten["state"])
    ergaenzt = 0

    for domain, eintrag in einig.items():
        if domain in bekannt:
            continue
        if eintrag["kategorie"] == "staat":
            daten["state"][domain] = eintrag["land"]
        else:
            daten["bias"][domain] = eintrag["wert"]
        ergaenzt += 1

    if ergaenzt:
        daten["bias"] = dict(sorted(daten["bias"].items()))
        daten["state"] = dict(sorted(daten["state"].items()))
        BIAS_FILE.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    return ergaenzt
