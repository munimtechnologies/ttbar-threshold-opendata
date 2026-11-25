# Scoping note for a possible v0.2 (not a pre-registration)

MV2 of Munim, Inc. (mv2@munimtech.com). Written 2026-11-24 with AI agents working in his name. Apache-2.0 / text CC BY 4.0.

## Why
ttthresh-v2 (see `RESULTS-v0.1.md`) reproduced the 2019 ATLAS e-mu spin-correlation excess on the
public 2015-16 data (dA = +0.0132, Z = 2.60) and found it largest in the threshold region, but
the generator spread at threshold (Powheg+Herwig7 vs Powheg+Pythia8, 0.018) is larger than the
excess there (0.017). The question a v0.2 could answer: **how much of the 2019 excess remains
once a toponium / Green's-function threshold component of the measured size is added to the
prediction?**

As of 2026-11-24 we found no published number for this:
- H. Baer, V. Barger, arXiv:2611.22421 (review) say the 2019 excess "is not concentrated near
  threshold", without a refit.
- J. A. Aguilar-Saavedra, "Toponium Hunter's Guide", arXiv:2407.20330, states that the dphi
  mismodelling cannot be attributed to the toponium contribution because it is present far above
  threshold (our paraphrase).
- B. Fuks, K. Hagiwara, K. Ma, Y.-J. Zheng, arXiv:2102.11281, argue the opposite direction for
  small dphi and small mass.
- ATLAS e-mu lepton-kinematics GFRW fit (7.8 +- 2.4 pb, >3 sigma; cited in 2611.22421) uses
  collaboration data and tools, not the open release, and does not report a residual f_SM.

## Blocker found today
The 2025 education ntuples used by ttthresh-v2 carry no truth-top branches (only truth electrons,
muons, photons, taus, jets and MET; opendata.atlas.cern/docs/data/for_education/13TeV25_details,
read 2026-11-24). Standard PHYSLITE has a `TruthTop` container (coffea PHYSLITESchema lists it).
`probes/truthprobe-v1/` checks, on one file of the open PHYSLITE nominal ttbar sample (DSID
410472), whether `TruthTop` kinematics can be read, give a truth m(tt) per event, and carry
`eventNumber` for matching. Its verdict decides whether a v0.2 pre-registration is worth writing.
It is a feasibility probe only; nothing in it is graded.

## Update 2026-11-25: probe v1 returned NO_RECORD (probe defect); v2 queued
truthprobe-v1 found no record because the paragraph above names the wrong sample: the nominal
sample behind ttthresh-v2 is DSID **410470** (`PhPy8EG_A14_ttbar_hdamp258p75_nonallhad`), not
410472, and the portal's search does not index DSIDs. The sample is in
[CERN Open Data record 80017](https://opendata.cern.ch/record/80017) (190 PHYSLITE files,
478.6 GB). See `results/truthprobe-v1/NOTE.md`. `probes/truthprobe-v2/` (truthprobe 0.2.0) reads
that record directly. Its verdict still decides whether a v0.2 pre-registration gets written.

