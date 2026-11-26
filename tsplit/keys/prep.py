# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""prep 0.1.0 for job tsplit-keys-v1 (PREREG-v0.2 + AMENDMENT-0.2.1, ttbar-threshold-opendata).

Fetches the published code this job builds on, so nothing is retyped:
* fix_ttthresh.py (0.1.1), PINNED by sha256 9c2bdd68... = the file the graded job ttthresh-v2
  ran (results/ttthresh-v2/sha256.txt). FATAL on mismatch. fix_ttthresh.py itself then fetches
  ttthresh_core.py / ttthresh_job.py at commit 01d788aa63 and checks their git blob sha1.
* tsplit/tsplit_core.py and tsplit/test_tsplit_core.py (0.1.0, committed 2026-11-25 with
  test_first); their sha256 and git blob sha1 are printed and recorded in /out/prep.txt.

    python prep.py --work /work
"""
import argparse
import hashlib
import os
import sys
import time
import urllib.request

VERSION = "0.1.0"
RAW = "https://raw.githubusercontent.com/munimtechnologies/ttbar-threshold-opendata/main/"
PINNED = {"fix_ttthresh.py":
          "9c2bdd681a02cf1ae6891a065fa6af3381a7f909b5cc042178367a6d7b214fe6"}
RECORDED = ("tsplit/tsplit_core.py", "tsplit/test_tsplit_core.py")


def git_blob_sha1(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def check_pin(name, data, want):
    """True if sha256(data) equals the pinned value (case-insensitive)."""
    return hashlib.sha256(data).hexdigest() == want.lower()


def fetch(path):
    url = RAW + path
    last = None
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mv2-tsplit-prep/0.1"})
            with urllib.request.urlopen(req, timeout=120) as fh:
                return fh.read()
        except Exception as exc:  # pragma: no cover - network
            last = exc
            print("download attempt %d of %s failed: %s" % (k + 1, url, exc), flush=True)
            time.sleep(10 * (k + 1))
    raise SystemExit("FATAL could not download %s: %r" % (url, last))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    print("PREP prep %s" % VERSION, flush=True)
    for name, want in PINNED.items():
        data = fetch(name)
        if not check_pin(name, data, want):
            raise SystemExit("FATAL %s sha256 %s != pinned %s" % (
                name, hashlib.sha256(data).hexdigest(), want))
        with open(os.path.join(args.work, name), "wb") as fh:
            fh.write(data)
        print("PREP_PIN %s sha256=%s blob=%s OK" % (name, want, git_blob_sha1(data)), flush=True)
    for path in RECORDED:
        data = fetch(path)
        dest = os.path.join(args.work, path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(data)
        print("PREP_RECORDED %s sha256=%s blob=%s bytes=%d" % (
            path, hashlib.sha256(data).hexdigest(), git_blob_sha1(data), len(data)), flush=True)
    print("PREP_DONE", flush=True)


if __name__ == "__main__":
    sys.exit(main())
