# results/ttderive-v1: machine re-check of the post-hoc derived table

Munim, Inc. (MV2). Made with AI agents working in MV2's name; no physicist has checked this yet.
Text CC BY 4.0, code Apache-2.0.

**What this job did.** `RESULTS-v0.1.md` reports two post-hoc numbers (information only, never graded):
the data/prediction yield shape in the four m(llbb) bins, and the split of the inclusive
Delta-phi excess dA_incl into a part from the angular shape inside each mass bin and a part from
the mass spectrum (composition). Those values were first computed by hand into
`results/ttthresh-v2/derived_v2.csv`. This job downloaded the committed
`results/ttthresh-v2/results.json` from this repository's main branch, ran
`results/ttthresh-v2/derive_v2.py` on it, and compared the machine output with the hand-made CSV.

**Run.** compete job `ttderive-v1` (id ebf6b2c0f1ff), python:3.12, 1 CPU, 1 GB, on 2026-11-27
12:49-12:56 UTC; both steps exit 0. Files here are copied unchanged from the job:
`derive.txt` (every `DERIVE_` line), `derived_machine.csv`, `sha256.txt`, `job.json`, `summary.json`.

**Result: DERIVE_CHECK MATCH.** The machine CSV is identical to the hand CSV in every cell.

| Bin | m(llbb) GeV | data | prediction | data/pred | shape ratio | dA |
|---|---|---|---|---|---|---|
| B1 | 0-250 | 21,750 | 19,497.8 | 1.1155 | 1.0555 | +0.0170 |
| B2 | 250-305 | 20,503 | 19,256.1 | 1.0648 | 1.0075 | +0.0028 |
| B3 | 305-410 | 28,315 | 27,112.2 | 1.0444 | 0.9882 | +0.0057 |
| B4 | 410-inf | 28,327 | 27,710.1 | 1.0223 | 0.9673 | +0.0057 |

Split: dA_incl = +0.013155 = +0.007562 (within bins) + 0.005593 (composition); composition share
0.4251; closure 0.0; overall data/prediction 1.056839.

**Hand re-derivation (this run).** 21750 / 19497.818 = 1.11551; 98,895 / 93,576.24 = 1.05684;
1.115509 / 1.056839 = 1.05551; 1.022261 / 1.056839 = 0.96728; 0.007562 + 0.005593 = 0.013155;
0.005593 / 0.013155 = 0.4252 (the job's 0.4251 uses unrounded inputs). All agree.

**Hashes** (from `sha256.txt`): results.json 95bd94f2...28fcb, derive_v2.py a30df5be...ab14f7,
derived_v2.csv b254556b...436e5.

**What it changes.** Nothing in the grades (D0 PASS, H0b REPRODUCED, H1 WEAK, H2 NOT RESOLVED,
H3 ROBUST). It confirms the two information-only statements of `RESULTS-v0.1.md`: data have a
softer m(llbb) spectrum than the nominal Powheg+Pythia8 prediction (+5.6 % in B1, -3.3 % in B4 after
normalisation), and about 43 % of the inclusive excess in this selection comes from that mass
spectrum rather than from the Delta-phi shape at fixed mass. Both remain post hoc and coarse (four bins).