## Update 2026-11-25 (later): the education side of the match exists
The branch table of the 2025 education release
([13TeV25_details](https://opendata.atlas.cern/docs/data/for_education/13TeV25_details), read
2026-11-25 03:30 UTC) lists `runNumber` (unsigned int), `eventNumber` (unsigned long long) and
`channelNumber` (unsigned int, the DSID) for every event, plus truth electrons, muons, photons,
taus, jets and MET, and still no parton-level or top-quark truth branch. The page describes the
education samples as a simplified form of the 2024 open data for research. So a per-event match
education -> PHYSLITE is possible in principle on the key (channelNumber, eventNumber); whether
it works in practice (every selected education event found exactly once in record 80017) is not
known until it is tried. Things a v0.2 pre-registration must fix in advance if truthprobe-v2 says
FEASIBLE:
- match key (channelNumber, eventNumber), with runNumber kept as a check; duplicate keys inside
  record 80017 are counted and such events dropped, never resolved by choice;
- a gate on the match rate of the ttthresh-v2-selected nominal events (a value fixed before the
  match is run), because an education event missing from the research release would bias the
  truth split;
- the truth m(tt) bins (one bin at and below threshold, fixed before any truth number is seen by
  this project beyond truthprobe-v2's quantiles from 3,000 unselected events);
- that the data side is already known (ttthresh-v2), so v0.2 can only pre-specify the method that
  turns the known detector-level excess into a truth-mass split, and must say so.
No job or pre-registration was filed for this today.

## Update 2026-11-25 (run 214): the two alternative generators are in the research release too
What blocked H2 of v0.1 is the disagreement between generators at threshold, not the number of
events. The research release has the same alternative samples that ttthresh-v2 used from the
education release, so the disagreement itself can be studied at truth level. From the CERN Open
Data API (read 2026-11-25 05:20-05:35 UTC):

| ttthresh-v2 key | education DSIDs (`results/ttthresh-v2/files.csv`) | research PHYSLITE sample (record) | files | size |
|---|---|---|---|---|
| `nom` | 410470 nonallhad | `PhPy8EG_A14_ttbar_hdamp258p75_nonallhad` ([80017](https://opendata.cern.ch/record/80017), tasks 37620644/37620646) | 190 | 478.6 GB |
| `ph7` | 411234 dil (+ 411233 SingleLep) | `PowhegHerwig7EvtGen_tt_hdamp258p75_713_dil` ([80018](https://opendata.cern.ch/record/80018), task 38191188); SingleLep task 38312903 | 35 (+75) | 46.8 GB (+97.3 GB) |
| `pth1` | 601491 dil (+ 601497 singlelep) | `PhPy8EG_A14_ttbar_pThard1_dil` (80018, task 38312949); singlelep tasks 38312960/38312962 | 28 (+155) | 80.4 GB (+345.4 GB) |

Record 80018 is "ATLAS DAOD_PHYSLITE format MC simulation top systematic variation samples"
(631 files, 85.3 M events, 1.22 TB, DOI 10.7483/OPENDATA.ATLAS.F7P0.VAST, CC0); record 80017 is
the "top nominal samples" (437 files, 63.5 M events), with no dilepton-only nominal sample. Both
are children of record 80020. Record 80018 also holds tW DS and tW pThard1 variations and
Herwig 7 single-top samples. In the education files the single-lepton parts are small (23.7 MB of
346.5 MB for `ph7`, 89.1 MB of 621.9 MB for `pth1`, before the e-mu selection), so a first match
could read the dilepton samples only and report the single-lepton weight share as unmatched.

**What this makes possible (draft, nothing filed, no truth number seen yet).** In region T
(m(llbb) < 250 GeV, the ttthresh-v2 selection) the detector-level asymmetry is A_T = -0.02314
(`nom`) and -0.04139 (`ph7`): a gap of Delta = 0.01825. With truth m(tt) attached to every
selected simulated event, write A_T = sum_k f_k a_k over truth-mass bins k, where f_k is the
weighted share of region-T events in bin k and a_k is the asymmetry of those events. The gap
then splits exactly into a **composition part** C = sum_k (f_k^nom - f_k^ph7) (a_k^nom + a_k^ph7)/2
(the generators put different truth masses into region T, e.g. through different b-jet response)
and an **angular part** S = sum_k (f_k^nom + f_k^ph7)/2 (a_k^nom - a_k^ph7) (the generators give
different lepton angles at the same truth mass), with C + S = Delta. Proposed now, before any
truth number: truth m(tt) bins below 380, 380-450, 450-550 and at least 550 GeV; bands for
R_C = C / Delta of COMPOSITION (at least 0.7), MIXED (0.3 to 0.7) and ANGULAR (below 0.3), with
our prior 30 / 40 / 30. Why it matters: if the gap is mostly composition, the spread that hid
the threshold location is a mass-migration effect that a truth-level comparison can see through;
if it is mostly angular, the generators genuinely disagree about spin correlations at threshold,
which is exactly where toponium would act, and the open data cannot place the excess without a
threshold model. Either answer is new: we found no published decomposition of the
Herwig-Pythia difference in the dilepton azimuthal angle by truth top-pair mass.

Closest published work (web search 2026-11-25 05:40 UTC, "Powheg Herwig7 vs Pythia8 dilepton
delta phi ... ttbar invariant mass dependence"):
- ATLAS, [arXiv:2509.15066](https://arxiv.org/abs/2509.15066) (EPJC 2026): the e-mu Delta-phi
  measured in bins of the **lepton-pair** mass m(e-mu); Powheg+Herwig7.1 describes the double-
  differential distribution worst of the generators compared (its Table 8: chi2/Ndof 150.8/39
  for Powheg+Herwig 7.1.3, against 79.9/39 for Powheg+Pythia8 and 50.2/39 for Powheg
  MiNNLO+Pythia8; read in the arXiv HTML 2026-11-25), and it says the double-differential result
  "suggests that the slope between data and predictions increases with m^emu". It compares
  generators to data; it does not split the generator difference by truth top-pair mass, and it
  uses collaboration tools.
- ATLAS threshold talk at TOP2025
  ([slides](https://indico.cern.ch/event/1501204/contributions/6561398/attachments/3142580/5577953/Top25_ATLAS_threshold.pdf)):
  results shown separately with Powheg+Herwig7 and Powheg+Pythia8 in particle-level m(tt) bins
  below 380, 380-500 and above 500 GeV. Our proposed lowest bin edge (380 GeV) matches theirs, so
  numbers can be compared.
- ATLAS, [arXiv:2605.02341](https://arxiv.org/abs/2605.02341): Herwig7 vs Pythia8 is one of the
  uncertainties on the quasi-bound-state contribution in e-mu lepton kinematics.
Context, not used for any grade: since data disfavour Powheg+Herwig7 in Delta-phi x m(e-mu)
(2509.15066), and Herwig is the generator against which ttthresh-v2 saw the largest threshold
excess (dA = 0.0352), the decomposition also tells whether the two-point spread that made H2
NOT RESOLVED is driven by a set-up the data already disfavour. v0.1's grades stand unchanged.

These numbers become binding only in a PREREG-v0.2, written if truthprobe-v2 returns FEASIBLE
and frozen before the match job runs; the match rate gate (at least 0.98 of the selected,
weighted events of each dilepton sample) and the duplicate rule above would be in it.
