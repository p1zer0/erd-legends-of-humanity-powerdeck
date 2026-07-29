# Ausbauwege

Sortiert nach Aufwand. Jeder Weg steht für sich – nichts davon setzt einen
anderen voraus. Die Reihenfolge ist ein Vorschlag, keine Abhängigkeit.

---

## 1 · Bias-Tabelle verbreitern

**Aufwand: klein · Wirkung: sofort auf jeder Karte**

Aktuell werden 20–30 % der gefundenen Artikel eingeordnet, der Rest sind
Regionalmedien, die nicht in `data/bias_sources.json` stehen. Jede neue Domain
macht die Polarisierung einer Karte belastbarer.

- Die 200 häufigsten unbekannten Domains aus einem Lauf ausgeben lassen und
  abarbeiten – 80 % der Lücke steckt in wenigen Dutzend Domains.
- Länderspezifische Tabellen: die Links-Rechts-Achse bedeutet in Indien etwas
  anderes als in Deutschland. `bias.de`, `bias.us`, `bias.in` statt einer Tabelle.
- Eine zweite Achse aufnehmen: Faktentreue getrennt von politischer Richtung.
  Ground News zeigt beides, und die Trennung ist der lehrreichere Teil.

## 2 · Hartwerte aus Daten statt aus Redaktion

**Aufwand: mittel · Wirkung: Glaubwürdigkeit**

`militaer`, `nuklear`, `daten` und `compute` sind bisher begründete Schätzungen.
Vier davon lassen sich an offene Datensätze hängen:

| Wert | Quelle | Form |
|---|---|---|
| militaer | SIPRI Military Expenditure Database | CSV, jährlich |
| nuklear | Federation of American Scientists, Nuclear Notebook | Tabelle je Staat |
| compute | Epoch AI, Notable AI Models | CSV, laufend |
| daten | Nutzerzahlen aus Geschäftsberichten | halbautomatisch |

Der Weg dahin: Staatswerte am Land festmachen (`P27`/`P17`), nicht an der Person,
und über das amtierende Staatsoberhaupt auf die Karte ziehen. Dann aktualisiert
ein Regierungswechsel die Karte von selbst.

## 3 · Beziehungsgraph statt Einzelkarten

**Aufwand: mittel · Wirkung: neue Spielmechanik**

Wikidata kennt die Verbindungen bereits: `P108` (Arbeitgeber), `P463`
(Mitglied von), `P1830` (Eigentümer von), `P3373` (Geschwister), `P1327`
(Geschäftspartner). Ein Lauf über diese Eigenschaften ergibt einen Graphen.

Spielmechanisch: Kombos für Karten, die real verbunden sind. Aufklärerisch:
Spieler sehen, dass Macht in Netzwerken liegt, nicht in Personen. Das ist die
Erkenntnis, die ein Kartenspiel besser transportiert als ein Artikel.

## 4 · Ereignisse als tägliche Modifikatoren

**Aufwand: mittel · Wirkung: Grund, täglich zu spielen**

GDELT liefert nicht nur Volumen, sondern Ereignisse mit Ton und Akteuren.
Daraus wird ein täglicher Feed: „Person X steht seit gestern doppelt so stark
in den Nachrichten" → temporärer Buff auf `narrativ`, Debuff auf `chaos`-Gegner.

Das ist der Hebel, der aus dem Online-Only-Ansatz einen Vorteil macht statt
einer Einschränkung: Ein Deck, das sich mit der Welt bewegt, kann es offline
nicht geben.

## 5 · Regionale Macht durch mehrsprachige Pageviews

**Aufwand: klein · Wirkung: differenziertere Karten**

Der Builder fragt bisher nur `en.wikipedia`. Mit `de`, `es`, `hi`, `ar`, `zh`
entsteht ein Aufmerksamkeitsprofil pro Sprachraum. Daraus wird ein Kartenwert
„Reichweite" mit Ost/West-Gefälle – und Karten, die in verschiedenen Regionen
verschieden stark sind. Nebenbei fällt die deutsche Kurzbeschreibung ab
(`dewiki` wird schon mitgeholt, aber noch nicht genutzt).

## 6 · Quiz- und Quellenlayer

**Aufwand: klein · Wirkung: der Aufklärungsteil wird explizit**

Jede Karte trägt bereits Wikidata-Claims und Quellen-Links. Daraus lassen sich
automatisch Fragen erzeugen: „Wem gehört WhatsApp?", „Welches Land hat die
meisten Sprengköpfe?" Richtig beantwortet = kleiner Bonus im Spiel.

Damit ist das Lernen Teil der Mechanik statt Beiwerk – und die Antwort ist
immer belegt, weil sie aus der Quelle stammt.

## 7 · Historie und Veränderungsanzeige

**Aufwand: klein · Wirkung: Inhalt ohne Zusatzarbeit**

Jeder nächtliche Lauf überschreibt `public/cards.json`. Stattdessen zusätzlich
`public/history/YYYY-MM-DD.json` ablegen und die Differenz zum Vortag anzeigen:
„Wer ist diese Woche gestiegen?" Das ist wöchentlicher Content, der sich selbst
schreibt, und macht Machtverschiebungen sichtbar statt nur Zustände.

## 8 · Verifizierbare Karten und transparente Mittelverwendung

**Aufwand: groß · Wirkung: Vertrauen, zahlt aufs Kernversprechen ein**

Zwei getrennte Dinge, beide zum Krypto-Teil des Projekts:

- **Kartenintegrität**: Merkle-Root von `cards.json` on-chain verankern. Spieler
  können prüfen, dass die Werte ihrer Karten nicht nachträglich verändert wurden.
  Günstig, weil nur ein Hash pro Tag geschrieben wird.
- **Mittelverwendung**: Der Fee-Anteil für Friedens- und Umweltprojekte gehört
  in einen Contract mit öffentlicher Auszahlungsliste plus eine Seite, die zeigt,
  welches Projekt wie viel bekommen hat. Wer Aufklärung verspricht, muss beim
  eigenen Geldfluss anfangen.

## 9 · Backend statt Datei

**Aufwand: groß · Wirkung: erst nötig, wenn es viele Spieler gibt**

`cards.json` reicht für Zehntausende Abrufe pro Tag über ein CDN. Ein Backend
lohnt sich erst, wenn Spielstände, Matchmaking und Historie dazukommen. Dann:
schlanke API vor einer Postgres-Instanz, Deck-Builder als Cron-Job, der
schreibt statt Dateien zu erzeugen.

---

## Was bewusst nicht auf der Liste steht

- **Ground News scrapen.** Es gibt keine öffentliche API, und ein Scraper wäre
  gegen die Nutzungsbedingungen, technisch brüchig und rechtlich angreifbar.
  Die Bias-Schicht selbst zu pflegen ist mehr Arbeit, aber sie gehört dann euch.
- **Fotos lebender Personen ausliefern.** Siehe README: Bildlizenz und Recht am
  eigenen Bild sind zwei verschiedene Hürden, und beide gelten. Eigene
  Illustrationen sind der einzige Weg, der bei kommerzieller Nutzung trägt.
- **Werte ohne Begründung.** Jede Zahl in `roster.json` hat eine `note`. Wenn
  eine Zahl sich ändert, ändert sich die Begründung mit – sonst wird aus
  Aufklärung eine Behauptung.
