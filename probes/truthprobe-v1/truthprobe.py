# truthprobe.py 0.1.0 -- MV2 of Munim, Inc. (mv2@munimtech.com). Apache-2.0.
# Made with AI agents working in MV2's name.
#
# Feasibility probe for a possible ttbar-threshold-opendata v0.2 (not a pre-registered test):
# does the ATLAS 2024 open-data-for-research PHYSLITE release of the nominal ttbar dilepton
# sample (DSID 410472, mc20) carry truth top quarks (TruthTop) whose kinematics can be read with
# uproot, so that each event gets a truth m(tt) and could be matched by eventNumber to the 2025
# education ntuples used in ttthresh-v2?  The 2025 ntuples have no truth-top branches
# (opendata.atlas.cern/docs/data/for_education/13TeV25_details, read 2026-11-24).
#
# Output lines (stdout and /out/run.txt):
#   TPROBE_SEARCH   portal hits for the query
#   TPROBE_RECORD   chosen record, number of files, total size
#   TPROBE_FILE     file opened, size, entries, how it was read (stream / download)
#   TPROBE_TRUTH_KEYS  branch names of every Truth* container (first 200 names)
#   TPROBE_TOPS     events read, fraction with exactly one t and one tbar (pdgId +-6, by rule below)
#   TPROBE_MTT      truth m(tt) quantiles in GeV and fraction below 350 GeV
#   TPROBE_EVENTINFO  eventNumber / mcChannelNumber availability
#   TPROBE_COST     estimated bytes to read only the needed branches for the whole record
#   TPROBE_VERDICT  FEASIBLE | NO_TRUTHTOP | UNREADABLE | NO_RECORD
# Rule for tops: among TruthTop particles with pdgId == +6 (resp. -6) take the one with the
# largest index (last copy in the container); if a status branch exists, prefer status 62.
import json, os, re, sys, time, urllib.parse, urllib.request

OUT = sys.argv[sys.argv.index("--out-dir") + 1] if "--out-dir" in sys.argv else "/out"
DATA = sys.argv[sys.argv.index("--data-dir") + 1] if "--data-dir" in sys.argv else "/data"
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
                                                       "User-Agent": "mv2-truthprobe/0.1"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(20 * (i + 1))
    raise RuntimeError("GET %s failed: %r" % (url, last))


