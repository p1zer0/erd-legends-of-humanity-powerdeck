# PowerDeck

Ein Kartenspiel über die Menschen und Organisationen, die bestimmen, wie es auf
der Welt weitergeht — mit Werten, die aus offenen Quellen berechnet statt
behauptet werden.

Man spielt sie gegeneinander aus und lernt dabei, woraus Macht tatsächlich
besteht: Geld, Waffen, Daten, Rechenleistung, Erzählung. **Es gibt keinen
Gesamtwert, der eine Karte besser macht als eine andere.** Wer nur eine Form von
Macht hat, verliert gegen die richtige Antwort.

Die Gebühren aus dem Betrieb gehen an Friedens- und Nachhaltigkeitsprojekte, mit
veröffentlichter Liste. Warum, in welcher Reihenfolge und mit welchen Auflagen
steht in [docs/VISION.md](docs/VISION.md).

```bash
make deck        # Kartendaten aus offenen Quellen bauen (~25 min)
make deck-fast   # dasselbe ohne GDELT (~1 min)
make play        # eine Partie im Terminal
make watch       # Bot gegen Bot, nur zuschauen
make loop        # nach Verbesserungen suchen
make test        # 86 Tests, ohne Netz
make serve       # Kartenvorschau auf localhost:8000
```

Kein API-Key, keine Laufzeitabhängigkeit — nur die Python-Standardbibliothek.

## Die acht Werte

| Wert | Rolle | Woher |
|---|---|---|
| **kapital** | Angriff | Wikidata `P2218`, logarithmisch |
| **militaer** | Angriff | `data/roster.json`, redaktionell und begründet |
| **daten** | Angriff | `data/roster.json` |
| **narrativ** | Angriff | GDELT-Artikelvolumen + Wikipedia-Aufrufe, 30 Tage |
| **nuklear** | Eskalation | `data/roster.json` |
| **compute** | Eskalation | `data/roster.json` |
| **polarisierung** | Verteidigung | GDELT-Quellen × `data/bias_sources.json` |
| **chaos** | Wildcard | Schwankung der Wikipedia-Aufrufe |

Dazu `macht`, die gewichtete Summe — sie ist der **Preis der Karte beim
Deckbau**, nicht ihre Stärke im Kampf. Ein Deck aus lauter Spitzenkarten ist
unbezahlbar, also müssen günstige Karten Runden gewinnen können. Dafür gibt es
das Konter-Rad:

```
     Kapital ◄────────── Narrativ        Kapital  schlägt Militär
        │                    ▲           Militär  schlägt Daten
        ▼                    │           Daten    schlägt Narrativ
     Militär ──────────►  Daten          Narrativ schlägt Kapital
```

Vollständig in [docs/SPIELREGELN.md](docs/SPIELREGELN.md).

## Fünf Fraktionen

`staat` · `tech` · `kapital` · `narrativ` · **`zivil`**

Die fünfte ist die, um die es eigentlich geht: Organisationen mit Wirkung, aber
ohne Amt, Kapital oder Waffen — Amnesty, Ärzte ohne Grenzen, Greenpeace, ICAN,
die Wikimedia Foundation. Schwach in fast jeder Dimension, dafür stark in
Narrativ und Chaos, und sie dämpfen gegnerische Eskalation.

Das ist der Ort, an dem Non-Profits im Spiel sichtbar werden — als spielbare
Karten, nicht als Banner. Und die zweite Aussage des Spiels: **Macht ist nicht
dasselbe wie Wirkung.**

## Warum nicht Ground News

Ground News hat keine öffentliche API. Was das Produkt ausmacht, ist eine Schicht
über frei zugänglichen Daten: Artikel sammeln, Quellen nach Ausrichtung
einordnen, Verteilung zeigen. Genau das macht `pipeline/scoring.py` — mit GDELT
als Artikelquelle und `data/bias_sources.json` als Einordnung, die im Repo liegt,
versionierbar und diskutierbar ist.

```json
"berichterstattung": {
  "verteilung_prozent": { "links": 30, "mitte": 55, "rechts": 15, "staatsnah": 4 },
  "artikel_ausgewertet": 250,
  "abdeckung_prozent": 20,
  "staatsmedien": { "Russland": 3 }
}
```

