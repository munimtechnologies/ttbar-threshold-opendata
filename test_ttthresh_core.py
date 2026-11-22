# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Unit tests for ttthresh_core 0.1.0 and the selection of ttthresh_job 0.1.0."""
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ttthresh_core as tc  # noqa: E402


def _flat_H(n_per_bin=100.0, excess_T_small=0.0):
    """Synthetic histograms: every group flat; optional data excess in low m, small dphi."""
    H = {}
    base = np.full((tc.NM, tc.ND), 0.0)
    base[20:200, :] = n_per_bin          # 100-1000 GeV populated
    for g in ("ttbar_nom", "ttbar_ph7", "ttbar_pth1"):
        H[g] = {"os": base.copy(), "os2": base.copy() * 0.01, "ss": np.zeros_like(base),
                "ss2": np.zeros_like(base)}
    for g in ("tW_DR", "tW_DS", "Ztautau", "diboson", "ttV"):
        H[g] = {"os": base.copy() * 0.0, "os2": base.copy() * 0.0,
                "ss": np.zeros_like(base), "ss2": np.zeros_like(base)}
    d = base.copy()
    d[20:56, :tc.HALF] += excess_T_small
    H["data"] = {"os": d, "ss": np.zeros_like(base)}
    return H


class Kinematics(unittest.TestCase):
    def test_delta_phi_wraps(self):
        self.assertAlmostEqual(float(tc.delta_phi(3.0, -3.0)), 2 * math.pi - 6.0, places=12)
        self.assertAlmostEqual(float(tc.delta_phi(0.5, 0.2)), 0.3, places=12)
        self.assertAlmostEqual(float(tc.delta_phi(-math.pi, math.pi)), 0.0, places=12)

    def test_back_to_back_mass(self):
        px, py, pz, e = tc.p4(np.array([50.0, 50.0]), np.array([0.0, 0.0]),
                              np.array([0.0, math.pi]), np.array([50.0, 50.0]))
        self.assertAlmostEqual(float(tc.mass(px.sum(), py.sum(), pz.sum(), e.sum())), 100.0,
                               places=9)

    def test_event_vars(self):
        l = lambda a, b: np.array([[a, b]], float)  # noqa: E731
        dphi, mll, mllbb = tc.event_vars(l(50, 50), l(0, 0), l(0, math.pi), l(50, 50),
                                         l(50, 50), l(0, 0), l(math.pi / 2, -math.pi / 2),
                                         l(50, 50))
        self.assertAlmostEqual(float(dphi[0]), math.pi, places=12)
        self.assertAlmostEqual(float(mll[0]), 100.0, places=9)
        self.assertAlmostEqual(float(mllbb[0]), 200.0, places=9)

    def test_negative_m2_clipped(self):
        self.assertEqual(float(tc.mass(1.0, 0.0, 0.0, 0.5)), 0.0)


class Histos(unittest.TestCase):
    def test_hist2_overflow_and_edges(self):
        h, h2 = tc.hist2([2500.0, 10.0, 10.0], [math.pi, 0.0, 0.1], [2.0, 1.0, 3.0])
        self.assertEqual(h.shape, (tc.NM, tc.ND))
        self.assertEqual(h[tc.NM - 1, tc.ND - 1], 2.0)
        self.assertEqual(h[2, 0], 4.0)
        self.assertEqual(h2[2, 0], 10.0)
        self.assertEqual(h.sum(), 6.0)

    def test_hist2_empty(self):
        h, h2 = tc.hist2([], [], [])
        self.assertEqual(h.sum(), 0.0)

    def test_quantile_bin(self):
        marg = np.zeros(tc.NM)
        marg[:10] = 1.0
        self.assertEqual(tc.quantile_bin(marg, 0.2), 1)
        self.assertEqual(tc.quantile_bin(marg, 0.5), 4)
        with self.assertRaises(ValueError):
            tc.quantile_bin(np.zeros(5), 0.5)


