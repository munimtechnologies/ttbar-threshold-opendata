# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Offline tests of fix_ttthresh 0.1.1 (no network)."""
import re
import unittest

import fix_ttthresh as fx

PRE = "ODEO_FEB2025_v0_2J2LMET30_mc_"
DIB_KEYS = {  # real keys of CERN Open Data record 93913 (read 2026-11-24)
    "700600": "700600.Sh_2212_llll", "700601": "700601.Sh_2212_lllv",
    "700602": "700602.Sh_2212_llvv_os", "700603": "700603.Sh_2212_llvv_ss",
    "700604": "700604.Sh_2212_lvvv", "700605": "700605.Sh_2212_vvvv"}


def _rule(src):
    """The regex inside a '"diboson": [r"..."],' line."""
    return re.search(r'\[r"(.*)"\]', src).group(1)


class Fix(unittest.TestCase):
    def test_git_blob_sha1_known_values(self):
        self.assertEqual(fx.git_blob_sha1(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")
        self.assertEqual(fx.git_blob_sha1(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_patch_once_requires_exactly_one(self):
        self.assertEqual(fx.patch_once("a b c", "b", "x"), "a x c")
        with self.assertRaises(SystemExit):
            fx.patch_once("a c", "b", "x")
        with self.assertRaises(SystemExit):
            fx.patch_once("b b", "b", "x")

    def test_old_rule_misses_ww_new_rule_catches_it(self):
        old, new = _rule(fx.OLD_DIB), _rule(fx.NEW_DIB)
        hit_old = sorted(d for d, k in DIB_KEYS.items() if re.search(old, PRE + k + ".2J2LMET30.root"))
        hit_new = sorted(d for d, k in DIB_KEYS.items() if re.search(new, PRE + k + ".2J2LMET30.root"))
        self.assertEqual(hit_old, ["700600", "700601", "700604"])          # the 0.1.0 defect
        self.assertEqual(hit_new, ["700600", "700601", "700602", "700603", "700604"])

    def test_new_rule_does_not_touch_other_groups(self):
        new = _rule(fx.NEW_DIB)
        for k in ("410470.PhPy8EG_A14_ttbar_hdamp258p75_nonallhad", "700792.Sh_2214_Ztautau_maxHTpTV2_BFilter",
                  "410155.aMcAtNloPythia8EvtGen_MEN30NLO_A14N23LO_ttW"):
            self.assertIsNone(re.search(new, PRE + k + ".2J2LMET30.root"))

    def test_apply_patches_on_synthetic_job(self):
        src = ('"""ttthresh_job 0.1.0 -- runs\n"""\nVERSION = "0.1.0"\nRULES = {\n    '
               + fx.OLD_DIB + '\n}\n')
        out = fx.apply_patches("ttthresh_job.py", src)
        self.assertIn('VERSION = "0.1.1"', out)
        self.assertIn(fx.NEW_DIB, out)
        self.assertNotIn(fx.OLD_DIB, out)
        with self.assertRaises(SystemExit):           # applying twice must fail
            fx.apply_patches("ttthresh_job.py", out)

    def test_apply_patches_on_synthetic_test(self):
        src = ('import unittest\n\nclass S(unittest.TestCase):\n    def test_rules_unique(self):\n'
               '        files = [{"key": "x"},\n                 ' + fx.KEY_LLLV + '\n                 {"key": "y"}]\n'
               '        g = {}\n        self.assertEqual(len(g["diboson"]), 1)\n'
               '        self.assertEqual(sum(len(v) for v in g.values()), 3)\n\n\n'
               'if __name__ == "__main__":\n    unittest.main()\n')
        out = fx.apply_patches("test_ttthresh_core.py", src)
        self.assertIn("700602.Sh_2212_llvv_os", out)
        self.assertIn("class LlvvFix(unittest.TestCase):", out)
        self.assertIn('self.assertEqual(len(g["diboson"]), 2)', out)
        compile(out, "patched_test", "exec")             # still valid Python

    def test_untouched_files_have_no_patches(self):
        self.assertEqual(fx.apply_patches("ttthresh_core.py", "abc"), "abc")
        self.assertNotIn("ttthresh_core.py", fx.PATCHES)


if __name__ == "__main__":
    unittest.main()
