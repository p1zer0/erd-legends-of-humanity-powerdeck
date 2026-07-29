"""Aus Rohdaten werden Kartenwerte.

Alle Funktionen hier sind rein: rein Daten, raus Zahlen, kein Netz, keine Zeit.
Deshalb sind sie vollständig testbar – siehe tests/test_scoring.py.
"""

import math
import statistics

from .config import WEIGHTS

# Ab welchem Bias-Wert eine Quelle als links bzw. rechts gilt.
SPEKTRUM_SCHWELLE = 0.75

# Kapital-Skala: 1 Mrd USD = 1 Punkt (Untergrenze), 400 Mrd USD = 100 Punkte.
KAPITAL_MIN_LOG = 9.0
KAPITAL_MAX_LOG = math.log10(4e11)


def coverage_breakdown(domains, bias_table, state_table):
    """Wer berichtet über die Person – die Ground-News-Logik in einer Funktion.

    Die Spektrum-Anteile beziehen sich auf die *eingeordneten* Artikel. Bezöge
    man sie auf alle gefundenen, würde eine dünne Bias-Tabelle jede Person
    fälschlich ausgewogen aussehen lassen. `abdeckung_prozent` macht sichtbar,
    wie belastbar die Zahl ist.
    """
    buckets = {"links": 0, "mitte": 0, "rechts": 0, "staatsnah": 0, "unbekannt": 0}
    scores = []
    states = {}

    for raw in domains:
        domain = raw.lower().removeprefix("www.")
        if domain in state_table:
            buckets["staatsnah"] += 1
            land = state_table[domain]
            states[land] = states.get(land, 0) + 1
        elif domain in bias_table:
            bias = bias_table[domain]
            scores.append(bias)
            if bias <= -SPEKTRUM_SCHWELLE:
                buckets["links"] += 1
            elif bias >= SPEKTRUM_SCHWELLE:
                buckets["rechts"] += 1
            else:
                buckets["mitte"] += 1
        else:
            buckets["unbekannt"] += 1

    total = sum(buckets.values())
    rated = buckets["links"] + buckets["mitte"] + buckets["rechts"]
    pct = {k: (round(100 * buckets[k] / rated) if rated else 0)
           for k in ("links", "mitte", "rechts")}
    pct["staatsnah"] = round(100 * buckets["staatsnah"] / total) if total else 0

    return {
        "verteilung_prozent": pct,
        "artikel_ausgewertet": total,
        "artikel_mit_bias_rating": rated,
        "abdeckung_prozent": round(100 * rated / total) if total else 0,
        "bias_mittelwert": round(statistics.fmean(scores), 2) if scores else 0.0,
        "bias_streuung": round(statistics.pstdev(scores), 2) if len(scores) > 1 else 0.0,
        "staatsmedien": states,
    }


def attention_metrics(views):
    """Aufmerksamkeit und ihre Unberechenbarkeit – Chaos in Zahlen.

    `cv` ist die Schwankungsbreite relativ zum Mittel, `spike` der größte
    Ausschlag gegenüber dem Median. Beides zusammen unterscheidet konstant
    präsente Personen von solchen, um die es plötzlich laut wird.
    """
    if not views:
        return {"mittel": 0.0, "cv": 0.0, "spike": 1.0}
    mean = statistics.fmean(views)
    median = statistics.median(views) or 1
    std = statistics.pstdev(views) if len(views) > 1 else 0.0
    return {
        "mittel": mean,
        "cv": (std / mean) if mean else 0.0,
        "spike": (max(views) / median) if median else 1.0,
    }


def chaos_raw(attention):
    return 0.6 * attention["cv"] + 0.4 * min(attention["spike"], 10) / 10


def polarisierung_raw(coverage):
    """Einseitigkeit wiegt schwerer als Streuung: eine Person, über die nur
    eine Seite des Spektrums schreibt, ist stärker polarisiert als eine, über
    die alle schreiben – auch wenn beide eine hohe Streuung haben."""
    return 0.6 * abs(coverage["bias_mittelwert"]) / 2 + 0.4 * coverage["bias_streuung"] / 2


def scale(values, log=False, lo=1, hi=100):
    """Rohwerte -> Kartenwerte lo..hi, relativ zum Deck.

    Bei nur einem Wert (oder lauter gleichen) gibt es keine sinnvolle Relation;
    dann ist die Mitte die ehrlichste Antwort.
    """
    if not values:
        return []
    if log:
        values = [math.log10(v + 1) for v in values]
    lo_v, hi_v = min(values), max(values)
    if hi_v - lo_v < 1e-9:
        return [round((lo + hi) / 2)] * len(values)
    return [round(lo + (hi - lo) * (v - lo_v) / (hi_v - lo_v)) for v in values]


def kapital_score(net_worth_usd, override=None):
    """Vermögen logarithmisch auf 0..100.

    Staatsakteure überschreiben das: das Privatvermögen eines Präsidenten sagt
    nichts über die fiskalische Macht, die er tatsächlich ausübt.
    """
    if override is not None:
        return override
    if not net_worth_usd or net_worth_usd <= 0:
        return 10
    span = KAPITAL_MAX_LOG - KAPITAL_MIN_LOG
    return max(1, min(100, round(100 * (math.log10(net_worth_usd) - KAPITAL_MIN_LOG) / span)))


def macht(stats):
    """Gewichtete Summe aller acht Werte."""
    return round(sum(stats[key] * weight for key, weight in WEIGHTS.items()))
