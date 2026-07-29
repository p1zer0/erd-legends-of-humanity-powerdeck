"""HTTP-Zugriff mit Plattencache.

Alles hier ist absichtlich stumpf: keine Sessions, keine Abhängigkeiten, ein
Request nach dem anderen. Die Datenmengen sind klein, die Rate-Limits der
Quellen sind das eigentliche Nadelöhr.
"""

import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .config import CACHE_DIR, USER_AGENT


def _ssl_context():
    """Homebrew-Python bringt auf macOS oft kein Root-Zertifikat mit –
    dann greifen wir auf certifi bzw. das System-Bundle zurück."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    for bundle in ("/etc/ssl/cert.pem", "/usr/local/etc/openssl@3/cert.pem"):
        if Path(bundle).exists():
            try:
                return ssl.create_default_context(cafile=bundle)
            except OSError:
                continue
    return ssl.create_default_context()


SSL_CTX = _ssl_context()


def get(url, tries=3, quiet=False):
    """Text einer URL holen. Gibt None zurück, statt den Lauf abzubrechen."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=45, context=SSL_CTX) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == tries - 1:
                if not quiet:
                    print(f"    HTTP {e.code} für {url[:90]}", file=sys.stderr)
                return None
            time.sleep(10 * (attempt + 1) if e.code in (429, 503) else 3)
        except OSError as e:
            if attempt == tries - 1:
                if not quiet:
                    print(f"    Netzwerkfehler: {e}", file=sys.stderr)
                return None
            time.sleep(2 + attempt * 3)
    return None


def get_json(url, tries=3, quiet=False):
    body = get(url, tries, quiet)
    if body is None:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def build_url(base, params):
    return base + "?" + urllib.parse.urlencode(params)


def cached(kind, key, ttl_hours, producer):
    """Ergebnis von producer() auf Platte halten.

    None wird nie gecacht – ein gescheiterter Abruf soll beim nächsten Lauf
    erneut versucht werden. Dadurch ist ein abgebrochener Lauf einfach
    wiederholbar: alles bereits Geholte kommt aus dem Cache.
    """
    safe = urllib.parse.quote(str(key), safe="")[:120]
    path = CACHE_DIR / f"{kind}__{safe}.json"
    if path.exists() and (time.time() - path.stat().st_mtime) / 3600 < ttl_hours:
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    value = producer()
    if value is not None:
        CACHE_DIR.mkdir(exist_ok=True)
        path.write_text(json.dumps(value))
    return value
