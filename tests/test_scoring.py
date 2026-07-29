"""Tests für die reine Rechenschicht – kein Netz, keine Uhr."""

import unittest

from powerdeck import scoring
from powerdeck.config import WEIGHTS

BIAS = {"nytimes.com": -1.0, "cnn.com": -1.0, "foxnews.com": 2.0,
        "reuters.com": 0.0, "apnews.com": 0.0}
STATE = {"rt.com": "Russland", "globaltimes.cn": "China"}


class CoverageBreakdown(unittest.TestCase):
    def test_spektrum_bezieht_sich_auf_eingeordnete_artikel(self):
        # 2 links, 1 mitte, 1 rechts, 6 unbekannt
        domains = (["nytimes.com", "cnn.com", "reuters.com", "foxnews.com"]
                   + ["irgendwo-lokal.example"] * 6)
        result = scoring.coverage_breakdown(domains, BIAS, STATE)

        self.assertEqual(result["verteilung_prozent"]["links"], 50)
        self.assertEqual(result["verteilung_prozent"]["mitte"], 25)
        self.assertEqual(result["verteilung_prozent"]["rechts"], 25)
        self.assertEqual(result["artikel_ausgewertet"], 10)
        self.assertEqual(result["artikel_mit_bias_rating"], 4)
        self.assertEqual(result["abdeckung_prozent"], 40)

    def test_www_praefix_wird_ignoriert(self):
        result = scoring.coverage_breakdown(["WWW.FoxNews.com"], BIAS, STATE)
        self.assertEqual(result["verteilung_prozent"]["rechts"], 100)

    def test_staatsmedien_zaehlen_nicht_ins_spektrum(self):
        result = scoring.coverage_breakdown(
            ["rt.com", "globaltimes.cn", "reuters.com", "apnews.com"], BIAS, STATE)
        self.assertEqual(result["verteilung_prozent"]["mitte"], 100)
        self.assertEqual(result["verteilung_prozent"]["staatsnah"], 50)
        self.assertEqual(result["staatsmedien"], {"Russland": 1, "China": 1})

    def test_leere_eingabe_kippt_nicht(self):
        result = scoring.coverage_breakdown([], BIAS, STATE)
        self.assertEqual(result["artikel_ausgewertet"], 0)
        self.assertEqual(result["abdeckung_prozent"], 0)
        self.assertEqual(result["bias_mittelwert"], 0.0)

    def test_einseitige_berichterstattung_erzeugt_hohen_mittelwert(self):
        einseitig = scoring.coverage_breakdown(["foxnews.com"] * 5, BIAS, STATE)
        gemischt = scoring.coverage_breakdown(
            ["foxnews.com", "foxnews.com", "nytimes.com", "cnn.com"], BIAS, STATE)
        self.assertGreater(abs(einseitig["bias_mittelwert"]),
                           abs(gemischt["bias_mittelwert"]))
        self.assertGreater(scoring.polarisierung_raw(einseitig), 0)


class AttentionMetrics(unittest.TestCase):
    def test_konstante_aufmerksamkeit_hat_kein_chaos(self):
        metrics = scoring.attention_metrics([100] * 30)
        self.assertEqual(metrics["cv"], 0.0)
        self.assertEqual(metrics["spike"], 1.0)

    def test_ausschlag_erhoeht_chaos(self):
        ruhig = scoring.attention_metrics([100] * 29 + [110])
        laut = scoring.attention_metrics([100] * 29 + [5000])
        self.assertGreater(scoring.chaos_raw(laut), scoring.chaos_raw(ruhig))

    def test_leere_reihe(self):
        self.assertEqual(scoring.attention_metrics([])["mittel"], 0.0)


class Scale(unittest.TestCase):
    def test_spannt_auf_1_bis_100(self):
        self.assertEqual(scoring.scale([0, 5, 10]), [1, 50, 100])

    def test_gleiche_werte_landen_in_der_mitte(self):
        self.assertEqual(scoring.scale([7, 7, 7]), [50, 50, 50])

    def test_einzelwert_hat_keine_relation(self):
        self.assertEqual(scoring.scale([42]), [50])

    def test_leere_liste(self):
        self.assertEqual(scoring.scale([]), [])

    def test_log_daempft_ausreisser(self):
        linear = scoring.scale([1, 10, 1000])
        logarithmisch = scoring.scale([1, 10, 1000], log=True)
        self.assertLess(linear[1], logarithmisch[1])


class KapitalScore(unittest.TestCase):
    def test_override_gewinnt(self):
        self.assertEqual(scoring.kapital_score(2.5e9, override=82), 82)

    def test_ohne_vermoegen_gibt_es_einen_sockel(self):
        self.assertEqual(scoring.kapital_score(None), 10)
        self.assertEqual(scoring.kapital_score(0), 10)

    def test_logarithmisch_zwischen_1_und_400_milliarden(self):
        # Untergrenze ist 1, nicht 0: wer eine Milliarde hat, ist nicht machtlos.
        self.assertEqual(scoring.kapital_score(1e9), 1)
        self.assertEqual(scoring.kapital_score(4e11), 100)
        self.assertGreater(scoring.kapital_score(1e11), scoring.kapital_score(1e10))

    def test_deckelt_bei_100(self):
        self.assertEqual(scoring.kapital_score(9e12), 100)


class Macht(unittest.TestCase):
    def test_gewichte_ergeben_eins(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0, places=9)

    def test_hoechstwert_ist_hundert(self):
        self.assertEqual(scoring.macht(dict.fromkeys(WEIGHTS, 100)), 100)

    def test_nullkarte_ist_null(self):
        self.assertEqual(scoring.macht(dict.fromkeys(WEIGHTS, 0)), 0)


if __name__ == "__main__":
    unittest.main()