class Stats(unittest.TestCase):
    def test_asym_binomial(self):
        a, s = tc.asym(60.0, 40.0, 60.0, 40.0)
        self.assertAlmostEqual(a, 0.2, places=12)
        self.assertAlmostEqual(s, math.sqrt((1 - 0.04) / 100.0), places=12)

    def test_asym_empty(self):
        a, s = tc.asym(0.0, 0.0, 0.0, 0.0)
        self.assertTrue(math.isnan(a) and math.isnan(s))

    def test_verdicts(self):
        self.assertEqual(tc.verdict_three(2.0, 2.0, "H", "M", "L"), "H")
        self.assertEqual(tc.verdict_three(1.99, 2.0, "H", "M", "L"), "M")
        self.assertEqual(tc.verdict_three(0.0, 2.0, "H", "M", "L"), "L")
        self.assertEqual(tc.verdict_three(float("nan"), 2.0, "H", "M", "L"), "NOT GRADABLE")
        self.assertEqual(tc.verdict_h2(1.5), "CONCENTRATED AT THRESHOLD")
        self.assertEqual(tc.verdict_h2(-1.5), "CONCENTRATED AT HIGH MASS")
        self.assertEqual(tc.verdict_h2(1.49), "NOT RESOLVED")

    def test_gate(self):
        self.assertEqual(tc.gate(30000, 30000, 0.9)[0], "PASS")
        self.assertEqual(tc.gate(30000, 20000, 0.9)[0], "FAIL")
        self.assertEqual(tc.gate(30000, 30000, 0.7)[0], "FAIL")
        self.assertEqual(tc.gate(1000, 1000, 0.9)[0], "FAIL")


class Grade(unittest.TestCase):
    def test_null(self):
        r = tc.grade(_flat_H())
        self.assertEqual(r["gate"]["verdict"], "PASS")
        self.assertAlmostEqual(r["regions"]["T"]["dA"], 0.0, places=12)
        self.assertEqual(r["H1"]["verdict"], "NOT SEEN")
        self.assertEqual(r["H2"]["verdict"], "NOT RESOLVED")
        self.assertEqual(r["H3"]["verdict"], "NOT ROBUST")
        # T is the lowest 20 %: populated 100-1000 GeV uniformly -> T ends at 280 GeV
        self.assertEqual(r["regions"]["T"]["hi_GeV"], 280.0)
        self.assertEqual(r["regions"]["C"]["lo_GeV"], 550.0)

    def test_injected_threshold_excess(self):
        r = tc.grade(_flat_H(excess_T_small=30.0))
        self.assertGreater(r["regions"]["T"]["dA"], 0.0)
        self.assertEqual(r["H1"]["verdict"], "EXCESS SEEN")
        self.assertEqual(r["H2"]["verdict"], "CONCENTRATED AT THRESHOLD")
        self.assertEqual(r["H3"]["verdict"], "ROBUST")
        self.assertAlmostEqual(r["regions"]["C"]["dA"], 0.0, places=12)

    def test_generator_envelope(self):
        H = _flat_H(excess_T_small=30.0)
        H["ttbar_ph7"]["os"][20:56, :tc.HALF] += 30.0     # alt generator explains the excess
        r = tc.grade(H)
        T = r["regions"]["T"]
        self.assertAlmostEqual(T["pred"]["ph7"]["dA"], 0.0, places=12)
        self.assertGreater(T["sig_gen"], 0.0)
        self.assertLess(T["Z"], 1.5)
        self.assertEqual(r["H3"]["verdict"], "NOT ROBUST")

    def test_residual_nonprompt_added(self):
        H = _flat_H()
        H["data"]["ss"][30, 0] = 50.0
        p, p2, fake = tc.combine(H, "ttbar_nom")
        self.assertEqual(fake.sum(), 50.0)
        self.assertEqual(p.sum(), H["ttbar_nom"]["os"].sum() + 50.0)

    def test_gate_fail_blocks_verdicts(self):
        H = _flat_H()
        H["data"]["os"] *= 2.0
        r = tc.grade(H)
        self.assertEqual(r["gate"]["verdict"], "FAIL")
        self.assertTrue(r["H1"]["verdict"].startswith("NOT GRADABLE"))


