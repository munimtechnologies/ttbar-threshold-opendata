# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Unit tests for keys_job 0.1.0 and prep 0.1.0 (standard library only)."""
import hashlib
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import keys_job as kj  # noqa: E402
import prep  # noqa: E402

HALF_EDGE = math.pi / 2.0


class RegionAndShort(unittest.TestCase):
    def test_region_t_edges(self):
        self.assertTrue(kj.region_t_flag(0.0))
        self.assertTrue(kj.region_t_flag(249.9999))
        self.assertFalse(kj.region_t_flag(250.0))      # an edge goes to the upper bin
        self.assertFalse(kj.region_t_flag(1.0e6))      # overflow clipped into the last bin
        self.assertTrue(kj.region_t_flag(-3.0))        # clipped to 0
        self.assertFalse(kj.region_t_flag(float("nan")))

    def test_short_edges(self):
        self.assertTrue(kj.short_flag(0.0, HALF_EDGE))
        self.assertTrue(kj.short_flag(HALF_EDGE - 1e-12, HALF_EDGE))
        self.assertFalse(kj.short_flag(HALF_EDGE, HALF_EDGE))
        self.assertFalse(kj.short_flag(math.pi, HALF_EDGE))
        self.assertFalse(kj.short_flag(4.0, HALF_EDGE))  # clipped to pi

    def test_constants(self):
        self.assertEqual(kj.REGION_T_HI_BIN * 5.0, kj.REGION_T_HI_GEV)
        dS = kj.PRED_T["ph7"][0] - kj.PRED_T["nom"][0]
        dL = kj.PRED_T["ph7"][1] - kj.PRED_T["nom"][1]
        self.assertAlmostEqual(dS, -993.26, places=2)   # tsplit_core.REF_DS_PRED
        self.assertAlmostEqual(dL, -707.86, places=2)   # tsplit_core.REF_DL_PRED


class Rows(unittest.TestCase):
    def test_csv_row(self):
        r = kj.csv_row(410470, 284500, 18446744073709551615, "nom", 0.000678039338617127,
                       1.2345678, 199.99999, True)
        self.assertEqual(r, "410470,284500,18446744073709551615,nom,0.000678039338617,"
                            "1.234568,200.0000,1")
        self.assertEqual(len(r.split(",")), len(kj.CSV_HEADER.split(",")))

    def test_duplicates(self):
        n, d, rows = kj.count_duplicates([(1, 5), (1, 6), (1, 5), (2, 5), (1, 5)])
        self.assertEqual((n, d, rows), (5, 1, 3))
        self.assertEqual(kj.count_duplicates([]), (0, 0, 0))

    def test_bkg_and_close(self):
        self.assertEqual(kj.bkg_t((10.0, 20.0), (4.0, 5.0)), (6.0, 15.0))
        self.assertTrue(kj.rel_close(88766.364, 88766.364 * (1 + 5e-8)))
        self.assertFalse(kj.rel_close(88766.364, 88766.364 * (1 + 5e-6)))


class Prep(unittest.TestCase):
    def test_blob_sha1(self):
        self.assertEqual(prep.git_blob_sha1(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")

    def test_pin(self):
        data = b"numpy\nuproot\nawkward\n"
        want = hashlib.sha256(data).hexdigest()
        self.assertTrue(prep.check_pin("x", data, want.upper()))
        self.assertFalse(prep.check_pin("x", data + b" ", want))

    def test_pinned_value(self):
        self.assertEqual(prep.PINNED["fix_ttthresh.py"][:8], "9c2bdd68")
        self.assertEqual(len(prep.PINNED["fix_ttthresh.py"]), 64)


if __name__ == "__main__":
    unittest.main()
