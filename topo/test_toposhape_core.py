# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Unit tests for toposhape_core 0.1.0 (numpy only)."""
import math
import os
import unittest

try:
    import numpy as np
    HAVE_NP = True
except ImportError:  # pragma: no cover
    HAVE_NP = False

RUN = HAVE_NP and os.name == "posix"


@unittest.skipUnless(RUN, "needs numpy on POSIX (runs inside the compete job)")
class TestCore(unittest.TestCase):
    def setUp(self):
        import toposhape_core as core
        self.core = core

    def test_delta_phi_range(self):
        d = self.core.delta_phi(np.array([3.0, -3.0, 0.1]), np.array([-3.0, 3.0, 0.1]))
        self.assertTrue(np.all(d >= 0) and np.all(d <= np.pi))
        self.assertAlmostEqual(float(d[0]), 2 * np.pi - 6.0, places=12)
        self.assertAlmostEqual(float(d[2]), 0.0, places=12)

    def test_inv_mass(self):
        self.assertAlmostEqual(float(self.core.inv_mass(0, 0, 3.0, 5.0)), 4.0, places=12)

    def test_mbin_overflow(self):
        b = self.core.mbin(np.array([0.0, 4.99, 5.0, 2500.0]))
        self.assertEqual(list(b), [0, 0, 1, self.core.NM - 1])

    def test_regions_match_ttthresh_scheme(self):
        core = self.core
        rng = np.random.default_rng(1)
        m = rng.uniform(100, 600, 200000)
        w = np.ones_like(m)
        r = core.regions_from_reference(m, w)
        # T = lowest 20 % -> upper edge near 200 GeV for a uniform 100-600 spectrum
        lo, hi = core.edges_gev(r["T"])
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 205.0, delta=5.0)
        self.assertEqual(r["B1"], r["T"])
        self.assertEqual(r["B2"][0], r["B1"][1])
        self.assertEqual(r["B3"][0], r["B2"][1])
        self.assertEqual(r["B4"][0], r["B3"][1])
        self.assertEqual(r["B4"][1], core.NM)
        self.assertEqual(r["incl"], (0, core.NM))
        # C = upper half
        clo, _ = core.edges_gev(r["C"])
        self.assertAlmostEqual(clo, 355.0, delta=5.0)

    def test_quantile_bin_like_ttthresh(self):
        marg = np.zeros(self.core.NM)
        marg[[2, 5, 9]] = [1.0, 1.0, 2.0]
        self.assertEqual(self.core.quantile_bin(marg, 0.25), 2)
        self.assertEqual(self.core.quantile_bin(marg, 0.5), 5)
        self.assertEqual(self.core.quantile_bin(marg, 0.51), 9)

    def test_region_sl_and_asym(self):
        core = self.core
        m = np.array([10.0, 10.0, 10.0, 300.0])
        d = np.array([0.1, 0.2, 3.0, 0.1])
        w = np.array([1.0, 2.0, 1.0, 5.0])
        s, l, s2, l2 = core.region_sl(m, d, w, (0, 10))
        self.assertEqual((s, l, s2, l2), (3.0, 1.0, 5.0, 1.0))
        a, e = core.asym(s, l, s2, l2)
        self.assertAlmostEqual(a, 0.5, places=12)
        self.assertTrue(e > 0)
        a0, e0 = core.asym(0.0, 0.0, 0.0, 0.0)
        self.assertTrue(math.isnan(a0) and math.isnan(e0))

    def test_asym_error_unweighted_binomial(self):
        # unit weights: var(A) = (1 - A^2) / N
        s, l = 600.0, 400.0
        a, e = self.core.asym(s, l, s, l)
        self.assertAlmostEqual(e, math.sqrt((1 - a * a) / 1000.0), places=12)

    def test_mix_shift_identity(self):
        core = self.core
        n_sm, a_sm, n_c, a_c = 1000.0, -0.3, 37.0, 0.25
        s_sm, l_sm = n_sm * (1 + a_sm) / 2, n_sm * (1 - a_sm) / 2
        s_c, l_c = n_c * (1 + a_c) / 2, n_c * (1 - a_c) / 2
        a_mix = (s_sm + s_c - l_sm - l_c) / (n_sm + n_c)
        self.assertAlmostEqual(core.mix_shift(n_sm, a_sm, n_c, a_c), a_mix - a_sm, places=14)

    def test_predict_region(self):
        core = self.core
        p = core.predict_region(0.1, 0.2, 0.3, 0.01, -0.1, 9.3)
        f = 9.3 * 0.2 / (832.0 * 0.1 + 9.3 * 0.2)
        self.assertAlmostEqual(p["f"], f, places=14)
        self.assertAlmostEqual(p["dA_pred"], f * 0.4, places=14)
        self.assertAlmostEqual(p["s_pred"], f * 0.01, places=14)
        bad = core.predict_region(0.0, 0.2, 0.3, 0.01, -0.1, 9.3)
        self.assertTrue(math.isnan(bad["dA_pred"]))

    def test_diff_component(self):
        core = self.core
        # sample 3 = sample 1 + component with S=30, L=10
        n, a, e = core.diff_component(130.0, 110.0, 1.0, 1.0, 100.0, 100.0, 1.0, 1.0)
        self.assertAlmostEqual(n, 40.0)
        self.assertAlmostEqual(a, 0.5)
        self.assertTrue(e > 0)
        n2, a2, _ = core.diff_component(100.0, 100.0, 1, 1, 100.0, 100.0, 1, 1)
        self.assertEqual(n2, 0.0)
        self.assertTrue(math.isnan(a2))

    def test_verdict_boundaries(self):
        core = self.core
        self.assertEqual(core.verdict_share(0.7), "EXPLAINS MOST")
        self.assertEqual(core.verdict_share(0.69999), "EXPLAINS PART")
        self.assertEqual(core.verdict_share(0.3), "EXPLAINS PART")
        self.assertEqual(core.verdict_share(0.29999), "EXPLAINS LITTLE")
        self.assertEqual(core.verdict_share(-0.5), "EXPLAINS LITTLE")
        self.assertEqual(core.verdict_share(float("nan")), "NOT GRADABLE")
        self.assertEqual(core.verdict_residual(2.0), "SURVIVES")
        self.assertEqual(core.verdict_residual(1.99), "REDUCED")
        self.assertEqual(core.verdict_residual(0.0), "ABSORBED")
        self.assertEqual(core.verdict_highmass(0.001, 0.0073), "HIGH-MASS EXCESS NOT FROM THRESHOLD")
        self.assertEqual(core.verdict_highmass(0.003, 0.0073), "THRESHOLD COMPONENT REACHES HIGH MASS")

    def test_gate(self):
        core = self.core
        good = {"pythia_version": "8.318.3", "settings_ok": True, "rC": 0.008,
                "n_born_pass": 60000, "mode": "E", "n_c_pass": 3000}
        self.assertEqual(core.gate(good)[0], "PASS")
        for k, v in (("pythia_version", "8.317.0"), ("settings_ok", False), ("rC", 0.02),
                     ("rC", 0.003), ("n_born_pass", 10), ("n_c_pass", 999), ("mode", "X")):
            bad = dict(good)
            bad[k] = v
            self.assertEqual(core.gate(bad)[0], "FAIL", (k, v))
        diff = dict(good, mode="DIFF", diff_relerr=0.2)
        self.assertEqual(core.gate(diff)[0], "PASS")
        diff["diff_relerr"] = 0.3
        self.assertEqual(core.gate(diff)[0], "FAIL")

    def test_grade_uses_frozen_measured(self):
        core = self.core
        pred = {"incl": {"dA_pred": 0.5 * core.MEASURED["incl"]["dA"]},
                "T": {"dA_pred": 0.8 * core.MEASURED["T"]["dA"]},
                "C": {"dA_pred": 0.0001}}
        g = core.grade(pred)
        self.assertEqual(g["H1"]["verdict"], "EXPLAINS PART")
        self.assertEqual(g["H4"]["verdict"], "EXPLAINS MOST")
        self.assertEqual(g["H3"]["verdict"], "HIGH-MASS EXCESS NOT FROM THRESHOLD")
        z = 0.5 * core.MEASURED["incl"]["dA"] / core.MEASURED["incl"]["sig_total"]
        self.assertAlmostEqual(g["H2"]["Z_res"], z, places=12)
        self.assertEqual(g["H2"]["verdict"], "REDUCED")

    def test_frozen_constants(self):
        core = self.core
        self.assertEqual(core.SIGMA_SM_PB, 832.0)
        self.assertEqual(core.SIGMA_C_PRIMARY_PB, 9.3)
        self.assertEqual(core.MEASURED["B1"], core.MEASURED["T"])
        self.assertEqual(set(core.MEASURED), set(core.REGIONS))


if __name__ == "__main__":
    unittest.main()
