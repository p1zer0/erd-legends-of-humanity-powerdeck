# PowerDeck

Machtwerte für ein Kartenspiel — berechnet aus offenen Datenquellen statt behauptet.

Aus einer Liste realer Personen entsteht eine `cards.json` mit acht Werten pro Karte.
Vier davon werden täglich live aus Wikidata, Wikipedia und GDELT geholt, vier sind
redaktionell und in `data/roster.json` begründet.

Kein API-Key, keine Laufzeitabhängigkeiten — nur die Python-Standardbibliothek.

```bash
make deck        # volles Deck (~25 min, GDELT drosselt)
make deck-fast   # in ~1 min, ohne Polarisierung
make card N=Musk # eine Karte testen
make test        # Testsuite, braucht kein Netz
make serve       # Vorschau auf http://localhost:8000
```

## Die acht Werte

| Wert | Woher | Bedeutung |
|---|---|---|
| **kapital** | Wikidata `P2218`, logarithmisch (1 Mrd $ → 1, 400 Mrd $ → 100) | Verfügungsgewalt über Geld |
| **militaer** | `data/roster.json` | Kommandogewalt über Streitkräfte |
| **nuklear** | `data/roster.json` | Zugriff auf Kernwaffen |
| **daten** | `data/roster.json` | Personenbezogene Daten in großem Maßstab |
| **compute** | `data/roster.json` | Rechenleistung, Chips, KI-Modelle |
| **narrativ** | GDELT-Artikelvolumen + Wikipedia-Aufrufe, 30 Tage | Medienpräsenz |
| **polarisierung** | GDELT-Quellen × `data/bias_sources.json` | Wie einseitig berichtet wird |
| **chaos** | Schwankung der Aufrufe (Variationskoeffizient + größter Ausschlag) | Unberechenbarkeit der Aufmerksamkeit |

`macht` ist die gewichtete Summe. Die Gewichte stehen in `src/powerdeck/config.py`
und liegen jeder `cards.json` bei — wer die Rechnung nachvollziehen will, kann es.

**Staatsakteure bekommen `kapital_override`.** Das Privatvermögen eines Präsidenten
sagt nichts über die fiskalische Macht, die er tatsächlich ausübt.

## Warum nicht Ground News

Ground News hat keine öffentliche API. Was das Produkt ausmacht, ist eine Schicht
über frei zugänglichen Daten: Artikel sammeln, Quellen nach politischer Ausrichtung
einordnen, Verteilung zeigen. Genau das macht `scoring.coverage_breakdown()` — mit
GDELT als Artikelquelle und `data/bias_sources.json` als Einordnung, die im Repo
liegt, versionierbar und begründbar ist.

Pro Karte entsteht daraus:

```json
"berichterstattung": {
  "verteilung_prozent": { "links": 30, "mitte": 55, "rechts": 15, "staatsnah": 4 },
  "artikel_ausgewertet": 250,
  "artikel_mit_bias_rating": 50,
  "abdeckung_prozent": 20,
  "bias_mittelwert": 0.22,
  "bias_streuung": 0.8,
  "staatsmedien": { "Russland": 3 }
}
```

Das ist der Aufklärungsteil: Spieler sehen nicht nur, *dass* jemand mächtig ist,
sondern *wer über ihn spricht* — und dass staatsnahe Medien eine eigene Kategorie sind.

`abdeckung_prozent` sagt, wie belastbar die Zahl ist. Bei einem globalen
GDELT-Sample sind das oft nur 20–30 %, weil viele Regionalmedien nicht in der
Tabelle stehen. Die Spektrum-Anteile beziehen sich deshalb auf die eingeordneten
Artikel — sonst sähe jede Karte künstlich ausgewogen aus.

## Werte sind relativ zum Deck

`narrativ`, `polarisierung` und `chaos` werden über das gesamte Deck normalisiert.
Zwei Konsequenzen:

- Ein Einzellauf mit `--only` liefert für diese drei immer 50. Das ist kein Fehler,
  sondern die ehrliche Antwort: ohne Vergleich gibt es keine Relation.
- Kommen Karten dazu, verschieben sich die Werte der anderen leicht. Für ein Spiel
  über Macht ist das genau richtig — Macht ist ein Verhältnis, kein Absolutwert.

