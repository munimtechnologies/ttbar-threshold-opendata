# RESULTS v0.1 - graded run ttthresh-v2 (ttthresh 0.1.1)

Munim, Inc. (MV2). Graded 2026-11-24 by the rules of `PREREG-v0.1.md` section 5 as amended by
`AMENDMENT-0.1.1.md` (WW samples added before any data were read). Made with AI agents working in
MV2's name; no physicist has checked this yet. Text CC BY 4.0, code Apache-2.0. Not affiliated
with or endorsed by the ATLAS Collaboration.

Raw outputs, unchanged: `results/ttthresh-v2/` (`run.txt` with every `TT_` line, `results.json`,
`dphi_by_region.csv`, `files.csv`, `tests.txt` (21 unit tests OK), `fix_tests.txt` (7 tests OK),
`fix.txt` (all five frozen 0.1.0 files matched their git blob sha1 at commit 01d788a), `sha256.txt`,
`compile.txt`, `job.json`). Job ran on 2026-11-24 06:01-06:41 UTC, 1,996 s, peak 1.1 GB.
ttthresh-v1 (0.1.0) produced no output; there is no 0.1.0 result to report.

## Sample

* Data: 16 files of record 93934 (2015+2016, 36 fb-1), 6,242,521 events read, 98,895 opposite-sign
  (OS) e-mu events selected, 571 same-sign.
* Nominal prediction 93,576 events, of which ttbar 88,766 (94.9 %). Data / prediction = 1.057.
  The WW samples added by amendment 0.1.1 (700602, 700603) were read; the whole diboson group
  contributes 89.5 OS events (0.1 %), as expected.
* m(llbb) regions from quantiles of the nominal prediction: T (threshold) = [0, 250) GeV;
  C (control) = [335, inf) GeV; information bins B1 [0, 250), B2 [250, 305), B3 [305, 410),
  B4 [410, inf).

## Grades

A = (N[dphi < pi/2] - N[dphi >= pi/2]) / N; dA = A_data - A_nominal. Positive dA means more
lepton pairs close in azimuth than predicted, the direction of the 2019 ATLAS spin-correlation
excess (arXiv:1903.07570).

| Test | Rule | Number | Verdict | Our prior |
|---|---|---|---|---|
| Gate D0 | data/pred in [0.85, 1.15], ttbar frac >= 0.80, >= 20,000 events | 1.057, 0.949, 98,895 | **PASS** | PASS 75 % |
| H0b reproduce | Z_incl >= 2 | dA = +0.0132, Z = 2.60 | **REPRODUCED** | 40 % |
| H1 threshold excess | Z_T >= 2 | dA_T = +0.0170, sigma 0.0201, Z = 0.85 | **WEAK** | 45 % |
| H2 where | Z_dd >= 1.5 or <= -1.5 | dd = +0.0097, sigma 0.0213, Z = 0.45 | **NOT RESOLVED** | 60 % |
| H3 generators | dA_T > 0 and stat-only Z >= 2 for all three ttbar set-ups | Z_stat 2.02 / 3.69 / 2.29 | **ROBUST** | 30 % |

Region details (from `results.json`):

| Region | A_data | A_nom | dA | s_data | sig_gen | sig_tW | Z |
|---|---|---|---|---|---|---|---|
| T  [0,250)   | -0.0062 | -0.0231 | +0.0170 | 0.0068 | 0.0182 | 0.0006 | 0.85 |
| C  [335,inf) | -0.4576 | -0.4649 | +0.0073 | 0.0041 | 0.0019 | 0.0017 | 1.30 |
| incl         | -0.2871 | -0.3003 | +0.0132 | 0.0030 | 0.0034 | 0.0003 | 2.60 |
| B2 [250,305) | -0.1869 | -0.1897 | +0.0028 | 0.0069 | 0.0077 | 0.0003 | 0.24 |
| B3 [305,410) | -0.3635 | -0.3692 | +0.0057 | 0.0055 | 0.0039 | 0.0006 | 0.72 |
| B4 [410,inf) | -0.4991 | -0.5048 | +0.0057 | 0.0051 | 0.0043 | 0.0027 | 0.70 |

Threshold region T against each ttbar generator: Powheg+Pythia8 nominal dA = +0.0170;
Powheg+Herwig7 dA = +0.0352; Powheg+Pythia8 pThard=1 dA = +0.0196; nominal with tW DS dA = +0.0176.

## What the grades say

1. The public 2015-16 ATLAS e-mu events reproduce the direction and rough size of the published
   spin-correlation excess: more lepton pairs at small azimuthal separation than Powheg+Pythia8
   predicts, at 2.6 sigma including our generator and tW envelopes.
2. In the lowest-mass fifth of the events (T), the excess per event is the largest of the four
   mass bins (+0.017, three to six times the +0.003 to +0.006 of the other bins) and it is positive
   against every generator set-up, at 2.0 to 3.7 sigma statistically (H3 ROBUST).
3. But the three generators disagree with each other at threshold by more than the excess itself:
   Herwig7 predicts A_T lower by 0.018 than Pythia8. With that spread counted as an uncertainty,
   the threshold excess is only 0.85 sigma (H1 WEAK), and the difference between threshold and
   high mass is 0.45 sigma (H2 NOT RESOLVED). At detector level, with these public samples, the
   toponium question cannot be decided; the limit is generator modelling at threshold, not the
   number of events.

Predictions: D0, H1 and H2 came out as our most likely outcome; H0b REPRODUCED (prior 40 %) and
H3 ROBUST (prior 30 %) came out stronger than we expected.

## Information only (post hoc, not graded)

Computed after the grades by `results/ttthresh-v2/derive_v2.py` from `results.json`; the values in
`results/ttthresh-v2/derived_v2.csv` were first computed by hand and were re-checked by the
machine job `ttderive-v1` on 2026-11-27: the machine output matches the hand CSV in every cell
(`DERIVE_CHECK MATCH`; outputs and note in `results/ttderive-v1/`).

* Yield shape: data/prediction is 1.116 in B1, 1.065 in B2, 1.044 in B3 and 1.022 in B4; after
  removing the overall 1.057 normalisation, data have 5.6 % more events than predicted in the
  lowest-mass bin and 3.3 % fewer in the highest. This softer spectrum is the known direction of
  top-pT mismodelling in NLO+shower simulation; toponium would push the same way, and this test
  cannot tell them apart.
* Split of the inclusive excess: dA_incl = +0.01316 = +0.00756 (Delta-phi shape inside the four
  mass bins) + 0.00559 (data having relatively more low-m(llbb) events, where A is naturally
  higher). So about 43 % of the inclusive excess in this selection comes from the mass spectrum,
  not from the angular distribution at fixed mass. With only four mass bins this split is coarse.

## Limits

Detector-level shape test; m(llbb) is a coarse stand-in for m(tt); no toponium simulation in the
release; nominal scale factors only, no detector systematics; two-point generator envelopes are not
full modelling uncertainties; the selection is not ATLAS's 2019 selection.
