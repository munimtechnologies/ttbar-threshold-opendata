# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""ttthresh_core 0.1.0 -- numpy-only core of the pre-registered test PREREG-v0.1.md.

Question: in the public ATLAS 2015-16 data (36 fb-1, 13 TeV), does the excess of
small lepton azimuthal separation (stronger-than-predicted top-quark spin correlation)
sit near the top-pair production threshold, where toponium would put it, or is it spread
over all masses?

Contents
* event variables from two leptons and two jets: delta-phi(l,l), m(ll), m(llbb);
* 2D histograms in m(llbb) (5 GeV bins, 0-2000 GeV, overflow in the last bin) x
  delta-phi (12 bins of pi/12);
* regions fixed by quantiles of the NOMINAL prediction (never by data);
* the asymmetry A = (N[dphi < pi/2] - N[dphi >= pi/2]) / N with its statistical error,
  generator and tW envelopes, and the pre-registered verdicts (PREREG-v0.1 sec. 5).
"""
import math

import numpy as np

VERSION = "0.1.0"
M_EDGES = np.arange(0.0, 2000.0 + 1e-9, 5.0)        # 401 edges -> 400 bins
D_EDGES = np.linspace(0.0, np.pi, 13)               # 12 bins of pi/12
NM = len(M_EDGES) - 1
ND = len(D_EDGES) - 1
HALF = 6                                            # first 6 dphi bins = dphi < pi/2
TTBAR = {"nom": "ttbar_nom", "ph7": "ttbar_ph7", "pth1": "ttbar_pth1"}
BKG = ("tW_DR", "Ztautau", "diboson", "ttV")
ALT_TW = "tW_DS"
Q_T = 0.20      # threshold region T: lowest 20 % of the nominal prediction in m(llbb)
Q_C = 0.50      # control region C: upper 50 %
INFO_Q = (0.20, 0.40, 0.70)

# Pre-registered thresholds (PREREG-v0.1 sec. 5). Never change them after data.
GATE_RATIO = (0.85, 1.15)
GATE_TTFRAC = 0.80
GATE_NDATA = 20000
Z_H0B = 2.0
Z_H1 = 2.0
Z_H2 = 1.5
Z_H3 = 2.0


# ----------------------------------------------------------------------------- kinematics
def p4(pt, eta, phi, e):
    pt = np.asarray(pt, float)
    eta = np.asarray(eta, float)
    phi = np.asarray(phi, float)
    return pt * np.cos(phi), pt * np.sin(phi), pt * np.sinh(eta), np.asarray(e, float)


def mass(px, py, pz, en):
    m2 = np.asarray(en) ** 2 - np.asarray(px) ** 2 - np.asarray(py) ** 2 - np.asarray(pz) ** 2
    return np.sqrt(np.clip(m2, 0.0, None))


def delta_phi(a, b):
    d = np.abs(np.asarray(a, float) - np.asarray(b, float)) % (2.0 * np.pi)
    return np.where(d > np.pi, 2.0 * np.pi - d, d)


def event_vars(lpt, leta, lphi, le, jpt, jeta, jphi, je):
    """Arrays of shape [N, 2] (two leptons, two chosen jets) -> dphi_ll, m_ll, m_llbb."""
    lx, ly, lz, lE = p4(lpt, leta, lphi, le)
    jx, jy, jz, jE = p4(jpt, jeta, jphi, je)
    lphi = np.asarray(lphi, float)
    dphi = delta_phi(lphi[:, 0], lphi[:, 1])
    mll = mass(lx.sum(1), ly.sum(1), lz.sum(1), lE.sum(1))
    mllbb = mass(lx.sum(1) + jx.sum(1), ly.sum(1) + jy.sum(1), lz.sum(1) + jz.sum(1),
                 lE.sum(1) + jE.sum(1))
    return dphi, mll, mllbb


# ----------------------------------------------------------------------------- histograms
def zeros():
    return np.zeros((NM, ND))


def hist2(mllbb, dphi, w):
    """Weighted 2D histogram and sum of squared weights; overflow goes into the last bin."""
    m = np.clip(np.asarray(mllbb, float), 0.0, M_EDGES[-1] - 1e-6)
    d = np.clip(np.asarray(dphi, float), 0.0, np.pi)
    w = np.asarray(w, float)
    h, _, _ = np.histogram2d(m, d, bins=[M_EDGES, D_EDGES], weights=w)
    h2, _, _ = np.histogram2d(m, d, bins=[M_EDGES, D_EDGES], weights=w * w)
    return h, h2


def quantile_bin(marg, q):
    """First m(llbb) bin index k with cumulative content >= q * total."""
    c = np.cumsum(np.asarray(marg, float))
    tot = c[-1]
    if not tot > 0:
        raise ValueError("empty prediction")
    return int(np.searchsorted(c, q * tot, side="left"))


def region_sl(h, lo, hi):
    return float(h[lo:hi, :HALF].sum()), float(h[lo:hi, HALF:].sum())


def asym(s, l, w2s, w2l):
    """A = (S - L) / (S + L) and its error from the sums of squared weights."""
    t = s + l
    if not t > 0:
        return float("nan"), float("nan")
    a = (s - l) / t
    var = (2.0 * l / t ** 2) ** 2 * w2s + (2.0 * s / t ** 2) ** 2 * w2l
    return float(a), float(math.sqrt(max(var, 0.0)))


# ----------------------------------------------------------------------------- predictions
def _get(H, g, k):
    return H[g][k] if g in H and k in H[g] else zeros()


def combine(H, ttbar_key, tw_key="tW_DR"):
    """Prediction (OS) = ttbar + tW + Z->tautau + diboson + ttV + residual non-prompt term.
    Residual non-prompt term = data SS - all nominal MC SS (PREREG-v0.1 sec. 3.4)."""
    groups = [ttbar_key, tw_key] + [g for g in BKG if g != "tW_DR"]
    os_ = sum(_get(H, g, "os") for g in groups)
    os2 = sum(_get(H, g, "os2") for g in groups)
    nom = [TTBAR["nom"]] + list(BKG)
    fake = H["data"]["ss"] - sum(_get(H, g, "ss") for g in nom)
    fake2 = H["data"]["ss"] + sum(_get(H, g, "ss2") for g in nom)
    return os_ + fake, os2 + fake2, fake


def _finite(*xs):
    return all(isinstance(x, (int, float)) and math.isfinite(x) for x in xs)


def verdict_three(z, thr, hi, mid, lo):
    if not _finite(z):
        return "NOT GRADABLE"
    if z >= thr:
        return hi
    if z > 0:
        return mid
    return lo


def verdict_h2(z):
    if not _finite(z):
        return "NOT GRADABLE"
    if z >= Z_H2:
        return "CONCENTRATED AT THRESHOLD"
    if z <= -Z_H2:
        return "CONCENTRATED AT HIGH MASS"
    return "NOT RESOLVED"


def gate(n_data, n_pred, ttfrac):
    r = n_data / n_pred if n_pred > 0 else float("nan")
    ok = (_finite(r) and GATE_RATIO[0] <= r <= GATE_RATIO[1] and ttfrac >= GATE_TTFRAC
          and n_data >= GATE_NDATA)
    return ("PASS" if ok else "FAIL"), r


def grade(H):
    """H: {'data': {'os','ss'}, group: {'os','os2','ss','ss2'}} -> results dict."""
    preds = {k: combine(H, v) for k, v in TTBAR.items()}
    preds["nomDS"] = combine(H, TTBAR["nom"], ALT_TW)
    d = H["data"]["os"]
    pn = preds["nom"][0]
    marg = pn.sum(1)
    kT = quantile_bin(marg, Q_T)
    kC = quantile_bin(marg, Q_C)
    kq = [quantile_bin(marg, q) for q in INFO_Q]
    regions = {"T": (0, kT + 1), "C": (kC + 1, NM), "incl": (0, NM),
               "B1": (0, kq[0] + 1), "B2": (kq[0] + 1, kq[1] + 1),
               "B3": (kq[1] + 1, kq[2] + 1), "B4": (kq[2] + 1, NM)}
    out = {"ttthresh_core": VERSION, "regions": {}, "yields": {}}
    for name, (lo, hi) in regions.items():
        s, l = region_sl(d, lo, hi)
        ad, sd = asym(s, l, s, l)
        r = {"lo_GeV": float(M_EDGES[lo]), "hi_GeV": float(M_EDGES[hi]) if hi < NM else "inf",
             "data_S": s, "data_L": l, "A_data": ad, "s_data": sd, "pred": {}}
        for k, (p, p2, _) in preds.items():
            ps, pl = region_sl(p, lo, hi)
            w2s, w2l = region_sl(p2, lo, hi)
            ap, sp = asym(ps, pl, w2s, w2l)
            zs = (ad - ap) / math.sqrt(sd ** 2 + sp ** 2) if _finite(ad, ap, sd, sp) and (sd ** 2 + sp ** 2) > 0 else float("nan")
            r["pred"][k] = {"S": ps, "L": pl, "A": ap, "s_mc": sp, "dA": ad - ap, "Z_stat": zs}
        an = r["pred"]["nom"]["A"]
        sig_gen = max(abs(r["pred"]["ph7"]["A"] - an), abs(r["pred"]["pth1"]["A"] - an))
        sig_tw = abs(r["pred"]["nomDS"]["A"] - an)
        tot = math.sqrt(sd ** 2 + r["pred"]["nom"]["s_mc"] ** 2 + sig_gen ** 2 + sig_tw ** 2)
        r.update({"sig_gen": sig_gen, "sig_tw": sig_tw, "sig_total": tot,
                  "dA": ad - an, "Z": (ad - an) / tot if tot > 0 else float("nan")})
        out["regions"][name] = r
    # H2: double difference T - C
    T, C = out["regions"]["T"], out["regions"]["C"]
    dd = T["dA"] - C["dA"]
    gen_dd = max(abs((T["pred"][g]["A"] - T["pred"]["nom"]["A"])
                     - (C["pred"][g]["A"] - C["pred"]["nom"]["A"])) for g in ("ph7", "pth1"))
    tw_dd = abs((T["pred"]["nomDS"]["A"] - T["pred"]["nom"]["A"])
                - (C["pred"]["nomDS"]["A"] - C["pred"]["nom"]["A"]))
    s_dd = math.sqrt(T["s_data"] ** 2 + C["s_data"] ** 2 + T["pred"]["nom"]["s_mc"] ** 2
                     + C["pred"]["nom"]["s_mc"] ** 2 + gen_dd ** 2 + tw_dd ** 2)
    z2 = dd / s_dd if s_dd > 0 else float("nan")
    out["H2"] = {"dd": dd, "gen_dd": gen_dd, "tw_dd": tw_dd, "sigma": s_dd, "Z": z2,
                 "verdict": verdict_h2(z2)}
    # yields and gate
    n_data = float(d.sum())
    n_pred = float(pn.sum())
    tt = float(_get(H, TTBAR["nom"], "os").sum())
    ttfrac = tt / n_pred if n_pred > 0 else float("nan")
    g, ratio = gate(n_data, n_pred, ttfrac)
    fake_tot = float(preds["nom"][2].sum())
    ylds = {"data_os": n_data, "pred_nom_os": n_pred, "ttbar_nom_os": tt, "ttbar_frac": ttfrac,
            "data_over_pred": ratio, "residual_nonprompt": fake_tot,
            "data_ss": float(H["data"]["ss"].sum())}
    for k in ("ph7", "pth1", "nomDS"):
        ylds["pred_%s_os" % k] = float(preds[k][0].sum())
    lo, hi = regions["T"]
    ylds["R_T_shape"] = ((float(d[lo:hi].sum()) / n_data) / (float(pn[lo:hi].sum()) / n_pred)
                         if n_data > 0 and n_pred > 0 else float("nan"))
    out["yields"] = ylds
    out["gate"] = {"verdict": g, "ratio": ratio, "ttbar_frac": ttfrac, "n_data": n_data}
    I = out["regions"]["incl"]
    if g != "PASS":
        ng = "NOT GRADABLE (gate D0 %s)" % g
        out["H0b"] = {"Z": I["Z"], "verdict": ng}
        out["H1"] = {"Z": T["Z"], "verdict": ng}
        out["H2"]["verdict"] = ng
        out["H3"] = {"verdict": ng}
        return out
    out["H0b"] = {"Z": I["Z"], "verdict": verdict_three(I["Z"], Z_H0B, "REPRODUCED", "WEAK",
                                                         "NOT REPRODUCED")}
    out["H1"] = {"Z": T["Z"], "verdict": verdict_three(T["Z"], Z_H1, "EXCESS SEEN", "WEAK",
                                                       "NOT SEEN")}
    h3 = [(k, T["pred"][k]["dA"], T["pred"][k]["Z_stat"]) for k in ("nom", "ph7", "pth1")]
    if not all(_finite(a, z) for _, a, z in h3):
        v3 = "NOT GRADABLE"
    elif all(a > 0 and z >= Z_H3 for _, a, z in h3):
        v3 = "ROBUST"
    else:
        v3 = "NOT ROBUST"
    out["H3"] = {"per_generator": [{"gen": k, "dA": a, "Z_stat": z} for k, a, z in h3],
                 "verdict": v3}
    return out