class Selection(unittest.TestCase):
    """The awkward-array selection of ttthresh_job (skipped without awkward)."""

    def setUp(self):
        try:
            import awkward  # noqa: F401
        except ImportError:
            self.skipTest("awkward not installed")

    def _events(self):
        import awkward as ak
        good = dict(lep_pt=[60.0, 40.0], lep_eta=[0.1, -0.2], lep_phi=[0.0, 0.5],
                    lep_e=[60.3, 40.8], lep_charge=[1, -1], lep_type=[11, 13],
                    lep_isTightID=[True, True], lep_isTightIso=[True, True],
                    lep_isTrigMatched=[True, False],
                    jet_pt=[30.0, 80.0, 50.0], jet_eta=[0.0, 0.3, -1.0],
                    jet_phi=[2.0, 3.0, -2.0], jet_e=[30.0, 84.0, 77.2],
                    jet_btag_quantile=[1, 5, 4], trigE=True, trigM=False, mcWeight=2.0,
                    ScaleFactor_PILEUP=0.5)
        ev = [dict(good)]
        ss = dict(good, lep_charge=[1, 1])
        ee = dict(good, lep_type=[11, 11])
        crack = dict(good, lep_eta=[1.4, -0.2])
        nob = dict(good, jet_btag_quantile=[1, 2, 3])
        three = dict(good, lep_pt=[60.0, 40.0, 30.0], lep_eta=[0.1, -0.2, 0.0],
                     lep_phi=[0.0, 0.5, 1.0], lep_e=[60.3, 40.8, 30.0], lep_charge=[1, -1, 1],
                     lep_type=[11, 13, 13], lep_isTightID=[True, True, True],
                     lep_isTightIso=[True, True, True], lep_isTrigMatched=[True, False, False])
        notrig = dict(good, lep_isTrigMatched=[False, True])     # matched muon has pt 40 > 27
        lowpt = dict(good, lep_isTrigMatched=[False, True], lep_pt=[60.0, 26.0])
        ev += [ss, ee, crack, nob, three, notrig, lowpt]
        return ak.Array(ev)

    def test_cuts(self):
        import ttthresh_job as tj
        a = self._events()
        v, cf = tj.select_arrays(a, True, ["ScaleFactor_PILEUP"])
        self.assertEqual(cf["in"], 8)
        self.assertEqual(cf["two_lep"], 7)
        self.assertEqual(list(v["os"]), [True, False, False, False, False, True, False])
        self.assertEqual(list(v["ss"]), [False, True, False, False, False, False, False])
        self.assertEqual(cf["OS"], 2)
        self.assertEqual(cf["SS"], 1)
        self.assertAlmostEqual(float(v["w"][0]), 1.0, places=12)
        self.assertAlmostEqual(float(v["dphi"][0]), 0.5, places=12)
        # the two chosen jets are the quantile-5 (80 GeV) and quantile-4 (50 GeV) jets
        import ttthresh_core as core
        lx, ly, lz, le = core.p4(np.array([60.0, 40.0]), np.array([0.1, -0.2]),
                                 np.array([0.0, 0.5]), np.array([60.3, 40.8]))
        jx, jy, jz, je = core.p4(np.array([80.0, 50.0]), np.array([0.3, -1.0]),
                                 np.array([3.0, -2.0]), np.array([84.0, 77.2]))
        m = core.mass(lx.sum() + jx.sum(), ly.sum() + jy.sum(), lz.sum() + jz.sum(),
                      le.sum() + je.sum())
        self.assertAlmostEqual(float(v["mllbb"][0]), float(m), places=9)

    def test_data_weight_one(self):
        import ttthresh_job as tj
        v, cf = tj.select_arrays(self._events(), False)
        self.assertTrue(np.all(v["w"] == 1.0))

    def test_rules_unique(self):
        import ttthresh_job as tj
        files = [{"key": "ODEO_FEB2025_v0_2J2LMET30_mc_410470.PhPy8EG_A14_ttbar_hdamp258p75_nonallhad.2J2LMET30.root"},
                 {"key": "ODEO_FEB2025_v0_2J2LMET30_mc_700601.Sh_2212_lllv.2J2LMET30.root"},
                 {"key": "ODEO_FEB2025_v0_2J2LMET30_mc_410155.aMcAtNloPythia8EvtGen_MEN30NLO_A14N23LO_ttW.2J2LMET30.root"},
                 {"key": "ODEO_FEB2025_v0_2J2LMET30_mc_700325.Sh_2211_Zmumu_maxHTpTV2_CVetoBVeto.2J2LMET30.root"},
                 {"key": "ODEO_FEB2025_v0_2J2LMET30_mc_601495.PhPy8EG_A14_ttbar_pThard1_allhad.2J2LMET30.root"}]
        g = tj.assign(files)
        self.assertEqual(len(g["ttbar_nom"]), 1)
        self.assertEqual(len(g["diboson"]), 1)
        self.assertEqual(len(g["ttV"]), 1)
        self.assertEqual(sum(len(v) for v in g.values()), 3)


if __name__ == "__main__":
    unittest.main()
