"""Die Aufgaben des Verbesserungs-Loops.

Jede Aufgabe schaut sich den aktuellen Stand an und schlägt eine konkrete,
belegte Ergänzung vor. Keine Aufgabe schreibt in eine Datendatei – sie geben
Vorschläge zurück, über die ein Mensch entscheidet.

Die Aufgaben sind bewusst unspektakulär. Sie erledigen genau die Fleißarbeit,
an der das Projekt sonst hängen bleibt: Quellen einordnen, neue Personen
finden, veraltete Karten melden.
"""

import json
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from ..pipeline import http
from ..pipeline.config import BIAS_FILE, CACHE_DIR, DEFAULT_OUT, ROSTER_FILE
from ..pipeline.sources import wikidata
from .proposals import Vorschlag

# Wie viele Vorschläge eine Aufgabe höchstens macht. Ein Mensch soll sie
# tatsächlich lesen können – 200 Zeilen prüft niemand.
MAX_VORSCHLAEGE = 25


# ------------------------------------------------------- Quellen einordnen

def unbekannte_domains(mindestens=3):
    """Welche Medien berichten, ohne dass wir sie einordnen können?

    Liest die GDELT-Antworten aus dem Cache – kostet keine einzige Anfrage.
    Das ist die wirksamste Einzelmaßnahme im Projekt: jede eingeordnete Domain
    hebt die Aussagekraft der Polarisierung auf allen Karten gleichzeitig.
    """
    sources = json.loads(BIAS_FILE.read_text(encoding="utf-8"))
    bekannt = {d.lower() for d in sources["bias"]} | {d.lower() for d in sources["state"]}

    zaehler = Counter()
    for datei in CACHE_DIR.glob("gdelt_dom__*.json"):
        try:
            for domain in json.loads(datei.read_text(encoding="utf-8")):
                d = domain.lower().removeprefix("www.")
                if d and d not in bekannt:
                    zaehler[d] += 1
        except (json.JSONDecodeError, OSError):
            continue

    return [(d, n) for d, n in zaehler.most_common() if n >= mindestens]


def aufgabe_bias_luecken():
    treffer = unbekannte_domains()
    if not treffer:
        return None

    oben = treffer[:MAX_VORSCHLAEGE]
    abgedeckt = sum(n for _, n in oben)
    gesamt = sum(n for _, n in treffer)

    return Vorschlag(
        aufgabe="bias-luecken",
        datei="data/bias_sources.json",
        titel=f"{len(oben)} häufige Medien sind noch nicht eingeordnet",
        begruendung=(
            f"In den zwischengespeicherten GDELT-Antworten tauchen {len(treffer)} "
            f"Domains auf, die weder in der Bias-Tabelle noch in der Staatsmedien-"
            f"Liste stehen. Die {len(oben)} häufigsten decken {abgedeckt} von "
            f"{gesamt} dieser Nennungen ab ({round(100 * abgedeckt / gesamt)} %).\n\n"
            "Jede eingeordnete Domain erhöht `abdeckung_prozent` auf allen Karten "
            "gleichzeitig. Der Wert 0.0 unten ist ein Platzhalter – er muss "
            "ersetzt werden, nicht übernommen."
        ),
        eintraege={d: 0.0 for d, _ in oben},
        belege=[f"https://{d}" for d, _ in oben[:10]],
        hinweise=[
            "Jede Domain einzeln einordnen (-2 links … +2 rechts), Platzhalter 0.0 ersetzen",
            "Staatsnahe Medien gehören in den Abschnitt 'state', nicht in 'bias'",
            "Im Zweifel weglassen: eine falsche Einordnung ist schlechter als keine",
        ],
    )


# ------------------------------------------------------ Neue Karten finden

def meistgelesen(jahr, monat, tag):
    """Die meistgelesenen Wikipedia-Artikel eines Tages.

    Eine einzige Anfrage liefert 1000 Artikel – die ehrlichste verfügbare
    Antwort auf 'wen hat die Welt gerade nachgeschlagen'.
    """
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
           f"en.wikipedia/all-access/{jahr:04d}/{monat:02d}/{tag:02d}")
    daten = http.get_json(url)
    if not daten or not daten.get("items"):
        return []
    return [(e["article"], e["views"]) for e in daten["items"][0].get("articles", [])]


def _ist_person_oder_organisation(qid):
    """P31 = instance of: Mensch (Q5) oder Organisation (Q43229)."""
    entity = wikidata.entity(qid)
    if not entity:
        return None, None
    typen = {(wikidata.claim_value(c) or {}).get("id")
             for c in wikidata.claims(entity, "P31")}
    if "Q5" in typen:
        return "mensch", entity
    if "Q43229" in typen:
        return "organisation", entity
    return None, entity


