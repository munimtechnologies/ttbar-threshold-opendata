# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""keys_job 0.1.0 -- job A of PREREG-v0.2 (tsplit), ttbar-threshold-opendata.

Re-runs ttthresh-v2's selection UNCHANGED on the top-pair samples of the ATLAS Open Data 2025
education ntuples and writes, for every selected opposite-sign e-mu top-pair event in region T
(m(llbb) < 250 GeV), its match key and what the split needs:

    keys_T.csv.gz  dsid,run,event,group,w,dphi,mllbb,short

How the frozen code is reused (AMENDMENT-0.2.1): ttthresh_job 0.1.1 (built by fix_ttthresh.py
from commit 01d788aa63, blob-sha1 checked) is imported from --src. Its own process_file() reads
each file, with two changes made from outside and nothing retyped: (1) the three key branches
eventNumber, runNumber, channelNumber are appended to its EVT branch list, so they are read in
the same chunks (select_arrays never looks at them); (2) select_arrays is wrapped: the wrapper
calls the original and keeps, for the selected OS events, the key branches, the raw weight,
Delta-phi and m(llbb). The file normalisation is the one process_file returns (info['norm']).
Region-T and short flags use the same clipping and bin edges as ttthresh_core.hist2, and the
job checks that its per-event sums equal the histogram sums process_file filled (KEYS_XCHECK).

Gate G0 (PREREG-v0.2) is evaluated with tsplit_core.gate_g0 against the ttthresh-v2 numbers.

    python keys_job.py --src /work/src --tsplit /work/tsplit --data-dir /data --out /out
