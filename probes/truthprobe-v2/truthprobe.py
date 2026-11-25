# truthprobe.py 0.2.0 -- MV2 of Munim, Inc. (mv2@munimtech.com). Apache-2.0.
# Made with AI agents working in MV2's name.
#
# Feasibility probe for a possible ttbar-threshold-opendata v0.2 (not a pre-registered test;
# nothing here is graded). Question: does the ATLAS 2024 open-data-for-research PHYSLITE release
# of the NOMINAL ttbar sample used by ttthresh-v2 (DSID 410470, PhPy8EG_A14_ttbar_hdamp258p75_
# nonallhad, mc20a) carry truth top quarks whose kinematics can be read with uproot, so that each
# event gets a truth m(tt) and could be matched by eventNumber to the 2025 education ntuples?
#
# Why 0.2.0: truthprobe 0.1.0 (job truthprobe-v1, 2026-11-25) ended NO_RECORD because (a) it
# searched the portal for DSID 410472 (dilepton), which is not in the release, while ttthresh-v2's
# nominal sample is 410470 (test_fix_ttthresh.py), and (b) portal full-text search does not index
# the DSID. The sample is in record 80017 ("ATLAS DAOD_PHYSLITE format MC simulation top nominal
# samples", DOI 10.7483/OPENDATA.ATLAS.MM1Y.O0PH), file index
# mc20_13TeV_MC_PhPy8EG_A14_ttbar_hdamp258p75_nonallhad_file_index.json (190 files, 478.6 GB).
# Index file keys end in "_file_index.json_<n>", so 0.2.0 selects ROOT files by uri/filename.
#
# Output lines (stdout and /out/run.txt):
#   TPROBE_RECORD   record, index chosen, number of files, total size
#   TPROBE_FILE     file opened, size, entries, how it was read (stream / download)
#   TPROBE_TRUTH_CONTAINERS / TPROBE_TRUTH_KEYS  names of every Truth* branch (first 300)
#   TPROBE_TOPS     events read, fraction with a t and a tbar (pdgId +-6, rule below)
#   TPROBE_MTT      truth m(tt) quantiles in GeV and fraction below 350 / 345 GeV
#   TPROBE_EVENTINFO  eventNumber / mcChannelNumber / mcEventWeights availability
#   TPROBE_COST     bytes to read only the needed branches, per file and for the whole sample
#   TPROBE_VERDICT  FEASIBLE | NO_TRUTHTOP | UNREADABLE | NO_RECORD
# Rule for tops: among TruthTop particles with pdgId == +6 (resp. -6) take the one with the
# largest index (last copy in the container); if a status branch exists, prefer status 62.
import json, os, re, sys, time, urllib.request

OUT = sys.argv[sys.argv.index("--out-dir") + 1] if "--out-dir" in sys.argv else "/out"
DATA = sys.argv[sys.argv.index("--data-dir") + 1] if "--data-dir" in sys.argv else "/data"
RECID = 80017
INDEX_RE = r"PhPy8EG_A14_ttbar_hdamp258p75_nonallhad"
NREAD = 3000
LOG = []


def say(line):
    print(line, flush=True)
    LOG.append(line)


