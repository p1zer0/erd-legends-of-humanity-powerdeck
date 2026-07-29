# Spielregeln

Stand: v1, umgesetzt in `src/powerdeck/game/rules.py`. Die Konstanten dort sind
die Stellschrauben — jede Zahl in diesem Dokument steht auch im Code.

## Die Karte

Acht Werte, jeder 0–100:

| Wert | Rolle im Spiel | Bedeutung |
|---|---|---|
| **kapital** | Angriff | Verfügungsgewalt über Geld |
| **militaer** | Angriff | Kommandogewalt über Streitkräfte |
| **daten** | Angriff | Personenbezogene Daten in großem Maßstab |
| **narrativ** | Angriff | Medienpräsenz und Deutungshoheit |
| **nuklear** | Eskalation | Zugriff auf Kernwaffen |
| **compute** | Eskalation | Rechenleistung, Chips, KI-Modelle |
| **polarisierung** | passiv | Schutz gegen Narrativ-Angriffe |
| **chaos** | passiv | Wahrscheinlichkeit, eine verlorene Runde zu kippen |

Dazu `macht` — die gewichtete Summe. **Sie spielt im Kampf keine Rolle.** Sie ist
der Preis der Karte beim Deckbau.

## Deckbau

- 8 Karten
- Summe der Machtwerte höchstens **420**
- keine Karte doppelt

Damit ist ein Deck aus lauter Spitzenkarten unbezahlbar. Wer eine 75er-Karte
spielen will, finanziert sie mit mehreren günstigen — und die günstigen müssen
Runden gewinnen können, sonst funktioniert das Spiel nicht. Genau dafür gibt es
das Konter-Rad.

## Ablauf

Fünf Runden, der Angriff wechselt. Wer zuerst drei Runden gewinnt, gewinnt die
Partie.

Pro Runde:

1. Der Angreifer legt eine Karte und nennt eine **Angriffsdimension**.
2. Der Verteidiger legt eine Karte und antwortet mit einer **erlaubten Dimension**.
3. Werte vergleichen, höherer gewinnt.
4. Beide Karten sind für den Rest der Partie verbraucht.

Bei acht Karten und fünf Runden bleibt jeder Seite Auswahl bis zum Schluss —
aber nicht genug, um jede Runde die perfekte Antwort zu haben.

## Das Konter-Rad

Der Verteidiger darf entweder **dieselbe Dimension** spielen (Kraft gegen Kraft)
oder die **konternde**:

```
     Kapital ◄────────── Narrativ
        │                    ▲
        │                    │
        ▼                    │
     Militär ──────────►  Daten
```

| Angriff | wird gekontert von | warum |
|---|---|---|
| Kapital | Narrativ | Boykott, Reputationsverlust, Kursverfall |
| Militär | Kapital | Sanktionen, Lieferketten, Söldner |
| Daten | Militär | physischer Zugriff auf Infrastruktur |
| Narrativ | Daten | wer die Zielgruppe kennt, steuert die Erzählung |

Das Rad ist geschlossen: jede Dimension kontert genau eine und wird von genau
einer gekontert. Es gibt keine Dimension ohne Antwort — ein Test prüft das.

## Eskalation

`nuklear` und `compute` sind Angriffsdimensionen mit Sonderregeln:

- **Höchstens einmal pro Partie** und Seite.
- **Nuklear** ist nur durch Nuklear zu beantworten. Wer sie einsetzt, verliert
  **dauerhaft die Hälfte seines Narrativs** auf allen Karten — für den Rest der
  Partie. Die Welt vergisst das nicht.
- **Compute** wird durch **Militär** gekontert. Rechenzentren stehen an
  physischen Orten.
- Verteidigt eine **Zivilgesellschafts-Karte**, wirkt die Eskalation nur zur
  Hälfte. Zivilgesellschaft ist das, was Eskalation teuer macht.

Eskalation gewinnt fast jede Runde, in der sie fällt. Der Preis kommt danach.

## Polarisierung

Wird eine Karte auf **Narrativ** angegriffen und antwortet mit Narrativ, zählt
zusätzlich die **halbe Polarisierung** zur Verteidigung.

Wer stark polarisiert, ist gegen Kritik weitgehend immun. Das ist unangenehm und
genau deshalb im Spiel: es ist beobachtbar wahr, und man spürt es, wenn man
dagegen anrennt.

Gegen alle anderen Dimensionen hilft Polarisierung nicht.

## Chaos

Nach der Auswertung bekommt die **unterlegene Karte** eine Chance, das Ergebnis
zu drehen: `chaos / 400`. Bei chaos 100 also jede vierte verlorene Runde.

Chaos macht Außenseiter gefährlich, ohne das Spiel dem Zufall zu überlassen.
Der Wert stammt aus echten Daten — er misst, wie unberechenbar die
Aufmerksamkeit um eine Person schwankt.

Jeder Umschlag steht im Protokoll. Nichts passiert unsichtbar.

## Zivilgesellschaft

Karten der Fraktion `zivil` sind in fast jeder Dimension schwach. Dafür:

- Sie **halbieren gegnerische Eskalation**, gegen die sie verteidigen.
- Sie **gewinnen den Gleichstand** bei Narrativ-Verteidigung gegen `staat` und
  `kapital`. Sonst entscheidet Gleichstand für den Angreifer.
- Ihre Chaos-Werte sind typischerweise hoch — sie kippen Runden, die sie
  eigentlich verloren hatten.

## Stellschrauben

Alles Folgende steht als Konstante in `rules.py` bzw. `cards.py` und ist zum
Drehen gedacht:

| Konstante | Wert | Wirkung beim Erhöhen |
|---|---|---|
| `MACHT_BUDGET` | 420 | teurere Decks möglich, Spitzenkarten häufiger |
| `DECKGROESSE` | 8 | mehr Auswahl pro Partie, weniger Härte in der Kartenwahl |
| `POLARISIERUNGS_SCHUTZ` | 0.5 | Narrativ-Angriffe werden schwächer |
| `CHAOS_TEILER` | 400 | weniger Umschläge, mehr Vorhersagbarkeit |
| `NUKLEAR_NARRATIV_REST` | 0.5 | Nuklear-Eskalation wird billiger |
| `ZIVIL_ESKALATIONS_DAEMPFUNG` | 0.5 | Zivilgesellschaft wird schwächer gegen Eskalation |

Nach jeder Änderung: `make test`. Der Balance-Test spielt 120 Partien und
scheitert, wenn der Startvorteil über 70 % steigt oder eine Angriffsdimension
nie mehr gespielt wird.

## Offen für v2

- **Enthüllung**: Zivil-Karten dürfen einmal pro Partie die gegnerische Hand
  aufdecken. Information als Gegenmacht — passt thematisch, braucht aber
  verdeckte Züge, und die gibt es erst mit Server.
- **Verdeckte Züge**: Beide legen gleichzeitig, dann wird aufgedeckt. Macht
  Lesen und Bluffen möglich. Aktuell zieht der Verteidiger nach.
- **Bündnisse**: Karten, die real verbunden sind (Wikidata `P108`, `P463`,
  `P1830`), geben zusammen einen Bonus. Siehe [ROADMAP.md](ROADMAP.md), Weg 3.