"""
import argparse
import gzip
import json
import math
import os
import sys
import time

VERSION = "0.1.0"
KEY_BRANCHES = ("channelNumber", "runNumber", "eventNumber")
REGION_T_HI_GEV = 250.0        # results/ttthresh-v2/results.json regions.T = [0, 250)
REGION_T_HI_BIN = 50           # M_EDGES[50] == 250.0 (5 GeV bins)
# Full region-T prediction of ttthresh-v2 (results/ttthresh-v2/results.json regions.T.pred)
PRED_T = {"nom": (9523.284335451435, 9974.533948080054),
          "ph7": (8530.027513660552, 9266.67752649883),
          "pth1": (8393.545212568833, 8837.209630395851)}
GROUP_TAG = {"ttbar_nom": "nom", "ttbar_ph7": "ph7", "ttbar_pth1": "pth1"}
CSV_HEADER = "dsid,run,event,group,w,dphi,mllbb,short"


# ----------------------------------------------------------------------------- pure helpers
def region_t_flag(mllbb, m_last_edge=2000.0):
    """Same rule as ttthresh_core.hist2 + region_sl(h, 0, 50): clip to [0, last - 1e-6], < 250."""
    m = min(max(float(mllbb), 0.0), m_last_edge - 1e-6)
    return m < REGION_T_HI_GEV


def short_flag(dphi, half_edge):
    """Delta-phi below the 6th of 12 edges (pi/2) after clipping to [0, pi], as in hist2."""
    d = min(max(float(dphi), 0.0), math.pi)
    return d < half_edge


def csv_row(dsid, run, event, tag, w, dphi, mllbb, short):
    return "%d,%d,%d,%s,%.12g,%.6f,%.4f,%d" % (int(dsid), int(run), int(event), tag, float(w),
                                                float(dphi), float(mllbb), 1 if short else 0)


def count_duplicates(keys):
    """keys: iterable of hashable. Returns (n_keys, n_distinct_duplicated, n_rows_in_dups)."""
    seen = {}
    n = 0
    for k in keys:
        n += 1
        seen[k] = seen.get(k, 0) + 1
    dup = [c for c in seen.values() if c > 1]
    return n, len(dup), sum(dup)


def bkg_t(pred_nom, tt_nom):
    return (pred_nom[0] - tt_nom[0], pred_nom[1] - tt_nom[1])


def rel_close(a, b, tol=1e-7):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


# ----------------------------------------------------------------------------- job
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--tsplit", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    t0 = time.time()
    sys.path.insert(0, args.src)
    sys.path.insert(0, args.tsplit)
    import numpy as np
    import awkward as ak
    import ttthresh_job as tj
    import tsplit_core as ts
    tc = tj.tc
    print("KEYS_VERSIONS keys_job=%s ttthresh_job=%s ttthresh_core=%s tsplit_core=%s %s" % (
        VERSION, tj.VERSION, tc.VERSION, ts.VERSION, json.dumps(tj.versions(), sort_keys=True)),
        flush=True)
    if tj.VERSION != "0.1.1" or tc.VERSION != "0.1.0" or ts.VERSION != "0.1.0":
        raise SystemExit("FATAL unexpected code versions")
    if float(tc.M_EDGES[REGION_T_HI_BIN]) != REGION_T_HI_GEV or tc.HALF != 6:
        raise SystemExit("FATAL bin edges differ from ttthresh-v2")
    half_edge = float(tc.D_EDGES[tc.HALF])
    m_last = float(tc.M_EDGES[-1])

    # (1) read the key branches in the same chunks
    tj.EVT = list(tj.EVT) + list(KEY_BRANCHES)
    # (2) wrap the selection
    orig = tj.select_arrays
    buf = []

    def wrapped(a, is_mc, sf_present=()):
        v, cf = orig(a, is_mc, sf_present)
        if v is not None:
            two = np.asarray(ak.to_numpy(ak.num(a["lep_pt"], axis=1) == 2), bool)
            m = np.asarray(v["os"], bool)
            if m.any():
                rec = {k: np.asarray(ak.to_numpy(a[k][two]))[m] for k in KEY_BRANCHES}
                for k in ("w", "dphi", "mllbb"):
                    rec[k] = np.asarray(v[k], float)[m]
                buf.append(rec)
        return v, cf

    tj.select_arrays = wrapped

    ddir = os.path.join(args.data_dir, "atlas-13tev25-2j2lmet30")   # same cache as ttthresh-v2
    os.makedirs(ddir, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)
    groups = tj.assign(tj.record_files(tj.MC_REC))
    summ = {"keys_job": VERSION, "groups": {}, "files": []}
    sl_flags = {}
    all_keys = {}
    t_keys = {}
    out_csv = os.path.join(args.out, "keys_T.csv.gz")
    n_rows = 0
    with gzip.open(out_csv, "wt", newline="\n") as gz:
        gz.write(CSV_HEADER + "\n")
        for g in tj.TTBAR_GROUPS:
            tag = GROUP_TAG[g]
            acc = {"os": tc.zeros(), "ss": tc.zeros(), "os2": tc.zeros(), "ss2": tc.zeros()}
            wcf = {}
            S = L = sumw_os = 0.0
            per_dsid = {}
            for f in groups[g]:
                path, src = tj.fetch(f, ddir)
                del buf[:]
                info = tj.process_file(path, True, acc, wcf)
                norm = float(info["norm"])
                n_file = n_t = 0
                for rec in buf:
                    w = rec["w"] * norm
                    for i in range(len(w)):
                        dsid = int(rec["channelNumber"][i])
                        run = int(rec["runNumber"][i])
                        ev = int(rec["eventNumber"][i])
                        key = (dsid, ev)
                        all_keys.setdefault(tag, []).append(key)
                        sumw_os += w[i]
                        d = per_dsid.setdefault(dsid, {"n_os": 0, "sumw_os": 0.0, "n_T": 0,
                                                       "S_T": 0.0, "L_T": 0.0, "runs": {}})
                        d["n_os"] += 1
                        d["sumw_os"] += float(w[i])
                        d["runs"][run] = d["runs"].get(run, 0) + 1
                        n_file += 1
                        if not region_t_flag(rec["mllbb"][i], m_last):
                            continue
                        sh = short_flag(rec["dphi"][i], half_edge)
                        if sh:
                            S += w[i]
                            d["S_T"] += float(w[i])
                        else:
                            L += w[i]
                            d["L_T"] += float(w[i])
                        d["n_T"] += 1
                        n_t += 1
                        t_keys.setdefault(tag, []).append(key)
                        gz.write(csv_row(dsid, run, ev, tag, w[i], rec["dphi"][i],
                                         rec["mllbb"][i], sh) + "\n")
                        n_rows += 1
                summ["files"].append({"group": g, "key": f["key"], "bytes": f["size"],
                                      "adler32": f["adler32"], "source": src, "norm": norm,
                                      "n_os": n_file, "n_T": n_t})
                print("KEYS_FILE %s %s bytes=%d adler32=%s norm=%.12g n_os=%d n_T=%d" % (
                    g, f["key"], f["size"], f["adler32"], norm, n_file, n_t), flush=True)
            hs, hl = tc.region_sl(acc["os"], 0, REGION_T_HI_BIN)
            hsum = float(acc["os"].sum())
            xok = rel_close(hs, S) and rel_close(hl, L) and rel_close(hsum, sumw_os)
            print("KEYS_XCHECK %s flags S=%.6f L=%.6f sumw_os=%.6f | hist S=%.6f L=%.6f "
                  "sumw_os=%.6f | %s" % (g, S, L, sumw_os, hs, hl, hsum,
                                         "OK" if xok else "MISMATCH"), flush=True)
            for dsid, d in per_dsid.items():
                d["runs"] = {str(k): v for k, v in sorted(d["runs"].items())}
            sl_flags[tag] = (S, L)
            na, nd, nr = count_duplicates(all_keys.get(tag, []))
            ta, td, tr = count_duplicates(t_keys.get(tag, []))
            summ["groups"][g] = {"S_T": S, "L_T": L, "sumw_os": sumw_os, "hist_S_T": hs,
                                 "hist_L_T": hl, "hist_sumw_os": hsum, "xcheck": xok,
                                 "cutflow": wcf, "per_dsid": {str(k): v for k, v in
                                                              sorted(per_dsid.items())},
                                 "dup_all_os": {"keys": na, "duplicated": nd, "rows": nr},
                                 "dup_T": {"keys": ta, "duplicated": td, "rows": tr}}
            print("KEYS_GROUP %s S_T=%.4f L_T=%.4f sumw_os=%.4f n_T=%d dup_T=%d/%d dup_os=%d/%d "
                  "dsids=%s" % (g, S, L, sumw_os, ta, td, tr, nd, nr,
                                ",".join(str(k) for k in sorted(per_dsid))), flush=True)
    # gate G0
    bk = bkg_t(PRED_T["nom"], sl_flags["nom"])
    ds_tt = sl_flags["ph7"][0] - sl_flags["nom"][0]
    dl_tt = sl_flags["ph7"][1] - sl_flags["nom"][1]
    g0 = ts.gate_g0(summ["groups"]["ttbar_nom"]["sumw_os"], ds_tt, dl_tt, bk)
    xall = all(v["xcheck"] for v in summ["groups"].values())
    summ["G0"] = {"ttbar_nom_os": summ["groups"]["ttbar_nom"]["sumw_os"],
                  "ref_ttbar_nom_os": ts.REF_TTBAR_NOM_OS, "dS_tt": ds_tt,
                  "ref_dS_pred": ts.REF_DS_PRED, "dL_tt": dl_tt, "ref_dL_pred": ts.REF_DL_PRED,
                  "bkg_T": list(bk), "checks": g0, "verdict": "PASS" if g0["pass"] else "FAIL"}
    # information: does the pth1-vs-nom difference close too?
    summ["info_pth1"] = {"dS_tt": sl_flags["pth1"][0] - sl_flags["nom"][0],
                         "dS_pred": PRED_T["pth1"][0] - PRED_T["nom"][0],
                         "dL_tt": sl_flags["pth1"][1] - sl_flags["nom"][1],
                         "dL_pred": PRED_T["pth1"][1] - PRED_T["nom"][1]}
    summ["xcheck_all"] = xall
    summ["rows_keys_T"] = n_rows
    summ["seconds"] = time.time() - t0
    with open(os.path.join(args.out, "keys_summary.json"), "w") as fh:
        json.dump(summ, fh, indent=1, sort_keys=True)
    print("KEYS_G0 verdict=%s ttbar_nom_os=%.4f (ref %.2f) dS_tt=%.4f (ref %.2f) dL_tt=%.4f "
          "(ref %.2f) bkg_T=(%.4f, %.4f) checks=%s" % (
              summ["G0"]["verdict"], summ["G0"]["ttbar_nom_os"], ts.REF_TTBAR_NOM_OS, ds_tt,
              ts.REF_DS_PRED, dl_tt, ts.REF_DL_PRED, bk[0], bk[1], json.dumps(g0, sort_keys=True)),
          flush=True)
    print("KEYS_INFO_PTH1 " + json.dumps(summ["info_pth1"], sort_keys=True), flush=True)
    print("KEYS_DONE rows=%d xcheck_all=%s total_s=%.0f" % (n_rows, xall, time.time() - t0),
          flush=True)
    return 0 if xall else 5


if __name__ == "__main__":
    sys.exit(main())
