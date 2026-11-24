# Apache-2.0. Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Information-only numbers derived from results/ttthresh-v2/results.json (post hoc, NOT graded).

For each of the four pre-registered m(llbb) information bins B1-B4 it prints the data and nominal
prediction yields, their ratio, the shape ratio (ratio / overall ratio) and Delta A. It then splits
the inclusive Delta A exactly into
  within = sum_i f_i^data * (A_i^data - A_i^nom)        (Delta-phi shape inside the mass bins)
  composition = sum_i f_i^data * A_i^nom - A_incl^nom    (data having a different m(llbb) mix)
so that within + composition = Delta A_incl.

Usage: python derive_v2.py results.json [--out derived_v2.csv] [--check derived_v2.csv]
"""
import argparse
import csv
import json
import sys

BINS = ("B1", "B2", "B3", "B4")
COLS = ("bin", "lo_GeV", "hi_GeV", "data_N", "pred_nom_N", "data_over_pred",
        "shape_ratio", "dA_nom")


def derive(res):
    regs = res["regions"]
    rows = []
    n_data = sum(regs[b]["data_S"] + regs[b]["data_L"] for b in BINS)
    n_pred = sum(regs[b]["pred"]["nom"]["S"] + regs[b]["pred"]["nom"]["L"] for b in BINS)
    overall = n_data / n_pred
    within = 0.0
    mix = 0.0
    for b in BINS:
        r = regs[b]
        nd = r["data_S"] + r["data_L"]
        npred = r["pred"]["nom"]["S"] + r["pred"]["nom"]["L"]
        ratio = nd / npred
        rows.append({"bin": b, "lo_GeV": r["lo_GeV"], "hi_GeV": r["hi_GeV"],
                     "data_N": nd, "pred_nom_N": round(npred, 3),
                     "data_over_pred": round(ratio, 6),
                     "shape_ratio": round(ratio / overall, 6),
                     "dA_nom": round(r["pred"]["nom"]["dA"], 6)})
        f = nd / n_data
        within += f * (r["A_data"] - r["pred"]["nom"]["A"])
        mix += f * r["pred"]["nom"]["A"]
    a_incl_nom = regs["incl"]["pred"]["nom"]["A"]
    composition = mix - a_incl_nom
    total = regs["incl"]["dA"]
    summary = {"dA_incl": round(total, 6), "within": round(within, 6),
               "composition": round(composition, 6),
               "composition_share": round(composition / total, 4),
               "closure": round(within + composition - total, 9),
               "overall_data_over_pred": round(overall, 6)}
    return rows, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--out")
    ap.add_argument("--check")
    a = ap.parse_args()
    with open(a.results) as fh:
        res = json.load(fh)
    rows, summary = derive(res)
    for r in rows:
        print("DERIVE_BIN", json.dumps(r))
    print("DERIVE_SPLIT", json.dumps(summary))
    if a.out:
        with open(a.out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS)
            w.writeheader()
            for r in rows:
                w.writerow(r)
    if a.check:
        bad = 0
        with open(a.check) as fh:
            given = list(csv.DictReader(fh))
        if len(given) != len(rows):
            print("DERIVE_CHECK row count differs", len(given), len(rows))
            bad += 1
        for g, r in zip(given, rows):
            for k in ("data_N", "pred_nom_N", "data_over_pred", "shape_ratio", "dA_nom"):
                tol = 2e-3 if k == "pred_nom_N" else 2e-6
                if abs(float(g[k]) - float(r[k])) > tol:
                    print("DERIVE_CHECK MISMATCH", r["bin"], k, g[k], r[k])
                    bad += 1
        print("DERIVE_CHECK", "MATCH" if bad == 0 else "MISMATCH %d" % bad)
        return 0 if bad == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
