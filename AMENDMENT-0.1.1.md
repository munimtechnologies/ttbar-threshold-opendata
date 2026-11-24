# AMENDMENT 0.1.1 to PREREG-v0.1 - the WW background was missing from the diboson rule

Munim, Inc. (MV2). Written 2026-11-24, **before any data or simulation was read**: job
ttthresh-v1 had not returned any output, and no file of CERN Open Data records 93934 or
93913 has been opened by this project. Made with AI agents working in MV2's name; no
physicist has checked it yet. Licence: text CC BY 4.0, code Apache-2.0.

## 1. What was wrong

A pre-run review compared the 0.1.0 sample rules (`ttthresh_job.py` RULES, quoted in
PREREG-v0.1 section 2) with the real file names in the CERN Open Data portal record 93913
(API read on 2026-11-24). Every ttbar, tW, Z->tautau and ttV dataset ID in the rules exists
with the expected key. The diboson rule

    _mc_7006\d\d\.Sh_221\d_(llll|lllv|llvv|lvvv)\.

needs a dot straight after `llvv`, but the release names the two-charged-lepton,
two-neutrino samples

    ODEO_FEB2025_v0_2J2LMET30_mc_700602.Sh_2212_llvv_os.2J2LMET30.root   (36,438,790 bytes)
    ODEO_FEB2025_v0_2J2LMET30_mc_700603.Sh_2212_llvv_ss.2J2LMET30.root   ( 8,620,328 bytes)

so 0.1.0 would have skipped them silently. 700602 contains WW -> e mu nu nu, the main
diboson background of an opposite-sign e-mu selection. The unit test of the rule only used an
`lllv` key, so it could not catch this. Other checks of the same review found no defect:
the data-file filter (`_data15_` / `_data16_` keys), momentum units (GeV in this release,
as the release's own HZZ notebook states), the normalisation (xsec x kfac x filteff x
mcWeight x scale factors x luminosity / sum_of_weights, as in the release's own notebook),
the binomial error of A, the region slicing and the overflow handling.

Expected size: WW with two jets and a b-tagged jet is of order 0.1 % of the selected e-mu
events, so the effect on A is expected to be small compared with the statistical error. It is
still a known missing background in a pre-registered prediction, so it is fixed before the run.

## 2. The change (ttthresh 0.1.1)

Only three things change; `ttthresh_core.py` (all statistics, regions, thresholds) and
PREREG-v0.1 sections 3-5 are unchanged:

1. diboson rule -> `_mc_7006\d\d\.Sh_221\d_(llll|lllv|llvv|llvv_os|llvv_ss|lvvv)\.`
   (adds 700602 and 700603; 700605 `vvvv` stays out because it has no charged leptons);
2. `ttthresh_job.py` VERSION 0.1.0 -> 0.1.1;
3. the unit test of the rule now includes an `llvv_os` key and a `vvvv` key, and a new test
   class checks all six diboson keys of the release.

The 0.1.1 files are not retyped. `fix_ttthresh.py` downloads the frozen 0.1.0 files from this
repository at commit 01d788aa635c97554afb42c0d465d2aebbdee83b, checks each one's git blob sha1
against the tree (any mismatch is fatal), applies each textual patch exactly once (fatal
otherwise), and prints the sha256 of every file before and after. Its own offline tests are
in `test_fix_ttthresh.py`.

## 3. Which run is graded

* Job **ttthresh-v2** (`jobs/ttthresh-v2/job.json`) supersedes ttthresh-v1 in the queue
  (same data_key, CPU and memory). Its 0.1.1 output is the **primary** result, graded by
  PREREG-v0.1 section 5 exactly as written.
* If ttthresh-v1 output exists anyway (for instance because it had already started), it is
  reported as the frozen 0.1.0 result, information only, next to the primary one. Any
  difference between the two is attributed to the WW samples and printed.
* Gate D0, the hypotheses H0b-H3, every threshold and every prediction (D0 PASS 75 %; H0b
  REPRODUCED 40 / WEAK 45 / NOT REPRODUCED 15 %; H1 EXCESS 35 / WEAK 45 / NOT SEEN 20 %; H2 AT
  THRESHOLD 30 / NOT RESOLVED 60 / HIGH MASS 10 %; H3 ROBUST 30 %) are unchanged.
* No new graded quantity. The TT_FILE lines of the job list 700602 and 700603 when they are
  read, and the diboson TT_SAMPLE totals include them; the hists.npz output keeps the diboson
  group separate, so the WW share can be shown in the write-up.
