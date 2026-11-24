# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""fix_ttthresh 0.1.1 -- builds ttthresh 0.1.1 from the frozen, public 0.1.0 files.

AMENDMENT-0.1.1.md (written before any data or simulation was read): the 0.1.0 diboson rule
    _mc_7006\\d\\d\\.Sh_221\\d_(llll|lllv|llvv|lvvv)\\.
never matches the release's WW sample keys "..._mc_700602.Sh_2212_llvv_os.2J2LMET30.root" and
"..._mc_700603.Sh_2212_llvv_ss.2J2LMET30.root", so the main diboson background of an e-mu
selection would be left out. 0.1.1 changes only that rule (adds llvv_os and llvv_ss), the job's
version string, and the unit test that covers the rule.

The frozen files are downloaded from the public repository at a fixed commit and checked
against their git blob sha1 (FATAL on mismatch), so nothing published is retyped. Each patch
must apply exactly once (FATAL otherwise). sha256 of every file before and after is printed.

    python fix_ttthresh.py --dest /work/src --reqs /work/requirements.txt
"""
import argparse
import hashlib
import os
import sys
import time
import urllib.request

VERSION = "0.1.1"
REPO_RAW = "https://raw.githubusercontent.com/munimtechnologies/ttbar-threshold-opendata/"
COMMIT = "01d788aa635c97554afb42c0d465d2aebbdee83b"
# git blob sha1 of each file at COMMIT (from the repository tree API, 2026-11-24)
BLOBS = {
    "ttthresh_core.py": "cff0f4da7e62bc3b828796050aabf0f6aed742ec",
    "ttthresh_job.py": "5c10137d549be3abdd35e791d63ec198ae7f3cd3",
    "test_ttthresh_core.py": "5328c114ad17ffad669062f173c4302aede16e9a",
    "requirements.txt": "3d374fce1763784919e9df87c1366ad06e3e59c8",
    "PREREG-v0.1.md": "685d81756eb4cc38f45d413d1744a8d9038b4065",
}

OLD_DIB = r'''"diboson": [r"_mc_7006\d\d\.Sh_221\d_(llll|lllv|llvv|lvvv)\."],'''
NEW_DIB = r'''"diboson": [r"_mc_7006\d\d\.Sh_221\d_(llll|lllv|llvv|llvv_os|llvv_ss|lvvv)\."],'''
KEY_LLLV = '{"key": "ODEO_FEB2025_v0_2J2LMET30_mc_700601.Sh_2212_lllv.2J2LMET30.root"},'
KEY_ADD = (KEY_LLLV
           + ' {"key": "ODEO_FEB2025_v0_2J2LMET30_mc_700602.Sh_2212_llvv_os.2J2LMET30.root"},'
           + ' {"key": "ODEO_FEB2025_v0_2J2LMET30_mc_700605.Sh_2212_vvvv.2J2LMET30.root"},')
NEW_TEST_CLASS = '''

class LlvvFix(unittest.TestCase):
    """AMENDMENT-0.1.1: every diboson key of the release with two or more charged leptons."""

    def test_llvv_keys_assigned(self):
        import ttthresh_job as tj
        pre = "ODEO_FEB2025_v0_2J2LMET30_mc_"
        keys = ["700600.Sh_2212_llll", "700601.Sh_2212_lllv", "700602.Sh_2212_llvv_os",
                "700603.Sh_2212_llvv_ss", "700604.Sh_2212_lvvv", "700605.Sh_2212_vvvv"]
        g = tj.assign([{"key": pre + k + ".2J2LMET30.root"} for k in keys])
        got = sorted(f["key"][len(pre):len(pre) + 6] for f in g["diboson"])
        self.assertEqual(got, ["700600", "700601", "700602", "700603", "700604"])
        self.assertEqual(sum(len(v) for v in g.values()), 5)

    def test_version(self):
        import ttthresh_job as tj
        self.assertEqual(tj.VERSION, "0.1.1")

'''
PATCHES = {
    "ttthresh_job.py": [
        ('"""ttthresh_job 0.1.0 --', '"""ttthresh_job 0.1.1 --'),
        ('VERSION = "0.1.0"', 'VERSION = "0.1.1"'),
        (OLD_DIB, NEW_DIB),
    ],
    "test_ttthresh_core.py": [
        (KEY_LLLV, KEY_ADD),
        ('self.assertEqual(len(g["diboson"]), 1)', 'self.assertEqual(len(g["diboson"]), 2)'),
        ("self.assertEqual(sum(len(v) for v in g.values()), 3)",
         "self.assertEqual(sum(len(v) for v in g.values()), 4)"),
        ('\nif __name__ == "__main__":', NEW_TEST_CLASS + 'if __name__ == "__main__":'),
    ],
}


def git_blob_sha1(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def patch_once(text, old, new):
    n = text.count(old)
    if n != 1:
        raise SystemExit("FATAL patch target found %d times (need 1): %r" % (n, old[:80]))
    return text.replace(old, new)


def apply_patches(name, text):
    for old, new in PATCHES.get(name, []):
        text = patch_once(text, old, new)
    return text


def fetch(name):
    url = REPO_RAW + COMMIT + "/" + name
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fix_ttthresh/0.1.1"})
            with urllib.request.urlopen(req, timeout=120) as fh:
                return fh.read()
        except Exception as exc:  # pragma: no cover - network
            print("download attempt %d of %s failed: %s" % (k + 1, url, exc), flush=True)
            time.sleep(10 * (k + 1))
    raise SystemExit("FATAL could not download " + url)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    ap.add_argument("--reqs", required=True, help="requirements.txt used by the setup step")
    args = ap.parse_args()
    os.makedirs(args.dest, exist_ok=True)
    print("FIX fix_ttthresh %s commit %s" % (VERSION, COMMIT), flush=True)
    for name, blob in BLOBS.items():
        raw = fetch(name)
        got = git_blob_sha1(raw)
        if got != blob:
            raise SystemExit("FATAL %s blob %s != pinned %s" % (name, got, blob))
        print("FIX_PIN %s blob=%s sha256=%s OK" % (name, got, hashlib.sha256(raw).hexdigest()),
              flush=True)
        if name in PATCHES:
            new = apply_patches(name, raw.decode("utf-8")).encode("utf-8")
            print("FIX_PATCHED %s patches=%d sha256=%s" % (
                name, len(PATCHES[name]), hashlib.sha256(new).hexdigest()), flush=True)
        else:
            new = raw
        with open(os.path.join(args.dest, name), "wb") as fh:
            fh.write(new)
        if name == "requirements.txt":
            with open(args.reqs, "rb") as fh:
                local = fh.read()
            if local.replace(b"\r\n", b"\n") != raw.replace(b"\r\n", b"\n"):
                raise SystemExit("FATAL setup requirements differ from the frozen ones")
            print("FIX_REQS identical to the frozen requirements.txt", flush=True)
    print("FIX_DONE", flush=True)


if __name__ == "__main__":
    sys.exit(main())
