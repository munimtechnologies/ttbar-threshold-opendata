# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""ttthresh_job 0.1.0 -- runs PREREG-v0.1 on the ATLAS Open Data 13 TeV 2025 beta release.

    python ttthresh_job.py --data-dir /data --out /out

Inputs: CERN Open Data records 93934 (2015-16 collision data, 2J2LMET30 skim) and 93913
(matching MC). File lists, sizes and adler32 checksums come from the portal API; every file
is checked before use. Every number a grade needs is printed (lines TT_*).
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ttthresh_core as tc  # noqa: E402

VERSION = "0.1.0"
API = "https://opendata.cern.ch/api/records/%d"
DATA_REC, MC_REC = 93934, 93913
PREFIXES = ("https://opendata.cern.ch/eos/opendata/atlas/rucio/opendata/",
            "https://eospublic.cern.ch:8444//eos/opendata/atlas/rucio/opendata/")
LUMI_PB = 36000.0          # as in the release's own ttbar notebook (36 fb-1)
MAX_BKG_BYTES = 3.5e9      # a background file bigger than this is skipped (printed)
RULES = {                  # sample group -> regexes on the file key (PREREG-v0.1 sec. 3.3)
    "ttbar_nom": [r"_mc_410470\."],
    "ttbar_ph7": [r"_mc_411233\.", r"_mc_411234\."],
    "ttbar_pth1": [r"_mc_601491\.", r"_mc_601497\."],
    "tW_DR": [r"_mc_601352\.", r"_mc_601355\."],
    "tW_DS": [r"_mc_601627\.", r"_mc_601631\."],
    "Ztautau": [r"_mc_70079[234]\.", r"_mc_70090[123]\."],
    "diboson": [r"_mc_7006\d\d\.Sh_221\d_(llll|lllv|llvv|lvvv)\."],
    "ttV": [r"_mc_410155\.", r"_ttZ", r"_ttll", r"_ttee", r"_ttmumu", r"_tttautau"],
}
TTBAR_GROUPS = ("ttbar_nom", "ttbar_ph7", "ttbar_pth1")
LEP = ["lep_pt", "lep_eta", "lep_phi", "lep_e", "lep_charge", "lep_type", "lep_isTightID",
       "lep_isTightIso", "lep_isTrigMatched"]
JET = ["jet_pt", "jet_eta", "jet_phi", "jet_e", "jet_btag_quantile"]
EVT = ["trigE", "trigM"]
SF = ["ScaleFactor_PILEUP", "ScaleFactor_ELE", "ScaleFactor_MUON", "ScaleFactor_FTAG",
      "ScaleFactor_JVT", "ScaleFactor_LepTRIGGER"]
NORM = ["xsec", "kfac", "filteff", "sum_of_weights", "num_events"]
BTAG_MIN_QUANTILE = 4      # the release's own ttbar example cut (DL1dv01 pseudo-continuous)
CUTS = ["in", "two_lep", "tight_iso_pt25_nocrack", "emu", "trigger_match27",
        "ge2jets_ge1b", "mll15", "OS", "SS"]


