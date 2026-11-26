# tsplit/match: PHYSLITE truth match jobs (PREREG-v0.2, AMENDMENT-0.2.2)

MV2 of Munim, Inc. (mv2@munimtech.com). Code Apache-2.0, text CC BY 4.0. Made with AI agents
working in MV2's name; no human expert has checked it yet.

`match_job.py` 0.1.0 reads the public ATLAS PHYSLITE top-pair simulation (CERN Open Data records
80017 and 80018) for one sample and one part of its files, keeps the events whose
(mcChannelNumber, eventNumber) is one of job A's selected region-T keys
(`results/tsplit-keys-v1/keys_T.csv.gz`, pinned by sha256), and writes their truth top-pair mass
(largest- and smallest-barcode copy rules), copy multiplicities and status flags.

    python match_job.py --group nom --part 0 --nparts 4 \
        --keys-sha256 <sha256 of keys_T.csv.gz, or 'record'> --keys-ref <40-hex commit> \
        --tsplit-sha256 <sha256 of tsplit_core.py> --work /work --out /out

`--keys-ref` fetches the key file at a fixed commit, so its content cannot change; with
`--keys-sha256 record` the hash is printed and stored in the part's json, and the grade job
requires all parts to report the same hash.

Outputs: `match_<group>_p<part>.csv.gz` (one row per occurrence of a selected key) and
`match_<group>_p<part>.json` (per-file status, entries, rows). Exit 6 = the record's file count
differs from AMENDMENT-0.2.2; exit 7 = a file could not be read after 3 attempts.

Planned jobs (filed only after job A returns): `tsplit-match-nom-p{0,1,2,3}-v1`,
`tsplit-match-ph7-v1`, `tsplit-match-pth1-v1`. Then one grade job applies the duplicate rule, the
gates G1-G3 and the split (tsplit_core.decompose, bootstrap) and grades H1 and H1r.

Tests: `python -m unittest -v test_match_job` (14 tests; the 2 that use tsplit_core run when
`tsplit_core.py` is in `..` or `./tsplit`).
