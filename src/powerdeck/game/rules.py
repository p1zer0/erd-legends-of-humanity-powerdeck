"""Die Regeln. Rein, testbar, ohne Zustand außerhalb der übergebenen Argumente.

Der Kern der Gestaltung: **es gibt keinen Gesamtwert im Kampf.** `macht` ist
Deckbau-Währung, nicht Siegbedingung. Wer gewinnt, entscheidet sich in einer
einzelnen Dimension – und jede Dimension hat eine, die sie schlägt.

Damit gibt es keine Karte, die einer anderen überlegen ist. Genau das ist die
Aussage des Spiels: Macht ist mehrdimensional, und wer nur eine Form davon hat,
verliert gegen die richtige Antwort.
"""

from dataclasses import dataclass, field

# Dimensionen, die angegriffen werden können.
ANGRIFF = ("kapital", "militaer", "daten", "narrativ")

# Eskalation: sehr stark, aber einmal pro Partie und mit Preis.
ESKALATION = ("nuklear", "compute")

# Passiv: polarisierung verteidigt, chaos kippt Ergebnisse.
PASSIV = ("polarisierung", "chaos")

# Das Konter-Rad. KONTER[angriff] darf der Verteidiger stattdessen einsetzen.
#   Kapital  <- Narrativ    Boykott, Reputationsverlust, Kursverfall
#   Militär  <- Kapital     Sanktionen, Lieferketten, Söldner
#   Daten    <- Militär     physischer Zugriff auf Infrastruktur
#   Narrativ <- Daten       wer die Zielgruppe kennt, steuert die Erzählung
KONTER = {
    "kapital": "narrativ",
    "militaer": "kapital",
    "daten": "militaer",
    "narrativ": "daten",
}

# Eskalation ist nur durch genau eine Dimension zu beantworten.
ESKALATIONS_KONTER = {
    "nuklear": "nuklear",   # nur Abschreckung hält Abschreckung auf
    "compute": "militaer",  # Rechenzentren stehen an physischen Orten
}

# Anteil der Polarisierung, der als Schutz gegen Narrativ-Angriffe zählt.
# Wer stark polarisiert, ist gegen Kritik weitgehend immun – unangenehm, aber wahr.
POLARISIERUNGS_SCHUTZ = 0.5

# Chaos des Verlierers geteilt durch diesen Wert = Wahrscheinlichkeit, dass die
# Runde doch andersherum ausgeht. Bei chaos 100 also jede vierte Runde.
CHAOS_TEILER = 400

# Preis der Nuklear-Eskalation: dauerhafter Anteil, der vom eigenen Narrativ bleibt.
NUKLEAR_NARRATIV_REST = 0.5

# Die Zivilgesellschaft halbiert den Vorteil gegnerischer Eskalation.
ZIVIL_ESKALATIONS_DAEMPFUNG = 0.5


@dataclass
class Seite:
    """Veränderlicher Zustand einer Partei über die Partie hinweg."""

    name: str
    punkte: int = 0
    eskalation_genutzt: set = field(default_factory=set)
    narrativ_faktor: float = 1.0  # sinkt, wer nuklear eskaliert


@dataclass
class Zug:
    karte: object          # game.cards.Karte
    dimension: str


@dataclass
class Rundenergebnis:
    gewinner: str                  # "angriff" oder "verteidigung"
    angriffswert: float
    verteidigungswert: float
    chaos_umschlag: bool
    protokoll: list                # nachvollziehbare Begründung, Zeile für Zeile


def erlaubte_verteidigung(angriffsdimension):
    """Welche Dimensionen darf der Verteidiger einsetzen?

    Immer dieselbe Dimension (Kraft gegen Kraft) – oder die konternde.
    """
    if angriffsdimension in ESKALATIONS_KONTER:
        konter = ESKALATIONS_KONTER[angriffsdimension]
        return (angriffsdimension,) if konter == angriffsdimension else (angriffsdimension, konter)
    return (angriffsdimension, KONTER[angriffsdimension])


