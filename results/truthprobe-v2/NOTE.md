# truthprobe-v2: returned 2026-11-25, verdict FEASIBLE (feasibility probe; nothing graded)

Job: `probes/truthprobe-v2/job.json` (truthprobe 0.2.0). Ran on the Blade 2026-11-25 19:18-19:28 UTC,
1 CPU, every step exit 0. Files here are copied unchanged from the job's `/out`.

What it read: CERN Open Data record 80017 (ATLAS PHYSLITE top nominal samples), the
`PhPy8EG_A14_ttbar_hdamp258p75_nonallhad` index (DSID 410470, 190 ROOT files, 478.6 GB), one file
(`DAOD_PHYSLITE.37620646._000024.pool.root.1`, 2.18 GB, 150,000 entries), streamed over HTTPS.

What it found:
- The `TruthTop` container is present, with `TruthTopAuxDyn.{px,py,pz,e,m,pdgId,status,barcode}`
  and parent/child links.
- In 3,000 events read, every event has both a top and an antitop. The number of +6 entries per
  event has median 2 and maximum 4: the container keeps more than one copy of a top in some events,
  so any truth m(tt) needs a fixed rule for which copy to use. This probe took, for each sign, the
  status-62 copy (Pythia's last copy before decay) when there is one, else the last copy in the
  container; that rule is Pythia-specific, so a study that also uses Herwig 7 samples must fix its
  own rule in advance.
- Truth m(tt) quantiles over these 3,000 unselected events (0, 5, 20, 50, 80, 95, 100 %): 291.3,
  358.6, 394.2, 471.3, 614.2, 882.9, 2036.2 GeV; fraction below 350 GeV 0.0187, below 345 GeV 0.0093.
- `EventInfoAuxDyn.eventNumber`, `mcChannelNumber` and `mcEventWeights` are readable, so the match
  key (channelNumber, eventNumber) proposed in `SCOPING-v0.2.md` exists on the PHYSLITE side.
- Cost: the branches a match needs take 122.9 MB in this file (819.5 bytes per event); about 27 GB
  for the whole nominal sample if all files are similar.

What follows: `SCOPING-v0.2.md` said a v0.2 pre-registration (composition versus angular split of
the Herwig-Pythia gap in region T, truth m(tt) bins below 380, 380-450, 450-550 and at least 550
GeV) would be written only if this probe said FEASIBLE. It did. The pre-registration must also fix
the top-copy rule (above) before the match job runs. The quantiles here come from unselected events
and are the only truth numbers this project has seen.

Made with AI agents working in MV2's name. Apache-2.0 (code), CC BY 4.0 (text).
