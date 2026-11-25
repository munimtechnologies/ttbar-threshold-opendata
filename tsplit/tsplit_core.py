# SPDX-License-Identifier: Apache-2.0
# tsplit_core 0.1.0 - exact composition/angular split of the Herwig7-vs-Pythia8 gap in the
# region-T e-mu spin asymmetry, as fixed in PREREG-v0.2.md (ttbar-threshold-opendata).
# MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name.
#
# Pure functions only; standard library at import time (numpy is imported lazily by the
# bootstrap). No I/O, no ROOT, no network.
"""Core of the tsplit test (PREREG-v0.2).

Bins k (fixed by PREREG-v0.2): four truth m(tt) bins for matched top-pair events, 'um' for
selected top-pair events that were not matched, and 'bkg' for the rest of the prediction.
Per sample s: f_k = share of the region-T prediction in bin k, a_k = (S_k - L_k)/(S_k + L_k),
A = sum_k f_k a_k. Delta = A_nom - A_ph7 = C + S with
  C = sum_k (f_k^nom - f_k^ph7) (a_k^nom + a_k^ph7) / 2     (composition)
  S = sum_k (f_k^nom + f_k^ph7) / 2 (a_k^nom - a_k^ph7)     (angular)
"""
import math

VERSION = "0.1.0"

MASS_BINS = ("m<380", "m380-450", "m450-550", "m>=550")
UM = "um"
BKG = "bkg"
ALL_BINS = MASS_BINS + (UM, BKG)
BOOT_SEED = 20261125
BOOT_REPS = 200

# ttthresh-v2 reference numbers used by gate G0 (results/ttthresh-v2/results.json).
REF_TTBAR_NOM_OS = 88766.36
REF_DS_PRED = -993.26   # S_pred,ph7 - S_pred,nom in region T
REF_DL_PRED = -707.86   # L_pred,ph7 - L_pred,nom in region T


def mass_bin(mtt_gev):
    """Truth m(tt) bin label: below 380, 380-450, 450-550, at least 550 GeV."""
    if mtt_gev is None or not math.isfinite(mtt_gev):
        return None
    if mtt_gev < 380.0:
        return MASS_BINS[0]
    if mtt_gev < 450.0:
        return MASS_BINS[1]
    if mtt_gev < 550.0:
        return MASS_BINS[2]
    return MASS_BINS[3]


def p4_from_ptetaphim(pt, eta, phi, m):
    """(px, py, pz, E) from (pt, eta, phi, m), same units in and out."""
    px = pt * math.cos(phi)
    py = pt * math.sin(phi)
    pz = pt * math.sinh(eta)
    e = math.sqrt(max(0.0, px * px + py * py + pz * pz + m * m))
    return (px, py, pz, e)


def inv_mass(p4a, p4b):
    """Invariant mass of two (px, py, pz, E) four-vectors (negative m^2 clipped to 0)."""
    px = p4a[0] + p4b[0]
    py = p4a[1] + p4b[1]
    pz = p4a[2] + p4b[2]
    e = p4a[3] + p4b[3]
    m2 = e * e - px * px - py * py - pz * pz
    return math.sqrt(m2) if m2 > 0.0 else 0.0


def pick_tops(entries, rule="largest"):
    """Top copy rule of PREREG-v0.2: for pdgId +6 and -6 separately, the entry with the
    largest barcode (rule='largest'; 'smallest' is the information-only variant).
    entries: iterable of dicts with keys pdgId, barcode (and kinematics).
    Returns (top, antitop) or None if either is missing. Ties in barcode -> None (ambiguous)."""
    if rule not in ("largest", "smallest"):
        raise ValueError("rule must be 'largest' or 'smallest'")
    best = {6: None, -6: None}
    tie = {6: False, -6: False}
    for ent in entries:
        pid = int(ent["pdgId"])
        if pid not in best:
            continue
        cur = best[pid]
        bc = int(ent["barcode"])
        if cur is None:
            best[pid] = ent
            tie[pid] = False
            continue
        cbc = int(cur["barcode"])
        better = bc > cbc if rule == "largest" else bc < cbc
        if better:
            best[pid] = ent
            tie[pid] = False
        elif bc == cbc:
            tie[pid] = True
    if best[6] is None or best[-6] is None or tie[6] or tie[-6]:
        return None
    return best[6], best[-6]


