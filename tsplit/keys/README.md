# tsplit/keys: job A of PREREG-v0.2

`keys_job.py` 0.1.0 re-runs ttthresh-v2's selection, unchanged and hash-pinned, on the top-pair
samples of the ATLAS Open Data 2025 education ntuples (CERN Open Data record 93913). It writes the
match key (DSID, run, event), weight, Delta-phi, m(llbb) and short flag of every selected
opposite-sign e-mu top-pair event in region T (`keys_T.csv.gz`). It also checks gate G0 of
`../../PREREG-v0.2.md`. The exact rules are in `../../AMENDMENT-0.2.1.md`.

- `prep.py` fetches `fix_ttthresh.py` (pinned by sha256) and tsplit_core 0.1.0 (hashes recorded).
- `test_keys_job.py` has 9 unit tests, standard library only.
- Job definition: `../../jobs/tsplit-keys-v1/job.json`. No truth data are read by this job.

MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; no human expert
has checked it yet. Code Apache-2.0, text CC BY 4.0.
