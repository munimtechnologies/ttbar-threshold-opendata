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
