# PREREG-TOPO v0.2 - How much of the public-data top spin excess would toponium of the measured size explain?

Munim, Inc. (MV2). Written 2026-11-24, before any Pythia sample for this question was generated
or looked at. Made with AI agents working in MV2's name; no physicist has checked it yet.
Licence: text CC BY 4.0, code Apache-2.0. Follows PREREG-v0.1 and its graded results
(RESULTS-v0.1.md, results/ttthresh-v2/results.json).

## 1. Question

ttthresh-v2 reproduced, on the public ATLAS 2015-16 e-mu data, the excess of lepton pairs close in
azimuth (inclusive dA = +0.0132, Z = 2.60), largest in the lowest-m(llbb) fifth (dA_T = +0.0170)
but with a generator spread there larger than the excess. Since 2025 ATLAS and CMS have measured a
threshold excess of about 9 pb (ATLAS dilepton, Green's-function model: 9.3 pb; eta_t model:
13.1 pb; CMS dilepton 8.8 pb; as summarised in arXiv:2611.22421). Fuks et al. (arXiv:2102.11281)
argued that toponium would sit at small dphi and small mass and "possibly" explain the 2019
excess; arXiv:2407.20330 argued that the dphi mismodelling "cannot be attributed to the toponium
contribution, since it is present far above threshold"; Baer and Barger (arXiv:2611.22421) state
that the excess "is not concentrated near threshold". We found no published number for the share
of the excess that a threshold component **of the measured size** produces, nor any such number
in mass-binned regions of the public data.

**Question: if a below-threshold top-pair component with the measured cross-section and the
spin-singlet decay pattern is added to the SM prediction, how much of the measured dA does it
produce in each ttthresh region (inclusive, T, C, B1-B4), and how much remains?**

The wow, if it comes out one way: a public-data statement that toponium of the measured size
explains most of the decade-old spin excess, or that it cannot, settling a disagreement in the
literature with numbers instead of assertions.

## 2. Component model (fixed)

Pythia 8.318.3 (`pythia8mc==8.318.3`), pp at 13 TeV, `Top:gg2ttbar` and `Top:qqbar2ttbar`,
m_t = 172.5 GeV, Gamma_t = 1.34 GeV (`6:doForceWidth = true`), both W forced to e or mu
(`24:onIfAny = 11 13`), ISR on, FSR, MPI and hadronisation off (as in Pythia's own example
main371). Green's-function threshold model of Sjostrand, Khoze and Preuss (arXiv:2605.19546):
`TopThreshold:model = 3`, `tWidthGreen = 0.1`, `thrRegion = 10`, `alphasOrder = 2`,
`alphasValue = 0.118`, `ggSingletFrac = 0.285714` (2/7), `qqSingletFrac = 0`, `massSel = 0`,
pseudoscalar decay correlations on with `psEBeginDamp = 10`, `psEEndDamp = 20`.

Samples (300,000 events each; seeds fixed in `toposhape_job.py`):
* `born`: model 0, no pseudoscalar correlations, all masses (defines the regions and acc_SM);
* `thr3ps`: model 3 + pseudoscalar, PhaseSpace mHat 250-400 GeV (the component);
* `thr1`: model 1 (Coulomb only), same window (fallback, sec. 3);
* `thr3`: model 3 without pseudoscalar, same window (information only: spin effect).

**Component C (primary)**: events of `thr3ps` with original threshold energy
`info.toponiumE < 0` (below threshold), with weights `info.weight()`.
**Fallback (only if `toponiumE` is not readable from Python)**: C = `thr3ps` minus `thr1`, per
region, in cross-section units (sigmaGen / sum of weights).

## 3. Selection and regions (fixed)

Parton level after ISR: exactly one electron and one muon from W decays of the tops, opposite
charge, pT > 25 GeV, |eta| < 2.5, electrons outside 1.37 < |eta| < 1.52, one lepton above 27 GeV,
m(ll) > 15 GeV; both b quarks from the top decays with pT > 25 GeV and |eta| < 2.5.
m(llbb) from the two leptons and the two b quarks; dphi(l,l) in [0, pi].
Regions: the same quantile scheme as ttthresh_core 0.1.0 (5 GeV bins; T = lowest 20 %, C = upper
50 %, B1-B4 at 20/40/70 %), applied to the `born` sample's parton-level m(llbb). Regions are
matched to the measured regions **by quantile, not by GeV** (parton-level m(llbb) is not
detector-level m(llbb)).