def files_in(obj):
    if isinstance(obj, dict):
        for k in ("_files", "files"):
            v = obj.get(k)
            if isinstance(v, list) and v and isinstance(v[0], dict) and "key" in v[0]:
                return v
        for v in obj.values():
            r = files_in(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = files_in(v)
            if r:
                return r
    return None


def index_files(md):
    """Large records list their files in index JSON files (_file_indices)."""
    out = []
    for ix in md.get("_file_indices", []) or []:
        for f in ix.get("files", []) or []:
            if isinstance(f, dict) and "key" in f:
                out.append(f)
    return out


def search():
    hits = []
    for q in ("410472 PHYSLITE", "410472", "PhPy8EG_A14_ttbar_hdamp258p75_dil"):
        url = ("https://opendata.cern.ch/api/records/?q=%s&experiment=ATLAS&size=50"
               % urllib.parse.quote(q))
        try:
            js = get_json(url)
        except Exception as e:  # noqa: BLE001
            say("TPROBE_SEARCH q=%r error %r" % (q, e))
            continue
        for h in js.get("hits", {}).get("hits", []):
            md = h.get("metadata", {})
            hits.append((md.get("recid", h.get("id")), str(md.get("title", ""))))
        say("TPROBE_SEARCH q=%r hits=%d" % (q, len(js.get("hits", {}).get("hits", []))))
        if hits:
            break
    seen = []
    for r, t in hits:
        if (r, t) not in seen:
            seen.append((r, t))
    for r, t in seen[:30]:
        say("TPROBE_SEARCH_HIT %s | %s" % (r, t[:200]))
    return seen


def pick(hits):
    def score(t):
        s = 0
        s += 4 if "410472" in t else 0
        s += 3 if re.search("PHYSLITE", t, re.I) else 0
        s += 1 if re.search("mc20", t, re.I) else 0
        s -= 5 if re.search("ntuple|education|2J2LMET30|1LMET30", t, re.I) else 0
        return s
    ranked = sorted(hits, key=lambda h: -score(h[1]))
    return [h for h in ranked if score(h[1]) >= 4]


def record_files(recid):
    js = get_json("https://opendata.cern.ch/api/records/%s" % recid)
    md = js.get("metadata", js)
    fl = files_in(md) or []
    if not fl or not any(str(f.get("key", "")).endswith(".root") or ".root." in str(f.get("key", ""))
                         for f in fl):
        fl = index_files(md) or fl
        if not fl:
            for ix in md.get("_file_indices", []) or []:
                key = ix.get("key") or ""
                if key.endswith(".json"):
                    try:
                        sub = get_json("https://opendata.cern.ch/record/%s/files/%s" % (recid, key))
                        if isinstance(sub, list):
                            fl += [f for f in sub if isinstance(f, dict) and "key" in f]
                    except Exception as e:  # noqa: BLE001
                        say("TPROBE_RECORD index %s error %r" % (key, e))
    roots = [f for f in fl if re.search(r"\.root(\.\d+)?$", str(f.get("key", "")))]
    return md, roots


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
            fh = uproot.open(u, timeout=120)
            return fh["CollectionTree"], "stream " + u
        except Exception as e:  # noqa: BLE001
            errs.append("%s: %r" % (u, e))
    size = int(f.get("size", -1))
    if 0 < size < 4.5e9:
        dest = os.path.join(DATA, os.path.basename(str(f["key"])))
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
        hits = search()
        cands = pick(hits)
        if not cands:
            return verdict
        md, roots = None, []
        for recid, title in cands[:5]:
            md, roots = record_files(recid)
            tot = sum(int(f.get("size", 0)) for f in roots)
            say("TPROBE_RECORD %s | %s | root files %d | %.1f GB" % (recid, title[:160], len(roots),
                                                                   tot / 1e9))
            if roots:
                break
        if not roots:
            return verdict
        verdict = "UNREADABLE"
        f = sorted(roots, key=lambda x: int(x.get("size", 0)))[0]
        tree, how = open_tree(f)
        say("TPROBE_FILE %s | %.2f GB | entries %d | %s" % (f["key"], int(f.get("size", 0)) / 1e9,
                                                             tree.num_entries, how))
        keys = list(tree.keys())
        tkeys = [k for k in keys if k.startswith("Truth")]
        conts = sorted({k.split("Aux")[0].split(".")[0] for k in tkeys})
        say("TPROBE_TRUTH_CONTAINERS " + json.dumps(conts))
        say("TPROBE_TRUTH_KEYS " + json.dumps(tkeys[:200]))
        top = [k for k in tkeys if k.startswith("TruthTop")]
        if not top:
            verdict = "NO_TRUTHTOP"
            return verdict
        import numpy as np
        import awkward as ak

        def br(name):
            for k in top:
                if k.endswith("." + name):
                    return k
            return None
        need = {n: br(n) for n in ("px", "py", "pz", "e", "m", "pt", "eta", "phi", "pdgId", "status")}
        say("TPROBE_TOP_BRANCHES " + json.dumps(need))
        a = tree.arrays([v for v in need.values() if v], entry_stop=NREAD, library="ak")
        pid = a[need["pdgId"]]
        n = len(pid)
        if need["px"] and need["e"]:
            px, py, pz, e = (a[need[x]] for x in ("px", "py", "pz", "e"))
        else:
            pt, eta, phi, m = (a[need[x]] for x in ("pt", "eta", "phi", "m"))
            px, py, pz = pt * np.cos(phi), pt * np.sin(phi), pt * np.sinh(eta)
            e = np.sqrt(px ** 2 + py ** 2 + pz ** 2 + m ** 2)
        idx = ak.local_index(pid)
        sel = {}
        for s in (6, -6):
            mask = pid == s
            if need["status"]:
                m62 = mask & (a[need["status"]] == 62)
                mask = ak.where(ak.any(m62, axis=1), m62, mask)
            last = ak.max(ak.where(mask, idx, -1), axis=1)
            sel[s] = last
        ok = (sel[6] >= 0) & (sel[-6] >= 0)
        ok = ak.to_numpy(ok)
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
        ev = [k for k in keys if k.startswith("EventInfo") and (k.endswith(".eventNumber")
                                                                  or k.endswith(".mcChannelNumber")
                                                                  or k.endswith(".mcEventWeights"))]
        say("TPROBE_EVENTINFO " + json.dumps(ev))
        if ev:
            en = [k for k in ev if k.endswith(".eventNumber")]
            if en:
                v = ak.to_numpy(tree[en[0]].array(entry_stop=5, library="ak"))
                say("TPROBE_EVENTINFO first eventNumbers " + " ".join(str(int(x)) for x in v))
        nb = sum(tree[k].compressed_bytes for k in [v for v in need.values() if v] + ev)
        per_ev = nb / max(tree.num_entries, 1)
        tot_ev = None
        try:
            tot_ev = sum(int(x) for x in [tree.num_entries])
        except Exception:  # noqa: BLE001
            pass
        say("TPROBE_COST needed branches %.1f MB in this file (%.1f bytes/event); record total about %.1f GB"
            " if all files are similar" % (nb / 1e6, per_ev,
                                          nb / max(int(f.get("size", 1)), 1)
                                          * sum(int(x.get("size", 0)) for x in roots) / 1e9))
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
