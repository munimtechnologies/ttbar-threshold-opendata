# PREREG v0.2: why do Herwig and Pythia disagree about top spin at threshold? (pre-registration)

MV2 of Munim, Inc. (mv2@munimtech.com). Written 2026-11-25, after `results/truthprobe-v2` returned
FEASIBLE and **before any code for this test exists and before any matched truth number was seen**.
Made with AI agents working in MV2's name; no human expert has checked it. Text CC BY 4.0, code
Apache-2.0. This makes the plan in `SCOPING-v0.2.md` (run 214 update) binding, with the additions
below. PREREG-v0.1, AMENDMENT-0.1.1 and the ttthresh-v2 grades (`RESULTS-v0.1.md`) are unchanged.

## Question

ttthresh-v2 reproduced the 2019 ATLAS e-mu spin-correlation excess on public data (Z = 2.60), but
could not say whether it sits at the top-pair threshold (H2 NOT RESOLVED), because the two parton
showers disagree there: in region T the detector-level asymmetry is A_T = -0.02314 with
Powheg+Pythia8 (`nom`) and -0.04139 with Powheg+Herwig7 (`ph7`), a gap Delta = 0.01825, larger than
the excess itself. Is that gap **composition** (the showers put different true top-pair masses into
region T, e.g. through b-jet response) or **angular** (at the same true mass they give different
lepton angles, i.e. they disagree about spin correlations at threshold, where toponium acts)?
We found no published split of this generator difference by true top-pair mass (searches in
`SCOPING-v0.2.md`, closest work ATLAS arXiv:2509.15066, the TOP2025 threshold talk, arXiv:2605.02341).
The data side is already known; v0.2 uses simulation only and pre-specifies the method.

## Inputs (fixed)

- Event selection, per-event weights, Delta-phi, A and region T: exactly those of ttthresh-v2
  (`ttthresh_job.py`, `ttthresh_core.py`, `fix_ttthresh.py` at commit 01d788aa63, fetched pinned by
  git blob sha1), on the same 2025 education ntuples. Region T is the m(llbb) range recorded in
  `results/ttthresh-v2/results.json` (`regions.T`: 0-250 GeV). Only opposite-sign e-mu events of
  the top-pair samples are matched; the rest of the prediction enters as the bkg bin below.
- Truth side: ATLAS PHYSLITE in CERN Open Data. `nom` = DSID 410470, record 80017 (190 files).
  `ph7` = DSID 411234 (dilepton), record 80018 task 38191188 (35 files). `pth1` = DSID 601491
  (dilepton), record 80018 task 38312949 (28 files). The single-lepton DSIDs 411233 and 601497 are
  not read; their selected weight is reported as unmatched.
- Match key (mcChannelNumber, eventNumber); runNumber compared as a check and reported. A key that
  occurs more than once in the PHYSLITE files of its DSID, or more than once among selected
  education events, is dropped and counted, never resolved by choice.
- Top copy rule: for each event, the TruthTop entry with pdgId +6 and the largest barcode, and the
  same for -6. Truth m(tt) is the invariant mass of that pair (GeV).
- Truth m(tt) bins k: below 380, 380-450, 450-550, at least 550 GeV.

## Quantities

Read on 2026-11-25 while writing this (`results/ttthresh-v2/results.json`): the A_T values above
are those of the **full prediction** (`regions.T.pred.{nom,ph7}`: top pairs plus backgrounds plus
the same-sign term), not of the top-pair sample alone; `nom` and `ph7` differ only in the top-pair
sample. So the split runs over the full region-T prediction, with six exact bins k: the four truth
m(tt) bins (matched top-pair events), **um** (selected top-pair events not matched, including all
of 411233 in `ph7`) and **bkg** (everything else in the prediction, taken as
(S, L)_bkg = (S, L)_pred,nom - (S, L)_tt,nom in region T, identical for both samples). S and L are
the weighted counts with Delta-phi below and at or above pi/2, as in v0.1.

