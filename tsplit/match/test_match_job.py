# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Unit tests for match_job 0.1.0 (standard library only; the tsplit_core tests run when
tsplit_core.py is found in ../ (repository layout) or ./tsplit (job layout))."""
import gzip
import hashlib
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import match_job as mj  # noqa: E402

TS = None
for _d in (os.path.join(HERE, "tsplit"), os.path.dirname(HERE)):
    if os.path.exists(os.path.join(_d, "tsplit_core.py")):
        sys.path.insert(0, _d)
        try:
            import tsplit_core as TS  # noqa: E402,N812
        except Exception:  # pragma: no cover
            TS = None
        break


def _inv_mass(a, b):
    m2 = (a[3] + b[3]) ** 2 - sum((a[i] + b[i]) ** 2 for i in range(3))
    return math.sqrt(m2) if m2 > 0 else 0.0


def _ent(pdg, bc, st, px, py, pz, e):
    return {"pdgId": pdg, "barcode": bc, "status": st, "px": px, "py": py, "pz": pz, "e": e}


E100 = math.sqrt(172500.0 ** 2 + 100000.0 ** 2)
EVENT = [_ent(6, 3, 22, 0.0, 0.0, 0.0, 172500.0), _ent(-6, 4, 22, 0.0, 0.0, 0.0, 172500.0),
         _ent(6, 10, 62, 100000.0, 0.0, 0.0, E100), _ent(-6, 11, 62, -100000.0, 0.0, 0.0, E100),
         _ent(5, 12, 23, 1.0, 2.0, 3.0, 50.0)]


class Index(unittest.TestCase):
    REC = {"metadata": {"_file_indices": [
        {"key": "mc20_13TeV_MC_PowhegHerwig7EvtGen_tt_hdamp258p75_713_SingleLep_file_index.json",
         "files": [{"uri": "root://x//eos/opendata/a/DAOD_PHYSLITE.1._000001.pool.root.1"}]},
        {"key": "mc20_13TeV_MC_PowhegHerwig7EvtGen_tt_hdamp258p75_713_dil_file_index.json",
         "files": [{"uri": "root://x//eos/opendata/a/DAOD_PHYSLITE.2._000002.pool.root.1"},
                   {"uri": "root://x//eos/opendata/a/DAOD_PHYSLITE.2._000001.pool.root.1"},
                   {"uri": "root://x//eos/opendata/a/notes.txt"}]},
        {"key": "mc20_13TeV_MC_PowhegHerwig7EvtGen_tt_hdamp258p75_713_dil_file_index.txt",
         "files": [{"uri": "root://x//eos/opendata/a/DAOD_PHYSLITE.2._000001.pool.root.1"}]}]}}

    def test_index_files_dil_only_sorted(self):
        keys, files = mj.index_files(self.REC, mj.SAMPLES["ph7"]["index"])
        self.assertEqual(len(keys), 1)
        self.assertEqual(len(files), 2)
        self.assertTrue(files[0]["uri"].endswith("DAOD_PHYSLITE.2._000001.pool.root.1"))
        self.assertTrue(files[1]["uri"].endswith("DAOD_PHYSLITE.2._000002.pool.root.1"))

    def test_regexes_distinct(self):
        self.assertIsNone(__import__("re").search(
            mj.SAMPLES["ph7"]["index"],
            "mc20_13TeV_MC_PowhegHerwig7EvtGen_tt_hdamp258p75_713_SingleLep_file_index.json"))
        self.assertIsNotNone(__import__("re").search(
            mj.SAMPLES["pth1"]["index"], "mc20_13TeV_MC_PhPy8EG_A14_ttbar_pThard1_dil_file_index.json"))
        self.assertIsNone(__import__("re").search(
            mj.SAMPLES["pth1"]["index"],
            "mc20_13TeV_MC_PhPy8EG_A14_ttbar_pThard1_singlelep_file_index.json"))
        self.assertIsNotNone(__import__("re").search(
            mj.SAMPLES["nom"]["index"],
            "mc20_13TeV_MC_PhPy8EG_A14_ttbar_hdamp258p75_nonallhad_file_index.json"))

    def test_part_files(self):
        fl = list(range(10))
        parts = [mj.part_files(fl, p, 4) for p in range(4)]
        self.assertEqual(parts[0], [0, 4, 8])
        self.assertEqual(sorted(sum(parts, [])), fl)
        with self.assertRaises(ValueError):
            mj.part_files(fl, 4, 4)

    def test_urls(self):
        u = mj.https_urls("root://eospublic.cern.ch//eos/opendata/atlas/rucio/mc20_13TeV/F.root.1")
        self.assertEqual(u[0], "https://opendata.cern.ch/eos/opendata/atlas/rucio/mc20_13TeV/F.root.1")
        self.assertEqual(len(u), 2)
        self.assertEqual(mj.https_urls("file.root"), [])


class Keys(unittest.TestCase):
    TEXT = ("dsid,run,event,group,w,dphi,mllbb,short\n"
            "411234,284500,334982429,ph7,0.5,1.0,200.0,1\n"
            "411233,284500,334982429,ph7,0.5,1.0,200.0,1\n"
            "411234,284500,18446744073709551615,ph7,0.5,2.0,100.0,0\n"
            "411234,284500,334982429,ph7,0.5,1.0,200.0,1\n")

    def test_load_keys(self):
        keys, n_dsid, n_all = mj.load_keys(self.TEXT, 411234)
        self.assertEqual(keys, {334982429, 18446744073709551615})
        self.assertEqual((n_dsid, n_all), (3, 4))

    def test_negative_event_rejected(self):
        with self.assertRaises(ValueError):
            mj.load_keys("dsid,run,event,group\n410470,1,-5,nom\n", 410470)

    def test_gzip_roundtrip(self):
        raw = gzip.compress(self.TEXT.encode("utf-8"))
        keys, _, _ = mj.load_keys(gzip.decompress(raw).decode("utf-8"), 411233)
        self.assertEqual(keys, {334982429})


class Rows(unittest.TestCase):
    def test_entries_and_mass(self):
        ents = mj.entries_from_lists([6, -6], [1, 2], [62, 62], [0, 0], [0, 0], [0, 0],
                                     [172500, 172500])
        self.assertEqual(ents[0]["pdgId"], 6)
        self.assertAlmostEqual(mj.mtt_from_pair((ents[0], ents[1]), _inv_mass), 345.0, places=9)
        self.assertTrue(math.isnan(mj.mtt_from_pair(None, _inv_mass)))

    def test_csv_row(self):
        tr = {"n_t": 2, "n_tbar": 2, "mtt_l": 398.77931, "mtt_s": float("nan"), "st_t": 62,
              "st_tbar": 62, "s62": 1}
        r = mj.csv_row(410470, 334982429, 284500, 17, 123, tr)
        self.assertEqual(r, "410470,334982429,284500,17,123,2,2,398.7793,nan,62,62,1")
        self.assertEqual(len(r.split(",")), len(mj.CSV_HEADER.split(",")))

    def test_hashes(self):
        self.assertEqual(mj.git_blob_sha1(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")
        self.assertEqual(mj.sha256_hex(b"abc"), hashlib.sha256(b"abc").hexdigest())

    def test_raw_url_and_pin(self):
        self.assertTrue(mj.raw_url("a/b.gz").endswith("/ttbar-threshold-opendata/main/a/b.gz"))
        sha = "0123456789abcdef0123456789abcdef01234567"
        self.assertTrue(mj.raw_url("a/b.gz", sha).endswith("/ttbar-threshold-opendata/%s/a/b.gz"
                                                           % sha))
        with self.assertRaises(ValueError):
            mj.raw_url("a/b.gz", "0123abc")
        h = hashlib.sha256(b"x").hexdigest()
        self.assertTrue(mj.pin_ok(h, h.upper()))
        self.assertTrue(mj.pin_ok(h, "record"))
        self.assertFalse(mj.pin_ok(h, "0" * 64))

    def test_samples(self):
        self.assertEqual({k: v["dsid"] for k, v in mj.SAMPLES.items()},
                         {"nom": 410470, "ph7": 411234, "pth1": 601491})
        self.assertEqual({k: v["files"] for k, v in mj.SAMPLES.items()},
                         {"nom": 190, "ph7": 35, "pth1": 28})


@unittest.skipUnless(TS is not None, "tsplit_core.py not found next to the tests")
class WithCore(unittest.TestCase):
    def test_truth_row_largest_and_smallest(self):
        tr = mj.truth_row(EVENT, TS)
        self.assertEqual((tr["n_t"], tr["n_tbar"]), (2, 2))
        self.assertAlmostEqual(tr["mtt_l"], 2.0 * E100 * 0.001, places=6)
        self.assertAlmostEqual(tr["mtt_s"], 345.0, places=6)
        self.assertEqual((tr["st_t"], tr["st_tbar"], tr["s62"]), (62, 62, 1))

    def test_truth_row_tie_and_missing(self):
        tie = EVENT + [_ent(6, 10, 62, 0.0, 0.0, 0.0, 172500.0)]
        tr = mj.truth_row(tie, TS)
        self.assertTrue(math.isnan(tr["mtt_l"]))
        self.assertEqual((tr["st_t"], tr["s62"]), (-1, 0))
        tr2 = mj.truth_row([_ent(6, 1, 62, 0.0, 0.0, 0.0, 172500.0)], TS)
        self.assertEqual((tr2["n_t"], tr2["n_tbar"], tr2["s62"]), (1, 0, 0))
        self.assertTrue(math.isnan(tr2["mtt_s"]))


if __name__ == "__main__":
    unittest.main()
