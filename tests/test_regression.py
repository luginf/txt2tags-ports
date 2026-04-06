"""
Regression tests for txt2tags3_mod.

Each test converts tests/input.t2t (or tests/input_table.t2t for table-only
targets) and compares the result byte-for-byte with the reference file stored
in targets/<target>/.

To regenerate the reference files after an intentional change:
    python tests/regenerate_targets.py

To run the tests:
    pytest tests/test_regression.py -v
"""

import os
import re
import subprocess
import sys
import tempfile
import pytest

# Locate repository root (parent of this file's directory)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(REPO, "tests", "input.t2t")
INPUT_TABLE = os.path.join(REPO, "tests", "input_table.t2t")
TARGETS_DIR = os.path.join(REPO, "targets")

# ---------------------------------------------------------------------------
# Target catalogue
# (target, extension, input_file, extra_args)
# ---------------------------------------------------------------------------
TARGETS = [
    # HTML family
    ("html",    "html",  INPUT,       []),
    ("html5",   "html",  INPUT,       []),
    ("xhtml",   "xhtml", INPUT,       []),
    ("xhtmls",  "xhtml", INPUT,       []),
    ("htmls",   "html",  INPUT,       []),
    ("wp",      "html",  INPUT,       []),
    # Wiki / lightweight markup
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
    # Office / structured
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
    # Plain text / ASCII art
    ("txt",     "txt",   INPUT,       []),
    ("aat",     "txt",   INPUT,       ["--width=72"]),
    ("aatw",    "html",  INPUT,       ["--width=72"]),
    # Table-only (CSV creates one file per table, named after the section)
    ("csv",     None,    INPUT_TABLE, []),
    ("csvs",    None,    INPUT_TABLE, []),
]


def _normalize_cmdline(text: str, outfile: str) -> str:
    """Strip the generated cmdline comment so paths don't cause diffs."""
    # html/xhtml: <!-- cmdline: ... -->
    text = re.sub(r"<!-- cmdline:.*?-->", "<!-- cmdline: (normalized) -->", text)
    # rst/adoc/...: .. cmdline: ...
    text = re.sub(r"\.\. cmdline:.*", ".. cmdline: (normalized)", text)
    # man/utmac: .\" cmdline: ...
    text = re.sub(r'\.\\" cmdline:.*', '.\\" cmdline: (normalized)', text)
    # moin: /* cmdline: ... */
    text = re.sub(r"/\* cmdline:.*?\*/", "/* cmdline: (normalized) */", text)
    # other comment styles
    text = re.sub(r"% cmdline:.*", "% cmdline: (normalized)", text)
    text = re.sub(r"# cmdline:.*", "# cmdline: (normalized)", text)
    text = re.sub(r"; cmdline:.*", "; cmdline: (normalized)", text)
    return text


def _run(target: str, src: str, outfile: str, extra: list[str]) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "txt2tags3_mod",
           "-t", target, "-o", outfile] + extra + [src]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)


# ---------------------------------------------------------------------------
# Parametrised test
# ---------------------------------------------------------------------------

def target_ids():
    return [t[0] for t in TARGETS]


@pytest.mark.parametrize("target,ext,src,extra", TARGETS, ids=target_ids())
def test_output_matches_reference(target, ext, src, extra, tmp_path):
    """Convert input and compare with the stored reference output."""

    # ── CSV / CSVS: creates one file per table, named after section ──────
    if ext is None:
        result = subprocess.run(
            [sys.executable, "-m", "txt2tags3_mod", "-t", target] + extra + [src],
            capture_output=True, text=True, cwd=str(tmp_path),
            env={**os.environ, "PYTHONPATH": REPO},
        )
        assert result.returncode == 0, \
            f"{target} conversion failed:\n{result.stderr}\n{result.stdout}"

        ref_dir = os.path.join(TARGETS_DIR, target)
        for ref_file in os.listdir(ref_dir):
            got_path = tmp_path / ref_file
            assert got_path.exists(), \
                f"Expected output file {ref_file} not produced by {target}"
            got = got_path.read_text(encoding="utf-8", errors="replace")
            ref = open(os.path.join(ref_dir, ref_file),
                       encoding="utf-8", errors="replace").read()
            assert got == ref, \
                f"{target}: {ref_file} differs from reference"
        return

    # ── All other targets: single output file ────────────────────────────
    out_path = tmp_path / f"input.{ext}"
    result = _run(target, src, str(out_path), extra)

    assert result.returncode == 0, \
        f"{target} conversion failed:\n{result.stderr}\n{result.stdout}"
    assert out_path.exists(), f"{target}: output file not created"

    ref_path = os.path.join(TARGETS_DIR, target, f"input.{ext}")
    assert os.path.exists(ref_path), \
        f"Reference file missing: {ref_path}\nRun: python tests/regenerate_targets.py"

    got = _normalize_cmdline(
        out_path.read_text(encoding="utf-8", errors="replace"), str(out_path))
    ref = _normalize_cmdline(
        open(ref_path, encoding="utf-8", errors="replace").read(), ref_path)

    assert got == ref, (
        f"{target}: output differs from reference {ref_path}\n"
        "If change is intentional, regenerate: python tests/regenerate_targets.py"
    )


