"""
Regenerate all reference files in targets/.

Run this after an intentional change to txt2tags3_mod output:

    python tests/regenerate_targets.py

This script is intentionally separate from the test suite so that
regeneration is always an explicit, deliberate action.
"""

import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(REPO, "tests", "input.t2t")
INPUT_TABLE = os.path.join(REPO, "tests", "input_table.t2t")
TARGETS_DIR = os.path.join(REPO, "targets")

TARGETS = [
    ("html",    "html",  INPUT,       []),
    ("html5",   "html",  INPUT,       []),
    ("xhtml",   "xhtml", INPUT,       []),
    ("xhtmls",  "xhtml", INPUT,       []),
    ("htmls",   "html",  INPUT,       []),
    ("wp",      "html",  INPUT,       []),
    ("txt2t",   "t2t",   INPUT,       []),
    ("wiki",    "wiki",  INPUT,       []),
    ("gwiki",   "wiki",  INPUT,       []),
    ("doku",    "txt",   INPUT,       []),
    ("pmw",     "txt",   INPUT,       []),
    ("moin",    "txt",   INPUT,       []),
    ("adoc",    "adoc",  INPUT,       []),
    ("rst",     "rst",   INPUT,       []),
    ("creole",  "txt",   INPUT,       []),
    ("md",      "md",    INPUT,       []),
    ("gmi",     "gmi",   INPUT,       []),
    ("bbcode",  "txt",   INPUT,       []),
    ("red",     "txt",   INPUT,       []),
    ("spip",    "txt",   INPUT,       []),
    ("tml",     "txt",   INPUT,       []),
    ("vimwiki", "txt",   INPUT,       []),
    ("sgml",    "sgml",  INPUT,       []),
    ("dbk",     "xml",   INPUT,       []),
    ("tex",     "tex",   INPUT,       []),
    ("lout",    "lout",  INPUT,       []),
    ("man",     "1",     INPUT,       []),
    ("utmac",   "utmac", INPUT,       []),
    ("mgp",     "mgp",   INPUT,       []),
    ("pm6",     "txt",   INPUT,       []),
    ("rtf",     "rtf",   INPUT,       []),
    ("mom",     "mom",   INPUT,       []),
    ("txt",     "txt",   INPUT,       []),
    ("aat",     "txt",   INPUT,       ["--width=72"]),
    ("aatw",    "html",  INPUT,       ["--width=72"]),
    ("csv",     None,    INPUT_TABLE, []),
    ("csvs",    None,    INPUT_TABLE, []),
]


def regenerate():
    ok, fail = [], []

    for target, ext, src, extra in TARGETS:
        outdir = os.path.join(TARGETS_DIR, target)
        os.makedirs(outdir, exist_ok=True)

        # CSV/CSVS: output goes to cwd, named after the section heading
        if ext is None:
            result = subprocess.run(
                [sys.executable, "-m", "txt2tags3_mod", "-t", target] + extra + [src],
                capture_output=True, text=True, cwd=outdir,
            )
            if result.returncode == 0:
                ok.append(target)
                for f in os.listdir(outdir):
                    if f != "__init__.py":
                        print(f"  OK  {target:10s} -> targets/{target}/{f}")
            else:
                err = (result.stderr + result.stdout).strip().split("\n")[-1]
                fail.append((target, err))
                print(f"  FAIL {target:10s}: {err[:80]}")
            continue

        outfile = os.path.join(outdir, f"input.{ext}")
        cmd = [sys.executable, "-m", "txt2tags3_mod",
               "-t", target, "-o", outfile] + extra + [src]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)

        if result.returncode == 0 and os.path.exists(outfile):
            size = os.path.getsize(outfile)
            ok.append(target)
            print(f"  OK  {target:10s} -> targets/{target}/input.{ext}  ({size} bytes)")
        else:
            err = (result.stderr + result.stdout).strip().split("\n")[-1]
            fail.append((target, err))
            print(f"  FAIL {target:10s}: {err[:80]}")

    print(f"\nRegenerated: {len(ok)}/{len(ok)+len(fail)}")
    if fail:
        print("Failed:", [t for t, _ in fail])
        sys.exit(1)


if __name__ == "__main__":
    regenerate()
