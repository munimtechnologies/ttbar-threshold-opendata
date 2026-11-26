# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Unit tests for grade_job 0.1.0. Standard library only, except the end-to-end tests, which run
when tsplit_core.py is found in ../ (repository layout) or ./tsplit (job layout) and numpy is
installed."""
import gzip
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import grade_job as gj  # noqa: E402

TS = None
for _d in (os.path.join(HERE, "tsplit"), os.path.dirname(HERE)):
    if os.path.exists(os.path.join(_d, "tsplit_core.py")):
        sys.path.insert(0, _d)
        try:
            import tsplit_core as TS  # noqa: E402,N812
        except Exception:  # pragma: no cover
            TS = None
        break
try:
    import numpy  # noqa: F401
    HAVE_NP = True
except Exception:  # pragma: no cover
    HAVE_NP = False


class StubTS:
    """The PREREG-v0.2 mass bins, for the stdlib-only tests of classify()."""
    UM = "um"

    @staticmethod
    def mass_bin(m):
        if m is None or not math.isfinite(m):
            return None
        if m < 380.0:
            return "m<380"
        if m < 450.0:
            return "m380-450"
        if m < 550.0:
            return "m450-550"
        return "m>=550"


CORE = TS if TS is not None else StubTS
MASSES = (350.0, 400.0, 500.0, 600.0)


def mrow(dsid, ev, mtt=400.0, mtt_s=345.0, run=284500, s62=1, n_t=1, n_tbar=1, fidx=0):
    return "%d,%d,%d,%d,0,%d,%d,%s,%s,62,62,%d" % (
        dsid, ev, run, fidx, n_t, n_tbar, "nan" if mtt is None else "%.4f" % mtt,
        "nan" if mtt_s is None else "%.4f" % mtt_s, s62)


def part_summary(group, part, keys_sha, tsplit_sha="", files=None, failed=0):
    g = gj.GROUPS[group]
    idx = range(part, g["files"], g["nparts"]) if files is None else files
    return {"match_job": "0.1.0", "group": group, "dsid": g["dsid"], "part": part,
            "nparts": g["nparts"], "files_total": g["files"], "keys_sha256": keys_sha,
            "tsplit_sha256": tsplit_sha, "failed_files": failed,
            "files": [{"file": i, "status": "OK"} for i in idx]}


def make_inputs(perfect=True, keys_sha="k" * 64, tsplit_sha=""):
    """Synthetic keys_T text, keys_summary, and parts {group: [(csv, summary)]}."""
    keys = [gj.KEYS_HEADER]
    sums = {"nom": [0.0, 0.0], "ph7": [0.0, 0.0], "pth1": [0.0, 0.0]}

    def add(dsid, ev, group, w, short):
        keys.append("%d,284500,%d,%s,%.12g,1.000000,200.0000,%d" % (dsid, ev, group, w,
                                                                    1 if short else 0))
        sums[group][0 if short else 1] += w

    match = {"nom": [gj.MATCH_HEADER], "ph7": [gj.MATCH_HEADER], "pth1": [gj.MATCH_HEADER]}
    for ev in range(1, 41):
        add(410470, ev, "nom", 200.0, ev % 3 == 0)
        if perfect or ev not in (38, 39, 40):
            match["nom"].append(mrow(410470, ev, MASSES[ev % 4]))
    if not perfect:
        match["nom"].append(mrow(410470, 38, None))
        match["nom"].append(mrow(410470, 39, 400.0, fidx=1))
        match["nom"].append(mrow(410470, 39, 400.0, fidx=2))
        add(410470, 41, "nom", 1.0, False)
        add(410470, 41, "nom", 1.0, False)
        match["nom"].append(mrow(410470, 41, 400.0))
    for ev in range(1, 31):
        add(411234, ev, "ph7", 180.0, ev % 2 == 0)
        match["ph7"].append(mrow(411234, ev, MASSES[(ev + 1) % 4]))
    if not perfect:
        add(411233, 7, "ph7", 50.0, True)
        add(411233, 8, "ph7", 50.0, False)
    for ev in range(1, 11):
        add(601491, ev, "pth1", 100.0, ev % 2 == 1)
        match["pth1"].append(mrow(601491, ev, MASSES[ev % 4]))
    pn = gj.PRED_T["nom"]
    ksum = {"groups": {gj.GROUPS[g]["summary"]: {"S_T": sums[g][0], "L_T": sums[g][1]}
                       for g in gj.GROUPS},
            "G0": {"verdict": "PASS", "checks": {"pass": True},
                   "bkg_T": [pn[0] - sums["nom"][0], pn[1] - sums["nom"][1]]},
            "xcheck_all": True, "rows_keys_T": len(keys) - 1}
    parts = {}
    for g in gj.GROUPS:
        lst = []
        for p in range(gj.GROUPS[g]["nparts"]):
            text = "\n".join(match[g] if p == 0 else [gj.MATCH_HEADER]) + "\n"
            lst.append((text, part_summary(g, p, keys_sha, tsplit_sha)))
        parts[g] = lst
    return "\n".join(keys) + "\n", ksum, parts


class Parse(unittest.TestCase):
    def test_keys(self):
        text, _, _ = make_inputs()
        rows = gj.parse_keys(text)
        self.assertEqual(len(rows), 80)
        self.assertEqual(rows[0], {"dsid": 410470, "run": 284500, "event": 1, "group": "nom",
                                   "w": 200.0, "short": False})
        self.assertTrue(rows[2]["short"])

    def test_keys_bad(self):
        with self.assertRaises(ValueError):
            gj.parse_keys("dsid,event\n1,2\n")
        with self.assertRaises(ValueError):
            gj.parse_keys(gj.KEYS_HEADER + "\n410470,1,2,nom,1.0,1.0,200.0,2\n")

    def test_match(self):
        rows = gj.parse_match(gj.MATCH_HEADER + "\n" + mrow(410470, 5, None, None) + "\n")
        self.assertEqual(rows[0]["event"], 5)
        self.assertTrue(math.isnan(rows[0]["mtt_l"]) and math.isnan(rows[0]["mtt_s"]))
        with self.assertRaises(ValueError):
            gj.parse_match("dsid,event\n")

    def test_part_dirs(self):
        d = gj.parse_part_dirs([])
        self.assertEqual(len(d), 6)
        self.assertEqual(d[("nom", 3)], "results/tsplit-match-nom-p3-v1")
        d = gj.parse_part_dirs(["nom:2=results/tsplit-match-nom-p2-v2/"])
        self.assertEqual(d[("nom", 2)], "results/tsplit-match-nom-p2-v2")
        for bad in ("ph7:1=results/x", "nom:0=../x", "xx:0=a", "nom:0="):
            with self.assertRaises(ValueError):
                gj.parse_part_dirs([bad])

    def test_raw_url(self):
        sha = "0123456789abcdef0123456789abcdef01234567"
        self.assertTrue(gj.raw_url("a/b", sha).endswith("/ttbar-threshold-opendata/%s/a/b" % sha))
        with self.assertRaises(ValueError):
            gj.raw_url("a/b", "main")


class Parts(unittest.TestCase):
    def test_complete(self):
        s = [part_summary("nom", p, "a" * 64) for p in range(4)]
        r = gj.check_parts("nom", s, "A" * 64)
        self.assertTrue(r["ok"], r["problems"])
        self.assertEqual(r["files_read"], 190)

    def test_missing_twice_failed_sha(self):
        s = [part_summary("nom", p, "a" * 64) for p in range(4)]
        s[1]["files"] = s[1]["files"][1:]
        self.assertFalse(gj.check_parts("nom", s, "a" * 64)["ok"])
        s = [part_summary("ph7", 0, "a" * 64)]
        s[0]["files"].append({"file": 3, "status": "OK"})
        self.assertIn("files read twice: [3]", gj.check_parts("ph7", s, "a" * 64)["problems"])
        s = [part_summary("ph7", 0, "a" * 64, failed=1)]
        self.assertFalse(gj.check_parts("ph7", s, "a" * 64)["ok"])
        s = [part_summary("ph7", 0, "a" * 64)]
        self.assertFalse(gj.check_parts("ph7", s, "b" * 64)["ok"])
        s = [part_summary("ph7", 0, "a" * 64, tsplit_sha="c" * 64)]
        self.assertTrue(gj.check_parts("ph7", s, "a" * 64, "c" * 64)["ok"])
        self.assertFalse(gj.check_parts("ph7", s, "a" * 64, "d" * 64)["ok"])
        self.assertFalse(gj.check_parts("nom", [part_summary("nom", 0, "a" * 64)], "a" * 64)["ok"])


class Classify(unittest.TestCase):
    def setUp(self):
        text, _, _ = make_inputs(perfect=False)
        _, _, parts = make_inputs(perfect=False)
        rows = gj.parse_keys(text)
        self.nom = [r for r in rows if r["group"] == "nom"]
        self.ph7 = [r for r in rows if r["group"] == "ph7"]
        self.pnom = gj.parse_match(parts["nom"][0][0])
        self.pph7 = gj.parse_match(parts["ph7"][0][0])

    def test_reasons_nom(self):
        cls, phys, foreign = gj.classify(self.nom, self.pnom, 410470, CORE)
        self.assertEqual(foreign, 0)
        st = gj.match_stats(cls, phys, 410470)
        self.assertEqual({k: v["n"] for k, v in st["reasons"].items()},
                         {"not_read": 0, "edu_dup": 2, "phys_missing": 1, "phys_dup": 1,
                          "no_pair": 1})
        self.assertEqual(st["matched_n"], 37)
        self.assertEqual(st["selected_n"], 42)
        self.assertAlmostEqual(st["g1_frac"], 7400.0 / 8002.0, places=12)
        self.assertEqual(st["g2_s62_n"], 37)
        self.assertEqual(st["g2_once_keys"], 39)
        self.assertEqual(st["g2_both_n"], 39)
        self.assertEqual((st["run_equal"], st["run_differ"], st["run_absent"]), (37, 0, 0))
        by_ev = {c["event"]: c for c in cls}
        self.assertEqual(by_ev[4]["bin"], "m<380")          # MASSES[0]
        self.assertEqual(by_ev[5]["bin"], "m380-450")
        self.assertEqual(by_ev[38]["bin"], "um")
        self.assertEqual(by_ev[1]["bin_s"], "m<380")        # mtt_s = 345

    def test_reasons_ph7_single_lepton(self):
        cls, phys, _ = gj.classify(self.ph7, self.pph7, 411234, CORE)
        st = gj.match_stats(cls, phys, 411234)
        self.assertEqual(st["reasons"]["not_read"]["n"], 2)
        self.assertAlmostEqual(st["reasons"]["not_read"]["w"], 100.0)
        self.assertEqual(st["matched_n"], 30)
        self.assertAlmostEqual(st["g1_frac"], 1.0)

    def test_foreign_and_run(self):
        rows = [{"dsid": 410470, "run": 1, "event": 9, "group": "nom", "w": 1.0, "short": True}]
        phys = gj.parse_match(gj.MATCH_HEADER + "\n" + mrow(410470, 9, 400.0, run=2) + "\n"
                              + mrow(411234, 9, 400.0) + "\n")
        cls, ph, foreign = gj.classify(rows, phys, 410470, CORE)
        st = gj.match_stats(cls, ph, 410470)
        self.assertEqual(foreign, 1)
        self.assertEqual((st["run_equal"], st["run_differ"]), (0, 1))


@unittest.skipUnless(TS is not None and HAVE_NP, "tsplit_core.py or numpy not available")
class EndToEnd(unittest.TestCase):
    def test_perfect(self):
        text, ksum, parts = make_inputs(perfect=True)
        res = gj.grade(text, ksum, parts, TS, "k" * 64, n_rep=5)
        self.assertTrue(res["gates_ok"], res["gates"])
        sp = res["split"]
        self.assertLess(sp["closure"], 1e-9)
        self.assertAlmostEqual(sp["C"] + sp["S"], sp["Delta"], places=12)
        self.assertAlmostEqual(res["split_check"]["total_nom"],
                               res["split_check"]["pred_nom_total"], places=6)
        self.assertAlmostEqual(sp["A_nom"], res["split_check"]["A_pred_nom"], places=9)
        self.assertEqual(sp["f_nom"]["um"], 0.0)
        self.assertIn(res["H1"], ("COMPOSITION", "MIXED", "ANGULAR"))
        self.assertIn(res["H1r"], ("RESOLVED", "NOT RESOLVED"))
        self.assertEqual(len(res["bootstrap"]["R_C"]), 5)
        self.assertTrue(res["info"]["pth1_vs_nom"]["valid"])
        self.assertTrue(any(ln.startswith("GRADE_H1 ") for ln in gj.grade_lines(res)))

    def test_imperfect_not_gradable(self):
        text, ksum, parts = make_inputs(perfect=False)
        res = gj.grade(text, ksum, parts, TS, "k" * 64, boot=False)
        self.assertEqual(res["gates"]["G1"], "FAIL")
        self.assertEqual(res["H1"], "NOT GRADABLE")
        self.assertEqual(res["H1r"], "NOT GRADABLE")
        self.assertTrue(res["G0"]["consistency_pass"])
        self.assertAlmostEqual(res["match"]["ph7"]["single_lep_w"], 100.0)

    def test_consistency_catches_bad_summary(self):
        text, ksum, parts = make_inputs(perfect=True)
        ksum["groups"]["ttbar_ph7"]["S_T"] += 1.0
        res = gj.grade(text, ksum, parts, TS, "k" * 64, boot=False)
        self.assertEqual(res["gates"]["G0"], "FAIL")
        self.assertEqual(res["H1"], "NOT GRADABLE")

    def test_main_local(self):
        tmp = tempfile.mkdtemp()
        try:
            with open(TS.__file__, "rb") as fh:
                tdata = fh.read()
            tsha = hashlib.sha256(tdata).hexdigest()
            os.makedirs(os.path.join(tmp, "tsplit"))
            with open(os.path.join(tmp, "tsplit", "tsplit_core.py"), "wb") as fh:
                fh.write(tdata)
            text0, _, _ = make_inputs(perfect=True)
            kraw = gzip.compress(text0.encode("utf-8"))
            ksha = hashlib.sha256(kraw).hexdigest()
            text, ksum, parts = make_inputs(perfect=True, keys_sha=ksha, tsplit_sha=tsha)
            self.assertEqual(text, text0)
            kd = os.path.join(tmp, "results", "tsplit-keys-v1")
            os.makedirs(kd)
            with open(os.path.join(kd, "keys_T.csv.gz"), "wb") as fh:
                fh.write(kraw)
            with open(os.path.join(kd, "keys_summary.json"), "w") as fh:
                json.dump(ksum, fh)
            for (g, p), d in gj.default_dirs().items():
                os.makedirs(os.path.join(tmp, d))
                csv_text, summ = parts[g][p]
                with open(os.path.join(tmp, d, "match_%s_p%d.csv.gz" % (g, p)), "wb") as fh:
                    fh.write(gzip.compress(csv_text.encode("utf-8")))
                with open(os.path.join(tmp, d, "match_%s_p%d.json" % (g, p)), "w") as fh:
                    json.dump(summ, fh)
            out = os.path.join(tmp, "out")
            rc = gj.main(["--ref", "local", "--tsplit-sha256", tsha, "--work",
                          os.path.join(tmp, "work"), "--out", out, "--local", tmp])
            self.assertEqual(rc, 0)
            with open(os.path.join(out, "results.json")) as fh:
                res = json.load(fh)
            self.assertTrue(res["gates_ok"], res["gates"])
            self.assertEqual(res["bootstrap"]["reps"], 200)
            self.assertEqual(len(res["inputs"]), 15)
            with open(os.path.join(out, "grade.txt")) as fh:
                self.assertIn("GRADE_H1R ", fh.read())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
