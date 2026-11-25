# SPDX-License-Identifier: Apache-2.0
# Unit tests for tsplit_core 0.1.0 (PREREG-v0.2). MV2 of Munim, Inc. Made with AI agents.
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tsplit_core as tc  # noqa: E402

try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except Exception:  # pragma: no cover
    HAVE_NUMPY = False


def rand_sl(rng):
    return {k: (rng.uniform(10, 1000), rng.uniform(10, 1000)) for k in tc.ALL_BINS}


class TestTsplitCore(unittest.TestCase):

    def test_split_identity_random(self):
        rng = random.Random(1)
        for _ in range(200):
            sn, sp = rand_sl(rng), rand_sl(rng)
            sp[tc.BKG] = sn[tc.BKG]
            d = tc.decompose(sn, sp)
            self.assertLess(d["closure"], 1e-12)
            self.assertAlmostEqual(d["C"] + d["S"], d["Delta"], places=12)
            self.assertAlmostEqual(d["S_k"][tc.BKG], 0.0, places=15)

    def test_A_matches_totals(self):
        sl = {"m<380": (30.0, 10.0), "m380-450": (5.0, 15.0), "um": (1.0, 1.0),
              "bkg": (4.0, 4.0)}
        f, a, A, tot = tc.bin_shares(sl)
        self.assertAlmostEqual(tot, 70.0)
        self.assertAlmostEqual(A, (40.0 - 30.0) / 70.0)
        self.assertAlmostEqual(sum(f.values()), 1.0)
        self.assertEqual(f["m>=550"], 0.0)
        self.assertEqual(a["m>=550"], 0.0)
        self.assertAlmostEqual(a["m<380"], 0.5)

    def test_pure_composition(self):
        # identical a_k, different shares -> S = 0, R_C = 1
        sn = {"m<380": (60.0, 40.0), "m>=550": (40.0, 60.0), "bkg": (10.0, 10.0)}
        sp = {"m<380": (30.0, 20.0), "m>=550": (80.0, 120.0), "bkg": (10.0, 10.0)}
        d = tc.decompose(sn, sp)
        self.assertAlmostEqual(d["S"], 0.0, places=12)
        self.assertAlmostEqual(d["R_C"], 1.0, places=12)
        self.assertEqual(tc.grade_h1(d["R_C"]), "COMPOSITION")

    def test_pure_angular(self):
        # identical shares, different a_k -> C = 0, R_C = 0
        sn = {"m<380": (60.0, 40.0), "m>=550": (50.0, 50.0), "bkg": (10.0, 10.0)}
        sp = {"m<380": (45.0, 55.0), "m>=550": (50.0, 50.0), "bkg": (10.0, 10.0)}
        d = tc.decompose(sn, sp)
        self.assertAlmostEqual(d["C"], 0.0, places=12)
        self.assertAlmostEqual(d["R_C"], 0.0, places=12)
        self.assertEqual(tc.grade_h1(d["R_C"]), "ANGULAR")
        self.assertAlmostEqual(d["S_lt380"], d["S"], places=12)

    def test_zero_delta_not_gradable(self):
        sl = {"m<380": (60.0, 40.0), "bkg": (1.0, 1.0)}
        d = tc.decompose(sl, dict(sl))
        self.assertIsNone(d["R_C"])
        self.assertEqual(tc.grade_h1(d["R_C"]), "NOT GRADABLE")

    def test_c_pieces_sum(self):
        rng = random.Random(7)
        sn, sp = rand_sl(rng), rand_sl(rng)
        sp[tc.BKG] = sn[tc.BKG]
        d = tc.decompose(sn, sp)
        self.assertAlmostEqual(d["C_mass"] + d["C_bkg"] + d["C_um"], d["C"], places=12)

    def test_mass_bin_edges(self):
        self.assertEqual(tc.mass_bin(379.999), "m<380")
        self.assertEqual(tc.mass_bin(380.0), "m380-450")
        self.assertEqual(tc.mass_bin(449.999), "m380-450")
        self.assertEqual(tc.mass_bin(450.0), "m450-550")
        self.assertEqual(tc.mass_bin(550.0), "m>=550")
        self.assertEqual(tc.mass_bin(4000.0), "m>=550")
        self.assertIsNone(tc.mass_bin(float("nan")))
        self.assertIsNone(tc.mass_bin(None))

    def test_pick_tops_rules(self):
        ents = [
            {"pdgId": 6, "barcode": 3, "status": 22},
            {"pdgId": 6, "barcode": 9, "status": 62},
            {"pdgId": -6, "barcode": 4, "status": 22},
            {"pdgId": -6, "barcode": 12, "status": 62},
            {"pdgId": 5, "barcode": 99, "status": 1},
        ]
        t, tb = tc.pick_tops(ents)
        self.assertEqual((t["barcode"], tb["barcode"]), (9, 12))
        t, tb = tc.pick_tops(ents, "smallest")
        self.assertEqual((t["barcode"], tb["barcode"]), (3, 4))
        self.assertTrue(tc.largest_is_status62(ents))
        self.assertIsNone(tc.pick_tops(ents[:2]))
        self.assertFalse(tc.largest_is_status62(ents[:2]))
        tie = ents + [{"pdgId": 6, "barcode": 9, "status": 62}]
        self.assertIsNone(tc.pick_tops(tie))
        with self.assertRaises(ValueError):
            tc.pick_tops(ents, "middle")

    def test_inv_mass(self):
        # two tops at rest: m = 2 * 172.5
        a = tc.p4_from_ptetaphim(0.0, 0.0, 0.0, 172.5)
        self.assertAlmostEqual(tc.inv_mass(a, a), 345.0, places=9)
        # back-to-back, |p| = 100 GeV each: m = 2 sqrt(100^2 + 172.5^2)
        top = {"pt": 100000.0, "eta": 0.0, "phi": 0.3, "m": 172500.0}
        atop = {"pt": 100000.0, "eta": 0.0, "phi": 0.3 + math.pi, "m": 172500.0}
        self.assertAlmostEqual(tc.mtt_gev(top, atop), 2 * math.hypot(100.0, 172.5), places=6)
        # boost along z does not change the mass
        top2 = {"pt": 100000.0, "eta": 1.1, "phi": 0.3, "m": 172500.0}
        atop2 = {"pt": 100000.0, "eta": 1.1, "phi": 0.3, "m": 172500.0}
        self.assertAlmostEqual(tc.mtt_gev(top2, atop2), 345.0, places=6)

    def test_duplicates_dropped(self):
        keys = [(410470, 1), (410470, 2), (410470, 2), (411234, 2), (410470, 3), (410470, 3),
                (410470, 3)]
        u, d = tc.split_duplicates(keys)
        self.assertEqual(u, {(410470, 1), (411234, 2)})
        self.assertEqual(d, {(410470, 2), (410470, 3)})

    def test_accumulate_and_bkg(self):
        ev = [("m<380", 2.0, True), ("m<380", 1.5, False), ("um", 1.0, True)]
        sl = tc.accumulate(ev)
        self.assertEqual(sl["m<380"], [2.0, 1.5])
        self.assertEqual(sl["um"], [1.0, 0.0])
        sl2 = tc.accumulate(ev, [0, 2, 1])
        self.assertEqual(sl2["m<380"], [0.0, 3.0])
        with self.assertRaises(KeyError):
            tc.accumulate([("x", 1.0, True)])
        bkg = tc.bkg_from_prediction((100.0, 90.0), (70.0, 80.0))
        self.assertEqual(bkg, (30.0, 10.0))
        full = tc.with_bkg(sl, bkg)
        self.assertEqual(full["bkg"], (30.0, 10.0))

    def test_grades(self):
        self.assertEqual(tc.grade_h1(0.7), "COMPOSITION")
        self.assertEqual(tc.grade_h1(1.4), "COMPOSITION")
        self.assertEqual(tc.grade_h1(0.6999), "MIXED")
        self.assertEqual(tc.grade_h1(0.3), "MIXED")
        self.assertEqual(tc.grade_h1(0.2999), "ANGULAR")
        self.assertEqual(tc.grade_h1(-0.5), "ANGULAR")
        self.assertEqual(tc.grade_h1(0.8, gates_ok=False), "NOT GRADABLE")
        self.assertEqual(tc.grade_h1r(0.71, 0.95), "RESOLVED")
        self.assertEqual(tc.grade_h1r(0.65, 0.75), "NOT RESOLVED")
        self.assertEqual(tc.grade_h1r(-0.2, 0.29), "RESOLVED")
        self.assertEqual(tc.grade_h1r(None, 0.5), "NOT GRADABLE")

    def test_gates(self):
        g = tc.gate_g0(88766.36 * 1.0009, -993.26 * 1.019, -707.86 * 0.981, (1.0, 0.0))
        self.assertTrue(g["pass"])
        g = tc.gate_g0(88766.36 * 1.0011, -993.26, -707.86, (1.0, 1.0))
        self.assertFalse(g["yield"])
        self.assertFalse(g["pass"])
        g = tc.gate_g0(88766.36, -993.26 * 1.03, -707.86, (1.0, 1.0))
        self.assertFalse(g["dS"])
        g = tc.gate_g0(88766.36, -993.26, -707.86, (-0.1, 1.0))
        self.assertFalse(g["bkg_nonneg"])
        self.assertTrue(tc.gate_fraction(98, 100, 0.98))
        self.assertFalse(tc.gate_fraction(97.9, 100, 0.98))
        self.assertFalse(tc.gate_fraction(1, 0, 0.98))
        self.assertTrue(tc.gate_g3(0.05, 0.01))
        self.assertFalse(tc.gate_g3(0.0501, 0.01))

    def test_percentile_matches_numpy_linear(self):
        v = [5.0, 1.0, 3.0, 2.0, 4.0]
        self.assertAlmostEqual(tc.percentile(v, 16), 1.64)
        self.assertAlmostEqual(tc.percentile(v, 84), 4.36)
        self.assertAlmostEqual(tc.percentile(v + [None], 50), 3.0)
        self.assertIsNone(tc.percentile([None], 50))

    @unittest.skipUnless(HAVE_NUMPY and os.name == "posix", "needs numpy on POSIX")
    def test_bootstrap_reproducible(self):
        import numpy as np
        rng = random.Random(3)
        def events(shift):
            out = []
            for _ in range(400):
                k = tc.MASS_BINS[rng.randrange(4)]
                short = rng.random() < (0.45 + (shift if k == "m<380" else 0.0))
                out.append((k, rng.uniform(0.5, 1.5), short))
            return out
        en, ep = events(0.0), events(0.08)
        r1 = tc.bootstrap_rc(en, ep, (50.0, 50.0), n_rep=20)
        r2 = tc.bootstrap_rc(en, ep, (50.0, 50.0), n_rep=20)
        self.assertEqual(r1, r2)
        self.assertEqual(len(r1), 20)
        r3 = tc.bootstrap_rc(en, ep, (50.0, 50.0), n_rep=20, seed=1)
        self.assertNotEqual(r1, r3)
        vals = [x for x in r1 if x is not None]
        self.assertAlmostEqual(tc.percentile(vals, 16), float(np.percentile(vals, 16)),
                               places=12)


if __name__ == "__main__":
    unittest.main()
