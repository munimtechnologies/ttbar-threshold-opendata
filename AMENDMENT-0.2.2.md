# AMENDMENT 0.2.2 to PREREG-v0.2 (tsplit): how the PHYSLITE match jobs read truth

MV2 of Munim, Inc. (mv2@munimtech.com). Written 2026-11-26, **before job A (`tsplit-keys-v1`) has
returned, before any match job exists in the queue and before any PHYSLITE truth record was
matched**. Made with AI agents working in MV2's name; no human expert has checked it. Text CC BY 4.0,
code Apache-2.0. PREREG-v0.2's tests, gates, bins, bands and predictions are unchanged;
AMENDMENT-0.2.1 is unchanged. This fixes what PREREG-v0.2 left open for the match step.

1. **Files.** Read from the CERN Open Data records on 2026-11-26. `nom` (DSID 410470): record 80017,
   index `mc20_13TeV_MC_PhPy8EG_A14_ttbar_hdamp258p75_nonallhad_file_index.json`, 190 files.
   `ph7` (411234): record 80018, index `..._PowhegHerwig7EvtGen_tt_hdamp258p75_713_dil_file_index.json`,
   35 files (task 38191188). `pth1` (601491): record 80018, index
   `..._PhPy8EG_A14_ttbar_pThard1_dil_file_index.json`, 28 files (task 38312949). A job whose file
   count differs stops (exit 6) without reading any event. Files are sorted by uri and split
   round-robin into parts (part p takes files p, p + n, ...); `nom` runs in 4 parts, `ph7` and
   `pth1` in 1 each. Files are streamed over HTTPS (opendata.cern.ch, then eospublic:8444).
2. **Code.** `tsplit/match/match_job.py` 0.1.0. It fetches `tsplit/tsplit_core.py` from the
   repository and pins it by the sha256 that job A recorded in `prep.txt`. It fetches
   `results/tsplit-keys-v1/keys_T.csv.gz` at a fixed 40-hex commit (so the content cannot change)
   and either checks a known sha256 or, if none is available, records it; the grade job then
   requires every part to report the same keys sha256, equal to the one it reads itself.
   The copy rule (`pick_tops`, largest barcode), the information-only smallest-barcode rule, the G2
   status-62 helper and the mass formula (`inv_mass` on (px, py, pz, E), MeV converted to GeV) all
   come from tsplit_core; nothing is retyped.
3. **What is read and written.** Branches `EventInfoAuxDyn.eventNumber`, `.mcChannelNumber`, a
   `runNumber` branch of EventInfo if one exists (else -1), and `TruthTopAuxDyn.{pdgId, barcode,
   status, px, py, pz, e}`. An event is kept if its mcChannelNumber equals the sample's DSID and its
   eventNumber is a region-T key of that DSID. **Every occurrence** is written (one row each), so
   the grade job can apply the duplicate rule across all parts. Events of another mcChannelNumber
   in a file are counted and reported.
4. **Read failures.** A file is retried 3 times; rows of a file are written only after the whole
   file was read. If any file still fails, the job exits 7 with the other files' rows kept; that
   part is then re-run unchanged under the next version (an outside failure, not a code change).
   The grade job requires every file of a sample read exactly once; otherwise H1 is NOT GRADABLE.
5. **Matched, um and duplicates (fixed now).** A selected region-T event is *matched* if its key
   occurs exactly once among the selected education events and exactly once in the PHYSLITE files
   of its DSID, **and** the largest-barcode rule finds a +6 and a -6 entry. Every other selected
   top-pair event (no PHYSLITE occurrence, duplicate on either side, or no top pair under the rule)
   goes to the `um` bin with its weight and counts as unmatched for G1. Counts for each reason are
   reported.
6. **Gates as computed.** G1: matched weight over selected weight in region T, per DSID 410470,
   411234, 601491 (weights from `keys_T.csv.gz`). G2 for `nom`: among matched 410470 events, the
   fraction (event count, unweighted) with `s62` = 1; for `ph7`: among 411234 events found in
   PHYSLITE exactly once, the fraction with at least one +6 and one -6 entry. G3 and the split are
   computed by tsplit_core as PREREG-v0.2 says. runNumber agreement is reported for information.
7. **Order.** Match jobs are filed only after `tsplit-keys-v1` returns with KEYS_XCHECK OK and its
   outputs are committed. If G0 fails, the match jobs are not run (H1 NOT GRADABLE).