`abdeckung_prozent` sagt, wie belastbar die Zahl ist. Die Spektrum-Anteile
beziehen sich auf die eingeordneten Artikel — sonst sähe jede Karte künstlich
ausgewogen aus.

## Architektur

```
src/powerdeck/
├── pipeline/     Daten: sources · scoring · build     → public/cards.json
├── game/         Regeln: cards · rules · battle · bot
└── loop/         Verbesserungen: tasks · proposals
```

`game/` importiert nichts aus `pipeline/` außer dem Pfad zur `cards.json`. Es
kennt weder Wikidata noch GDELT und geht nie ins Netz. Das Spiel läuft, wenn
jede Datenquelle ausfällt, und die Regeln sind ohne Netz testbar.

Der ganze Partieverlauf hängt an einem Seed — gleiche Züge plus gleicher Seed
ergeben zwingend dasselbe Ergebnis. Sobald eine Partie über Werte entscheidet,
muss sie nachrechenbar sein. Details in [docs/ARCHITEKTUR.md](docs/ARCHITEKTUR.md).

## Der Verbesserungs-Loop

`make loop` sucht Lücken und schreibt Vorschläge nach `proposals/` — welche
Medien noch nicht eingeordnet sind, welche stark nachgeschlagenen Personen im
Deck fehlen, welche Karten die Welt von gestern zeigen. Ein Workflow lässt ihn
wöchentlich laufen und öffnet einen Pull Request.

**Der Loop schlägt vor, ein Mensch entscheidet.** Änderungen an `data/roster.json`
sind prüfpflichtig und lassen sich ohne ausdrückliche Bestätigung nicht
übernehmen — durchgesetzt im Code, nicht nur in der Doku. Begründung und die
Stufen, über die mehr Autonomie verdient wird, in [docs/AGENTEN.md](docs/AGENTEN.md).

## Das Deck sagt Bescheid, wenn es veraltet

Jede Person hat ein Feld `expect` mit einem Stichwort ihrer Rolle. Der Builder
prüft gegen Wikidata und meldet Abweichungen und Todesdaten.

Beim ersten Lauf hat das sofort gegriffen: Ali Khamenei ist laut Wikidata am
28.02.2026 gestorben, seit dem 08.03.2026 ist Mojtaba Khamenei im Amt. Ein Deck
über Machthaber, das Amtswechsel verschläft, wäre das Gegenteil von Aufklärung.

## Rechtliches in einem Absatz

Wikidata-Fakten sind CC0, Wikipedia-Texte CC BY-SA 4.0 mit Namensnennung.
**Bilder sind der Stolperstein** — Dateilizenz und Recht am eigenen Bild sind
zwei getrennte Hürden, für ein kommerzielles Spiel führt der sichere Weg über
eigene Illustrationen. MiCA ist seit dem 1. Juli 2026 voll scharf, deshalb steht
der Token am Ende der Reihenfolge und nicht am Anfang. Vollständig in
[docs/RECHTLICHES.md](docs/RECHTLICHES.md).

## Dokumentation

| Datei | Inhalt |
|---|---|
| [VISION.md](docs/VISION.md) | Was das Spiel will, in welchen Phasen, und was es nicht ist |
| [SPIELREGELN.md](docs/SPIELREGELN.md) | Regeln, Konter-Rad, Eskalation, Stellschrauben |
| [ARCHITEKTUR.md](docs/ARCHITEKTUR.md) | Schichten, Grenzen, Entscheidungen im Rückblick |
| [AGENTEN.md](docs/AGENTEN.md) | Der Verbesserungs-Loop und seine Leitplanken |
| [RECHTLICHES.md](docs/RECHTLICHES.md) | MiCA, Glücksspiel, Persönlichkeitsrecht, Lizenzen |
| [ROADMAP.md](docs/ROADMAP.md) | Neun Ausbauwege nach Aufwand |

## Lizenz

MIT für den Code. Die erzeugten Daten stehen unter den Bedingungen ihrer
Quellen — siehe [LICENSE](LICENSE).
