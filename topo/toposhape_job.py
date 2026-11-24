# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""toposhape_job 0.1.0 -- runs PREREG-TOPO-v0.2.md.

Generates four parton-level (ISR on; FSR, MPI and hadronisation off) Pythia 8.318 top-pair
samples at 13 TeV with both W bosons forced to e or mu, selects e-mu events with simple
ATLAS-like cuts, and predicts, region by region in m(llbb), the shift of the lepton
azimuthal asymmetry A that a below-threshold component of the measured size would cause.
Every graded number is printed on a line starting with TOPO_.
"""
import argparse
import hashlib
import json
import math
import multiprocessing as mp
import os
import sys
import time
import urllib.request

import numpy as np

import toposhape_core as core

VERSION = "0.1.0"
MEASURED_URL = ("https://raw.githubusercontent.com/munimtechnologies/ttbar-threshold-opendata/"
                "main/results/ttthresh-v2/results.json")

COMMON = [
    "Beams:eCM = 13000.",
    "Top:gg2ttbar = on",
    "Top:qqbar2ttbar = on",
    "6:m0 = 172.5",
    "6:doForceWidth = true",
    "6:mWidth = 1.34",
    "24:onMode = off",
    "24:onIfAny = 11 13",
    "PartonLevel:ISR = on",
    "PartonLevel:FSR = off",
    "PartonLevel:MPI = off",
    "HadronLevel:all = off",
    "Next:numberCount = 0",
    "Random:setSeed = on",
]
THR = [
    "TopThreshold:tWidthGreen = 0.1",
    "TopThreshold:thrRegion = 10.",
    "TopThreshold:alphasOrder = 2",
    "TopThreshold:alphasValue = 0.118",
    "TopThreshold:ggSingletFrac = 0.285714",
    "TopThreshold:qqSingletFrac = 0.",
    "TopThreshold:massSel = 0",
    "TopThreshold:psEBeginDamp = 10.",
    "TopThreshold:psEEndDamp = 20.",
]
WINDOW = ["PhaseSpace:mHatMin = 250.", "PhaseSpace:mHatMax = 400."]

SAMPLES = {
    # name: (settings, expected TopThreshold:model, seed)
    "born": (["TopThreshold:model = 0", "TopThreshold:pseudoscalar = off"], 0, 11001),
    "thr3ps": (["TopThreshold:model = 3", "TopThreshold:pseudoscalar = on"] + THR + WINDOW, 3, 11003),
    "thr1": (["TopThreshold:model = 1", "TopThreshold:pseudoscalar = off"] + THR + WINDOW, 1, 11005),
    "thr3": (["TopThreshold:model = 3", "TopThreshold:pseudoscalar = off"] + THR + WINDOW, 3, 11007),
}


# ----------------------------------------------------------------------------- pythia side
def _import_pythia():
    import pythia8mc  # noqa: WPS433
    return pythia8mc


def _info(py):
    return py.infoPython() if hasattr(py, "infoPython") else py.info


def _toponium_e(info):
    v = getattr(info, "toponiumE", None)
    if v is None:
        return None
    if callable(v):
        v = v()
    return float(v)


def _from_top(ev, i, need_w):
    """Walk mother1 through copies; True if a top is reached (through a W if need_w)."""
    j = i
    cur = ev[i].idAbs()
    seen_w = False
    for _ in range(60):
        m = ev[j].mother1()
        if m <= 0:
            return False
        a = ev[m].idAbs()
        if a == 6:
            return seen_w or not need_w
        if a == cur:                      # recoil / shower copy of the same particle
            j = m
            continue
        if a == 24 and need_w and not seen_w:
            seen_w = True
            cur = 24
            j = m
            continue
        return False
    return False


def analyse_event(ev):
    """Return (dphi, mllbb) for a selected e-mu event, else None."""
    leps = []
    bs = []
    for i in range(ev.size()):
        p = ev[i]
        if not p.isFinal():
            continue
        a = p.idAbs()
        if a in (11, 13):
            if _from_top(ev, i, True):
                leps.append(p)
        elif a == 5:
            if _from_top(ev, i, False):
                bs.append(p)
    if len(leps) != 2 or len(bs) != 2:
        return None
    l1, l2 = leps
    if {l1.idAbs(), l2.idAbs()} != {11, 13}:
        return None
    if l1.id() * l2.id() >= 0:
        return None
    for l in leps:
        if l.pT() < 25.0 or abs(l.eta()) > 2.5:
            return None
        if l.idAbs() == 11 and 1.37 < abs(l.eta()) < 1.52:
            return None
    if max(l1.pT(), l2.pT()) < 27.0:
        return None
    for b in bs:
        if b.pT() < 25.0 or abs(b.eta()) > 2.5:
            return None
    px = sum(p.px() for p in leps)
    py_ = sum(p.py() for p in leps)
    pz = sum(p.pz() for p in leps)
    e = sum(p.e() for p in leps)
    if float(core.inv_mass(px, py_, pz, e)) < 15.0:
        return None
    PX = px + sum(p.px() for p in bs)
    PY = py_ + sum(p.py() for p in bs)
    PZ = pz + sum(p.pz() for p in bs)
    E = e + sum(p.e() for p in bs)
    dphi = float(core.delta_phi(l1.phi(), l2.phi()))
    return dphi, float(core.inv_mass(PX, PY, PZ, E))


def run_sample(args):
    name, n_events = args
    settings, model_expected, seed = SAMPLES[name]
    t0 = time.time()
    p8 = _import_pythia()
    py = p8.Pythia()
    ok = True
    bad = []
    for s in COMMON + settings + ["Random:seed = %d" % seed]:
        if not py.readString(s):
            ok = False
            bad.append(s)
    model_read = int(py.settings.mode("TopThreshold:model"))
    if model_read != model_expected:
        ok = False
        bad.append("model readback %d" % model_read)
    if not py.init():
        return {"name": name, "error": "init failed", "settings_ok": ok, "bad": bad}
    m_l, d_l, w_l, e_l = [], [], [], []
    sum_w = 0.0
    sum_w_eneg = 0.0
    sum_w2_eneg = 0.0
    n_ok = n_fail = n_eneg = 0
    e_avail = None
    w_max = 0.0
    for _ in range(n_events):
        if not py.next():
            n_fail += 1
            continue
        info = _info(py)
        w = float(info.weight())
        n_ok += 1
        sum_w += w
        w_max = max(w_max, w)
        ethr = _toponium_e(info)
        if e_avail is None:
            e_avail = ethr is not None
        if ethr is None:
            ethr = float("nan")
        if ethr < 0:
            n_eneg += 1
            sum_w_eneg += w
            sum_w2_eneg += w * w
        r = analyse_event(py.event)
        if r is None:
            continue
        d_l.append(r[0])
        m_l.append(r[1])
        w_l.append(w)
        e_l.append(ethr)
    info = _info(py)
    sigma_mb = float(info.sigmaGen())
    return {
        "name": name, "settings_ok": ok, "bad": bad, "model_read": model_read,
        "sigma_gen_pb": 1e9 * sigma_mb, "sum_w": sum_w, "n_ok": n_ok, "n_fail": n_fail,
        "n_eneg": n_eneg, "sum_w_eneg": sum_w_eneg, "sum_w2_eneg": sum_w2_eneg,
        "e_available": bool(e_avail), "w_max": w_max,
        "mllbb": np.asarray(m_l), "dphi": np.asarray(d_l), "w": np.asarray(w_l),
        "ethr": np.asarray(e_l), "seconds": time.time() - t0,
    }


# ----------------------------------------------------------------------------- measured input
def git_blob_sha1(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def load_measured(path_or_url, out_dir):
    if path_or_url.startswith("http"):
        with urllib.request.urlopen(path_or_url, timeout=60) as r:
            data = r.read()
    else:
        with open(path_or_url, "rb") as f:
            data = f.read()
    with open(os.path.join(out_dir, "measured_ttthresh_v2.json"), "wb") as f:
        f.write(data)
    print("TOPO_MEASURED blob_sha1=%s sha256=%s bytes=%d" % (
        git_blob_sha1(data), hashlib.sha256(data).hexdigest(), len(data)))
    js = json.loads(data.decode())
    for reg, vals in core.MEASURED.items():
        R = js["regions"][reg]
        got = {"A_nom": R["pred"]["nom"]["A"], "dA": R["dA"], "sig_total": R["sig_total"]}
        for k, v in vals.items():
            if abs(got[k] - v) > 1e-12:
                raise SystemExit("TOPO_ABORT measured %s %s = %r differs from frozen %r"
                                 % (reg, k, got[k], v))
    if js.get("gate", {}).get("verdict") != "PASS":
        raise SystemExit("TOPO_ABORT measured gate is not PASS")
    print("TOPO_MEASURED_CHECK frozen values match")


# ----------------------------------------------------------------------------- analysis
def analyse(samples):
    born = samples["born"]
    regs = core.regions_from_reference(born["mllbb"], born["w"])
    out = {"regions": {}, "samples": {}}
    for k, s in samples.items():
        out["samples"][k] = {x: s[x] for x in ("settings_ok", "bad", "model_read", "sigma_gen_pb",
                                                "sum_w", "n_ok", "n_fail", "n_eneg", "sum_w_eneg",
                                                "e_available", "w_max", "seconds")}
        out["samples"][k]["n_pass"] = int(len(s["w"]))
    # cross sections per unit weight (same forced decays in every sample)
    xs = {k: s["sigma_gen_pb"] / s["sum_w"] if s["sum_w"] > 0 else float("nan")
          for k, s in samples.items()}
    t3 = samples["thr3ps"]
    mode = "E" if t3["e_available"] else "DIFF"
    sig_born = samples["born"]["sigma_gen_pb"]
    info = {"mode": mode, "pythia_version": PYTHIA_VERSION,
            "settings_ok": all(s["settings_ok"] for s in samples.values()),
            "n_born_pass": int(len(born["w"]))}
    if mode == "E":
        sig_c = xs["thr3ps"] * t3["sum_w_eneg"]
        cmask = t3["ethr"] < 0
        info["n_c_pass"] = int(cmask.sum())
        info["sigma_c_gen_pb"] = sig_c
    else:
        t1 = samples["thr1"]
        sig_c = t3["sigma_gen_pb"] - t1["sigma_gen_pb"]
        info["sigma_c_gen_pb"] = sig_c
    info["rC"] = sig_c / sig_born if sig_born > 0 else float("nan")
    comp = {}
    diff_tot = None
    for name, reg in regs.items():
        s, l, s2, l2 = core.region_sl(born["mllbb"], born["dphi"], born["w"], reg)
        acc_sm = (s + l) / born["sum_w"]
        a_py_born, _ = core.asym(s, l, s2, l2)
        if mode == "E":
            cs, cl, cs2, cl2 = core.region_sl(t3["mllbb"][cmask], t3["dphi"][cmask],
                                              t3["w"][cmask], reg)
            acc_c = (cs + cl) / t3["sum_w_eneg"] if t3["sum_w_eneg"] > 0 else float("nan")
            a_c, s_ac = core.asym(cs, cl, cs2, cl2)
            n_c_pass = int(((core.mbin(t3["mllbb"][cmask]) >= reg[0])
                            & (core.mbin(t3["mllbb"][cmask]) < reg[1])).sum())
        else:
            t1 = samples["thr1"]
            a3 = core.region_sl(t3["mllbb"], t3["dphi"], t3["w"], reg)
            a1 = core.region_sl(t1["mllbb"], t1["dphi"], t1["w"], reg)
            x3, x1 = xs["thr3ps"], xs["thr1"]
            n, a_c, s_ac = core.diff_component(a3[0] * x3, a3[1] * x3, a3[2] * x3 ** 2,
                                               a3[3] * x3 ** 2, a1[0] * x1, a1[1] * x1,
                                               a1[2] * x1 ** 2, a1[3] * x1 ** 2)
            acc_c = n / sig_c if sig_c > 0 else float("nan")
            n_c_pass = -1
            if name == "incl":
                err = math.sqrt(a3[2] * x3 ** 2 + a3[3] * x3 ** 2 + a1[2] * x1 ** 2
                                + a1[3] * x1 ** 2)
                diff_tot = err / n if n > 0 else float("nan")
        a_sm = core.MEASURED[name]["A_nom"]
        preds = {}
        for sc in core.SIGMA_C_SCAN_PB:
            preds["%.1f" % sc] = core.predict_region(acc_sm, acc_c, a_c, s_ac, a_sm, sc)
        # information only: SM reference from the uncorrelated Pythia Born sample instead
        info_born = core.predict_region(acc_sm, acc_c, a_c, s_ac, a_py_born,
                                        core.SIGMA_C_PRIMARY_PB)
        lo, hi = core.edges_gev(reg)
        comp[name] = {"lo_GeV_parton": lo, "hi_GeV_parton": hi, "acc_sm": acc_sm,
                      "acc_c": acc_c, "A_C": a_c, "s_A_C": s_ac, "A_SM_ref": a_sm,
                      "A_pythia_born": a_py_born, "n_c_pass": n_c_pass, "pred": preds,
                      "info_pred_with_pythia_born_ref": info_born,
                      "measured": core.MEASURED[name]}
    if diff_tot is not None:
        info["diff_relerr"] = diff_tot
    out["regions"] = comp
    out["gate_info"] = info
    g, reasons = core.gate(info)
    out["gate"] = {"verdict": g, "reasons": reasons}
    prim = {k: comp[k]["pred"]["%.1f" % core.SIGMA_C_PRIMARY_PB] for k in comp}
    if g == "PASS":
        out["grades"] = core.grade(prim)
    else:
        out["grades"] = {h: {"verdict": "NOT GRADABLE (gate %s)" % g} for h in ("H1", "H2", "H3", "H4")}
    # information only: the spin effect (thr3 without pseudoscalar correlations), mode E only
    if mode == "E" and samples["thr3"]["e_available"]:
        t = samples["thr3"]
        cm = t["ethr"] < 0
        s, l, s2, l2 = core.region_sl(t["mllbb"][cm], t["dphi"][cm], t["w"][cm], regs["T"])
        out["info_no_pseudoscalar_T"] = {"A_C": core.asym(s, l, s2, l2)[0]}
    return out


def main():
    global PYTHIA_VERSION
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--n-events", type=int, default=300000)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--measured", default=MEASURED_URL)
    ap.add_argument("--probe", action="store_true",
                    help="init every sample, generate a few events, check settings, exit")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    t0 = time.time()
    try:
        from importlib.metadata import version
        PYTHIA_VERSION = version("pythia8mc")
    except Exception as exc:  # noqa: BLE001
        PYTHIA_VERSION = "unknown (%s)" % exc
    print("TOPO_START toposhape_job %s core %s pythia8mc %s numpy %s" % (
        VERSION, core.VERSION, PYTHIA_VERSION, np.__version__))
    if a.probe:
        bad = False
        for n in SAMPLES:
            r = run_sample((n, a.n_events))
            if "error" in r or not r["settings_ok"]:
                bad = True
            print("TOPO_PROBE %s settings_ok=%s bad=%s error=%s model_read=%s n_ok=%s "
                  "n_pass=%s n_eneg=%s e_available=%s sigma_gen_pb=%s" % (
                      n, r.get("settings_ok"), r.get("bad"), r.get("error", ""),
                      r.get("model_read"), r.get("n_ok"), len(r.get("w", [])),
                      r.get("n_eneg"), r.get("e_available"), r.get("sigma_gen_pb")))
        print("TOPO_PROBE_VERDICT %s" % ("FAIL" if bad else "OK"))
        sys.exit(3 if bad else 0)
    load_measured(a.measured, a.out_dir)
    names = list(SAMPLES)
    ctx = mp.get_context("fork")
    with ctx.Pool(a.workers) as pool:
        res = pool.map(run_sample, [(n, a.n_events) for n in names], chunksize=1)
    samples = {r["name"]: r for r in res}
    for r in res:
        if "error" in r:
            print("TOPO_ABORT sample %s: %s %s" % (r["name"], r["error"], r.get("bad")))
            sys.exit(2)
        print("TOPO_SAMPLE %s sigma_gen_pb=%.6g n_ok=%d n_fail=%d n_pass=%d n_eneg=%d "
              "sum_w_eneg=%.6g e_available=%s w_max=%.3f settings_ok=%s s=%.0f" % (
                  r["name"], r["sigma_gen_pb"], r["n_ok"], r["n_fail"], len(r["w"]),
                  r["n_eneg"], r["sum_w_eneg"], r["e_available"], r["w_max"],
                  r["settings_ok"], r["seconds"]))
    np.savez_compressed(os.path.join(a.out_dir, "events.npz"),
                        **{"%s_%s" % (k, x): samples[k][x] for k in samples
                           for x in ("mllbb", "dphi", "w", "ethr")})
    out = analyse(samples)
    gi = out["gate_info"]
    print("TOPO_GATE %s mode=%s rC=%.5f sigma_c_gen_pb=%.5g n_c_pass=%s n_born_pass=%d %s" % (
        out["gate"]["verdict"], gi["mode"], gi["rC"], gi["sigma_c_gen_pb"],
        gi.get("n_c_pass"), gi["n_born_pass"], "; ".join(out["gate"]["reasons"])))
    for name, c in out["regions"].items():
        p = c["pred"]["%.1f" % core.SIGMA_C_PRIMARY_PB]
        print("TOPO_REGION %s parton_m=[%s,%s) acc_sm=%.5f acc_c=%.5f A_C=%.4f+-%.4f "
              "A_SM_ref=%.4f f=%.5f dA_pred=%.5f+-%.5f measured_dA=%.5f" % (
                  name, c["lo_GeV_parton"], c["hi_GeV_parton"], c["acc_sm"], c["acc_c"],
                  c["A_C"], c["s_A_C"], c["A_SM_ref"], p["f"], p["dA_pred"], p["s_pred"],
                  c["measured"]["dA"]))
        print("TOPO_SCAN %s %s" % (name, " ".join("%s:%.5f" % (k, v["dA_pred"])
                                                  for k, v in c["pred"].items())))
    for h, g in out["grades"].items():
        print("TOPO_%s %s" % (h, json.dumps(g, sort_keys=True)))
    out["job"] = {"toposhape_job": VERSION, "toposhape_core": core.VERSION,
                  "pythia8mc": PYTHIA_VERSION, "numpy": np.__version__,
                  "n_events": a.n_events, "seconds": time.time() - t0}
    with open(os.path.join(a.out_dir, "results.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    print("TOPO_DONE total_s=%.0f" % (time.time() - t0))


PYTHIA_VERSION = "unknown"

if __name__ == "__main__":
    main()
