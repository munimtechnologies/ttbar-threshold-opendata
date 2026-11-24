# ttbar-threshold-opendata

Does the excess of top-quark pairs with strongly correlated spins sit at the production
threshold, where "toponium" would put it, or is it spread over all masses? A pre-registered
test on the public ATLAS 2015-16 data (13 TeV, 36 fb-1, CERN Open Data record 93910, CC0).

**Result (2026-11-24, `RESULTS-v0.1.md`):** the public data reproduce the published excess of
lepton pairs close in azimuth (Z = 2.6). The excess per event is largest in the lowest-mass fifth
of the events and is there against all three top-pair generators, but the generators disagree
with each other at threshold by more than the excess itself, so whether it lives at threshold is
NOT RESOLVED (Z = 0.45). Gate PASS; H0b REPRODUCED; H1 WEAK; H2 NOT RESOLVED; H3 ROBUST.

* `PREREG-v0.1.md`: the question, selection, regions, statistic, gate, hypotheses and the
  predictions, all fixed before any data were read.
* `AMENDMENT-0.1.1.md`: adds the missing WW samples, written before any data were read.
* `RESULTS-v0.1.md`: the grades, the numbers behind them and post-hoc information.
* `results/ttthresh-v2/`: the graded job's raw outputs, unchanged, and `derive_v2.py`.
* `ttthresh_core.py`: numpy-only core (event variables, histograms, regions, statistic, verdicts).
* `ttthresh_job.py`: downloads the 2J2LMET30 skim and matching simulation from the CERN Open Data
  portal (adler32-checked), applies the eμ + b-tag selection and prints every graded number.
* `fix_ttthresh.py`: rebuilds the 0.1.1 files from the frozen 0.1.0 commit (blob-sha1 pinned).
* `test_ttthresh_core.py`, `test_fix_ttthresh.py`: unit tests (the selection tests need `awkward`).

Run: see `jobs/ttthresh-v2/job.json` (about 18.6 GB of downloads; 33 minutes on 2 CPUs).

Made by AI agents working for MV2 of Munim, Inc. (mv2@munimtech.com). No physicist has checked
this yet. Code Apache-2.0; text CC BY 4.0. ATLAS Open Data are CC0; this project is not
affiliated with or endorsed by the ATLAS Collaboration.