def mtt_gev(top, antitop, mev=True):
    """Truth m(tt) in GeV from two entries with pt, eta, phi, m (MeV if mev)."""
    scale = 0.001 if mev else 1.0
    a = p4_from_ptetaphim(top["pt"] * scale, top["eta"], top["phi"], top["m"] * scale)
    b = p4_from_ptetaphim(antitop["pt"] * scale, antitop["eta"], antitop["phi"],
                          antitop["m"] * scale)
    return inv_mass(a, b)


def largest_is_status62(entries):
    """Gate G2 helper: are the largest-barcode +6 and -6 entries both status 62?"""
    pair = pick_tops(entries, "largest")
    if pair is None:
        return False
    return int(pair[0].get("status", -1)) == 62 and int(pair[1].get("status", -1)) == 62


def split_duplicates(keys):
    """Duplicate rule of PREREG-v0.2: a key occurring more than once is dropped entirely.
    Returns (unique_keys_set, dropped_keys_set)."""
    seen = {}
    for k in keys:
        seen[k] = seen.get(k, 0) + 1
    uniq = {k for k, n in seen.items() if n == 1}
    dup = {k for k, n in seen.items() if n > 1}
    return uniq, dup


def bin_shares(sl):
    """sl: dict bin -> (S, L). Returns (f, a, A, total) with f, a dicts over ALL_BINS.
    Empty bins get f = 0 and a = 0."""
    total = 0.0
    for k in ALL_BINS:
        s, l = sl.get(k, (0.0, 0.0))
        total += s + l
    if total <= 0.0:
        raise ValueError("empty prediction")
    f, a = {}, {}
    num = 0.0
    for k in ALL_BINS:
        s, l = sl.get(k, (0.0, 0.0))
        n = s + l
        f[k] = n / total
        a[k] = (s - l) / n if n != 0.0 else 0.0
        num += s - l
    return f, a, num / total, total


def decompose(sl_nom, sl_ph7):
    """Exact split of Delta = A_nom - A_ph7 into composition C and angular S.
    Returns a dict with A_nom, A_ph7, Delta, C, S, R_C (None if Delta == 0), closure
    (|C + S - Delta|), C pieces (mass, bkg, um), S share from m<380 and per-bin f, a."""
    fn, an, a_nom, _ = bin_shares(sl_nom)
    fp, ap, a_ph7, _ = bin_shares(sl_ph7)
    c_k, s_k = {}, {}
    for k in ALL_BINS:
        c_k[k] = (fn[k] - fp[k]) * (an[k] + ap[k]) / 2.0
        s_k[k] = (fn[k] + fp[k]) / 2.0 * (an[k] - ap[k])
    c = sum(c_k.values())
    s = sum(s_k.values())
    delta = a_nom - a_ph7
    return {
        "A_nom": a_nom, "A_ph7": a_ph7, "Delta": delta, "C": c, "S": s,
        "R_C": (c / delta) if delta != 0.0 else None,
        "closure": abs(c + s - delta),
        "C_mass": sum(c_k[k] for k in MASS_BINS), "C_bkg": c_k[BKG], "C_um": c_k[UM],
        "S_lt380": s_k[MASS_BINS[0]],
        "f_nom": fn, "a_nom": an, "f_ph7": fp, "a_ph7": ap, "C_k": c_k, "S_k": s_k,
    }


