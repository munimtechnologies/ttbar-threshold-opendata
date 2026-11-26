# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""grade_job 0.1.0 -- the grade step of PREREG-v0.2 (tsplit), ttbar-threshold-opendata.

Reads, at ONE fixed 40-hex commit of the repository (so no input can change afterwards):
  results/tsplit-keys-v1/keys_T.csv.gz and keys_summary.json      (job A, keys_job 0.1.0)
  <part dir>/match_<group>_p<k>.csv.gz and match_<group>_p<k>.json  (match_job 0.1.0)
  tsplit/tsplit_core.py                                            (PINNED by sha256)
and grades PREREG-v0.2 as fixed by AMENDMENTS 0.2.1, 0.2.2 and 0.2.3:
  gates G0 (+ consistency), FILES, G1, G2, G3, CLOSURE -> H1 (R_C band), H1r (68 % interval),
  plus the information-only items (pth1 split, smallest-barcode rule, share of S below
  380 GeV, single-lepton share, runNumber agreement).

Every number that the prereg fixes (bins, bands, gates, bootstrap seed and size, the split
formulae) comes from tsplit_core; nothing is retyped here. Outputs: /out/results.json and
/out/grade.txt (GRADE_* lines).

    python grade_job.py --ref <40-hex commit> --tsplit-sha256 <hex> --work /work --out /out