## 4. Prediction (fixed)

In each region: acc_SM = passing `born` weight in the region / all `born` weight; acc_C = passing
component weight in the region / all component weight; A_C = asymmetry of the passing component;
A_SM = the ATLAS **nominal prediction** A of that region from ttthresh-v2 (detector level,
Powheg+Pythia8 with NLO spin correlation; frozen in `toposhape_core.MEASURED`, re-checked
against the committed results.json to 1e-12 by the job).
f = sigma_C acc_C / (sigma_SM acc_SM + sigma_C acc_C), sigma_SM = 832 pb (NNLO+NNLL, m_t = 172.5),
**dA_pred = f (A_C - A_SM)**. Primary sigma_C = **9.3 pb**; scan 4.0, 6.5, 9.3, 13.1 pb
(information). Forced decays cancel in every acceptance ratio. Information only: the same
prediction with A_SM from the uncorrelated Pythia `born` sample.

## 5. Gate, hypotheses and our predictions (fixed before any sample)

* **Gate G0**: pythia8mc 8.318.x; every setting accepted and `TopThreshold:model` read back;
  r_C = sigma(C) / sigma(born) (same forced decays) in [0.004, 0.016] (the paper's Table 1 gives
  4.41 / 516.26 = 0.0085); >= 50,000 passing `born` events; primary mode: >= 1,000 passing
  component events; fallback mode: relative error of the inclusive difference yield <= 0.25.
  Otherwise every verdict is NOT GRADABLE and a fix needs a written amendment. Prediction: PASS 70 %.
* **H1 (share of the inclusive excess)**: R_incl = dA_pred(incl) / 0.013155. R >= 0.7 EXPLAINS
  MOST; 0.3 <= R < 0.7 EXPLAINS PART; R < 0.3 EXPLAINS LITTLE.
  Prediction: MOST 25 %, PART 50 %, LITTLE 25 %.
* **H2 (does the inclusive excess survive?)**: Z_res = (0.013155 - dA_pred(incl)) / 0.005067
  (the measured total error). Z_res >= 2 SURVIVES; 0 < Z_res < 2 REDUCED; <= 0 ABSORBED.
  Prediction: SURVIVES 20 %, REDUCED 60 %, ABSORBED 20 %.
* **H3 (high-mass part)**: dA_pred(C) < 0.3 x 0.007328 HIGH-MASS EXCESS NOT FROM THRESHOLD; else
  THRESHOLD COMPONENT REACHES HIGH MASS. Prediction: NOT FROM THRESHOLD 80 %. (The measured C
  excess is itself only Z = 1.30.)
* **H4 (share of the threshold-region excess)**: R_T = dA_pred(T) / 0.016983, same bands as H1.
  Prediction: MOST 45 %, PART 40 %, LITTLE 15 %.

Information only: per-region dA_pred for every sigma_C in the scan; B1-B4; A_C without
pseudoscalar correlations (spin effect); the prediction with the Pythia Born reference.

## 6. Honest limits, stated in advance

* Parton level with ISR only, LO Pythia: no b-jet response, no FSR, no neutrino-related
  smearing; region matching by quantile is approximate. The lepton angle itself is measured well.
* The component definition (E < 0) is the bound-state-like part of one model; ATLAS's 9.3 pb
  is defined with its own GFRW model and relative to NLO pQCD, which already contains part of the
  above-threshold Coulomb effect. The scan shows how the answer scales with sigma_C.
* A_SM is a detector-level number and A_C a parton-level one; their difference carries this
  mismatch. The information-only Pythia-Born variant shows its size.
* dA_pred is a model prediction, not a fit; nothing is fitted to the data.

## 7. Execution

Job `toposhape-v1` (compete lane, python:3.12, numpy + pythia8mc 8.318.3, 2 CPU, 2 GB): unit
tests, sha256 and versions, a short `--probe` run of every sample (stops the job if a setting is
rejected), then the full run. Graded numbers are printed on lines starting `TOPO_`. Results will
be committed unchanged with a RESULTS-TOPO file grading each hypothesis by the rules above,
including any prediction that fails.
