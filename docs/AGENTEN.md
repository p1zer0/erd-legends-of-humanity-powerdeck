# Der Verbesserungs-Loop

Das Projekt soll sich kontinuierlich selbst weiterentwickeln: mehr Quellen,
mehr Karten, aktuellere Daten — ohne dass jemand die Fleißarbeit von Hand macht.

Der Loop tut genau das. Mit einer Grenze, die bewusst gezogen ist.

## Die Grenze

**Der Loop schlägt vor. Ein Mensch entscheidet.**

Das ist keine Bequemlichkeit, sondern die Bedingung dafür, dass das Projekt sein
Kernversprechen halten kann. ERD Legends of Humanity – PowerDeck behauptet: *jede Zahl hat eine Quelle*.
Genau das ist der einzige Unterschied zu allen anderen, die auch erklären, wer
die Welt lenkt.

Ein System, das unbeaufsichtigt Werte über namentlich genannte lebende Menschen
schreibt und veröffentlicht, kann dieses Versprechen nicht halten. Ein einziger
falscher Wert kostet die Glaubwürdigkeit aller anderen — und ist eine
Tatsachenbehauptung über eine reale Person mit allem, was daran hängt.

Die Grenze steht nicht nur in diesem Dokument, sondern im Code:

```python
# proposals.py
PRUEFPFLICHTIG = {"data/roster.json"}

def anwenden(vorschlag, wurzel, bestaetigt=False):
    if vorschlag.prueffplicht and not bestaetigt:
        raise PermissionError(...)
```

Ein Test beweist, dass die Zieldatei unangetastet bleibt, wenn die Bestätigung
fehlt (`test_loop.py::Pruefpflicht`). Wer die Grenze verschieben will, muss
einen Test brechen — nicht nur eine Meinung ändern.

## Wie er läuft

```bash
python3 -m powerdeck loop                       # alle Aufgaben
python3 -m powerdeck loop --aufgabe bias-luecken
python3 -m powerdeck loop --anwenden proposals/2026-07-29-bias-luecken.json
```

Jede Aufgabe schreibt zwei Dateien nach `proposals/`: ein JSON (maschinenlesbar,
für `--anwenden`) und ein Markdown (für Menschen, mit Belegen und Checkliste).

Der wöchentliche Workflow lässt den Loop laufen und öffnet einen Pull Request
mit den Vorschlägen. Reviewen heißt hier tatsächlich lesen — die Checklisten im
Markdown sind die Prüfpunkte.

## Die Aufgaben

| Aufgabe | Was sie tut | Kosten |
|---|---|---|
| `bias-luecken` | Zählt Domains aus dem GDELT-Cache, die noch nicht eingeordnet sind, und schlägt die häufigsten vor | keine Anfrage — reine Cache-Auswertung |
| `neue-karten` | Holt die meistgelesenen Wikipedia-Artikel eines Tages, filtert auf Personen und Organisationen, meldet die, die im Roster fehlen | eine Anfrage + Wikidata-Lookups |
| `frische` | Liest die Warnungen des letzten Deck-Laufs und meldet Karten, deren Rolle Wikidata nicht mehr bestätigt | keine |

Beim ersten Lauf hat `bias-luecken` 242 unbekannte Domains gefunden; die 25
häufigsten decken 40 % aller nicht eingeordneten Nennungen ab. Das ist die
wirksamste Einzelmaßnahme im Projekt — und niemand hätte sie von Hand gefunden.

Ein Beispiel dafür, warum die Prüfung nötig ist: In derselben Liste stand
`english.news.cn`. Das ist Xinhua und gehört in den Abschnitt `state`, nicht in
die Links-Rechts-Tabelle. Eine Automatik hätte es als „Mitte" eingeordnet.

## Wo ein KI-Agent andockt

Der Loop ist absichtlich ohne Modell gebaut: er läuft überall, kostet nichts und
kann nicht halluzinieren. Ein Sprachmodell ist an genau drei Stellen nützlich —
und an allen dreien als **Zulieferer für den Vorschlag**, nicht als Entscheider:

