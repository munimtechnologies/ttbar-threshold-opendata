# truthprobe-v1: result note

MV2 of Munim, Inc. (mv2@munimtech.com). Written 2026-11-25 with AI agents working in his name.
Apache-2.0 / text CC BY 4.0. Feasibility probe only; nothing here is graded.

**Verdict: NO_RECORD, a defect in the probe, not an answer.** The job ran on 2026-11-24 23:44 to
2026-11-25 00:12 UTC (Dell, exit 0). All three portal searches returned 0 hits, so no file was
opened (files: `run.txt`, `stdout_probe.txt`, `sha256.txt`, `versions.txt`, `job.json`,
`summary.json`).

Why, found after the run (2026-11-25):
1. Wrong sample. truthprobe 0.1.0 looked for DSID 410472 (Powheg+Pythia8 dilepton). The nominal
   top-pair sample behind ttthresh-v2 is DSID **410470** (`PhPy8EG_A14_ttbar_hdamp258p75_nonallhad`,
   see `test_fix_ttthresh.py`), and 410472 is not in the 2024 research release at all.
2. Search does not index the DSID. Neither `410472` nor `PHYSLITE ttbar` returns any hit from the
   portal's search API. The research-release top samples sit in one record:
   [CERN Open Data record 80017](https://opendata.cern.ch/record/80017), "ATLAS DAOD_PHYSLITE format
   MC simulation top nominal samples" (DOI 10.7483/OPENDATA.ATLAS.MM1Y.O0PH), whose file index
   `mc20_13TeV_MC_PhPy8EG_A14_ttbar_hdamp258p75_nonallhad_file_index.json` lists 190 files
   (478.6 GB).
3. Even with the record found, 0.1.0 would have kept no file, because index entries have keys like
   `..._file_index.json_183`. Only their `uri` / `filename` ends in `.root.1`.

truthprobe 0.2.0 (`probes/truthprobe-v2/`) reads record 80017 directly, picks the 410470 index,
selects files by uri and reads the truth-top branches one at a time, reporting any branch that
uproot cannot read. Its output lines are the same as 0.1.0, and so are its verdict rules.