## Das Deck sagt Bescheid, wenn es veraltet

Jede Person hat im Roster ein Feld `expect` mit einem Stichwort ihrer Rolle. Der
Builder prüft gegen Wikidata (`P39` ohne Enddatum, `P169`, Kurzbeschreibung) und
zusätzlich auf ein Todesdatum (`P570`). Abweichungen erscheinen am Ende des Laufs.

Beim ersten Lauf hat das sofort gegriffen: Ali Khamenei ist laut Wikidata am
28.02.2026 gestorben, seit dem 08.03.2026 ist Mojtaba Khamenei im Amt. Der Roster
wurde korrigiert. Ein Deck über Machthaber, das die Welt von gestern zeigt, wäre
das Gegenteil von Aufklärung — deshalb sind diese Warnungen kein Rauschen.

## Architektur

```
src/powerdeck/
├── config.py         Pfade, Gewichte, Cache-Zeiten – alle Stellschrauben
├── http.py           HTTP + Plattencache + SSL-Fallback
├── scoring.py        reine Rechenschicht: rein Daten, raus Zahlen
├── deck.py           Orchestrierung: collect → finalize
├── cli.py            Kommandozeile
└── sources/          je Datenquelle ein Modul – alles Netzabhängige lebt hier
    ├── wikidata.py
    ├── wikimedia.py
    └── gdelt.py

data/                 gepflegte Eingaben: roster.json, bias_sources.json
public/               was ausgeliefert wird: index.html + cards.json
tests/                40 Tests, ohne Netz lauffähig
docs/ROADMAP.md       Ausbauwege
```

Die Trennung hat einen Grund: `scoring.py` enthält alle Entscheidungen darüber,
was Macht bedeutet, und ist deshalb vollständig testbar. `sources/` enthält alles,
was schiefgehen kann, und darf ausfallen, ohne den Lauf zu kippen.

## Cache und abgebrochene Läufe

Alle Antworten landen in `.cache/` (Wikidata 7 Tage, QIDs 30 Tage, Pageviews und
GDELT 20 Stunden). Fehlgeschlagene Abrufe werden **nicht** gecacht — ein zweiter
Lauf holt deshalb genau die fehlenden Personen nach und nimmt den Rest aus dem
Cache. GDELT drosselt unregelmäßig; zweimal laufen zu lassen ist die normale
Antwort darauf, nicht die Ausnahme. Der nächtliche Workflow macht es genauso.

Cache verwerfen: `make clean-cache`.

## Rechtliches, bevor es teuer wird

- **Wikipedia-Texte** (Feld `steckbrief`) stehen unter CC BY-SA 4.0: Namensnennung
  und Link zum Artikel sind Pflicht, `quellen.wikipedia` liefert beides.
  Wikidata-Fakten selbst sind CC0, also frei.
- **Bilder sind der Stolperstein.** `quellen.bild` ist nur ein Link auf Wikimedia
  Commons; jede Datei hat ihre eigene Lizenz. `quellen.bild_lizenz` führt auf die
  Dateiseite mit den Bedingungen. Für ein kommerzielles Spiel ist der sichere Weg:
  eigene Illustrationen. Fotos lebender Personen sind in Deutschland zusätzlich
  über das Recht am eigenen Bild (KUG § 22) geschützt — unabhängig von der Lizenz.
- **Personendarstellung**: Jeder Wert ist entweder belegt oder als redaktionelle
  Einschätzung gekennzeichnet (`redaktionelle_notiz`). Das ist der Unterschied
  zwischen Aufklärung und Rufschädigung. Wer eine Zahl ändert, ändert die
  Begründung mit.

## Weiterbauen

`docs/ROADMAP.md` listet neun Ausbauwege nach Aufwand sortiert — von der
Bias-Tabelle verbreitern (klein, wirkt sofort) über den Beziehungsgraphen aus
Wikidata (neue Spielmechanik) bis zur on-chain verankerten Kartenintegrität.

## Lizenz

MIT für den Code. Die erzeugten Daten stehen unter den Bedingungen ihrer Quellen —
siehe `LICENSE`.
