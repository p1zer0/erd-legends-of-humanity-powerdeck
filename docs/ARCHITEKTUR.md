# Architektur

## Zwei Schichten, eine Grenze

```
┌─────────────────────────────────────────────────────────────┐
│  pipeline/            Datenschicht                          │
│                                                             │
│  sources/  wikidata · wikimedia · gdelt   ← das Netz        │
│  scoring   Rohdaten -> Kartenwerte        ← rein rechnerisch│
│  build     Orchestrierung                                   │
│                                                             │
│                        ▼ schreibt                           │
│                  public/cards.json                          │
└─────────────────────────────────────────────────────────────┘
                         │  einzige Verbindung
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  game/                Spielschicht                          │
│                                                             │
│  cards     Karten, Decks, Budgetregeln                      │
│  rules     Konter-Rad, Eskalation, Auflösung  ← rein        │
│  battle    Partie als Zustandsmaschine                      │
│  bot       Gegner zum Prüfen des Spielgefühls               │
└─────────────────────────────────────────────────────────────┘
```

**Die Grenze ist die wichtigste Entscheidung im Projekt.** `game/` importiert
nichts aus `pipeline/` außer dem Pfad zur `cards.json`. Es kennt weder Wikidata
noch GDELT und geht nie ins Netz.

Was das bringt:

- Das Spiel läuft, wenn jede Datenquelle ausfällt.
- Die Regeln sind ohne Netz testbar — 35 Tests laufen in Millisekunden.
- Die Datenpipeline kann ersetzt werden, ohne eine Regel anzufassen.
- Später kann `game/` serverseitig laufen, während `pipeline/` ein Cron-Job bleibt.

## Warum die Regeln kanonisch in Python liegen

Sobald eine Partie über Werte entscheidet, darf man dem Client nicht glauben.
Die Regeln müssen serverseitig nachgerechnet werden. Deshalb:

- Der gesamte Partieverlauf hängt an einem Seed. Gleiche Züge plus gleicher Seed
  ergeben zwingend dasselbe Ergebnis (`test_gleicher_seed_gleicher_verlauf`).
- `Partie.zug_gueltig()` prüft ohne auszuführen — dieselbe Funktion nutzt später
  der Server für eingehende Züge.
- `Partie.protokoll()` gibt den ganzen Verlauf als Text: Log, Replay und Nachweis
  in einem.

Ein Web-Client wird die Regeln **nicht** noch einmal in JavaScript enthalten.
Er zeigt an und schickt Züge; gerechnet wird an einer Stelle. Eine zweite
Regelimplementierung driftet garantiert auseinander, und zwar genau dort, wo es
teuer wird.

## Warum JSON statt Datenbank

`cards.json` ist ein paar hundert Kilobyte, ändert sich einmal am Tag und wird
nur gelesen. Ein CDN trägt das für Zehntausende Spieler. Eine Datenbank lohnt
sich ab dem Moment, wo Spielstände, Konten und Matchmaking dazukommen — also in
Phase 2, nicht vorher.

Nebeneffekt: Die Datei ist versionierbar. Der nächtliche Workflow committet sie,
also ist jede Änderung an jeder Karte nachvollziehbar. Das ist Aufklärung über
den eigenen Datenstand.

## Warum nur Standardbibliothek

Keine Laufzeitabhängigkeit heißt: kein Dependency-Update bricht das Projekt,
kein Lieferkettenrisiko, und jeder mit Python 3.9+ kann es sofort laufen lassen.
Für die Datenmengen hier ist `requests` bequemer, aber nicht nötig — das
Nadelöhr sind die Rate-Limits der Quellen, nicht die HTTP-Bibliothek.

## Entscheidungen im Rückblick

| Entscheidung | Warum | Alternative und warum nicht |
|---|---|---|
| Kein Ground News | Keine öffentliche API | Scraper: gegen ToS, brüchig, rechtlich angreifbar |
| Eigene Bias-Tabelle | Versionierbar, begründbar, im Repo | Zugekaufte Ratings: teuer, undurchsichtig, nicht diskutierbar |
| `macht` ist ein Preis | Sonst ist die stärkste Karte immer die beste | `macht` als Kampfwert: macht 90 % der Karten sinnlos |
| Werte relativ zum Deck | Macht ist ein Verhältnis | Absolute Skalen: willkürliche Obergrenzen |
| Seed statt echtem Zufall | Nachrechenbarkeit | `random` ohne Seed: Partien nicht überprüfbar |
| Fehlschläge nicht cachen | Zweiter Lauf holt genau die Lücken nach | Fehler cachen: Lücken bleiben bis zum TTL-Ablauf |
| Schutzschalter für GDELT | Ein blockierter Lauf endet in Minuten statt Stunden | Endlos wiederholen: Lauf hängt |

## Was noch nicht da ist

Diese Schichten sind geplant, aber bewusst nicht angefangen. Die Pfeile zeigen
die erlaubte Abhängigkeitsrichtung — nach oben darf niemand greifen.

```
   token/     Zahlungsschicht über lizenziertem Partner      Phase 4
     │
   server/    Partien, Konten, Matchmaking                   Phase 2
     │
   web/       Client: zeigt an, schickt Züge, rechnet nicht  Phase 2
     │
   game/      Regeln  ◄── kanonisch, hier ist die Wahrheit   fertig
     │
   pipeline/  Daten                                          fertig
```

Reihenfolge und Begründung stehen in [VISION.md](VISION.md), die Auflagen in
[RECHTLICHES.md](RECHTLICHES.md).

## Tests als Architekturaussage

| Testdatei | Prüft | Warum das die Architektur sichert |
|---|---|---|
| `test_scoring.py` | Kartenwert-Berechnung | Die Entscheidung, was Macht bedeutet, ist isoliert prüfbar |
| `test_wikidata.py` | Auswertung gegen Fixture | Quellenlogik ohne Netz testbar |
| `test_data_files.py` | Roster und Bias-Tabelle | Die von Hand gepflegten Teile können nicht still verrutschen |
| `test_rules.py` | Konter-Rad, Eskalation, Chaos | Die Spielaussage ist als Test formuliert, nicht als Absicht |
| `test_battle.py` | Zustandsmaschine, Balance | Balance ist gemessen, nicht behauptet |

Der Balance-Test spielt 120 Partien Bot gegen Bot und lässt den Build scheitern,
wenn der Startvorteil über 70 % steigt oder eine Angriffsdimension nie gespielt
wird. Eine tote Regel ist ein Fehler, kein Schönheitsfleck.