def accumulate(events, weights=None):
    """events: iterable of (bin, w, is_short). Returns dict bin -> [S, L].
    is_short: Delta-phi below pi/2 (counts to S), else L. Optional per-event multipliers."""
    out = {k: [0.0, 0.0] for k in ALL_BINS}
    for i, (k, w, short) in enumerate(events):
        if k not in out:
            raise KeyError("unknown bin %r" % (k,))
        x = w * (weights[i] if weights is not None else 1.0)
        out[k][0 if short else 1] += x
    return out


def with_bkg(sl, bkg_sl):
    out = {k: (v[0], v[1]) for k, v in sl.items()}
    out[BKG] = (bkg_sl[0], bkg_sl[1])
    return out


def bkg_from_prediction(pred_sl, tt_sl):
    """(S, L)_bkg = (S, L)_pred,nom - (S, L)_tt,nom in region T (PREREG-v0.2)."""
    return (pred_sl[0] - tt_sl[0], pred_sl[1] - tt_sl[1])


def bootstrap_rc(ev_nom, ev_ph7, bkg_sl, n_rep=BOOT_REPS, seed=BOOT_SEED):
    """Poisson(1) weights per top-pair event, both samples independently (nom drawn first,
    then ph7, per replica), bkg fixed. Returns the list of R_C (None where Delta == 0)."""
    import numpy as np  # lazy: module imports without numpy
    rng = np.random.default_rng(seed)
    ev_nom = list(ev_nom)
    ev_ph7 = list(ev_ph7)
    out = []
    for _ in range(n_rep):
        wn = rng.poisson(1.0, size=len(ev_nom))
        wp = rng.poisson(1.0, size=len(ev_ph7))
        sn = with_bkg(accumulate(ev_nom, wn), bkg_sl)
        sp = with_bkg(accumulate(ev_ph7, wp), bkg_sl)
        out.append(decompose(sn, sp)["R_C"])
    return out


def percentile(values, q):
    """Linear-interpolation percentile (numpy's default method), values without None."""
    v = sorted(x for x in values if x is not None)
    if not v:
        return None
    pos = (len(v) - 1) * q / 100.0
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def band(rc):
    if rc is None:
        return None
    if rc >= 0.7:
        return "COMPOSITION"
    if rc >= 0.3:
        return "MIXED"
    return "ANGULAR"


def grade_h1(rc, gates_ok=True):
    if not gates_ok or rc is None or not math.isfinite(rc):
        return "NOT GRADABLE"
    return band(rc)


def grade_h1r(lo, hi, gates_ok=True):
    if not gates_ok or lo is None or hi is None:
        return "NOT GRADABLE"
    return "RESOLVED" if band(lo) == band(hi) else "NOT RESOLVED"


def gate_g0(ttbar_nom_os, ds_tt, dl_tt, bkg_sl):
    """G0 closure: inclusive OS nom top-pair yield within 0.1 % of ttthresh-v2; region-T
    (S, L)_tt,ph7 - (S, L)_tt,nom within 2 % of the prediction differences; bkg S, L >= 0."""
    c1 = abs(ttbar_nom_os - REF_TTBAR_NOM_OS) <= 0.001 * REF_TTBAR_NOM_OS
    c2 = abs(ds_tt - REF_DS_PRED) <= 0.02 * abs(REF_DS_PRED)
    c3 = abs(dl_tt - REF_DL_PRED) <= 0.02 * abs(REF_DL_PRED)
    c4 = bkg_sl[0] >= 0.0 and bkg_sl[1] >= 0.0
    return {"yield": c1, "dS": c2, "dL": c3, "bkg_nonneg": c4, "pass": c1 and c2 and c3 and c4}


def gate_fraction(num, den, floor):
    """Generic >= floor gate (G1 match >= 0.98, G2 >= 0.99). den <= 0 fails."""
    if den <= 0:
        return False
    return num / den >= floor


def gate_g3(f_um_nom, f_um_ph7):
    return f_um_nom <= 0.05 and f_um_ph7 <= 0.05
