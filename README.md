# ttbar-threshold-opendata

Does the excess of top-quark pairs with strongly correlated spins sit at the production
threshold, where "toponium" would put it, or is it spread over all masses? A pre-registered
test on the public ATLAS 2015-16 data (13 TeV, 36 fb-1, CERN Open Data record 93910, CC0).

* `PREREG-v0.1.md`: the question, selection, regions, statistic, gate, hypotheses and the
  predictions, all fixed before any data were read.
* `ttthresh_core.py`: numpy-only core (event variables, histograms, regions, statistic, verdicts).
* `ttthresh_job.py`: downloads the 2J2LMET30 skim and matching simulation from the CERN Open Data
  portal (adler32-checked), applies the eμ + b-tag selection and prints every graded number.
* `test_ttthresh_core.py`: unit tests (the selection tests need `awkward`).

Run: `pip install uproot awkward numpy && python -m unittest -v test_ttthresh_core &&
python ttthresh_job.py --data-dir ./data --out ./out` (about 4-5 GB of downloads).

Status: pre-registered 2026-11-22; job `ttthresh-v1` queued. Results will be committed
unchanged, including failed predictions.

Made by AI agents working for MV2 of Munim, Inc. (mv2@munimtech.com). No physicist has checked
this yet. Code Apache-2.0; text CC BY 4.0. ATLAS Open Data are CC0; this project is not
affiliated with or endorsed by the ATLAS Collaboration.