def eskalation_erlaubt(seite, dimension):
    return dimension not in seite.eskalation_genutzt


def _wert(karte, dimension, seite):
    wert = float(karte.stats.get(dimension, 0))
    if dimension == "narrativ":
        wert *= seite.narrativ_faktor
    return wert


def _protokoll_zeile(karte, dimension, wert, zusatz=""):
    return f"{karte.name}: {dimension} {wert:.0f}{zusatz}"


def resolve(angriff, verteidigung, seite_a, seite_b, wuerfel):
    """Eine Runde auflösen.

    `wuerfel` ist ein random.Random – die Partie ist über ihren Seed vollständig
    reproduzierbar. Das ist keine Spielerei: ein Kampf um echte Werte muss
    nachrechenbar sein.
    """
    protokoll = []
    dim_a, dim_b = angriff.dimension, verteidigung.dimension

    if dim_b not in erlaubte_verteidigung(dim_a):
        raise ValueError(f"{dim_b} ist keine gültige Antwort auf {dim_a}")

    wert_a = _wert(angriff.karte, dim_a, seite_a)
    wert_b = _wert(verteidigung.karte, dim_b, seite_b)
    protokoll.append(_protokoll_zeile(angriff.karte, dim_a, wert_a))

    # Eskalation kostet und wirkt
    if dim_a in ESKALATION:
        seite_a.eskalation_genutzt.add(dim_a)
        if dim_a == "nuklear":
            seite_a.narrativ_faktor *= NUKLEAR_NARRATIV_REST
            protokoll.append(f"{seite_a.name} eskaliert nuklear – Narrativ dauerhaft halbiert.")
        if verteidigung.karte.faction == "zivil":
            wert_a *= ZIVIL_ESKALATIONS_DAEMPFUNG
            protokoll.append("Zivilgesellschaft dämpft die Eskalation um die Hälfte.")

    # Polarisierung schützt gegen Narrativ-Angriffe
    if dim_a == "narrativ" and dim_b == "narrativ":
        schutz = verteidigung.karte.stats.get("polarisierung", 0) * POLARISIERUNGS_SCHUTZ
        if schutz:
            wert_b += schutz
            protokoll.append(f"Polarisierung schützt: +{schutz:.0f} auf die Verteidigung.")

    protokoll.append(_protokoll_zeile(verteidigung.karte, dim_b, wert_b,
                                      " (Konter)" if dim_b != dim_a else ""))

    # Gleichstand: der Angreifer hat die Initiative – außer die Zivilgesellschaft
    # verteidigt ein Narrativ gegen Staat oder Kapital.
    if wert_a == wert_b:
        zivil_vorteil = (verteidigung.karte.faction == "zivil"
                         and dim_b == "narrativ"
                         and angriff.karte.faction in ("staat", "kapital"))
        gewinner = "verteidigung" if zivil_vorteil else "angriff"
        protokoll.append("Gleichstand – "
                         + ("Zivilgesellschaft behält das Wort." if zivil_vorteil
                            else "Initiative entscheidet für den Angriff."))
    else:
        gewinner = "angriff" if wert_a > wert_b else "verteidigung"

    # Chaos: die unterlegene Seite kann das Ergebnis kippen
    verlierer_karte = verteidigung.karte if gewinner == "angriff" else angriff.karte
    chaos = verlierer_karte.stats.get("chaos", 0)
    umschlag = chaos > 0 and wuerfel.random() < chaos / CHAOS_TEILER
    if umschlag:
        gewinner = "verteidigung" if gewinner == "angriff" else "angriff"
        protokoll.append(f"Chaos ({chaos}) kippt die Runde – {verlierer_karte.name} dreht sie um.")

    return Rundenergebnis(gewinner=gewinner, angriffswert=wert_a, verteidigungswert=wert_b,
                          chaos_umschlag=umschlag, protokoll=protokoll)
