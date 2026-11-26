# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""match_job 0.1.0 -- the PHYSLITE match jobs of PREREG-v0.2 (tsplit), ttbar-threshold-opendata.

For one top-pair sample (group nom / ph7 / pth1) and one part of its PHYSLITE files, this job
reads EventInfo (mcChannelNumber, eventNumber, runNumber if present) and the TruthTop container
of every event, keeps the events whose (mcChannelNumber, eventNumber) is a selected region-T key
of job A (keys_T.csv.gz, fetched from the repository and PINNED by sha256), and writes for EVERY
occurrence of such a key one row:

    match_<group>_p<part>.csv.gz
    dsid,event,run,file,entry,n_t,n_tbar,mtt_l,mtt_s,st_t,st_tbar,s62

n_t / n_tbar: TruthTop entries with pdgId +6 / -6. mtt_l: truth m(tt) in GeV of the
largest-barcode +6 and -6 entries (PREREG-v0.2 copy rule, tsplit_core.pick_tops 'largest');
mtt_s: the same with the smallest barcode (information only). 'nan' if the rule finds no pair.
st_t / st_tbar: status of the largest-barcode copies (-1 if none). s62: 1 if both are status 62
(gate G2 helper, tsplit_core.largest_is_status62).

Nothing is graded here. Duplicate keys (a key seen twice in the PHYSLITE files of its DSID) are
detected by the grade job, which reads every part; that is why every occurrence is written.
tsplit_core 0.1.0 is fetched from the repository and PINNED by sha256 (the value job A recorded
in prep.txt), so the copy rule and the mass formula are not retyped. Four-momenta are read as
(px, py, pz, e) in MeV and converted to GeV; m(tt) uses tsplit_core.inv_mass.

    python match_job.py --group nom --part 0 --nparts 4 --keys-sha256 <hex> \
        --tsplit-sha256 <hex> --work /work --out /out
"""
import argparse
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
RAW = "https://raw.githubusercontent.com/munimtechnologies/ttbar-threshold-opendata/main/"
KEYS_PATH = "results/tsplit-keys-v1/keys_T.csv.gz"
TSPLIT_PATH = "tsplit/tsplit_core.py"
API = "https://opendata.cern.ch/api/records/%d"

# Fixed by PREREG-v0.2 and AMENDMENT-0.2.2 (index keys read from the CERN Open Data records on
# 2026-11-26; file counts as listed there).
SAMPLES = {
    "nom": {"record": 80017, "dsid": 410470, "files": 190,
            "index": r"PhPy8EG_A14_ttbar_hdamp258p75_nonallhad_file_index\.json"},
    "ph7": {"record": 80018, "dsid": 411234, "files": 35,
            "index": r"PowhegHerwig7EvtGen_tt_hdamp258p75_713_dil_file_index\.json"},
    "pth1": {"record": 80018, "dsid": 601491, "files": 28,
             "index": r"PhPy8EG_A14_ttbar_pThard1_dil_file_index\.json"},
}
EI_EVENT = "EventInfoAuxDyn.eventNumber"
EI_CHAN = "EventInfoAuxDyn.mcChannelNumber"
TOP = {"pdgId": "TruthTopAuxDyn.pdgId", "barcode": "TruthTopAuxDyn.barcode",
       "status": "TruthTopAuxDyn.status", "px": "TruthTopAuxDyn.px",
       "py": "TruthTopAuxDyn.py", "pz": "TruthTopAuxDyn.pz", "e": "TruthTopAuxDyn.e"}
CSV_HEADER = "dsid,event,run,file,entry,n_t,n_tbar,mtt_l,mtt_s,st_t,st_tbar,s62"
STEP = 50000
ATTEMPTS = 3


# ----------------------------------------------------------------------------- pure helpers
def is_root(f):
    for k in ("uri", "filename", "key"):
        if re.search(r"\.root(\.\d+)?$", str(f.get(k, ""))):
            return True
    return False


def index_files(record_json, index_regex):
    """ROOT files of every _file_indices entry whose key matches index_regex, de-duplicated by
    uri and sorted by uri. Returns (matched_index_keys, files)."""
    md = record_json.get("metadata", record_json)
    keys, seen, out = [], set(), []
    for ix in md.get("_file_indices", []) or []:
        key = str(ix.get("key", ""))
        if not re.search(index_regex, key):
            continue
        keys.append(key)
        for f in ix.get("files") or []:
            if isinstance(f, dict) and is_root(f):
                u = str(f.get("uri", ""))
                if u and u not in seen:
                    seen.add(u)
                    out.append(f)
    out.sort(key=lambda f: str(f.get("uri", "")))
    return keys, out


def part_files(files, part, nparts):
    """Round-robin split of the sorted file list: part p gets files p, p + n, p + 2n, ..."""
    if nparts < 1 or not 0 <= part < nparts:
        raise ValueError("bad part %r of %r" % (part, nparts))
    return files[part::nparts]


def https_urls(uri):
    out = []
    if "/eos/" in uri:
        tail = "/eos/" + uri.split("/eos/", 1)[1]
        out.append("https://opendata.cern.ch" + tail)
        out.append("https://eospublic.cern.ch:8444/" + tail)
    return out


def load_keys(text, dsid):
    """text: keys_T.csv contents (header dsid,run,event,group,...). Returns (set of event
    numbers for this dsid, rows for this dsid, rows read in total). Rows whose event number is
    negative or unreadable raise ValueError (the key file is produced by our own job)."""
    rd = csv.DictReader(io.StringIO(text))
    want = int(dsid)
    keys, n_dsid, n_all = set(), 0, 0
    for row in rd:
        n_all += 1
        if int(row["dsid"]) != want:
            continue
        ev = int(row["event"])
        if ev < 0:
            raise ValueError("negative event number %r" % (row["event"],))
        n_dsid += 1
        keys.add(ev)
    return keys, n_dsid, n_all


def entries_from_lists(pdg, bc, st, px, py, pz, e):
    """One event's TruthTop lists -> list of dicts (MeV kept)."""
    return [{"pdgId": int(pdg[i]), "barcode": int(bc[i]), "status": int(st[i]),
             "px": float(px[i]), "py": float(py[i]), "pz": float(pz[i]), "e": float(e[i])}
            for i in range(len(pdg))]


