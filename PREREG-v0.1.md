# PREREG v0.1 - Where does the top-quark spin-correlation excess live? A pre-registered test on ATLAS public data

Munim, Inc. (MV2). Written 2026-11-22, before any data or simulation of this release was read
by this project. Made with AI agents working in MV2's name; no physicist has checked it yet.
Licence: text CC BY 4.0, code Apache-2.0.

## 1. Question and why it matters

In 2025 CMS (arXiv:2503.22382) and then ATLAS (ATLAS-CONF-2025-008, arXiv:2601.11780) observed an
excess of top-quark pairs right at the production threshold, about 1 % of selected dilepton
events, with the spin-singlet signature expected from quasi-bound "toponium". Before that,
ATLAS measured, in exactly the 2015-16 data released publicly in 2025 (36 fb-1), that the azimuthal
angle between the two charged leptons in eμ top-pair events shows a stronger spin correlation
than the NLO prediction (f_SM about 1.25; arXiv:1903.07570, Eur. Phys. J. C 80 (2020) 754).

Two recent readings disagree about whether that older excess is the toponium:
* Fuks et al. (as summarised in Baer and Barger, arXiv:2611.22421, Nov 2026): a toponium
  contribution "would be concentrated at small dilepton azimuthal separation and invariant
  mass, where ATLAS had reported an excess".
* Baer and Barger (same paper): "The excess is not concentrated near threshold, and one
  fixed-order NLO calculation is consistent with the data", "so it does not point to a threshold
  effect".

The 2015-16 ATLAS events and matching simulation are now public (CERN Open Data record 93910,
CC0). They include three top-pair generator set-ups, so we can ask, in public data and with
the selection fixed in advance: **does the small-Δφ excess sit at low m(llbb) (threshold) or is it
spread over all masses, and does it survive a change of top-pair generator?**

If it works, this would be the first look at the toponium question with public LHC data alone,
from outside the collaborations. A null or "not resolved" answer is also informative and
will be reported the same way.

## 2. Data and simulation (fixed)

* Data: record 93934, 2J2LMET30 skim of 2015+2016 collisions (16 files, 1,987,123,953 bytes,
  6,242,521 events), adler32 checksums from the portal API checked for every file.
* Simulation: record 93913 (same skim), files chosen by the key rules in `ttthresh_job.py` RULES:
  * ttbar nominal: 410470 Powheg+Pythia8 (hdamp 258.75, nonallhad);
  * ttbar alternative 1 "ph7": 411233 + 411234 Powheg+Herwig7.1.3 (single-lepton + dilepton);
  * ttbar alternative 2 "pth1": 601491 + 601497 Powheg+Pythia8 pThard=1 (dilepton + single-lepton);
  * tW nominal DR: 601352 + 601355; tW alternative DS: 601627 + 601631;
  * Z->tautau: 700792-700794 and 700901-700903 (Sherpa 2.2.14);
  * diboson: any key matching `_mc_7006\d\d\.Sh_221\d_(llll|lllv|llvv|lvvv)\.`;
  * ttV: 410155 and any key containing `_ttZ`, `_ttll`, `_ttee`, `_ttmumu`, `_tttautau`.
  A non-ttbar file above 3.5 GB is skipped and printed. No toponium simulation exists in the
  release; none is used.
* MC weight: mcWeight x ScaleFactor_{PILEUP, ELE, MUON, FTAG, JVT, LepTRIGGER} (those present)
  x xsec x kfac x filteff x 36,000 pb-1 / sum_of_weights (as in the release's own ttbar
  notebook; missing branches are printed and taken as 1).

## 3. Selection and variables (fixed)

