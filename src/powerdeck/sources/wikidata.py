"""Wikidata: Vermögen, Ämter, Todesdatum, Bild, Wikipedia-Titel.

Wikidata-Fakten stehen unter CC0 und sind damit die unproblematischste Quelle
im ganzen Projekt.
"""

import urllib.parse

from .. import http
from ..config import EUR_TO_USD, TTL

API = "https://www.wikidata.org/w/api.php"
ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"


def resolve_qid(name):
    """Personennamen -> Q-Nummer. Ergebnis wird 30 Tage gecacht."""
    def fetch():
        data = http.get_json(http.build_url(API, {
            "action": "wbsearchentities", "search": name, "language": "en",
            "format": "json", "limit": 5, "type": "item",
        }))
        if not data or not data.get("search"):
            return None
        return data["search"][0]["id"]

    return http.cached("qid", name, TTL["qid"], fetch)


def entity(qid):
    data = http.cached("wikidata", qid, TTL["wikidata"],
                       lambda: http.get_json(ENTITY.format(qid)))
    if not data:
        return None
    return data.get("entities", {}).get(qid)


def position_labels(qids):
    """Labels für Ämter-QIDs, gebündelt in 50er-Blöcken."""
    out = {}
    qids = [q for q in qids if q]
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]

        def fetch(chunk=chunk):
            return http.get_json(http.build_url(API, {
                "action": "wbgetentities", "ids": "|".join(chunk),
                "props": "labels", "languages": "en|de", "format": "json",
            }))

        data = http.cached("labels", ",".join(sorted(chunk)), TTL["labels"], fetch)
        for qid, ent in (data or {}).get("entities", {}).items():
            labels = ent.get("labels", {})
            out[qid] = (labels.get("en") or labels.get("de") or {}).get("value", "")
    return out


# --------------------------------------------------------------- Auswertung

def claims(ent, prop):
    return ent.get("claims", {}).get(prop, [])


def claim_value(claim):
    return claim.get("mainsnak", {}).get("datavalue", {}).get("value")


def latest_net_worth(ent):
    """P2218 mit dem jüngsten P585-Zeitstempel, umgerechnet in USD."""
    best, best_time = None, ""
    for claim in claims(ent, "P2218"):
        val = claim_value(claim)
        if not isinstance(val, dict):
            continue
        try:
            amount = float(val.get("amount", "0"))
        except (TypeError, ValueError):
            continue
        if (val.get("unit") or "").rsplit("/", 1)[-1] == "Q4916":  # EUR
            amount *= EUR_TO_USD
        stamp = ""
        for q in claim.get("qualifiers", {}).get("P585", []):
            stamp = max(stamp, q.get("datavalue", {}).get("value", {}).get("time", ""))
        if amount > 0 and (best is None or stamp >= best_time):
            best, best_time = amount, stamp
    return best, (best_time[1:5] if best_time else None)


def current_positions(ent):
    """Ämter ohne Enddatum plus Geschäftsführungs-Rollen."""
    out = []
    for claim in claims(ent, "P39"):
        val = claim_value(claim)
        if isinstance(val, dict) and val.get("id") and not claim.get("qualifiers", {}).get("P582"):
            out.append(val["id"])
    for prop in ("P169", "P1037"):  # CEO of / director-manager of
        for claim in claims(ent, prop):
            val = claim_value(claim)
            if isinstance(val, dict) and val.get("id"):
                out.append(val["id"])
    return out


def extract(ent):
    """Die Felder, die eine Karte braucht – inklusive Frische-Hinweisen."""
    info = {"qid": ent.get("id"), "warnings": []}

    death = claims(ent, "P570")
    if death:
        when = (claim_value(death[0]) or {}).get("time", "?")
        info["warnings"].append(f"Laut Wikidata verstorben ({when[1:11]}) – Karte prüfen.")

    info["net_worth_usd"], info["net_worth_year"] = latest_net_worth(ent)
    info["_position_qids"] = current_positions(ent)
    info["description"] = (ent.get("descriptions", {}).get("en", {}) or {}).get("value", "")

    img = claims(ent, "P18")
    if img and isinstance(claim_value(img[0]), str):
        quoted = urllib.parse.quote(claim_value(img[0]).replace(" ", "_"))
        info["image_url"] = (
            f"https://commons.wikimedia.org/wiki/Special:FilePath/{quoted}?width=500")
        info["image_license_page"] = f"https://commons.wikimedia.org/wiki/File:{quoted}"

    sitelinks = ent.get("sitelinks", {})
    info["enwiki"] = sitelinks.get("enwiki", {}).get("title")
    info["dewiki"] = sitelinks.get("dewiki", {}).get("title")
    return info


def role_confirmed(expect, labels, description):
    """Bestätigt Wikidata die im Roster erwartete Rolle noch?"""
    needle = (expect or "").lower()
    if not needle:
        return True
    haystack = " | ".join(labels).lower() + " | " + (description or "").lower()
    return needle in haystack
