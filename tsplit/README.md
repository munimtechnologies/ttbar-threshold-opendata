# tsplit: composition or angles? (PREREG-v0.2)

Code for the test fixed in `../PREREG-v0.2.md`: why the Powheg+Herwig7 and Powheg+Pythia8
predictions of the region-T e-mu spin asymmetry differ by 0.01825, the gap that kept ttthresh-v2
from placing the top-spin excess at the top-pair threshold.

- `tsplit_core.py` 0.1.0: pure functions. The exact split Delta = C + S over the six bins of
  PREREG-v0.2 (four truth m(tt) bins, `um`, `bkg`), the top copy rule (largest barcode per
  pdgId +6 / -6; ties are ambiguous and dropped), the duplicate-key rule, the Poisson(1)
  bootstrap (seed 20261125, 200 replicas), gates G0-G3 and the H1/H1r grades.
- `test_tsplit_core.py`: 15 unit tests (split identity, pure-composition and pure-angular cases,
  copy rule, duplicates, bin edges, invariant mass, gates, grade boundaries, bootstrap
  reproducibility; the bootstrap test needs numpy on POSIX).

Not yet written (next): job A `tsplit-keys-v1`, which re-runs ttthresh-v2's selection on the 2025
education ntuples (code fetched pinned at commit 01d788aa63) and writes the selected top-pair
keys with weight, Delta-phi and region flags; then the PHYSLITE truth-match jobs. Any detail not
fixed in PREREG-v0.2 goes into AMENDMENT-0.2.1 before a match job runs. No truth data have been
read for this test.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; no human
expert has checked it yet. Code Apache-2.0, text CC BY 4.0.
