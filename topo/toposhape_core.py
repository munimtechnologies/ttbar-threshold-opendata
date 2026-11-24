# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""toposhape_core 0.1.0 -- numpy-only core of PREREG-TOPO-v0.2.md.

Question: how much of the small-delta-phi excess measured on the public ATLAS 2015-16 e-mu
data (ttthresh-v2, PREREG-v0.1) would a below-threshold (toponium-like) top-pair component
of the measured size produce, region by region in m(llbb)?

The component's shape (acceptance and A per region) comes from Pythia 8.318 with the
Green's-function threshold model (TopThreshold:model = 3) and pseudoscalar decay
correlations, at parton level with ISR. The SM reference A per region is the ATLAS nominal
prediction of ttthresh-v2 (detector level, with full NLO spin correlation).

Mixing identity used for the prediction: adding a component C with yield N_C and asymmetry
A_C to an SM sample with N_SM and A_SM shifts A by f * (A_C - A_SM), f = N_C / (N_SM + N_C).
"""
import math

import numpy as np

VERSION = "0.1.0"
M_EDGES = np.arange(0.0, 2000.0 + 1e-9, 5.0)   # same 5 GeV binning as ttthresh_core 0.1.0
NM = len(M_EDGES) - 1
Q_T = 0.20
Q_C = 0.50
INFO_Q = (0.20, 0.40, 0.70)
REGIONS = ("T", "C", "incl", "B1", "B2", "B3", "B4")

# Pre-registered constants (PREREG-TOPO-v0.2 sec. 4-5). Never change them after a run.
SIGMA_SM_PB = 832.0          # inclusive ttbar, 13 TeV, NNLO+NNLL, m_t = 172.5 GeV
SIGMA_C_PRIMARY_PB = 9.3     # ATLAS dilepton excess with the GFRW model
SIGMA_C_SCAN_PB = (4.0, 6.5, 9.3, 13.1)
R_MOST = 0.7
R_PART = 0.3
Z_SURVIVES = 2.0
H3_FRAC = 0.3
GATE_RC = (0.004, 0.016)     # sigma(E<0) / sigma(Born, all masses), same forced decays
GATE_NC_PASS = 1000
GATE_NBORN_PASS = 50000
GATE_DIFF_RELERR = 0.25

# Measured ttthresh-v2 numbers (results/ttthresh-v2/results.json, committed 2026-11-24).
# The job re-reads that file and aborts if any value differs by more than 1e-12.
MEASURED = {
    "T": {"A_nom": -0.023143595148271502, "dA": 0.016982675608041616, "sig_total": 0.02009588105028145},
    "C": {"A_nom": -0.46490223286663146, "dA": 0.007328030488733928, "sig_total": 0.005645379985279632},
    "incl": {"A_nom": -0.30029809635150023, "dA": 0.013155166981966893, "sig_total": 0.005067323918125096},
    "B1": {"A_nom": -0.023143595148271502, "dA": 0.016982675608041616, "sig_total": 0.02009588105028145},
    "B2": {"A_nom": -0.18970339459496408, "dA": 0.0027551431195702303, "sig_total": 0.011413874489707635},
    "B3": {"A_nom": -0.3691826420364862, "dA": 0.005665071844008718, "sig_total": 0.007861493244115027},
    "B4": {"A_nom": -0.504769323970336, "dA": 0.005704827200469831, "sig_total": 0.008131478266154516},
}


def _finite(*xs):
    return all(isinstance(x, (int, float)) and math.isfinite(x) for x in xs)


# ----------------------------------------------------------------------------- kinematics
def delta_phi(a, b):
    d = np.abs(np.asarray(a, float) - np.asarray(b, float)) % (2.0 * np.pi)
    return np.where(d > np.pi, 2.0 * np.pi - d, d)


def inv_mass(px, py, pz, e):
    m2 = np.asarray(e) ** 2 - np.asarray(px) ** 2 - np.asarray(py) ** 2 - np.asarray(pz) ** 2
    return np.sqrt(np.clip(m2, 0.0, None))


# ----------------------------------------------------------------------------- regions
def mbin(m):
    """5 GeV bin index, overflow into the last bin (as ttthresh_core.hist2)."""
    m = np.clip(np.asarray(m, float), 0.0, M_EDGES[-1] - 1e-6)
    return np.minimum((m // 5.0).astype(int), NM - 1)


def marginal(m, w):
    return np.bincount(mbin(m), weights=np.asarray(w, float), minlength=NM)


def quantile_bin(marg, q):
    """First m(llbb) bin index k with cumulative content >= q * total (ttthresh_core)."""
    c = np.cumsum(np.asarray(marg, float))
    tot = c[-1]
    if not tot > 0:
        raise ValueError("empty reference")
    return int(np.searchsorted(c, q * tot, side="left"))


def regions_from_reference(m_ref, w_ref):
    """Region bin ranges [lo, hi) from quantiles of the reference sample, same scheme as
    ttthresh_core.grade: T lowest 20 %, C upper 50 %, B1-B4 at 20/40/70 %."""
    marg = marginal(m_ref, w_ref)
    kT = quantile_bin(marg, Q_T)
    kC = quantile_bin(marg, Q_C)
    kq = [quantile_bin(marg, q) for q in INFO_Q]
    return {"T": (0, kT + 1), "C": (kC + 1, NM), "incl": (0, NM),
            "B1": (0, kq[0] + 1), "B2": (kq[0] + 1, kq[1] + 1),
            "B3": (kq[1] + 1, kq[2] + 1), "B4": (kq[2] + 1, NM)}


def edges_gev(reg):
    lo, hi = reg
    return float(M_EDGES[lo]), (float(M_EDGES[hi]) if hi < NM else "inf")


def region_sl(m, dphi, w, reg):
    """Weighted small-angle (dphi < pi/2) and large-angle sums, and their sums of w^2."""
    b = mbin(m)
    lo, hi = reg
    inr = (b >= lo) & (b < hi)
    w = np.asarray(w, float)
    small = np.asarray(dphi, float) < (np.pi / 2.0)
    s = float(w[inr & small].sum())
    l = float(w[inr & ~small].sum())
    s2 = float((w[inr & small] ** 2).sum())
    l2 = float((w[inr & ~small] ** 2).sum())
    return s, l, s2, l2


def asym(s, l, w2s, w2l):
    """A = (S - L) / (S + L) and its error from the sums of squared weights."""
    t = s + l
    if not t > 0:
        return float("nan"), float("nan")
    a = (s - l) / t
    var = (2.0 * l / t ** 2) ** 2 * w2s + (2.0 * s / t ** 2) ** 2 * w2l
    return float(a), float(math.sqrt(max(var, 0.0)))


# ----------------------------------------------------------------------------- mixing
def mix_shift(n_sm, a_sm, n_c, a_c):
    """Shift of A when a component (n_c, a_c) is added to (n_sm, a_sm)."""
    if not (n_sm + n_c) > 0:
        return float("nan")
    return n_c / (n_sm + n_c) * (a_c - a_sm)


def predict_region(acc_sm, acc_c, a_c, s_ac, a_sm, sigma_c, sigma_sm=SIGMA_SM_PB):
    """Predicted dA in one region. acc_* = fraction of each sample's generated weight that
    passes the selection and falls in the region (forced decays cancel in the ratio)."""
    if not _finite(acc_sm, acc_c, a_c, a_sm) or acc_sm <= 0:
        return {"f": float("nan"), "dA_pred": float("nan"), "s_pred": float("nan")}
    n_sm = sigma_sm * acc_sm
    n_c = sigma_c * acc_c
    f = n_c / (n_sm + n_c)
    d = f * (a_c - a_sm)
    s = f * s_ac if _finite(s_ac) else float("nan")
    return {"f": f, "dA_pred": d, "s_pred": s}


# ----------------------------------------------------------------------------- component (fallback)
def diff_component(s3, l3, s3w2, l3w2, s1, l1, s1w2, l1w2):
    """Fallback component = sample 3 minus sample 1, all in the same cross-section units.
    Returns yield, A_C and its error (errors of the two samples are independent)."""
    ds = s3 - s1
    dl = l3 - l1
    n = ds + dl
    if not n > 0:
        return n, float("nan"), float("nan")
    a = (ds - dl) / n
    # dA/dS = 2 L / N^2, dA/dL = -2 S / N^2 with S, L of the difference
    var = (2.0 * dl / n ** 2) ** 2 * (s3w2 + s1w2) + (2.0 * ds / n ** 2) ** 2 * (l3w2 + l1w2)
    return n, float(a), float(math.sqrt(max(var, 0.0)))


# ----------------------------------------------------------------------------- verdicts
def verdict_share(r):
    if not _finite(r):
        return "NOT GRADABLE"
    if r >= R_MOST:
        return "EXPLAINS MOST"
    if r >= R_PART:
        return "EXPLAINS PART"
    return "EXPLAINS LITTLE"


def verdict_residual(z):
    if not _finite(z):
        return "NOT GRADABLE"
    if z >= Z_SURVIVES:
        return "SURVIVES"
    if z > 0:
        return "REDUCED"
    return "ABSORBED"


def verdict_highmass(p_c, meas_c):
    if not _finite(p_c, meas_c) or meas_c <= 0:
        return "NOT GRADABLE"
    if p_c < H3_FRAC * meas_c:
        return "HIGH-MASS EXCESS NOT FROM THRESHOLD"
    return "THRESHOLD COMPONENT REACHES HIGH MASS"


def gate(info):
    """info: dict with version, settings_ok, rC, n_c_pass, n_born_pass, mode, diff_relerr."""
    reasons = []
    if not str(info.get("pythia_version", "")).startswith("8.318"):
        reasons.append("pythia8mc version %s is not 8.318.x" % info.get("pythia_version"))
    if not info.get("settings_ok", False):
        reasons.append("a TopThreshold setting was not accepted or read back wrongly")
    rc = info.get("rC", float("nan"))
    if not (_finite(rc) and GATE_RC[0] <= rc <= GATE_RC[1]):
        reasons.append("sigma(E<0)/sigma(Born) = %r outside %r" % (rc, GATE_RC))
    if not info.get("n_born_pass", 0) >= GATE_NBORN_PASS:
        reasons.append("Born passing events %r < %d" % (info.get("n_born_pass"), GATE_NBORN_PASS))
    if info.get("mode") == "E":
        if not info.get("n_c_pass", 0) >= GATE_NC_PASS:
            reasons.append("component passing events %r < %d" % (info.get("n_c_pass"), GATE_NC_PASS))
    elif info.get("mode") == "DIFF":
        re_ = info.get("diff_relerr", float("nan"))
        if not (_finite(re_) and re_ <= GATE_DIFF_RELERR):
            reasons.append("difference component relative error %r > %r" % (re_, GATE_DIFF_RELERR))
    else:
        reasons.append("no component definition available")
    return ("PASS" if not reasons else "FAIL"), reasons


def grade(pred, measured=MEASURED):
    """pred: {region: {'dA_pred': ...}} at the primary sigma_C. Returns the verdicts."""
    pi = pred["incl"]["dA_pred"]
    pt = pred["T"]["dA_pred"]
    pc = pred["C"]["dA_pred"]
    mi = measured["incl"]["dA"]
    mt = measured["T"]["dA"]
    mc = measured["C"]["dA"]
    r_incl = pi / mi if _finite(pi) else float("nan")
    r_t = pt / mt if _finite(pt) else float("nan")
    z_res = (mi - pi) / measured["incl"]["sig_total"] if _finite(pi) else float("nan")
    return {
        "H1": {"R_incl": r_incl, "verdict": verdict_share(r_incl)},
        "H2": {"Z_res": z_res, "residual": (mi - pi) if _finite(pi) else float("nan"),
               "verdict": verdict_residual(z_res)},
        "H3": {"P_C": pc, "measured_C": mc, "verdict": verdict_highmass(pc, mc)},
        "H4": {"R_T": r_t, "verdict": verdict_share(r_t)},
    }
