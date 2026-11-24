# topo/ - toponium-shape prediction for the public-data spin excess (PREREG-TOPO v0.2)

Part of [ttbar-threshold-opendata](../README.md) by MV2 of Munim, Inc. Made with AI agents
working in MV2's name; no physicist has checked it yet. Code Apache-2.0, text CC BY 4.0.

Question: if a below-threshold top-pair component of the measured size (about 9 pb) with the
spin-singlet decay pattern is added to the SM, how much of the small-dphi excess measured on the
public ATLAS 2015-16 e-mu data (`results/ttthresh-v2/`) does it produce, region by region in
m(llbb)? The component comes from Pythia 8.318's Green's-function threshold model
(Sjostrand, Khoze and Preuss, arXiv:2605.19546; `TopThreshold:model = 3`).

* `PREREG-TOPO-v0.2.md` - question, model, regions, gate, hypotheses and predictions, fixed
  before any sample was generated.
* `toposhape_core.py` - numpy-only core (regions, asymmetries, mixing, verdicts).
* `toposhape_job.py` - Pythia driver and grading; prints `TOPO_` lines.
* `test_toposhape_core.py` - unit tests (run inside the job).
* `job.json` - the exact compete job.

Pythia is GPL-2.0-or-later and is installed from PyPI at run time (`pythia8mc`); it is not
redistributed here.