For each sample s: f_k^s = share of the region-T prediction in bin k; a_k^s = (S_k - L_k)/(S_k + L_k).
Then A^s = sum_k f_k^s a_k^s reproduces A_T^s, and Delta = A^nom - A^ph7 = 0.01825 splits exactly:
- composition part C = sum_k (f_k^nom - f_k^ph7) (a_k^nom + a_k^ph7) / 2
- angular part S = sum_k (f_k^nom + f_k^ph7) / 2 (a_k^nom - a_k^ph7) (bkg gives 0 here)
- C + S = Delta exactly (checked to 1e-9); R_C = C / Delta. C is also reported in three pieces:
  truth bins (mass migration), bkg (top-pair yield change) and um.
Uncertainty: 200 bootstrap replicas with Poisson(1) weights per top-pair event (numpy default_rng
seed 20261125), applied to both samples independently, bkg held fixed; 68 % interval = 16th-84th
percentile of R_C.

## Gates (any failure -> H1 NOT GRADABLE, reported as such)

- **G0 closure**: before matching, the job's own top-pair numbers agree with ttthresh-v2: the
  inclusive opposite-sign `nom` top-pair yield with `yields.ttbar_nom_os` (88,766.36) within 0.1 %;
  in region T, (S_tt,ph7 - S_tt,nom) with (S_pred,ph7 - S_pred,nom) = -993.26 and the same for L
  (-707.86), each within 2 %; and (S, L)_bkg both >= 0.
- **G1 match**: matched weight / selected weight in region T >= 0.98 separately for DSIDs 410470,
  411234 and 601491 (601491 only gates the information test below).
- **G2 copy rule**: in matched `nom` events the largest-barcode top and antitop are also the
  status-62 copies in >= 0.99 of events; in `ph7` a +6 and a -6 entry exist in >= 0.99 of events.
- **G3 um share**: the um bin holds <= 5 % of the region-T prediction in `nom` and in `ph7`.

## Tests

- **H1 (main)**: R_C >= 0.7 **COMPOSITION**; 0.3 <= R_C < 0.7 **MIXED**; R_C < 0.3 **ANGULAR**
  (R_C above 1 or below 0 counts as COMPOSITION or ANGULAR respectively, and is reported).
- **H1r**: the 68 % interval lies inside one band -> RESOLVED, otherwise NOT RESOLVED.
- Information only, not graded: the same split for `pth1` vs `nom`; all f_k, a_k per sample; the
  share of S from the bin below 380 GeV; R_C with the smallest-barcode copy rule; runNumber
  agreement; the unmatched single-lepton weight share for `ph7` and `pth1`.

## What each outcome means (fixed now)

- COMPOSITION: the spread that hid the location of the excess is mostly a mass-migration effect, and
  a truth-mass-level comparison can see through it.
- ANGULAR: the two showers really disagree about the lepton angles at the same true mass, so the
  open data cannot place the excess without a threshold (toponium) model.
- MIXED: both matter; the numbers are reported per bin.
None of these says whether toponium exists; that is PREREG-TOPO-v0.2's question.

## Predictions (written before any code)

G0 PASS 75 % (the main risk: if ttthresh-v2's same-sign term differs between `nom` and `ph7`, the
region-T differences will not close); G1 PASS 75 %; G2 PASS 70 %; G3 PASS 85 %. H1: COMPOSITION 30 %, MIXED 40 %,
ANGULAR 30 % (as in SCOPING). H1r RESOLVED 40 %.

## Plan

Code (`tsplit/`, with unit tests for the split identity, bootstrap, copy rule and duplicate rule)
and jobs come next, before any truth data are read: one job writes the selected education keys,
weights, Delta-phi and region flags (committed); then PHYSLITE match jobs (about 34 GB of branches
streamed in total, split into parts under 2 GB of memory each) fetch the keys pinned. Any
implementation detail not fixed here goes into an amendment before the match jobs run.