def get_json(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json",
                                                       "User-Agent": "mv2-truthprobe/0.2"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(20 * (i + 1))
    raise RuntimeError("GET %s failed: %r" % (url, last))


def is_root(f):
    for k in ("uri", "filename", "key"):
        if re.search(r"\.root(\.\d+)?$", str(f.get(k, ""))):
            return True
    return False


def record_files(js):
    md = js.get("metadata", js)
    for ix in md.get("_file_indices", []) or []:
        key = str(ix.get("key", ""))
        if re.search(INDEX_RE, key):
            fl = [f for f in (ix.get("files") or []) if isinstance(f, dict) and is_root(f)]
            return key, fl
    return None, []


def urls_for(f):
    out = []
    uri = str(f.get("uri", ""))
    if "/eos/" in uri:
        tail = "/eos/" + uri.split("/eos/", 1)[1]
        out.append("https://opendata.cern.ch" + tail)
        out.append("https://eospublic.cern.ch:8444/" + tail)
    return out


def open_tree(f):
    import uproot
    errs = []
    for u in urls_for(f):
        try:
            fh = uproot.open(u, timeout=180)
            return fh["CollectionTree"], "stream " + u
        except Exception as e:  # noqa: BLE001
            errs.append("%s: %r" % (u, e))
    size = int(f.get("size", -1))
    if 0 < size < 4.5e9:
        name = os.path.basename(str(f.get("uri") or f.get("key")))
        dest = os.path.join(DATA, name)
        if not (os.path.exists(dest) and os.path.getsize(dest) == size):
            for u in urls_for(f):
                try:
                    urllib.request.urlretrieve(u, dest + ".part")
                    os.replace(dest + ".part", dest)
                    break
                except Exception as e:  # noqa: BLE001
                    errs.append("download %s: %r" % (u, e))
        if os.path.exists(dest):
            fh = uproot.open(dest)
            return fh["CollectionTree"], "download " + dest
    raise RuntimeError("; ".join(errs)[:2000])


def main():
    os.makedirs(OUT, exist_ok=True)
    verdict = "NO_RECORD"
    try:
        js = get_json("https://opendata.cern.ch/api/records/%d" % RECID)
        title = str(js.get("metadata", {}).get("title", ""))
        key, roots = record_files(js)
        tot = sum(int(f.get("size", 0)) for f in roots)
        say("TPROBE_RECORD %d | %s | index %s | root files %d | %.1f GB"
            % (RECID, title[:120], key, len(roots), tot / 1e9))
        if not roots:
            return verdict
        verdict = "UNREADABLE"
        f = sorted(roots, key=lambda x: int(x.get("size", 0)))[0]
        tree, how = open_tree(f)
        say("TPROBE_FILE %s | %.2f GB | entries %d | %s" % (f.get("uri"), int(f.get("size", 0)) / 1e9,
                                                             tree.num_entries, how))
        keys = list(tree.keys())
        tkeys = [k for k in keys if k.startswith("Truth")]
        conts = sorted({k.split("Aux")[0].split(".")[0] for k in tkeys})
        say("TPROBE_TRUTH_CONTAINERS " + json.dumps(conts))
        say("TPROBE_TRUTH_KEYS " + json.dumps(tkeys[:300]))
        top = [k for k in tkeys if k.startswith("TruthTop")]
        if not top:
            verdict = "NO_TRUTHTOP"
            return verdict
        import numpy as np
        import awkward as ak

        def br(name):
            for k in top:
                if k.endswith("." + name) or k.endswith("/" + name):
                    return k
            return None
        need = {n: br(n) for n in ("px", "py", "pz", "e", "m", "pt", "eta", "phi", "pdgId", "status")}
        say("TPROBE_TOP_BRANCHES " + json.dumps(need))
        a = {}
        for n_, k in need.items():
            if not k:
                continue
            try:
                a[n_] = tree[k].array(entry_stop=NREAD, library="ak")
            except Exception as e:  # noqa: BLE001
                say("TPROBE_BRANCH_ERROR %s %r" % (k, e))
        if "pdgId" not in a:
            return verdict
        pid = a["pdgId"]
        n = len(pid)
        if all(x in a for x in ("px", "py", "pz", "e")):
            px, py, pz, e = (a[x] for x in ("px", "py", "pz", "e"))
        elif all(x in a for x in ("pt", "eta", "phi", "m")):
            pt, eta, phi, m = (a[x] for x in ("pt", "eta", "phi", "m"))
            px, py, pz = pt * np.cos(phi), pt * np.sin(phi), pt * np.sinh(eta)
            e = np.sqrt(px ** 2 + py ** 2 + pz ** 2 + m ** 2)
        else:
            return verdict
        idx = ak.local_index(pid)
        sel = {}
        for s in (6, -6):
            mask = pid == s
            if "status" in a:
                m62 = mask & (a["status"] == 62)
                mask = ak.where(ak.any(m62, axis=1), m62, mask)
            sel[s] = ak.fill_none(ak.max(ak.where(mask, idx, -1), axis=1), -1)
        ok = ak.to_numpy((sel[6] >= 0) & (sel[-6] >= 0))
        mult6 = ak.to_numpy(ak.sum(pid == 6, axis=1))
        frac = float(ok.mean()) if n else 0.0
        say("TPROBE_TOPS read %d | both t and tbar %.4f | pdgId+6 count per event median %d max %d"
            % (n, frac, int(np.median(mult6)) if n else -1, int(mult6.max()) if n else -1))
        okm = ak.Array(ok)

        def pick_c(arr, i):
            return ak.to_numpy(ak.firsts(arr[okm][ak.singletons(i[okm])])).astype(float)
        P = [np.zeros(int(ok.sum())) for _ in range(4)]
        for s in (6, -6):
            for j, c in enumerate((e, px, py, pz)):
                P[j] = P[j] + pick_c(c, sel[s])
        mtt = np.sqrt(np.maximum(P[0] ** 2 - P[1] ** 2 - P[2] ** 2 - P[3] ** 2, 0.0))
        unit = 1e-3 if mtt.size and np.median(mtt) > 5000 else 1.0
        mtt = mtt * unit
        if mtt.size:
            q = np.quantile(mtt, [0.0, 0.05, 0.2, 0.5, 0.8, 0.95, 1.0])
            say("TPROBE_MTT GeV quantiles(0,5,20,50,80,95,100) %s | frac<350 %.4f | frac<2mt(345) %.4f"
                % (" ".join("%.1f" % x for x in q), float((mtt < 350).mean()),
                   float((mtt < 345).mean())))
            np.savetxt(os.path.join(OUT, "mtt_sample.csv"), mtt, fmt="%.3f", header="truth_mtt_GeV")
        ev = [k for k in keys if k.startswith("EventInfo") and (k.endswith("eventNumber")
                                                                  or k.endswith("mcChannelNumber")
                                                                  or k.endswith("mcEventWeights"))]
        say("TPROBE_EVENTINFO " + json.dumps(ev))
        en = [k for k in ev if k.endswith("eventNumber")]
        if en:
            try:
                v = ak.to_numpy(tree[en[0]].array(entry_stop=5, library="ak"))
                say("TPROBE_EVENTINFO first eventNumbers " + " ".join(str(int(x)) for x in v))
            except Exception as e:  # noqa: BLE001
                say("TPROBE_BRANCH_ERROR %s %r" % (en[0], e))
        nb = sum(tree[k].compressed_bytes for k in [v for v in need.values() if v] + ev)
        say("TPROBE_COST needed branches %.1f MB in this file (%.1f bytes/event); whole sample about"
            " %.2f GB if all files are similar" % (nb / 1e6, nb / max(tree.num_entries, 1),
                                                   nb / max(int(f.get("size", 1)), 1) * tot / 1e9))
        verdict = "FEASIBLE" if (n and frac >= 0.95 and mtt.size) else "UNREADABLE"
        return verdict
    finally:
        say("TPROBE_VERDICT " + verdict)
        with open(os.path.join(OUT, "run.txt"), "w") as fh:
            fh.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        say("TPROBE_ERROR %r" % (exc,))
        with open(os.path.join(OUT, "run.txt"), "a") as fh:
            fh.write("TPROBE_ERROR %r\n" % (exc,))
        sys.exit(0)
