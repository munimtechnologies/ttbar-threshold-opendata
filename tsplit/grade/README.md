# tsplit/grade: the grade step of PREREG-v0.2 (AMENDMENT-0.2.3)

MV2 of Munim, Inc. (mv2@munimtech.com). Code Apache-2.0, text CC BY 4.0. Made with AI agents
working in MV2's name; no human expert has checked it yet.

The question (PREREG-v0.2): in region T of the 2019 ATLAS e-mu spin-correlation test, Powheg+Pythia8
and Powheg+Herwig7 predict asymmetries that differ by Delta = 0.01825, more than the excess itself.
Is that gap **composition** (different true top-pair masses end up in region T) or **angular**
(different lepton angles at the same true mass, i.e. disagreement about spin correlations at the
threshold where toponium acts)?

`grade_job.py` 0.1.0 reads job A's keys and the six PHYSLITE match parts **at one fixed commit**,
pins `tsplit/tsplit_core.py` by sha256, and then:

1. checks G0 and its consistency with job A (row count, per-sample (S, L) sums, bkg);
2. checks that every PHYSLITE file of `nom` and `ph7` was read exactly once by match_job 0.1.0 with
   the same key file (FILES);
3. classifies every selected region-T top-pair event as matched (truth m(tt) bin) or `um`, with the
   reason (not_read, edu_dup, phys_missing, phys_dup, no_pair, in that order of precedence);
4. computes G1 (matched / selected weight), G2 (copy rule), G3 (um share) and the exact split
   C + S = Delta with `tsplit_core.decompose` (CLOSURE to 1e-9);
5. grades H1 (R_C band) and H1r (16th-84th percentile of 200 Poisson bootstrap replicas, seed
   20261125) with `tsplit_core`, and reports the information-only items.

    python grade_job.py --ref <40-hex commit> --tsplit-sha256 <hex> --work /work --out /out \
        [--keys-sha256 <hex>] [--part-dir nom:2=results/tsplit-match-nom-p2-v2]

`--part-dir` is only for a part that had to be re-run after an outside read failure (AMENDMENT-0.2.2
s4); every directory used is written to `results.json`. Outputs: `results.json`, `grade.txt`
(`GRADE_*` lines).

Tests: `python -m unittest -v test_grade_job` (14 tests; the 4 end-to-end tests run when
`tsplit_core.py` is in `..` or `./tsplit` and numpy is installed).