# ----------------------------------------------------------------------------- files
def _files_in(obj):
    """Find the list of file dicts (with 'key') anywhere in the portal JSON."""
    if isinstance(obj, dict):
        for k in ("_files", "files"):
            v = obj.get(k)
            if isinstance(v, list) and v and isinstance(v[0], dict) and "key" in v[0]:
                return v
        for v in obj.values():
            r = _files_in(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _files_in(v)
            if r:
                return r
    return []


def record_files(rec):
    for k in range(5):
        try:
            req = urllib.request.Request(API % rec, headers={"Accept": "application/json",
                                                             "User-Agent": "ttthresh/0.1"})
            with urllib.request.urlopen(req, timeout=180) as fh:
                js = json.load(fh)
            fl = _files_in(js)
            out = []
            for f in fl:
                key = os.path.basename(str(f["key"]))
                ck = str(f.get("checksum", ""))
                out.append({"key": key, "size": int(f.get("size", -1)),
                            "adler32": ck.split(":", 1)[1].lower() if ck.startswith("adler32:") else "",
                            "uri": str(f.get("uri", ""))})
            return out
        except Exception as exc:  # pragma: no cover - network
            print("api attempt %d for %d failed: %s" % (k + 1, rec, exc), flush=True)
            time.sleep(20 * (k + 1))
    raise SystemExit("could not read record %d" % rec)


def adler32_file(path):
    v = 1
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            v = zlib.adler32(chunk, v)
    return "%08x" % (v & 0xFFFFFFFF)


def _ok(path, f):
    return (os.path.exists(path) and os.path.getsize(path) == f["size"]
            and (not f["adler32"] or adler32_file(path) == f["adler32"]))


def fetch(f, ddir):
    path = os.path.join(ddir, f["key"])
    if _ok(path, f):
        return path, "cached"
    urls = []
    if "/eos/" in f["uri"]:
        urls.append("https://opendata.cern.ch/eos/" + f["uri"].split("/eos/", 1)[1])
    urls += [p + f["key"] for p in PREFIXES]
    for url in urls:
        for k in range(3):
            try:
                tmp = path + ".part"
                req = urllib.request.Request(url, headers={"User-Agent": "ttthresh/0.1"})
                with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as fh:
                    while True:
                        b = r.read(1 << 22)
                        if not b:
                            break
                        fh.write(b)
                os.replace(tmp, path)
                if _ok(path, f):
                    return path, url
                print("checksum/size mismatch for %s from %s" % (f["key"], url), flush=True)
            except Exception as exc:  # pragma: no cover - network
                print("download attempt %d %s failed: %s" % (k + 1, url, exc), flush=True)
                time.sleep(15 * (k + 1))
    raise SystemExit("could not fetch " + f["key"])


def assign(files):
    groups = {g: [] for g in RULES}
    for f in files:
        hit = [g for g, pats in RULES.items() if any(re.search(p, f["key"]) for p in pats)]
        if len(hit) > 1:
            raise SystemExit("file %s matches groups %s" % (f["key"], hit))
        if hit:
            groups[hit[0]].append(f)
    return groups


# ----------------------------------------------------------------------------- selection
def select_arrays(a, is_mc, sf_present=()):
    """a: mapping branch -> awkward array (one chunk). Returns (vars dict or None, cutflow)."""
    import awkward as ak
    lpt_all = a["lep_pt"]
    n_in = len(lpt_all)
    two = np.asarray(ak.to_numpy(ak.num(lpt_all, axis=1) == 2), bool)
    cf = dict.fromkeys(CUTS, 0)
    cf["in"] = n_in
    cf["two_lep"] = int(two.sum())
    if not two.any():
        return None, cf

    def L(name, dtype=float):
        x = a[name][two]
        return np.asarray(ak.to_numpy(ak.to_regular(x[:, :2], axis=1)), dtype)

    def E(name, dtype=float):
        return np.asarray(ak.to_numpy(a[name][two]), dtype)

    pt, eta, phi, e = L("lep_pt"), L("lep_eta"), L("lep_phi"), L("lep_e")
    q = L("lep_charge")
    typ = L("lep_type", int)
    tid, tiso, tm = L("lep_isTightID", bool), L("lep_isTightIso", bool), L("lep_isTrigMatched", bool)
    trig = E("trigE", bool) | E("trigM", bool)
    is_e = typ == 11
    crack = is_e & (np.abs(eta) > 1.37) & (np.abs(eta) < 1.52)
    c1 = tid.all(1) & tiso.all(1) & (pt > 25.0).all(1) & ~crack.any(1)
    c2 = c1 & (typ.sum(1) == 24) & (typ[:, 0] != typ[:, 1])
    c3 = c2 & trig & (tm & (pt > 27.0)).any(1)

    jpt, jeta, jphi, je = (a[n][two] for n in ("jet_pt", "jet_eta", "jet_phi", "jet_e"))
    jq = a["jet_btag_quantile"][two]
    good = (jpt > 25.0) & (np.abs(jeta) < 2.5)
    ngood = np.asarray(ak.to_numpy(ak.sum(good, axis=1)), int)
    nb = np.asarray(ak.to_numpy(ak.sum(good & (jq >= BTAG_MIN_QUANTILE), axis=1)), int)
    key = ak.where(good, jq * 100000.0 + jpt, -1.0)
    order = ak.argsort(key, axis=1, ascending=False)

    def J(x):
        y = ak.fill_none(ak.pad_none(x[order], 2, axis=1, clip=True), 0.0)
        return np.asarray(ak.to_numpy(ak.to_regular(y, axis=1)), float)

    c4 = c3 & (ngood >= 2) & (nb >= 1)
    dphi, mll, mllbb = tc.event_vars(pt, eta, phi, e, J(jpt), J(jeta), J(jphi), J(je))
    c5 = c4 & (mll > 15.0)
    qq = q[:, 0] * q[:, 1]
    os_, ss_ = c5 & (qq < 0), c5 & (qq > 0)
    for name, c in zip(CUTS[2:], (c1, c2, c3, c4, c5, os_, ss_)):
        cf[name] = int(c.sum())
    w = np.ones(len(dphi))
    if is_mc:
        w = E("mcWeight")
        for s in sf_present:
            w = w * E(s)
    return {"dphi": dphi, "mll": mll, "mllbb": mllbb, "w": w, "os": os_, "ss": ss_}, cf


# ----------------------------------------------------------------------------- reading
def process_file(path, is_mc, acc, wcf):
    import uproot
    t = uproot.open(path)["analysis"]
    keys = set(t.keys())
    need = LEP + JET + EVT + (["mcWeight"] if is_mc else [])
    miss = [b for b in need if b not in keys]
    if miss:
        raise SystemExit("%s lacks branches %s" % (os.path.basename(path), miss))
    sfp = [s for s in SF if s in keys] if is_mc else []
    norm, info = 1.0, {"entries": int(t.num_entries)}
    if is_mc:
        nb = [b for b in NORM if b in keys]
        first = t.arrays(nb, entry_stop=min(1000, t.num_entries), library="np")
        for b in nb:
            v = np.asarray(first[b], float)
            info[b] = float(v[0]) if len(v) else float("nan")
            info[b + "_spread"] = float(v.max() - v.min()) if len(v) else 0.0
        info["sf_missing"] = [s for s in SF if s not in keys]
        sw = info.get("sum_of_weights", float("nan"))
        norm = (info.get("xsec", float("nan")) * info.get("kfac", 1.0) * info.get("filteff", 1.0)
                * LUMI_PB / sw) if sw and np.isfinite(sw) else 0.0
        info["norm"] = norm
    for chunk in t.iterate(need + sfp, step_size="100 MB", library="ak"):
        v, cf = select_arrays(chunk, is_mc, sfp)
        for k2, n in cf.items():
            wcf[k2] = wcf.get(k2, 0) + n
        if v is None:
            continue
        w = v["w"] * norm
        for sign in ("os", "ss"):
            m = v[sign]
            if not m.any():
                continue
            h, h2 = tc.hist2(v["mllbb"][m], v["dphi"][m], w[m])
            acc[sign] += h
            acc[sign + "2"] += h2
            acc["sumw_" + sign] = acc.get("sumw_" + sign, 0.0) + float(w[m].sum())
    return info


def versions():
    from importlib import metadata
    out = {"python": sys.version.split()[0], "numpy": np.__version__}
    for p in ("uproot", "awkward"):
        try:
            out[p] = metadata.version(p)
        except Exception:
            pass
    return out


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return float(o) if np.isfinite(o) else str(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    t0 = time.time()
    os.makedirs(args.out, exist_ok=True)
    ddir = os.path.join(args.data_dir, "atlas-13tev25-2j2lmet30")
    os.makedirs(ddir, exist_ok=True)
    print("ttthresh_job %s, ttthresh_core %s" % (VERSION, tc.VERSION), flush=True)
    print("TT_VERSIONS " + json.dumps(versions(), sort_keys=True), flush=True)
    dfiles = record_files(DATA_REC)
    mfiles = record_files(MC_REC)
    print("TT_RECORDS data=%d files %.3f GB, mc=%d files %.3f GB" % (
        len(dfiles), sum(f["size"] for f in dfiles) / 1e9, len(mfiles),
        sum(f["size"] for f in mfiles) / 1e9), flush=True)
    groups = assign(mfiles)
    groups["data"] = [f for f in dfiles if "_data1" in f["key"]]
    rows = []
    H = {}
    for g in ["data"] + list(RULES):
        is_mc = g != "data"
        acc = {"os": tc.zeros(), "ss": tc.zeros(), "os2": tc.zeros(), "ss2": tc.zeros()}
        wcf = {}
        for f in groups[g]:
            if is_mc and g not in TTBAR_GROUPS and f["size"] > MAX_BKG_BYTES:
                print("TT_SKIP %s %s size %.2f GB above cap" % (g, f["key"], f["size"] / 1e9),
                      flush=True)
                continue
            path, src = fetch(f, ddir)
            ts = time.time()
            info = process_file(path, is_mc, acc, wcf)
            rows.append([g, f["key"], f["size"], f["adler32"], src])
            print("TT_FILE %s %s bytes=%d adler32=%s %s %.0fs" % (
                g, f["key"], f["size"], f["adler32"], json.dumps(info, sort_keys=True),
                time.time() - ts), flush=True)
        H[g] = acc
        print("TT_SAMPLE %s files=%d sumw_os=%.3f sumw_ss=%.3f cutflow=%s" % (
            g, len(groups[g]), acc.get("sumw_os", 0.0), acc.get("sumw_ss", 0.0),
            json.dumps(wcf)), flush=True)
    res = tc.grade(H)
    res["job"] = {"ttthresh_job": VERSION, "lumi_pb": LUMI_PB, "btag_min_quantile":
                  BTAG_MIN_QUANTILE, "versions": versions(), "seconds": time.time() - t0}
    y = res["yields"]
    print("TT_YIELDS " + json.dumps(jsonable(y), sort_keys=True), flush=True)
    print("TT_GATE verdict=%s data/pred=%.4f ttbar_frac=%.4f n_data=%d" % (
        res["gate"]["verdict"], res["gate"]["ratio"], res["gate"]["ttbar_frac"],
        res["gate"]["n_data"]), flush=True)
    for name, r in res["regions"].items():
        print("TT_REGION %s m_llbb=[%s,%s) data S=%d L=%d A=%.5f+-%.5f | dA=%.5f sig_gen=%.5f "
              "sig_tw=%.5f sig_tot=%.5f Z=%.3f" % (
                  name, r["lo_GeV"], r["hi_GeV"], r["data_S"], r["data_L"], r["A_data"],
                  r["s_data"], r["dA"], r["sig_gen"], r["sig_tw"], r["sig_total"], r["Z"]),
              flush=True)
        for k, p in r["pred"].items():
            print("TT_PRED %s %s S=%.2f L=%.2f A=%.5f+-%.5f dA=%.5f Z_stat=%.3f" % (
                name, k, p["S"], p["L"], p["A"], p["s_mc"], p["dA"], p["Z_stat"]), flush=True)
    print("TT_H0B Z=%.3f verdict=%s" % (res["H0b"]["Z"], res["H0b"]["verdict"]), flush=True)
    print("TT_H1 Z=%.3f verdict=%s" % (res["H1"]["Z"], res["H1"]["verdict"]), flush=True)
    h2 = res["H2"]
    print("TT_H2 dd=%.5f gen_dd=%.5f tw_dd=%.5f sigma=%.5f Z=%.3f verdict=%s" % (
        h2["dd"], h2["gen_dd"], h2["tw_dd"], h2["sigma"], h2["Z"], h2["verdict"]), flush=True)
    print("TT_H3 %s verdict=%s" % (json.dumps(jsonable(res["H3"].get("per_generator", []))),
                                   res["H3"]["verdict"]), flush=True)
    with open(os.path.join(args.out, "results.json"), "w") as fh:
        json.dump(jsonable(res), fh, indent=1)
    with open(os.path.join(args.out, "files.csv"), "w") as fh:
        fh.write("group,key,bytes,adler32,source\n")
        for r in rows:
            fh.write(",".join(str(x) for x in r) + "\n")
    np.savez_compressed(os.path.join(args.out, "hists.npz"), m_edges=tc.M_EDGES,
                        d_edges=tc.D_EDGES,
                        **{"%s_%s" % (g, k): v for g, acc in H.items() for k, v in acc.items()
                           if isinstance(v, np.ndarray)})
    # small human-readable marginals for the write-up (m_llbb 20 GeV and dphi 12 bins)
    with open(os.path.join(args.out, "dphi_by_region.csv"), "w") as fh:
        fh.write("region,dphi_lo,data,pred_nom,pred_ph7,pred_pth1\n")
        preds = {k: tc.combine(H, v)[0] for k, v in tc.TTBAR.items()}
        for name in ("T", "C", "incl"):
            lo_g, hi_g = res["regions"][name]["lo_GeV"], res["regions"][name]["hi_GeV"]
            lo = int(round(lo_g / 5.0))
            hi = tc.NM if hi_g == "inf" else int(round(hi_g / 5.0))
            for j in range(tc.ND):
                fh.write("%s,%.4f,%.1f,%.3f,%.3f,%.3f\n" % (
                    name, tc.D_EDGES[j], H["data"]["os"][lo:hi, j].sum(),
                    preds["nom"][lo:hi, j].sum(), preds["ph7"][lo:hi, j].sum(),
                    preds["pth1"][lo:hi, j].sum()))
    print("TT_DONE total_s=%.0f" % (time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