3.1 Exactly two preselected leptons, both tight ID and tight isolation, pT > 25 GeV, electrons
outside 1.37 < |η| < 1.52; one electron and one muon; trigE or trigM fired and at least one
trigger-matched lepton with pT > 27 GeV; m(ll) > 15 GeV.
3.2 Jets: pT > 25 GeV, |η| < 2.5; at least two, at least one with jet_btag_quantile >= 4 (the
release's own ttbar-example cut). The two jets used are the two with the highest b-tag
quantile (ties: higher pT).
3.3 Opposite-sign (OS) events form the signal sample; same-sign (SS) events give a residual
non-prompt term.
3.4 Prediction(OS) = ttbar + tW + Z->tautau + diboson + ttV + (data SS - all nominal MC SS),
cell by cell. Three predictions differ only in the ttbar sample (nom, ph7, pth1); a fourth
swaps tW DR for DS.
3.5 Variables: Δφ(l,l) in [0, π] (12 bins); m(llbb) of the two leptons and two chosen jets
(5 GeV bins, 0-2000 GeV, overflow in the last bin).

## 4. Regions and statistic (fixed)

* Regions in m(llbb) from quantiles of the NOMINAL prediction only (never from data): threshold
  region **T** = lowest 20 %; control **C** = upper 50 %; inclusive; and four information bins
  at the 20/40/70 % quantiles. Boundaries snap to 5 GeV bin edges as coded (`quantile_bin`).
* In each region, A = (N[Δφ < π/2] - N[Δφ >= π/2]) / N, for data and for each prediction;
  ΔA = A_data - A_pred. Errors: data binomial; MC from sums of squared weights; generator
  envelope sig_gen = max(|A_ph7 - A_nom|, |A_pth1 - A_nom|); tW envelope |A_DS - A_nom|.
  Z = ΔA_nom / sqrt(s_data² + s_mc² + sig_gen² + sig_tw²).
* Double difference for H2: dd = ΔA_T - ΔA_C, with error from both regions' statistical terms
  and the generator and tW envelopes of the difference (`grade` in ttthresh_core.py).

## 5. Gate, hypotheses, predictions (fixed before any data)

* **Gate D0**: data/prediction (OS, all) in [0.85, 1.15], ttbar fraction of the nominal
  prediction >= 0.80 and at least 20,000 data events. Otherwise every verdict is NOT
  GRADABLE; a fix needs a written amendment before any rerun. Prediction: PASS 75 %.
* **H0b (reproduce the known direction)**: Z_incl >= 2 REPRODUCED; 0 < Z < 2 WEAK; <= 0 NOT
  REPRODUCED. Prediction: REPRODUCED 40 %, WEAK 45 %, NOT REPRODUCED 15 %.
* **H1 (excess at threshold)**: Z_T >= 2 EXCESS SEEN; 0 < Z_T < 2 WEAK; <= 0 NOT SEEN.
  Prediction: EXCESS SEEN 35 %, WEAK 45 %, NOT SEEN 20 %.
* **H2 (where the excess lives)**: Z_dd >= 1.5 CONCENTRATED AT THRESHOLD; <= -1.5 CONCENTRATED AT
  HIGH MASS; otherwise NOT RESOLVED. Prediction: AT THRESHOLD 30 %, NOT RESOLVED 60 %, AT HIGH
  MASS 10 %.
* **H3 (generator robustness at threshold)**: ΔA_T > 0 and statistical-only Z >= 2 against each
  of the three ttbar set-ups: ROBUST; else NOT ROBUST. Prediction: ROBUST 30 %.

Information only (no grade): R_T (data/prediction shape ratio of yields in T), ΔA in the four
quantile bins per generator, Δφ distributions per region (`dphi_by_region.csv`).

## 6. Honest limits, stated in advance

* m(llbb) is a coarse stand-in for m(tt); toponium sits within about 20 GeV of threshold, so it
  is diluted across T. No neutrino reconstruction and no unfolding: this is a detector-level
  shape test.
* There is no toponium simulation in the release, so a threshold excess, if seen, is a deviation
  from fixed-order NLO+shower simulation with the expected sign, not a measured toponium cross
  section. Known top-pT mismodelling can shift both m(llbb) and Δφ; the double difference and
  the three-generator envelope reduce but do not remove this.
* The release is an education-format beta: only nominal scale factors, no detector systematic
  variations. Two-point generator envelopes are not full modelling uncertainties.
* The selection follows common ATLAS eμ practice but is not ATLAS's 2019 selection; numbers
  will not match theirs exactly.

## 7. Execution

Job `ttthresh-v1` (compete lane, python:3.12, uproot + awkward + numpy, 2 CPU, 3 GB, network on
for the portal only): py_compile, unit tests (`test_ttthresh_core.py`), sha256 of every file,
then `ttthresh_job.py`. All graded numbers are printed on lines starting `TT_`. Results will be
committed unchanged with a RESULTS file that grades each hypothesis by the rules above,
including any prediction that fails.
