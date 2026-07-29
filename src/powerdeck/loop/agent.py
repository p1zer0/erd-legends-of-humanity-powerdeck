"""Anschluss für Sprachmodelle – lokal, Free-Tier, oder beides.

Alle gängigen Anbieter sprechen dieselbe Sprache: das OpenAI-Chat-Format. Ein
lokales Ollama, Groq, OpenRouter, Together, Hermes über einen dieser Wege – der
Unterschied ist eine URL und ein Schlüssel. Deshalb gibt es hier genau einen
Client und eine **Kaskade**: Läuft ein Guthaben leer oder greift ein Limit,
rutscht der Loop auf den nächsten Anbieter und am Ende auf das lokale Modell.

Konfiguriert wird über `agents.json` im Projektwurzelverzeichnis (aus .gitignore
ausgenommen, damit Schlüssel nie im Repo landen). Vorlage: agents.example.json

Wichtig: Ein Modell entscheidet hier nichts. Es formuliert Vorschläge, die
denselben Weg gehen wie alle anderen – Beleg, Prüfliste, Mensch. Siehe
docs/AGENTEN.md.
"""

import json
import os
import time
import urllib.error
import urllib.request

from ..pipeline.config import ROOT
from ..pipeline.http import SSL_CTX

KONFIG = ROOT / "agents.json"

# Fehler, bei denen es sich lohnt, denselben Anbieter noch einmal zu fragen.
VORUEBERGEHEND = (429, 500, 502, 503, 504)


class KeinAnbieter(RuntimeError):
    """Kein einziger Anbieter konnte antworten."""


def lade_anbieter():
    """Anbieterliste in der Reihenfolge, in der sie versucht werden.

    Schlüssel dürfen direkt in der Datei stehen oder als ${UMGEBUNGSVARIABLE}.
    Die zweite Form ist die bessere: dann liegt das Geheimnis nicht auf Platte.
    """
    if not KONFIG.exists():
        return []
    daten = json.loads(KONFIG.read_text(encoding="utf-8"))
    anbieter = []
    for eintrag in daten.get("anbieter", []):
        if not eintrag.get("aktiv", True):
            continue
        schluessel = eintrag.get("schluessel", "")
        if schluessel.startswith("${") and schluessel.endswith("}"):
            schluessel = os.environ.get(schluessel[2:-1], "")
        if eintrag.get("schluessel") and not schluessel:
            continue  # Platzhalter ohne gesetzte Variable: überspringen
        anbieter.append({**eintrag, "schluessel": schluessel})
    return anbieter


def _anfrage(anbieter, nachrichten, max_tokens, temperatur):
    koerper = json.dumps({
        "model": anbieter["modell"],
        "messages": nachrichten,
        "max_tokens": max_tokens,
        "temperature": temperatur,
    }).encode("utf-8")

    kopf = {"Content-Type": "application/json"}
    if anbieter["schluessel"]:
        kopf["Authorization"] = f"Bearer {anbieter['schluessel']}"

    anfrage = urllib.request.Request(anbieter["url"], data=koerper, headers=kopf)
    with urllib.request.urlopen(anfrage, timeout=anbieter.get("timeout", 120),
                                context=SSL_CTX) as antwort:
        daten = json.loads(antwort.read().decode("utf-8"))
    return daten["choices"][0]["message"]["content"]


def frage(nachrichten, max_tokens=1200, temperatur=0.2, versuche=2, protokoll=None):
    """Die Kaskade durchlaufen, bis einer antwortet.

    Gibt (antwort, anbietername) zurück. Wirft KeinAnbieter, wenn keiner kann –
    der Loop fängt das ab und macht ohne Modell weiter.
    """
    anbieter = lade_anbieter()
    if not anbieter:
        raise KeinAnbieter("Keine agents.json oder kein aktiver Anbieter konfiguriert")

    fehler = []
    for eintrag in anbieter:
        for versuch in range(versuche):
            try:
                antwort = _anfrage(eintrag, nachrichten, max_tokens, temperatur)
                if protokoll:
                    protokoll(f"{eintrag['name']} hat geantwortet")
                return antwort, eintrag["name"]
            except urllib.error.HTTPError as e:
                fehler.append(f"{eintrag['name']}: HTTP {e.code}")
                if e.code in VORUEBERGEHEND and versuch < versuche - 1:
                    time.sleep(5 * (versuch + 1))
                    continue
                break  # Guthaben leer oder Schlüssel falsch: nächster Anbieter
            except Exception as e:
                fehler.append(f"{eintrag['name']}: {type(e).__name__}")
                break
        if protokoll:
            protokoll(f"{eintrag['name']} fällt aus, nächster Anbieter")

    raise KeinAnbieter("Alle Anbieter ausgefallen: " + "; ".join(fehler))


def verfuegbar():
    """Ist überhaupt ein Anbieter eingerichtet? Ohne Modell läuft der Loop trotzdem."""
    return bool(lade_anbieter())


def json_antwort(nachrichten, **kw):
    """Wie frage(), erwartet aber JSON und gibt es geparst zurück.

    Modelle verpacken JSON gern in Markdown-Zäune – das wird hier abgeräumt,
    statt es dem Aufrufer aufzubürden.
    """
    roh, name = frage(nachrichten, **kw)
    text = roh.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    try:
        return json.loads(text.strip()), name
    except json.JSONDecodeError as e:
        raise KeinAnbieter(f"{name} lieferte kein verwertbares JSON: {e}") from e