# ---------------------------------------------------------------------------
# Smoke tests (independent of reference files)
# ---------------------------------------------------------------------------

def test_help_exits_cleanly():
    result = subprocess.run(
        [sys.executable, "-m", "txt2tags3_mod", "--help"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert result.returncode == 0
    assert "--target" in result.stdout


def test_version_string():
    result = subprocess.run(
        [sys.executable, "-m", "txt2tags3_mod", "--version"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert result.returncode == 0
    assert "txt2tags version" in result.stdout


def test_targets_list():
    result = subprocess.run(
        [sys.executable, "-m", "txt2tags3_mod", "--targets"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert result.returncode == 0
    for expected in ("html", "rst", "md", "tex", "txt"):
        assert expected in result.stdout


def test_missing_input_file_error():
    result = subprocess.run(
        [sys.executable, "-m", "txt2tags3_mod", "-t", "html", "no_such_file.t2t"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert result.returncode != 0


@pytest.mark.parametrize("markup,expected_html", [
    ("**bold**",         "<B>bold</B>"),
    ("//italic//",       "<I>italic</I>"),
    ("__underline__",    "<U>underline</U>"),
    ("--strike--",       "<S>strike</S>"),
    ("``mono``",         "<CODE>mono</CODE>"),
])
def test_inline_markup_html(markup, expected_html, tmp_path):
    """Spot-check that inline markup renders correctly for HTML target."""
    src = tmp_path / "inline.t2t"
    src.write_text(f"Title\nAuthor\n2026-01-01\n\n{markup}\n")
    out = tmp_path / "inline.html"
    result = _run("html", str(src), str(out), [])
    assert result.returncode == 0
    content = out.read_text()
    assert expected_html in content, \
        f"Expected {expected_html!r} in HTML output for markup {markup!r}"


@pytest.mark.parametrize("target", [
    "html", "html5", "rst", "md", "txt", "tex", "man", "adoc",
])
def test_bold_present_in_output(target, tmp_path):
    """**bold** must produce some bold markup in all major targets."""
    src = tmp_path / "bold.t2t"
    src.write_text("Title\nAuthor\n2026-01-01\n\n**bold text**\n")
    out = tmp_path / f"bold.out"
    result = _run(target, str(src), str(out), [])
    assert result.returncode == 0
    content = out.read_text()
    assert "bold" in content.lower()


def test_table_in_html(tmp_path):
    src = tmp_path / "table.t2t"
    src.write_text(
        "Title\nAuthor\n2026-01-01\n\n"
        "|| head1 | head2\n"
        "|  val1  | val2\n"
    )
    out = tmp_path / "table.html"
    result = _run("html", str(src), str(out), [])
    assert result.returncode == 0
    content = out.read_text()
    assert "<TABLE" in content
    assert "<TH>" in content
    assert "head1" in content
    assert "val1" in content


def test_toc_option(tmp_path):
    src = tmp_path / "toc.t2t"
    src.write_text(
        "Title\nAuthor\n2026-01-01\n\n"
        "= Section One =\n\nText.\n\n"
        "= Section Two =\n\nText.\n"
    )
    out = tmp_path / "toc.html"
    result = _run("html", str(src), str(out), ["--toc"])
    assert result.returncode == 0
    content = out.read_text()
    assert "Section One" in content
    assert "Section Two" in content


def test_no_headers_option(tmp_path):
    src = tmp_path / "nohdr.t2t"
    src.write_text("Title\nAuthor\n2026-01-01\n\nBody text.\n")
    out = tmp_path / "nohdr.html"
    result = _run("html", str(src), str(out), ["--no-headers"])
    assert result.returncode == 0
    content = out.read_text()
    assert "<HTML>" not in content
    assert "Body text" in content
