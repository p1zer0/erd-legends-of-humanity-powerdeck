"""Wikipedia-Kurzbeschreibung und tägliche Seitenaufrufe.

Die Pageviews sind die ehrlichste frei verfügbare Aufmerksamkeitsmessung, die
es gibt: keine Plattform-Metrik, keine Werbelogik, nur wie oft Menschen
nachgeschlagen haben, wer jemand ist.
"""

import urllib.parse
from datetime import date, timedelta

from .. import http
from ..config import PAGEVIEW_DAYS, TTL

SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
VIEWS = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
         "en.wikipedia/all-access/user/{title}/daily/{start}/{end}")


def _quote(title):
    return urllib.parse.quote(title.replace(" ", "_"), safe="")


def summary(title):
    data = http.cached("summary", title, TTL["summary"],
                       lambda: http.get_json(SUMMARY.format(_quote(title))))
    if not data:
        return {}
    return {
        "beschreibung": data.get("description"),
        "steckbrief": data.get("extract"),
        "wiki_url": (data.get("content_urls", {}).get("desktop", {}) or {}).get("page"),
        "thumbnail": (data.get("thumbnail") or {}).get("source"),
    }


def pageviews(title, days=PAGEVIEW_DAYS, today=None):
    """Tägliche Aufrufe der letzten `days` Tage, endend gestern."""
    end = (today or date.today()) - timedelta(days=1)
    start = end - timedelta(days=days - 1)

    def fetch():
        data = http.get_json(VIEWS.format(
            title=_quote(title), start=f"{start:%Y%m%d}", end=f"{end:%Y%m%d}"))
        if not data:
            return None
        return [item["views"] for item in data.get("items", [])]

    return http.cached("pageviews", f"{title}_{end:%Y%m%d}_{days}",
                       TTL["pageviews"], fetch) or []
