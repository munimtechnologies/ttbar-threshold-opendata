# AMENDMENT 0.2.3 to PREREG-v0.2 (tsplit): how the grade job reads, checks and grades

MV2 of Munim, Inc. (mv2@munimtech.com). Written 2026-11-26, **before job A (`tsplit-keys-v1`) has
returned, before any match job was filed and before any PHYSLITE truth record was matched**. Made
with AI agents working in MV2's name; no human expert has checked it. Text CC BY 4.0, code
Apache-2.0. PREREG-v0.2's tests, bins, bands, gate thresholds and predictions are unchanged;
AMENDMENTS 0.2.1 and 0.2.2 are unchanged. This fixes what they left open for the grade step.

1. **Code and inputs.** `tsplit/grade/grade_job.py` 0.1.0. Every input is read at **one** full
   40-hex commit of this repository: `results/tsplit-keys-v1/{keys_T.csv.gz, keys_summary.json}`,
   `tsplit/tsplit_core.py` (pinned by the sha256 that job A recorded in `prep.txt`; version must be
   0.1.0) and, per part, `match_<group>_p<k>.{csv.gz,json}` from `results/tsplit-match-nom-p{0..3}-v1`,
   `results/tsplit-match-ph7-v1` and `results/tsplit-match-pth1-v1`. A part re-run after an outside
   read failure (AMENDMENT-0.2.2 s4) is read from its new folder instead; the folders used and the
   sha256 of every input are written to `results.json`. Bins, bands, the split, the bootstrap and
   every gate threshold come from tsplit_core.
2. **Consistency with job A (part of G0).** G0 passes only if job A's verdict is PASS with
   KEYS_XCHECK OK for all groups **and**: the number of rows in `keys_T.csv.gz` equals
   `rows_keys_T`; for each of nom, ph7, pth1 the (S, L) sums of its rows equal job A's `S_T`, `L_T`
   within 1e-6 relative; and job A's `bkg_T` equals pred_nom - tt_nom (recomputed from the rows and
   the ttthresh-v2 region-T prediction) within 1e-6 of the prediction total. **The bkg used in the
   split is job A's `bkg_T`**, the same for both samples (PREREG-v0.2).
3. **FILES (completeness, AMENDMENT-0.2.2 s4).** For `nom` and `ph7`: parts 0..n-1 all present, each
   written by match_job 0.1.0 for the right group, DSID, part count and file total, each reporting
   `failed_files` 0 and the same keys sha256 as the file the grade job reads (and the pinned
   tsplit_core sha256), and the union of their OK files is every file index exactly once. Failure
   makes H1 and H1r NOT GRADABLE. For `pth1` the same check only decides whether the information
   test is valid.
4. **Classification.** Within each sample, a row of `keys_T.csv.gz` is tested in this order and
   gets the first reason that applies, else it is *matched*: `not_read` (its DSID is not the
   PHYSLITE DSID of the sample, e.g. 411233, 601497); `edu_dup` (its (DSID, eventNumber) occurs more
   than once among the sample's region-T rows); `phys_missing` (no PHYSLITE row); `phys_dup` (more
   than one PHYSLITE row, across all parts); `no_pair` (the largest-barcode rule finds no +6/-6 pair,
   i.e. m(tt) is nan). Matched rows go to the truth m(tt) bin of `tsplit_core.mass_bin`; all others
   to `um`. Education-side duplicates are found among region-T rows only, because job A writes only
   those; job A's count of duplicates among all opposite-sign events is reported for information.
5. **Gates as computed.** G1: signed matched weight over signed selected weight of rows with the
   PHYSLITE DSID, >= 0.98 for 410470 and for 411234 (and for 601491 to make the pth1 information
   test valid). G2: for `nom`, matched rows with s62 = 1 over matched rows (event counts) >= 0.99;
   for `ph7`, distinct 411234 keys of region T with exactly one PHYSLITE row, counting those with
   at least one +6 and one -6 entry, >= 0.99. G3: `tsplit_core.gate_g3` on the um shares of the
   split. CLOSURE: |C + S - Delta| <= 1e-9. H1 and H1r are graded only if G0, FILES, G1, G2, G3 and
   CLOSURE all pass; otherwise NOT GRADABLE.
6. **Bootstrap.** `tsplit_core.bootstrap_rc` with 200 replicas and seed 20261125, the events of each
   sample in the order of `keys_T.csv.gz` (all rows of the sample, matched and um), bkg fixed.
   Replicas with Delta = 0 give no R_C; they are dropped and counted. The interval is
   `tsplit_core.percentile` at 16 and 84.
7. **Information only.** The pth1-vs-nom split (valid only if pth1 FILES and G1 pass and G0 passes);
   the split with the smallest-barcode rule (same matching, bin from the smallest-barcode m(tt), um
   if it is nan); S_lt380 / S; the single-lepton weight share of the region-T prediction for ph7
   (411233) and pth1 (601497); runNumber agreement of matched rows (equal, different, absent).
   The A values of the split are reported next to the ttthresh-v2 values for comparison.
8. **Order.** The grade job is filed only after all six match parts have returned and been
   committed. If any gate fails, the result is reported as NOT GRADABLE, with every number.