"""
import argparse
import collections
import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
import sys
import time
import urllib.request

VERSION = "0.1.0"
RAW = "https://raw.githubusercontent.com/munimtechnologies/ttbar-threshold-opendata/%s/"
KEYS_DIR = "results/tsplit-keys-v1"
TSPLIT_PATH = "tsplit/tsplit_core.py"
MATCH_HEADER = "dsid,event,run,file,entry,n_t,n_tbar,mtt_l,mtt_s,st_t,st_tbar,s62"
KEYS_HEADER = "dsid,run,event,group,w,dphi,mllbb,short"

# Fixed by PREREG-v0.2 / AMENDMENT-0.2.2 (DSIDs read in PHYSLITE, file counts, parts).
GROUPS = {"nom": {"dsid": 410470, "files": 190, "nparts": 4, "summary": "ttbar_nom"},
          "ph7": {"dsid": 411234, "files": 35, "nparts": 1, "summary": "ttbar_ph7"},
          "pth1": {"dsid": 601491, "files": 28, "nparts": 1, "summary": "ttbar_pth1"}}
SINGLE_LEP = {"ph7": 411233, "pth1": 601497}   # not read in PHYSLITE -> um (PREREG-v0.2)
# Region-T prediction of ttthresh-v2 (results/ttthresh-v2/results.json regions.T.pred), the same
# constants as keys_job 0.1.0 (AMENDMENT-0.2.1 s4).
PRED_T = {"nom": (9523.284335451435, 9974.533948080054),
          "ph7": (8530.027513660552, 9266.67752649883),
          "pth1": (8393.545212568833, 8837.209630395851)}
REF_A_T = {"nom": -0.02314, "ph7": -0.04139}   # rounded values quoted in PREREG-v0.2
G1_FLOOR = 0.98
G2_FLOOR = 0.99
CONSIST_TOL = 1e-6      # relative, AMENDMENT-0.2.3 s2
CLOSURE_TOL = 1e-9      # PREREG-v0.2: C + S = Delta checked to 1e-9
REASONS = ("not_read", "edu_dup", "phys_missing", "phys_dup", "no_pair")


def default_dirs():
    d = {("nom", p): "results/tsplit-match-nom-p%d-v1" % p for p in range(4)}
    d[("ph7", 0)] = "results/tsplit-match-ph7-v1"
    d[("pth1", 0)] = "results/tsplit-match-pth1-v1"
    return d


# ----------------------------------------------------------------------------- parsing
def _check_header(text, want):
    first = text.split("\n", 1)[0].strip()
    if first != want:
        raise ValueError("header %r != %r" % (first, want))


def parse_keys(text):
    """keys_T.csv text -> list of row dicts (file order kept)."""
    _check_header(text, KEYS_HEADER)
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        sh = r["short"].strip()
        if sh not in ("0", "1"):
            raise ValueError("bad short flag %r" % (sh,))
        out.append({"dsid": int(r["dsid"]), "run": int(r["run"]), "event": int(r["event"]),
                    "group": r["group"].strip(), "w": float(r["w"]), "short": sh == "1"})
    return out


def parse_match(text):
    """match_<group>_p<k>.csv text -> list of row dicts."""
    _check_header(text, MATCH_HEADER)
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        out.append({"dsid": int(r["dsid"]), "event": int(r["event"]), "run": int(r["run"]),
                    "file": int(r["file"]), "entry": int(r["entry"]),
                    "n_t": int(r["n_t"]), "n_tbar": int(r["n_tbar"]),
                    "mtt_l": float(r["mtt_l"]), "mtt_s": float(r["mtt_s"]),
                    "st_t": int(r["st_t"]), "st_tbar": int(r["st_tbar"]), "s62": int(r["s62"])})
    return out


def parse_part_dirs(overrides):
    """overrides: list of 'group:part=repo/dir'. Returns {(group, part): dir}."""
    d = default_dirs()
    for o in overrides or []:
        m = re.fullmatch(r"(nom|ph7|pth1):(\d+)=([A-Za-z0-9_./-]+)", o.strip())
        if not m:
            raise ValueError("bad --part-dir %r" % (o,))
        g, p, path = m.group(1), int(m.group(2)), m.group(3).rstrip("/")
        if not 0 <= p < GROUPS[g]["nparts"]:
            raise ValueError("part %d out of range for %s" % (p, g))
        if ".." in path.split("/"):
            raise ValueError("bad path %r" % (path,))
        d[(g, p)] = path
    return d


# ----------------------------------------------------------------------------- checks
def check_parts(group, summaries, keys_sha, tsplit_sha=""):
    """AMENDMENT-0.2.2 s4 / 0.2.3 s3: every file of the sample read exactly once, by the
    expected code, with the same keys file. summaries: list of match_*.json dicts."""
    g = GROUPS[group]
    probs = []
    parts = sorted(int(s.get("part", -1)) for s in summaries)
    if parts != list(range(g["nparts"])):
        probs.append("parts %s != 0..%d" % (parts, g["nparts"] - 1))
    seen = collections.Counter()
    for s in summaries:
        tag = "part %s" % (s.get("part"),)
        if s.get("match_job") != "0.1.0":
            probs.append("%s match_job %r" % (tag, s.get("match_job")))
        if s.get("group") != group:
            probs.append("%s group %r" % (tag, s.get("group")))
        if int(s.get("dsid", -1)) != g["dsid"]:
            probs.append("%s dsid %r" % (tag, s.get("dsid")))
        if int(s.get("nparts", -1)) != g["nparts"]:
            probs.append("%s nparts %r" % (tag, s.get("nparts")))
        if int(s.get("files_total", -1)) != g["files"]:
            probs.append("%s files_total %r" % (tag, s.get("files_total")))
        if str(s.get("keys_sha256", "")).lower() != str(keys_sha).lower():
            probs.append("%s keys_sha256 differs" % tag)
        ps = str(s.get("tsplit_sha256", "")).lower()
        if re.fullmatch(r"[0-9a-f]{64}", str(tsplit_sha).lower()) and ps != str(tsplit_sha).lower():
            probs.append("%s tsplit_sha256 differs" % tag)
        if int(s.get("failed_files", 1)) != 0:
            probs.append("%s failed_files %r" % (tag, s.get("failed_files")))
        for rec in s.get("files", []) or []:
            if rec.get("status") == "OK":
                seen[int(rec["file"])] += 1
            else:
                probs.append("%s file %s status %s" % (tag, rec.get("file"), rec.get("status")))
    missing = [i for i in range(g["files"]) if seen[i] == 0]
    twice = sorted(i for i, c in seen.items() if c > 1)
    extra = sorted(i for i in seen if not 0 <= i < g["files"])
    if missing:
        probs.append("%d files not read" % len(missing))
    if twice:
        probs.append("files read twice: %s" % twice[:10])
    if extra:
        probs.append("unknown file indices: %s" % extra[:10])
    return {"ok": not probs, "problems": probs, "files_read": len(seen)}


# ----------------------------------------------------------------------------- classify
def classify(rows, phys_rows, phys_dsid, ts):
    """AMENDMENT-0.2.2 s5 with the precedence of AMENDMENT-0.2.3 s4.
    rows: keys_T rows of ONE group (file order). phys_rows: all match rows of that group.
    Returns (list of per-row dicts, {event: [match rows]}, n_foreign_rows)."""
    edu = collections.Counter((r["dsid"], r["event"]) for r in rows)
    phys = {}
    foreign = 0
    for m in phys_rows:
        if m["dsid"] != phys_dsid:
            foreign += 1
            continue
        phys.setdefault(m["event"], []).append(m)
    out = []
    for r in rows:
        reason, m = None, None
        if r["dsid"] != phys_dsid:
            reason = "not_read"
        elif edu[(r["dsid"], r["event"])] > 1:
            reason = "edu_dup"
        else:
            hits = phys.get(r["event"], [])
            if not hits:
                reason = "phys_missing"
            elif len(hits) > 1:
                reason = "phys_dup"
            else:
                m = hits[0]
                if ts.mass_bin(m["mtt_l"]) is None:
                    reason = "no_pair"
        if reason is None:
            b = ts.mass_bin(m["mtt_l"])
            bs = ts.mass_bin(m["mtt_s"]) or ts.UM
        else:
            b = bs = ts.UM
        out.append({"dsid": r["dsid"], "event": r["event"], "run": r["run"], "w": r["w"],
                    "short": r["short"], "bin": b, "bin_s": bs, "reason": reason, "m": m})
    return out, phys, foreign


def match_stats(cls, phys, phys_dsid):
    """Numbers behind G1 and G2 for one group, plus um reasons and runNumber agreement."""
    sel = [c for c in cls if c["dsid"] == phys_dsid]
    mat = [c for c in sel if c["reason"] is None]
    sel_w = sum(c["w"] for c in sel)
    mat_w = sum(c["w"] for c in mat)
    reasons = {k: {"n": 0, "w": 0.0} for k in REASONS}
    for c in cls:
        if c["reason"] is not None:
            reasons[c["reason"]]["n"] += 1
            reasons[c["reason"]]["w"] += c["w"]
    s62 = sum(1 for c in mat if int(c["m"]["s62"]) == 1)
    once = sorted({c["event"] for c in sel if len(phys.get(c["event"], [])) == 1})
    both = sum(1 for e in once if phys[e][0]["n_t"] >= 1 and phys[e][0]["n_tbar"] >= 1)
    run_eq = sum(1 for c in mat if c["m"]["run"] == c["run"])
    run_none = sum(1 for c in mat if c["m"]["run"] == -1)
    return {"selected_n": len(sel), "selected_w": sel_w, "matched_n": len(mat),
            "matched_w": mat_w, "g1_frac": (mat_w / sel_w) if sel_w > 0 else None,
            "g1_frac_unweighted": (len(mat) / len(sel)) if sel else None,
            "reasons": reasons, "g2_s62_n": s62,
            "g2_s62_frac": (s62 / len(mat)) if mat else None,
            "g2_once_keys": len(once), "g2_both_n": both,
            "g2_both_frac": (both / len(once)) if once else None,
            "run_equal": run_eq, "run_absent": run_none,
            "run_differ": len(mat) - run_eq - run_none}


# ----------------------------------------------------------------------------- grade
def _close(a, b, scale):
    return abs(a - b) <= CONSIST_TOL * max(1.0, abs(scale))


def grade(keys_text, keys_summary, parts, ts, keys_sha, tsplit_sha="", n_rep=None, boot=True):
    """parts: {group: [(match_csv_text, match_summary_dict), ...]}. Returns the results dict."""
    res = {"grade_job": VERSION, "tsplit_core": ts.VERSION, "keys_sha256": keys_sha,
           "tsplit_sha256": tsplit_sha}
    rows = parse_keys(keys_text)
    by_group = {g: [r for r in rows if r["group"] == g] for g in GROUPS}
    res["keys_rows"] = len(rows)
    res["keys_rows_other_group"] = len(rows) - sum(len(v) for v in by_group.values())

    # ---- G0 and consistency with job A (AMENDMENT-0.2.3 s2)
    g0 = keys_summary.get("G0", {}) or {}
    tt = {}
    for g, rs in by_group.items():
        tt[g] = (sum(r["w"] for r in rs if r["short"]), sum(r["w"] for r in rs if not r["short"]))
    cons = {"rows": len(rows) == int(keys_summary.get("rows_keys_T", -1))}
    for g, spec in GROUPS.items():
        gs = keys_summary["groups"][spec["summary"]]
        scale = abs(gs["S_T"]) + abs(gs["L_T"])
        cons["sl_" + g] = _close(tt[g][0], gs["S_T"], scale) and _close(tt[g][1], gs["L_T"], scale)
    bkg = (float(g0["bkg_T"][0]), float(g0["bkg_T"][1]))
    bkg_re = ts.bkg_from_prediction(PRED_T["nom"], tt["nom"])
    pscale = PRED_T["nom"][0] + PRED_T["nom"][1]
    cons["bkg"] = _close(bkg[0], bkg_re[0], pscale) and _close(bkg[1], bkg_re[1], pscale)
    g0_pass = g0.get("verdict") == "PASS" and keys_summary.get("xcheck_all") is True
    res["G0"] = {"verdict": "PASS" if g0_pass else "FAIL", "job_A": g0.get("checks"),
                 "consistency": cons, "consistency_pass": all(cons.values()),
                 "bkg_T": list(bkg), "bkg_T_recomputed": list(bkg_re),
                 "tt_T": {g: list(v) for g, v in tt.items()}}

    # ---- per group: files, classification, match statistics
    cls, files, stats, ev, ev_s = {}, {}, {}, {}, {}
    for g, spec in GROUPS.items():
        plist = parts.get(g, [])
        files[g] = check_parts(g, [p[1] for p in plist], keys_sha, tsplit_sha)
        prow = []
        for text, _ in plist:
            prow.extend(parse_match(text))
        c, phys, foreign = classify(by_group[g], prow, spec["dsid"], ts)
        cls[g] = c
        st = match_stats(c, phys, spec["dsid"])
        st["phys_rows"] = len(prow)
        st["phys_foreign_rows"] = foreign
        st["phys_keys_dup"] = sum(1 for v in phys.values() if len(v) > 1)
        lep = SINGLE_LEP.get(g)
        st["single_lep_dsid"] = lep
        st["single_lep_w"] = sum(x["w"] for x in c if lep is not None and x["dsid"] == lep)
        stats[g] = st
        ev[g] = [(x["bin"], x["w"], x["short"]) for x in c]
        ev_s[g] = [(x["bin_s"], x["w"], x["short"]) for x in c]
    res["files"] = files
    res["match"] = stats

    sl = {g: ts.with_bkg(ts.accumulate(ev[g]), bkg) for g in GROUPS}
    dec = ts.decompose(sl["nom"], sl["ph7"])
    tot = {g: sum(v[0] + v[1] for v in sl[g].values()) for g in GROUPS}
    for g in GROUPS:
        stats[g]["single_lep_share"] = stats[g]["single_lep_w"] / tot[g] if tot[g] else None

    # ---- gates
    gates = {
        "G0": g0_pass and res["G0"]["consistency_pass"],
        "FILES": files["nom"]["ok"] and files["ph7"]["ok"],
        "G1": (ts.gate_fraction(stats["nom"]["matched_w"], stats["nom"]["selected_w"], G1_FLOOR)
               and ts.gate_fraction(stats["ph7"]["matched_w"], stats["ph7"]["selected_w"],
                                    G1_FLOOR)),
        "G2": (ts.gate_fraction(stats["nom"]["g2_s62_n"], stats["nom"]["matched_n"], G2_FLOOR)
               and ts.gate_fraction(stats["ph7"]["g2_both_n"], stats["ph7"]["g2_once_keys"],
                                    G2_FLOOR)),
        "G3": ts.gate_g3(dec["f_nom"][ts.UM], dec["f_ph7"][ts.UM]),
        "CLOSURE": dec["closure"] <= CLOSURE_TOL,
    }
    gates_ok = all(gates.values())
    res["gates"] = {k: ("PASS" if v else "FAIL") for k, v in gates.items()}
    res["gates_ok"] = gates_ok

    # ---- H1, H1r
    rc = dec["R_C"]
    res["split"] = dec
    res["split_check"] = {
        "total_nom": tot["nom"], "pred_nom_total": PRED_T["nom"][0] + PRED_T["nom"][1],
        "A_pred_nom": (PRED_T["nom"][0] - PRED_T["nom"][1]) / (PRED_T["nom"][0] + PRED_T["nom"][1]),
        "A_pred_ph7": (PRED_T["ph7"][0] - PRED_T["ph7"][1]) / (PRED_T["ph7"][0] + PRED_T["ph7"][1]),
        "A_T_prereg": REF_A_T, "Delta_prereg": 0.01825}
    res["H1"] = ts.grade_h1(rc, gates_ok)
    res["R_C_outside_0_1"] = (rc is not None) and (rc < 0.0 or rc > 1.0)
    if boot:
        reps = ts.BOOT_REPS if n_rep is None else int(n_rep)
        rcs = ts.bootstrap_rc(ev["nom"], ev["ph7"], bkg, n_rep=reps, seed=ts.BOOT_SEED)
        lo, hi = ts.percentile(rcs, 16), ts.percentile(rcs, 84)
        res["bootstrap"] = {"reps": reps, "seed": ts.BOOT_SEED, "none": sum(1 for x in rcs if x is None),
                            "p16": lo, "p84": hi, "R_C": rcs}
        res["H1r"] = ts.grade_h1r(lo, hi, gates_ok)
    else:
        res["bootstrap"] = None
        res["H1r"] = "NOT GRADABLE"

    # ---- information only (PREREG-v0.2 'not graded')
    info = {}
    pth = ts.decompose(sl["nom"], sl["pth1"])
    info["pth1_vs_nom"] = {"valid": files["pth1"]["ok"] and ts.gate_fraction(
        stats["pth1"]["matched_w"], stats["pth1"]["selected_w"], G1_FLOOR) and gates["G0"],
        "A_nom": pth["A_nom"], "A_pth1": pth["A_ph7"], "Delta": pth["Delta"], "C": pth["C"],
        "S": pth["S"], "R_C": pth["R_C"], "band": ts.band(pth["R_C"])}
    sm = ts.decompose(ts.with_bkg(ts.accumulate(ev_s["nom"]), bkg),
                      ts.with_bkg(ts.accumulate(ev_s["ph7"]), bkg))
    info["smallest_barcode"] = {"R_C": sm["R_C"], "band": ts.band(sm["R_C"]), "C": sm["C"],
                                "S": sm["S"]}
    info["S_lt380_share"] = (dec["S_lt380"] / dec["S"]) if dec["S"] != 0.0 else None
    res["info"] = info
    return res


# ----------------------------------------------------------------------------- report
def _f(x, nd=6):
    if x is None:
        return "None"
    if isinstance(x, float) and not math.isfinite(x):
        return "nan"
    return ("%." + str(nd) + "f") % x


def grade_lines(res):
    sp = res["split"]
    st = res["match"]
    b = res.get("bootstrap") or {}
    lines = [
        "GRADE_GATES " + " ".join("%s=%s" % (k, v) for k, v in res["gates"].items()),
        "GRADE_SPLIT A_nom=%s A_ph7=%s Delta=%s C=%s S=%s R_C=%s closure=%.3g C_mass=%s C_bkg=%s "
        "C_um=%s" % (_f(sp["A_nom"]), _f(sp["A_ph7"]), _f(sp["Delta"]), _f(sp["C"]), _f(sp["S"]),
                     _f(sp["R_C"], 4), sp["closure"], _f(sp["C_mass"]), _f(sp["C_bkg"]),
                     _f(sp["C_um"])),
        "GRADE_G1 nom=%s ph7=%s pth1=%s" % (_f(st["nom"]["g1_frac"], 4), _f(st["ph7"]["g1_frac"], 4),
                                            _f(st["pth1"]["g1_frac"], 4)),
        "GRADE_G2 nom_s62=%s ph7_both=%s" % (_f(st["nom"]["g2_s62_frac"], 4),
                                             _f(st["ph7"]["g2_both_frac"], 4)),
        "GRADE_G3 f_um_nom=%s f_um_ph7=%s" % (_f(sp["f_nom"]["um"], 4), _f(sp["f_ph7"]["um"], 4)),
        "GRADE_H1 %s (R_C=%s)" % (res["H1"], _f(sp["R_C"], 4)),
        "GRADE_H1R %s (p16=%s p84=%s reps=%s none=%s)" % (res["H1r"], _f(b.get("p16"), 4),
                                                         _f(b.get("p84"), 4), b.get("reps"),
                                                         b.get("none")),
        "GRADE_INFO pth1_R_C=%s smallest_R_C=%s S_lt380_share=%s single_lep_ph7=%s "
        "single_lep_pth1=%s" % (_f(res["info"]["pth1_vs_nom"]["R_C"], 4),
                                _f(res["info"]["smallest_barcode"]["R_C"], 4),
                                _f(res["info"]["S_lt380_share"], 4),
                                _f(st["ph7"]["single_lep_share"], 4),
                                _f(st["pth1"]["single_lep_share"], 4)),
    ]
    for g in GROUPS:
        r = st[g]["reasons"]
        lines.append("GRADE_UM %s %s run_equal=%d run_differ=%d run_absent=%d" % (
            g, " ".join("%s=%d" % (k, r[k]["n"]) for k in REASONS), st[g]["run_equal"],
            st[g]["run_differ"], st[g]["run_absent"]))
    for g in GROUPS:
        if res["files"][g]["problems"]:
            lines.append("GRADE_FILES_PROBLEM %s %s" % (g, "; ".join(res["files"][g]["problems"])[:500]))
    return lines


# ----------------------------------------------------------------------------- I/O
def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def raw_url(path, ref):
    if not re.fullmatch(r"[0-9a-f]{40}", ref):
        raise ValueError("ref must be a full 40-hex commit sha")
    return (RAW % ref) + path


def http_get(url, tries=4, timeout=180):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mv2-tsplit-grade/0.1"})
            with urllib.request.urlopen(req, timeout=timeout) as fh:
                return fh.read()
        except Exception as exc:  # pragma: no cover - network
            last = exc
            print("download attempt %d of %s failed: %r" % (k + 1, url, exc), flush=True)
            time.sleep(10 * (k + 1))
    raise SystemExit("FATAL could not download %s: %r" % (url, last))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="full 40-hex commit sha holding every input")
    ap.add_argument("--tsplit-sha256", required=True)
    ap.add_argument("--keys-sha256", default="record")
    ap.add_argument("--part-dir", action="append", default=[], help="group:part=repo/dir")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--local", default="", help="read inputs from this folder (tests only)")
    a = ap.parse_args(argv)
    t0 = time.time()
    os.makedirs(a.out, exist_ok=True)
    inputs = {}

    def get(path):
        if a.local:
            with open(os.path.join(a.local, path), "rb") as fh:
                data = fh.read()
        else:
            data = http_get(raw_url(path, a.ref))
        inputs[path] = {"sha256": sha256_hex(data), "bytes": len(data)}
        print("GRADE_INPUT %s sha256=%s bytes=%d" % (path, inputs[path]["sha256"], len(data)),
              flush=True)
        return data

    if not a.local and not re.fullmatch(r"[0-9a-f]{40}", a.ref):
        raise SystemExit("FATAL --ref must be a full 40-hex commit sha")
    pin = a.tsplit_sha256.lower()
    if not re.fullmatch(r"[0-9a-f]{64}", pin):
        raise SystemExit("FATAL --tsplit-sha256 must be 64 hex")
    tdata = get(TSPLIT_PATH)
    if sha256_hex(tdata) != pin:
        raise SystemExit("FATAL tsplit_core sha256 %s != pinned %s" % (sha256_hex(tdata), pin))
    tdir = os.path.join(a.work, "tsplit-pinned")
    os.makedirs(tdir, exist_ok=True)
    with open(os.path.join(tdir, "tsplit_core.py"), "wb") as fh:
        fh.write(tdata)
    sys.path.insert(0, tdir)
    import tsplit_core as ts
    if ts.VERSION != "0.1.0":
        raise SystemExit("FATAL tsplit_core version %s" % ts.VERSION)

    kraw = get(KEYS_DIR + "/keys_T.csv.gz")
    ksha = sha256_hex(kraw)
    if a.keys_sha256 != "record" and ksha != a.keys_sha256.lower():
        raise SystemExit("FATAL keys sha256 %s != pinned %s" % (ksha, a.keys_sha256))
    ktext = gzip.decompress(kraw).decode("utf-8")
    ksum = json.loads(get(KEYS_DIR + "/keys_summary.json").decode("utf-8"))
    dirs = parse_part_dirs(a.part_dir)
    parts = {g: [] for g in GROUPS}
    for (g, p), d in sorted(dirs.items()):
        craw = get("%s/match_%s_p%d.csv.gz" % (d, g, p))
        jraw = get("%s/match_%s_p%d.json" % (d, g, p))
        parts[g].append((gzip.decompress(craw).decode("utf-8"), json.loads(jraw.decode("utf-8"))))
    res = grade(ktext, ksum, parts, ts, ksha, pin)
    res["ref"] = a.ref
    res["part_dirs"] = {"%s:%d" % k: v for k, v in sorted(dirs.items())}
    res["inputs"] = inputs
    res["seconds"] = round(time.time() - t0, 1)
    lines = grade_lines(res)
    with open(os.path.join(a.out, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, sort_keys=True, default=str)
    with open(os.path.join(a.out, "grade.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    for ln in lines:
        print(ln, flush=True)
    print("GRADE_DONE s=%.0f" % (time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
