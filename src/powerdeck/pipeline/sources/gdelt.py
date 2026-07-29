"""GDELT DOC 2.0: Artikelvolumen und Quell-Domains.

GDELT ist die einzige launische Quelle im Projekt. Sie bittet um einen Request
alle fünf Sekunden, antwortet in der Praxis aber auch bei größeren Abständen
mit HTTP 429 oder mit einem Klartext-Hinweis statt JSON. Deshalb: großzügiger
Mindestabstand, mehrere Versuche mit wachsender Wartezeit, und im Zweifel ein
leeres Ergebnis statt eines Abbruchs.

Fehlgeschlagene Abrufe werden nicht gecacht – ein erneuter Lauf holt genau die
fehlenden Personen nach und übernimmt den Rest aus dem Cache.
"""

import json
import sys
import time
from datetime import date

from .. import http
from ..config import GDELT_MAX_ARTICLES, GDELT_TIMESPAN, TTL

API = "https://api.gdeltproject.org/api/v2/doc/doc"

MIN_GAP = 6.0      # Sekunden zwischen zwei Requests
TRIES = 5          # Versuche pro Abfrage
BACKOFF = 8.0      # Zusatzwartezeit je Fehlversuch, wachsend

# Schutzschalter: sperrt GDELT die IP länger, ist jeder weitere Versuch
# verschwendete Zeit. Nach so vielen Abfragen ohne eine einzige Antwort
# wird für diesen Lauf aufgegeben – der nächste Lauf holt alles nach,
# weil Fehlschläge nicht gecacht werden.
CIRCUIT_LIMIT = 3

_last_call = 0.0
_consecutive_failures = 0
_circuit_open = False


def available():
    """False, sobald der Schutzschalter für diesen Lauf ausgelöst hat."""
    return not _circuit_open


def _request(params):
    global _last_call, _consecutive_failures, _circuit_open

    if _circuit_open:
        return None

    url = http.build_url(API, params)
    for attempt in range(TRIES):
        wait = MIN_GAP - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        body = http.get(url, tries=1, quiet=True)
        _last_call = time.time()
        if body and body.lstrip().startswith("{"):
            _consecutive_failures = 0
            try:
                return json.loads(body)
            except ValueError:
                return None
        if attempt < TRIES - 1:
            time.sleep(BACKOFF * (attempt + 1))

    _consecutive_failures += 1
    if _consecutive_failures >= CIRCUIT_LIMIT:
        _circuit_open = True
        print(f"    GDELT antwortet seit {CIRCUIT_LIMIT} Abfragen nicht – "
              f"für diesen Lauf übersprungen. Erneut laufen lassen, sobald die "
              f"Drosselung vorbei ist; alles andere kommt dann aus dem Cache.",
              file=sys.stderr)
    else:
        print("    GDELT gedrosselt – Werte fehlen für diese Person", file=sys.stderr)
    return None


def volume(name, timespan=GDELT_TIMESPAN, today=None):
    """Rohes Artikelvolumen pro Zeitscheibe – wie laut ist die Person?"""
    def fetch():
        data = _request({"query": f'"{name}"', "mode": "timelinevolraw",
                         "timespan": timespan, "format": "json"})
        if not data:
            return None
        series = data.get("timeline") or []
        if not series:
            return []
        return [point.get("value", 0) for point in series[0].get("data", [])]

    stamp = today or date.today()
    return http.cached("gdelt_vol", f"{name}_{stamp:%Y%m%d}", TTL["gdelt"], fetch) or []


def domains(name, maxrecords=GDELT_MAX_ARTICLES, timespan=GDELT_TIMESPAN, today=None):
    """Domains der berichtenden Medien – Grundlage der Polarisierung."""
    def fetch():
        data = _request({"query": f'"{name}" sourcelang:eng', "mode": "artlist",
                         "maxrecords": maxrecords, "timespan": timespan,
                         "sort": "hybridrel", "format": "json"})
        if not data:
            return None
        return [a.get("domain", "") for a in data.get("articles", []) if a.get("domain")]

    stamp = today or date.today()
    return http.cached("gdelt_dom", f"{name}_{stamp:%Y%m%d}", TTL["gdelt"], fetch) or []
