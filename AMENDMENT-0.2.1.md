# AMENDMENT 0.2.1 to PREREG-v0.2 (tsplit): how job A reads the selected events

MV2 of Munim, Inc. (mv2@munimtech.com). Written 2026-11-26, **before job `tsplit-keys-v1` ran and
before any PHYSLITE truth record was matched**. Made with AI agents working in MV2's name; no human
expert has checked it. Text CC BY 4.0, code Apache-2.0. PREREG-v0.2's tests, gates, bins, bands
and predictions are unchanged. This fixes implementation details that PREREG-v0.2 left open.

1. **Code reuse.** Job A (`tsplit/keys/keys_job.py` 0.1.0) imports ttthresh_job 0.1.1 as built by
   `fix_ttthresh.py` 0.1.1. That builder is fetched by `prep.py` and pinned by sha256
   `9c2bdd681a02cf1ae6891a065fa6af3381a7f909b5cc042178367a6d7b214fe6`, the file that the graded
   job ttthresh-v2 ran (`results/ttthresh-v2/sha256.txt`). It fetches the 0.1.0 files at commit
   01d788aa63 and checks their git blob sha1 as before. The selection is not retyped. ttthresh's own
   `process_file()` reads the files, with two changes made from outside: the branches `eventNumber`,
   `runNumber` and `channelNumber` are appended to its event-branch list, and `select_arrays` is
   wrapped so that the opposite-sign events it selects are recorded with their raw weight,
   Delta-phi and m(llbb). The weight is the raw weight times the file normalisation returned by
   `process_file` (`info["norm"]`). tsplit_core 0.1.0 is fetched from `main`, and its sha256 and
   blob sha1 are recorded in `prep.txt`. Its 15 tests and ttthresh's tests run in the same job.
2. **Flags.** Region T: m(llbb), clipped to [0, 2000 - 1e-6] GeV as in `ttthresh_core.hist2`, below
   250 GeV (`results/ttthresh-v2/results.json` regions.T = [0, 250)). Short: Delta-phi, clipped to
   [0, pi], below `D_EDGES[6]` (pi/2). An event exactly on an edge goes to the upper bin, as in
   numpy's histogram. Check **KEYS_XCHECK**: for each top-pair group, the per-event sums S_T, L_T
   and the inclusive OS weight must equal the sums of the histograms that `process_file` filled
   (relative 1e-7). Any mismatch makes the job exit 5, and G0 is then NOT PASSED.
3. **What is written.** `keys_T.csv.gz` holds only the selected opposite-sign e-mu top-pair events
   in region T (the only events that H1 and gates G1 to G3 use). Columns: dsid (the ntuple's
   `channelNumber`), run, event, group (nom / ph7 / pth1), weight (12 significant digits),
   Delta-phi, m(llbb) and the short flag. `keys_summary.json` holds per-group and per-DSID sums,
   runNumber counts, duplicate-key counts, the cross-check and G0.
4. **G0 inputs.** These are taken from `results/ttthresh-v2/results.json` and written into the job:
   the region-T prediction (S, L) is nom (9523.284335451435, 9974.533948080054), ph7
   (8530.027513660552, 9266.67752649883) and pth1 (8393.545212568833, 8837.209630395851).
   bkg_T = pred_nom - tt_nom from this job. The ttthresh non-prompt term uses `nom` same-sign MC for
   every generator, so pred_ph7 - pred_nom should equal tt_ph7 - tt_nom exactly. G0 is evaluated by
   `tsplit_core.gate_g0` with its fixed 0.1 % and 2 % tolerances. The same difference for pth1 is
   reported for information only.
5. **Match key.** The ntuple key (channelNumber, eventNumber) is matched to the PHYSLITE
   (EventInfo mcChannelNumber, eventNumber). runNumber is recorded on the ntuple side and compared
   only as a check, as PREREG-v0.2 says. The 411233 (ph7 single-lepton) and 601497 (pth1
   single-lepton) rows are written with their DSID. Under PREREG-v0.2 they go to the `um` bin,
   because their PHYSLITE files are not read.
6. **If job A fails.** A crash or a missing branch means a fix, version 0.1.1 of the job, and an
   amendment note; G0 FAIL means H1 NOT GRADABLE (PREREG-v0.2). The match jobs are written only
   after job A returns, and they read `keys_T.csv.gz` from the repository, pinned by sha256.