1. **Bias-Einordnung vorschlagen.** Statt `0.0` als Platzhalter eine begründete
   Einschätzung mit Quellenangabe. Der Mensch prüft die Begründung, nicht die Zahl.
2. **Hartwerte recherchieren.** Militär-, Nuklear-, Compute- und Datenwerte für
   eine neue Karte samt `note` und Belegen entwerfen.
3. **Widersprüche finden.** Karten durchgehen und melden, wo die `note` nicht
   mehr zu den Werten passt.

Der Andockpunkt ist eine Funktion, die einen `Vorschlag` zurückgibt — dieselbe
Schnittstelle wie jede andere Aufgabe. Ein Agent ist damit austauschbar:
Hermes, Claude, ein lokales Modell, ein Mensch mit Skript. Der Loop kennt den
Unterschied nicht, und die Prüfpflicht gilt für alle gleich.

## Was bewusst nicht gesammelt wird

**Foren, Kommentarspalten, „Datensammlungen" über Personen.** Unbelegtes Material
über namentlich genannte Menschen ist juristisch eine Tatsachenbehauptung und
inhaltlich wertlos. Es bricht das Kernversprechen an genau der Stelle, an der es
zählt.

Die gute Nachricht: Es ist auch nicht nötig. Was aus geprüften Quellen kommt,
ist härter als alles aus Foren — Geschäftsberichte, Handelsregister, SIPRI,
FAS Nuclear Notebook, Epoch AI, Gerichtsentscheidungen. Dass wenige
Vermögensverwalter Großaktionäre fast jedes börsennotierten Konzerns sind, steht
in Pflichtmitteilungen. Das ist belegbar, und deshalb steht es.

**Daten über Spielerinnen und Spieler.** Aggregierte, freiwillige Telemetrie zur
Balance ist in Ordnung — Profile über Menschen sind es nicht. Das Spiel klärt
über Datenmacht auf; es kann sie nicht selbst aufbauen.

**Ein Browser-Harness.** Jede Quelle, die wir nutzen, hat eine API. Ein Browser
brächte heute nur Bruchstellen und ToS-Risiko. Er wird interessant, sobald wir an
Handelsregister, Gerichtsakten oder NGO-Jahresberichte gehen — also bei
Ausbauweg 2 der [ROADMAP](ROADMAP.md). Dann als eigene Aufgabenart mit demselben
Vorschlagsformat.

## Mehr Autonomie verdienen

Die Grenze ist nicht in Stein. Sie verschiebt sich mit nachgewiesener Zuverlässigkeit:

| Stufe | Was automatisch passiert | Voraussetzung |
|---|---|---|
| heute | Deck-Daten (abgeleitet, mit Quelle) committen automatisch | — |
| heute | Alles andere geht als PR mit Belegen ein | — |
| als Nächstes | `bias-luecken` mit Modell-Vorschlag darf automatisch mergen, wenn zwei unabhängige Läufe dieselbe Einordnung ergeben | 20 Vorschläge ohne Korrektur im Review |
| später | Neue Karten aus strukturierten Quellen (Register, SIPRI) automatisch | eigener Verifikationslauf gegen zwei Quellen |
| **nie** | Werte über reale Personen ohne Quellenangabe | — |

Die letzte Zeile ist die einzige, die nicht verhandelbar ist. Alles andere ist
eine Frage der Nachweise.

## Wenn er kaputtgeht

- Eine Aufgabe, die wirft, beendet den Loop nicht — sie wird gemeldet und
  übersprungen (`cli.py`).
- Vorschläge überschreiben nie eine bestehende Einordnung. Handarbeit gewinnt
  gegen Automatik, immer (`test_ueberschreibt_bestehende_einordnung_nicht`).
- Bei leerem Cache und ohne Netz macht der Loop schlicht nichts und sagt das.
  „Keine Vorschläge" ist ein gutes Ergebnis, kein Fehler.
