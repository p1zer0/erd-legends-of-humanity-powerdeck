"""Orchestrierung: Roster rein, fertiges Deck raus.

Ablauf in drei Schritten:
  collect()   je Person alle Rohdaten holen (Netz)
  finalize()  Rohdaten deckweit normalisieren (rein rechnerisch)
  build()     beides verbinden
"""

import json
from datetime import date

from . import scoring
from .config import BIAS_FILE, DATENQUELLEN, LEGENDE, ROSTER_FILE, WEIGHTS
from .sources import gdelt, wikidata, wikimedia


def load_inputs():
    roster = json.loads(ROSTER_FILE.read_text(encoding="utf-8"))
    sources = json.loads(BIAS_FILE.read_text(encoding="utf-8"))
    bias_table = {k.lower(): v for k, v in sources["bias"].items()}
    state_table = {k.lower(): v for k, v in sources["state"].items()}
    return roster, bias_table, state_table


def select(persons, only=None, limit=None):
    if only:
        needle = only.lower()
        persons = [p for p in persons if needle in p["name"].lower()]
    if limit:
        persons = persons[:limit]
    return persons


def collect(person, bias_table, state_table, use_gdelt=True):
    """Alle Rohdaten für eine Person. Wirft nicht – Probleme landen in warnings."""
    row = {
        "name": person["name"],
        "faction": person["faction"],
        "note": person.get("note"),
        "hard": person.get("hard", {}),
        "warnings": [],
    }

    qid = wikidata.resolve_qid(person["name"])
    entity = wikidata.entity(qid) if qid else None
    if not entity:
        row["warnings"].append("Nicht in Wikidata auflösbar – Karte unvollständig.")
        return row

    info = wikidata.extract(entity)
    row["warnings"].extend(info.pop("warnings"))
    position_qids = info.pop("_position_qids")
    row.update(info)

    if person.get("expect"):
        labels = wikidata.position_labels(position_qids).values()
        if not wikidata.role_confirmed(person["expect"], labels, info.get("description")):
            gefunden = ", ".join(sorted(set(labels))) or "nichts"
            row["warnings"].append(
                f"Rolle '{person['expect']}' nicht mehr in Wikidata bestätigt "
                f"(gefunden: {gefunden}) – Roster prüfen.")

    title = info.get("enwiki") or person["name"]
    row.update(wikimedia.summary(title))

    views = wikimedia.pageviews(title)
    if not views:
        row["warnings"].append("Keine Pageview-Daten – Aufmerksamkeitswerte geschätzt.")
    row["_attention"] = scoring.attention_metrics(views)
    row["aufmerksamkeit_30d"] = views[-30:]

    domains = []
    if use_gdelt and gdelt.available():
        domains = gdelt.domains(person["name"])
        row["_gdelt_total"] = sum(gdelt.volume(person["name"]))
        if not domains:
            row["warnings"].append(
                "GDELT gedrosselt – Polarisierung fehlt, nächster Lauf holt sie nach."
                if not gdelt.available()
                else "GDELT lieferte keine Artikel – Polarisierung unsicher.")
    else:
        row["_gdelt_total"] = 0
        if use_gdelt:
            row["warnings"].append(
                "GDELT für diesen Lauf übersprungen – Polarisierung fehlt.")
    row["_coverage"] = scoring.coverage_breakdown(domains, bias_table, state_table)

    return row


def finalize(rows, generated=None):
    """Deckweite Normalisierung und Ausgabeformat.

    narrativ, polarisierung und chaos entstehen im Verhältnis zum restlichen
    Deck – Macht ist eine Relation, kein Absolutwert.
    """
    live = [r for r in rows if "_attention" in r]
    if live:
        views_score = scoring.scale([r["_attention"]["mittel"] for r in live], log=True)
        gdelt_score = scoring.scale([r["_gdelt_total"] for r in live], log=True)
        chaos_score = scoring.scale([scoring.chaos_raw(r["_attention"]) for r in live])
        pol_score = scoring.scale([scoring.polarisierung_raw(r["_coverage"]) for r in live])
        for i, row in enumerate(live):
            row["_narrativ"] = round(0.5 * views_score[i] + 0.5 * gdelt_score[i])
            row["_chaos"] = chaos_score[i]
            row["_polarisierung"] = pol_score[i]

    cards = []
    for row in rows:
        hard = row.get("hard", {})
        qid = row.get("qid")
        stats = {
            "kapital": scoring.kapital_score(row.get("net_worth_usd"),
                                             hard.get("kapital_override")),
            "militaer": hard.get("militaer", 0),
            "nuklear": hard.get("nuklear", 0),
            "daten": hard.get("daten", 0),
            "compute": hard.get("compute", 0),
            "narrativ": row.get("_narrativ", 0),
            "polarisierung": row.get("_polarisierung", 0),
            "chaos": row.get("_chaos", 0),
        }
        cards.append({
            "id": qid or row["name"].lower().replace(" ", "-"),
            "name": row["name"],
            "faction": row["faction"],
            "beschreibung": row.get("beschreibung") or row.get("description"),
            "steckbrief": row.get("steckbrief"),
            "macht": scoring.macht(stats),
            "stats": stats,
            "berichterstattung": row.get("_coverage"),
            "aufmerksamkeit_30d": row.get("aufmerksamkeit_30d", []),
            "quellen": {
                "wikidata": f"https://www.wikidata.org/wiki/{qid}" if qid else None,
                "wikipedia": row.get("wiki_url"),
                "vermoegen_usd": row.get("net_worth_usd"),
                "vermoegen_stand": row.get("net_worth_year"),
                "bild": row.get("image_url"),
                "bild_lizenz": row.get("image_license_page"),
            },
            "redaktionelle_notiz": row.get("note"),
            "warnungen": row["warnings"],
        })

    cards.sort(key=lambda c: c["macht"], reverse=True)
    return {
        "generiert_am": (generated or date.today()).isoformat(),
        "kartenzahl": len(cards),
        "gewichtung": WEIGHTS,
        "legende": LEGENDE,
        "datenquellen": DATENQUELLEN,
        "cards": cards,
    }


def build(persons, bias_table, state_table, use_gdelt=True, on_person=None):
    rows = []
    for index, person in enumerate(persons, 1):
        if on_person:
            on_person(index, len(persons), person["name"])
        try:
            rows.append(collect(person, bias_table, state_table, use_gdelt))
        except Exception as err:  # eine kaputte Karte darf den Lauf nicht kippen
            rows.append({"name": person["name"], "faction": person["faction"],
                         "note": person.get("note"), "hard": person.get("hard", {}),
                         "warnings": [f"Abbruch beim Laden: {err}"]})
    return finalize(rows)