def mtt_from_pair(pair, inv_mass):
    """GeV from a (top, antitop) pair of entries with px, py, pz, e in MeV."""
    if pair is None:
        return float("nan")
    a = tuple(pair[0][k] * 0.001 for k in ("px", "py", "pz", "e"))
    b = tuple(pair[1][k] * 0.001 for k in ("px", "py", "pz", "e"))
    return inv_mass(a, b)


def truth_row(entries, ts):
    """Per-event truth summary with tsplit_core `ts` (pick_tops, inv_mass, largest_is_status62)."""
    n_t = sum(1 for x in entries if x["pdgId"] == 6)
    n_tb = sum(1 for x in entries if x["pdgId"] == -6)
    big = ts.pick_tops(entries, "largest")
    small = ts.pick_tops(entries, "smallest")
    return {"n_t": n_t, "n_tbar": n_tb,
            "mtt_l": mtt_from_pair(big, ts.inv_mass),
            "mtt_s": mtt_from_pair(small, ts.inv_mass),
            "st_t": int(big[0]["status"]) if big else -1,
            "st_tbar": int(big[1]["status"]) if big else -1,
            "s62": 1 if ts.largest_is_status62(entries) else 0}


def fmt_mass(x):
    return "nan" if (x is None or not math.isfinite(x)) else "%.4f" % x


def csv_row(dsid, event, run, fidx, entry, tr):
    return "%d,%d,%d,%d,%d,%d,%d,%s,%s,%d,%d,%d" % (
        int(dsid), int(event), int(run), int(fidx), int(entry), tr["n_t"], tr["n_tbar"],
        fmt_mass(tr["mtt_l"]), fmt_mass(tr["mtt_s"]), tr["st_t"], tr["st_tbar"], tr["s62"])


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


# ----------------------------------------------------------------------------- network
def http_get(url, tries=4, timeout=180):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mv2-tsplit-match/0.1"})
            with urllib.request.urlopen(req, timeout=timeout) as fh:
                return fh.read()
        except Exception as exc:  # pragma: no cover - network
            last = exc
            print("download attempt %d of %s failed: %r" % (k + 1, url, exc), flush=True)
            time.sleep(15 * (k + 1))
    raise SystemExit("FATAL could not download %s: %r" % (url, last))


