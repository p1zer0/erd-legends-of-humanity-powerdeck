"""Pfade, Konstanten und Gewichte an einer Stelle."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PUBLIC_DIR = ROOT / "public"
CACHE_DIR = ROOT / ".cache"

ROSTER_FILE = DATA_DIR / "roster.json"
BIAS_FILE = DATA_DIR / "bias_sources.json"
DEFAULT_OUT = PUBLIC_DIR / "cards.json"

USER_AGENT = "PowerDeckBuilder/1.0 (ERD Kartenspiel; https://github.com/)"

# Wie viele Tage Wikipedia-Aufrufe in Aufmerksamkeit und Chaos einfließen.
PAGEVIEW_DAYS = 60
# Wie viele Tage GDELT rückwärts betrachtet.
GDELT_TIMESPAN = "30d"
# Obergrenze der Artikel, aus denen das Medienspektrum berechnet wird.
GDELT_MAX_ARTICLES = 250

# Grobe Umrechnung, falls Wikidata ein Vermögen in Euro angibt.
EUR_TO_USD = 1.08

# Cache-Lebensdauer in Stunden, je Datenart.
TTL = {
    "qid": 24 * 30,
    "wikidata": 24 * 7,
    "labels": 24 * 30,
    "summary": 24 * 7,
    "pageviews": 20,
    "gdelt": 20,
}

# Gewichte für den Gesamtwert MACHT. Summe muss 1.0 ergeben (Test prüft das).
WEIGHTS = {
    "kapital": 0.18,
    "militaer": 0.13,
    "nuklear": 0.09,
    "daten": 0.14,
    "compute": 0.14,
    "narrativ": 0.22,
    "polarisierung": 0.05,
    "chaos": 0.05,
}

LEGENDE = {
    "kapital": "Verfügungsgewalt über Geld – Vermögen oder Staatshaushalt",
    "militaer": "Kommandogewalt über Streitkräfte",
    "nuklear": "Zugriff auf Kernwaffen",
    "daten": "Zugriff auf personenbezogene Daten in großem Maßstab",
    "compute": "Kontrolle über Rechenleistung, Chips und KI-Modelle",
    "narrativ": "Medienpräsenz und Aufmerksamkeit (live aus GDELT + Pageviews)",
    "polarisierung": "Wie einseitig das Spektrum über die Person berichtet",
    "chaos": "Wie unberechenbar die Aufmerksamkeit um die Person schwankt",
}

DATENQUELLEN = [
    "Wikidata (CC0)",
    "Wikipedia REST API – Texte CC BY-SA 4.0, Namensnennung erforderlich",
    "Wikimedia Pageviews API",
    "GDELT Project DOC 2.0 API",
    "data/bias_sources.json – eigene, editierbare Quellen-Einordnung",
]