def aufgabe_neue_karten(datum=None, obergrenze=12):
    """Wer wurde stark nachgeschlagen, steht aber nicht im Deck?"""
    datum = datum or (date.today() - timedelta(days=2))
    roster = json.loads(ROSTER_FILE.read_text(encoding="utf-8"))
    im_deck = {p["name"].lower() for p in roster["persons"]}

    kandidaten = []
    for artikel, aufrufe in meistgelesen(datum.year, datum.month, datum.day):
        if len(kandidaten) >= obergrenze:
            break
        name = artikel.replace("_", " ")
        # Wartungs- und Übersichtsseiten aussortieren
        if ":" in artikel or re.match(r"^(Main Page|Special)", artikel):
            continue
        if name.lower() in im_deck:
            continue

        qid = wikidata.resolve_qid(name)
        if not qid:
            continue
        art, entity = _ist_person_oder_organisation(qid)
        if art is None:
            continue

        beschreibung = (entity.get("descriptions", {}).get("en", {}) or {}).get("value", "")
        kandidaten.append({
            "name": name,
            "qid": qid,
            "art": art,
            "aufrufe": aufrufe,
            "beschreibung": beschreibung,
        })

    if not kandidaten:
        return None

    eintraege = {
        k["qid"]: {
            "name": k["name"],
            "faction": "",
            "expect": "",
            "hard": {"militaer": 0, "nuklear": 0, "daten": 0, "compute": 0},
            "note": "",
            "_hinweis": f"{k['beschreibung']} · {k['aufrufe']:,} Aufrufe am "
                        f"{datum.isoformat()} · {k['art']}",
        }
        for k in kandidaten
    }

    return Vorschlag(
        aufgabe="neue-karten",
        datei="data/roster.json",
        titel=f"{len(kandidaten)} stark nachgeschlagene Personen fehlen im Deck",
        begruendung=(
            f"Aus den meistgelesenen englischen Wikipedia-Artikeln vom "
            f"{datum.isoformat()} sind das die Personen und Organisationen, die "
            f"noch nicht im Roster stehen.\n\n"
            "Hohe Aufmerksamkeit ist ein Hinweis, kein Aufnahmegrund. Aufgenommen "
            "wird, wer über eine der fünf Machtformen tatsächlich verfügt – "
            "Prominenz allein reicht nicht."
        ),
        eintraege=eintraege,
        belege=[f"https://en.wikipedia.org/wiki/{k['name'].replace(' ', '_')}"
                for k in kandidaten],
        hinweise=[
            "Fraktion setzen (staat / tech / kapital / narrativ / zivil)",
            "Hartwerte begründen – ohne 'note' gehört keine Karte ins Deck",
            "'expect' auf ein Stichwort der Rolle setzen, damit der Frische-Check greift",
            "Prominenz ist keine Macht: im Zweifel nicht aufnehmen",
            "Feld '_hinweis' vor dem Übernehmen entfernen",
        ],
    )


# ------------------------------------------------------- Veraltetes melden

def aufgabe_frische():
    """Welche Karten hat der letzte Deck-Lauf als fragwürdig gemeldet?"""
    if not Path(DEFAULT_OUT).exists():
        return None
    deck = json.loads(Path(DEFAULT_OUT).read_text(encoding="utf-8"))

    betroffen = {c["name"]: c["warnungen"] for c in deck["cards"] if c["warnungen"]}
    ernst = {name: w for name, w in betroffen.items()
             if any("verstorben" in z or "nicht mehr" in z for z in w)}
    if not ernst:
        return None

    return Vorschlag(
        aufgabe="frische",
        datei="data/roster.json",
        titel=f"{len(ernst)} Karten zeigen möglicherweise die Welt von gestern",
        begruendung=(
            "Der letzte Deck-Lauf hat bei diesen Karten gemeldet, dass Wikidata "
            "die hinterlegte Rolle nicht mehr bestätigt oder ein Todesdatum "
            "kennt. Ein Deck über Machthaber, das Amtswechsel verschläft, ist das "
            "Gegenteil von Aufklärung.\n\n"
            "Es gibt hier keinen automatischen Vorschlag für den Nachfolger – wer "
            "ein Amt übernommen hat, ist eine Tatsachenbehauptung und gehört von "
            "Hand geprüft."
        ),
        eintraege={name: {"warnungen": w} for name, w in ernst.items()},
        belege=[f"https://www.wikidata.org/wiki/Special:Search?search={name}"
                for name in ernst],
        hinweise=[f"{name}: {' | '.join(w)}" for name, w in ernst.items()],
    )


AUFGABEN = {
    "bias-luecken": (aufgabe_bias_luecken, "unbekannte Medien aus dem GDELT-Cache sammeln"),
    "neue-karten": (aufgabe_neue_karten, "stark nachgeschlagene Personen finden, die fehlen"),
    "frische": (aufgabe_frische, "Karten melden, deren Rolle nicht mehr bestätigt ist"),
}