def raw_url(path, ref="main"):
    """raw.githubusercontent URL of `path` at branch or full 40-hex commit `ref`."""
    if ref != "main" and not re.fullmatch(r"[0-9a-f]{40}", ref):
        raise ValueError("ref must be 'main' or a full 40-hex commit sha")
    return RAW.replace("/main/", "/%s/" % ref) + path


def pin_ok(got, want):
    """want: 64-hex sha256 (must match) or 'record' (accepted, hash only recorded)."""
    if want == "record":
        return True
    return got == want.lower()


def fetch_pinned(path, want, dest=None, ref="main"):
    data = http_get(raw_url(path, ref))
    got = sha256_hex(data)
    if not pin_ok(got, want):
        raise SystemExit("FATAL %s sha256 %s != pinned %s" % (path, got, want))
    if dest:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(data)
    print("MATCH_PIN %s ref=%s sha256=%s blob=%s bytes=%d %s" % (
        path, ref, got, git_blob_sha1(data), len(data),
        "RECORDED" if want == "record" else "OK"), flush=True)
    return data


# ----------------------------------------------------------------------------- job
def process_file(fidx, f, dsid, keys_arr, ts, gz, np, ak, uproot):
    """Reads one PHYSLITE file; writes rows; returns its summary dict. Raises on read errors."""
    errs = []
    tree, how = None, None
    for u in https_urls(str(f.get("uri", ""))):
        try:
            tree = uproot.open(u, timeout=300)["CollectionTree"]
            how = u
            break
        except Exception as exc:  # noqa: BLE001
            errs.append("%s: %r" % (u, exc))
    if tree is None:
        raise RuntimeError("; ".join(errs)[:1500])
    names = set(tree.keys())
    run_br = None
    for k in sorted(names):
        if k.startswith("EventInfo") and k.endswith("runNumber"):
            run_br = k
            break
    for b in [EI_EVENT, EI_CHAN] + list(TOP.values()):
        if b not in names:
            raise RuntimeError("missing branch %s" % b)
    n = int(tree.num_entries)
    rows = foreign = 0
    s62 = both = 0
    lines = []
    for start in range(0, n, STEP):
        stop = min(n, start + STEP)
        ei = tree.arrays([EI_EVENT, EI_CHAN] + ([run_br] if run_br else []),
                         entry_start=start, entry_stop=stop, library="np")
        ev = np.asarray(ei[EI_EVENT]).astype(np.uint64)
        ch = np.asarray(ei[EI_CHAN]).astype(np.int64)
        foreign += int((ch != dsid).sum())
        hit = np.nonzero(np.isin(ev, keys_arr) & (ch == dsid))[0]
        if hit.size == 0:
            continue
        tops = tree.arrays(list(TOP.values()), entry_start=start, entry_stop=stop, library="ak")
        lists = {k: ak.to_list(tops[b][hit]) for k, b in TOP.items()}
        runs = np.asarray(ei[run_br]) if run_br else None
        for j, i in enumerate(hit):
            ents = entries_from_lists(lists["pdgId"][j], lists["barcode"][j], lists["status"][j],
                                      lists["px"][j], lists["py"][j], lists["pz"][j],
                                      lists["e"][j])
            tr = truth_row(ents, ts)
            run = int(runs[i]) if runs is not None else -1
            lines.append(csv_row(dsid, int(ev[i]), run, fidx, start + int(i), tr))
            rows += 1
            s62 += tr["s62"]
            both += 1 if (tr["n_t"] >= 1 and tr["n_tbar"] >= 1) else 0
    for ln in lines:  # written only after the whole file was read (no partial files)
        gz.write(ln + "\n")
    return {"entries": n, "rows": rows, "foreign_dsid": foreign, "s62": s62, "both": both,
            "run_branch": run_br, "source": how}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True, choices=sorted(SAMPLES))
    ap.add_argument("--part", type=int, required=True)
    ap.add_argument("--nparts", type=int, required=True)
    ap.add_argument("--keys-sha256", required=True, help="64-hex sha256 or 'record'")
    ap.add_argument("--keys-ref", default="main", help="'main' or the 40-hex commit sha")
    ap.add_argument("--tsplit-sha256", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    t0 = time.time()
    os.makedirs(args.out, exist_ok=True)
    smp = SAMPLES[args.group]
    dsid = smp["dsid"]
    tdir = os.path.join(args.work, "tsplit")
    fetch_pinned(TSPLIT_PATH, args.tsplit_sha256, os.path.join(tdir, "tsplit_core.py"))
    sys.path.insert(0, tdir)
    import tsplit_core as ts
    if ts.VERSION != "0.1.0":
        raise SystemExit("FATAL tsplit_core version %s" % ts.VERSION)
    raw = fetch_pinned(KEYS_PATH, args.keys_sha256, ref=args.keys_ref)
    keys_sha = sha256_hex(raw)
    keys, n_dsid, n_all = load_keys(gzip.decompress(raw).decode("utf-8"), dsid)
    print("MATCH_KEYS group=%s dsid=%d keys=%d rows_dsid=%d rows_all=%d" % (
        args.group, dsid, len(keys), n_dsid, n_all), flush=True)
    import numpy as np
    import awkward as ak
    import uproot
    print("MATCH_VERSIONS match_job=%s tsplit_core=%s numpy=%s awkward=%s uproot=%s" % (
        VERSION, ts.VERSION, np.__version__, ak.__version__, uproot.__version__), flush=True)
    keys_arr = np.array(sorted(keys), dtype=np.uint64)
    js = json.loads(http_get(API % smp["record"]).decode("utf-8"))
    ikeys, files = index_files(js, smp["index"])
    print("MATCH_INDEX record=%d indices=%s files=%d expected=%d" % (
        smp["record"], json.dumps(ikeys), len(files), smp["files"]), flush=True)
    if len(files) != smp["files"]:
        print("MATCH_FATAL file count %d != %d" % (len(files), smp["files"]), flush=True)
        return 6
    mine = part_files(files, args.part, args.nparts)
    fidx_of = {str(f.get("uri")): i for i, f in enumerate(files)}
    summ = {"match_job": VERSION, "group": args.group, "dsid": dsid, "part": args.part,
            "nparts": args.nparts, "record": smp["record"], "indices": ikeys,
            "files_total": len(files), "keys": len(keys), "keys_sha256": keys_sha,
            "keys_pin": args.keys_sha256, "keys_ref": args.keys_ref,
            "tsplit_sha256": args.tsplit_sha256, "files": []}
    out_csv = os.path.join(args.out, "match_%s_p%d.csv.gz" % (args.group, args.part))
    n_fail = 0
    with gzip.open(out_csv, "wt", newline="\n") as gz:
        gz.write(CSV_HEADER + "\n")
        for f in mine:
            uri = str(f.get("uri"))
            fidx = fidx_of[uri]
            rec = {"file": fidx, "uri": uri, "bytes": int(f.get("size", -1)), "status": "FAILED",
                   "attempts": 0, "errors": []}
            t1 = time.time()
            for att in range(1, ATTEMPTS + 1):
                rec["attempts"] = att
                try:
                    rec.update(process_file(fidx, f, dsid, keys_arr, ts, gz, np, ak, uproot))
                    rec["status"] = "OK"
                    break
                except Exception as exc:  # noqa: BLE001
                    rec["errors"].append(repr(exc)[:600])
                    time.sleep(30 * att)
            rec["seconds"] = round(time.time() - t1, 1)
            if rec["status"] != "OK":
                n_fail += 1
            summ["files"].append(rec)
            print("MATCH_FILE %s idx=%d status=%s entries=%s rows=%s foreign=%s s62=%s both=%s "
                  "att=%d s=%.0f" % (args.group, fidx, rec["status"], rec.get("entries"),
                                     rec.get("rows"), rec.get("foreign_dsid"), rec.get("s62"),
                                     rec.get("both"), rec["attempts"], rec["seconds"]),
                  flush=True)
    ok = [r for r in summ["files"] if r["status"] == "OK"]
    summ["rows"] = sum(r["rows"] for r in ok)
    summ["entries"] = sum(r["entries"] for r in ok)
    summ["failed_files"] = n_fail
    summ["seconds"] = round(time.time() - t0, 1)
    with open(os.path.join(args.out, "match_%s_p%d.json" % (args.group, args.part)), "w") as fh:
        json.dump(summ, fh, indent=1, sort_keys=True)
    print("MATCH_DONE group=%s part=%d/%d files=%d failed=%d entries=%d rows=%d s=%.0f" % (
        args.group, args.part, args.nparts, len(mine), n_fail, summ["entries"], summ["rows"],
        summ["seconds"]), flush=True)
    return 0 if n_fail == 0 else 7


if __name__ == "__main__":
    sys.exit(main())
