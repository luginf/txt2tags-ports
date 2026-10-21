# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains ports of [txt2tags](https://txt2tags.org) — a plain-text markup converter — to multiple languages. The original txt2tags is a monolithic Python 2 script; this repo refactors and ports it.

### Ports

- **`txt2tags3_mod/`** — Python 3 port, split into focused modules. This is the primary, actively developed port. Installable as `txt2tags3-mod` via pip (`pyproject.toml`).
- **`txt2tags3`** — The original monolithic Python 3 script (single file, ~416KB).
- **`txt2tags_perl/`** — Perl port (`Text::Txt2tags` module + `bin/txt2tags` CLI). Advanced tier (see "Scope policy" below).
- **`txt2tags_lua/`** — Lua prototype, simple tier plus a first advanced-tier slice. `txt2tags.lua` module + `bin/txt2tags` CLI (`-t html|tex`) + `t/` tests (custom TAP-style harness, no external deps). Has the LaTeX target (`M.to_latex`) alongside HTML, plus links (bracket `[label target]` and bare autolinks for URLs/mailto/email), definition lists, and the `%%date`/`%%toc` macros -- all still without a regex engine (plain string scanning). See the module doc comment in `txt2tags.lua` for exactly what's covered and what's still deferred (images, verbatim/raw blocks, block comments, other macros, `%!preproc`/`%!postproc`).
- **`txt2tags_tcl/`** — Tcl prototype, simple tier. `txt2tags.tcl` module + `bin/txt2tags` CLI + `t/` tests (stdlib `tcltest`). HTML only so far.
- **`txt2tags_rust/`** - Rust prototype. Cargo crate: `src/lib.rs` module + `src/bin/txt2tags.rs` CLI (`-t html|tex`) + `tests/convert.rs` (`cargo test`). Furthest along: has the `%%date`/`%%toc` macros, a LaTeX target, and a first advanced-tier pass - links, images, verbatim/raw blocks, definition lists, table column-alignment inference, and `%!preproc`/`%!postproc`. The `regex` crate is a dependency now, but only for the last of those (see the module doc comment in `src/lib.rs` for exactly where the simple-tier/advanced-tier line falls and what's still not implemented). Bare URLs follow the reference URL character set (stop at brackets, drop trailing `.,;:!?`); bracket nesting beyond `[label URL]` and `[[img.ext] URL]` is left literal on purpose.
- **`txt2tags_go/`** - Go prototype, at feature parity with the Rust port. Module: `txt2tags.go` package + `cmd/txt2tags/main.go` CLI (`-t html|tex`) + `txt2tags_test.go` (`go test ./...`, stdlib test harness, no external deps; mirrors `txt2tags_rust/tests/convert.rs`). Same feature set as Rust: `%%date`/`%%toc` macros, links, images (incl. the nested `[[img.ext] URL]` shape), verbatim and raw blocks, block comments, definition lists, table column-alignment inference, `%!preproc`/`%!postproc` (stdlib `regexp`, the only place a regex engine is used). `-t html` and `-t tex` output is byte-identical to the Rust CLI on the repo's sample inputs; keep it that way when changing either. See the module doc comment in `txt2tags.go`.
- Not in this repo, but related: `~/src/lionwiki-t2t/txt2tags.class.php` is an independent, much smaller single-class PHP port ("transposes some of the features", per its own header comment) used by the LionWiki engine. It has its own `--blank-closes-list` equivalent (`$listsingleblank` public property) — see that repo directly, it doesn't share code with this one.

## Scope policy: "simple" vs "advanced" ports

Every port in this repo — existing and future (Lua, Tcl, and any later
addition such as Rust or Go) — should track this two-tier split rather
than trying to match the full monolithic engine's feature set in one pass.

### Simple tier

Basic syntax only, deliberately kept implementable with plain string
operations (no regex/pattern-matching engine required — see the header
comments in `txt2tags_lua/txt2tags.lua` and `txt2tags_tcl/txt2tags.tcl`
for the "no regex" rationale). Covers:

- Head: title / author / date
- Headings: `= h1 =` .. `===== h5 =====`
- Inline marks: `**bold**`, `//italic//`, `__underline__`, `--strike--`,
  ` ``mono`` `, backslash-escaping
- Paragraphs, horizontal rules
- Lists: unordered (`- `) and ordered (`+ `), with indentation nesting
- Tables: `| cell |` rows, `||` header row — no column-alignment
  inference (that's whitespace-pattern detection, advanced-tier territory)
- Macros: `%%date`, `%%toc` — simple substitution belongs here too, it
  doesn't need `%!preproc`/`%!postproc` machinery

Export targets, in priority order:

1. **HTML** — always first.
2. **LaTeX** — second priority.
3. Everything else is anecdotal, DocBook being the one possible exception
   if a concrete need shows up. Pandoc now both reads and writes the
   txt2tags format directly, so chaining through Pandoc covers most of
   the remaining targets (wiki dialects, rst, etc.) better than a
   hand-rolled exporter would for a simple-tier port.

### Advanced tier

Everything the simple tier defers, gated behind an actual regex engine:
`%!preproc` / `%!postproc` (and other regex-driven `%!options`), full
greedy/glued mark matching, table column-alignment inference, definition
lists, links, images, verbatim/raw blocks, etc.

`txt2tags_perl/` and `txt2tags3_mod/` already operate at this tier.

**The advanced tier is also the eventual goal for the newer ports**
(Lua, Tcl, and future ones such as Rust or Go) — the two-tier split is
not "toy ports stay simple forever, only Perl/Python get advanced
features." It exists so the two stages stay cleanly separable *in the
code*: the simple-tier parser/renderer should stay a self-contained
layer that advanced-tier work (regex-driven preproc/postproc, greedy
mark matching, alignment inference, etc.) extends or wraps, not
something that gets torn up and rewritten once regex enters the
picture. Prefer, e.g., isolating the regex-dependent logic in its own
module/pass rather than interleaving it through the plain-string
functions from the simple tier.

One cap applies regardless of tier: for Lua, Tcl, Rust, Go and any
other new-from-scratch port, **HTML and LaTeX are the only export
targets planned**, even once a port reaches advanced-tier syntax
fidelity. The full ~20-target list (rst, wiki dialects, DocBook, etc.)
stays specific to `txt2tags_perl/` and `txt2tags3_mod/` — see the
"simple tier" export-priority note above for why (Pandoc now covers
that ground for txt2tags source directly).

## Python Port (`txt2tags3_mod`)

### Running

```bash
python -m txt2tags3_mod -t html input.t2t
python -m txt2tags3_mod --help
python -m txt2tags3_mod --targets
```

### Module Architecture

The monolithic script was split into these modules (load order matters due to globals):

| Module | Responsibility |
|---|---|
| `constants.py` | Immutable config, program info, i18n, all target definitions |
| `state.py` | Mutable runtime globals (`CONF`, `TAGS`, regex state, etc.) |
| `tags.py` | `getTags(config)` — per-target markup tag dictionaries |
| `rules.py` | `getRules(config)` — per-target processing rules |
| `regexes.py` | `getRegexes()` — compiled regex patterns |
| `aa.py` | ASCII Art rendering |
| `utils.py` | Error handling, file I/O, debug/logging |
| `cli.py` | `PathMaster`, `CommandLine`, option classes |
| `config.py` | `SourceDocument`, `ConfigMaster`, `ConfigLines` |
| `processing.py` | `MaskMaster`, `TitleMaster`, `TableMaster`, `BlockMaster`, `MacroMaster` |
| `output.py` | TOC, headers/footers, escaping, link/image helpers |
| `converter.py` | `process_source_file()`, `convert()`, top-level conversion logic |
| `gui.py` | Tkinter GUI (`Gui` class) |
| `usage.py` | `Usage()` help text and embedded templates |
| `__main__.py` | `exec_command_line()` entry point |
| `targets/` | One `.py` file per output target (e.g. `html.py`, `md.py`, `rst.py`) |

### Tests

```bash
# Run all tests
pytest tests/test_regression.py -v

# Run a single parametrized target test
pytest tests/test_regression.py -v -k html

# Run only smoke tests (no reference files needed)
pytest tests/test_regression.py -v -k "not test_output_matches_reference"
```

Regression tests convert `tests/input.t2t` (or `tests/input_table.t2t` for CSV targets) and compare byte-for-byte with reference files in `targets/<target>/`.

After intentional output changes, regenerate reference files:

```bash
python tests/regenerate_targets.py
```

## Perl Port (`txt2tags_perl`)

### Setup

```bash
cd txt2tags_perl
perl Makefile.PL
make
make test
```

Or use `cpanm` with the `cpanfile`:
```bash
cd txt2tags_perl
cpanm --installdeps .
```

### Tests

```bash
cd txt2tags_perl
prove -l t/
# or individual test files: prove -l t/07_convert.t
```

Test files are numbered by subsystem: `01_constants`, `02_regexes`, `03_tags`, `04_rules`, `05_output`, `06_config`, `07_convert`.

The Perl module lives at `lib/Text/Txt2tags.pm` and `lib/Text/Txt2tags/` (mirroring the Python module structure).

## Key Concepts

- **`.t2t` files** have a 3-line header (title, author, date) followed by optional config sections and body. The `%%` marker separates header from body.
- **Targets** are identified by short names (`html`, `rst`, `md`, `tex`, etc.). `targets/` in both `txt2tags3_mod/targets/` (Python) and the repo-level `targets/` (reference outputs) use this same naming.
- **CSV/CSVS targets** are special: they produce one output file per table section rather than a single output file.
- **AAT/AATW targets** require `--width=N` and render tables as ASCII art.
- The `--no-headers` flag strips the document wrapper (useful for fragment output).

## Non-default options (opt-in, backward compatible)

These two flags exist in `txt2tags3_mod` (Python) and `txt2tags_perl`. Both
default OFF, so existing documents render exactly as before unless a caller
opts in. **Not present in the plain monolithic `txt2tags3` file in this repo**
(that copy is kept as an unmodified reference/baseline) — a separately
patched standalone copy with both options exists at
`~/src/lone_wolf_fr/txt2tags3` for a specific downstream project, but it was
never merged back here.

### `--blank-closes-list`

Without it, txt2tags requires **two** consecutive blank lines to close a
list; a single blank line is folded into the last item as a sub-paragraph
instead (this is how `parainsidelist`/`spacedlistitem` work upstream). In
practice this means: any list immediately followed by an ordinary paragraph
or title, separated by just one blank line, gets that paragraph/title
silently swallowed into the list's last item. This is a real footgun for
generated `.t2t` content (e.g. `- **0** : Item.\n\n== Next section ==` —
the heading vanishes into the list, and every open list tag stays open).

With the flag on, a single blank line closes the list right away — *unless*
the next source line starts another item of the same list (or is itself
blank), in which case behavior is unchanged. This is a one-line lookahead,
not a config-parsing distinction, so it correctly preserves
blank-separated list items (`- a\n\n- b` stays one list).

**Known trade-off:** multi-paragraph list items (`- a\n\n  more of a`) rely
on that exact same single blank line, and a one-line lookahead cannot tell
"more of this item" from "unrelated paragraph, list is over" — they look
identical. With the flag on, the list closes on the first blank line and
the continuation text becomes a plain paragraph after the list instead.
Documents that intentionally use multi-paragraph list items should not
enable this option.

Implementation: `converter.py::convert()` / `Converter.pm::convert` — in the
blank-line handling branch, right where the first blank would normally be
folded into the current item (search `blank-closes-list` / `f_lastwasblank`).

### Single-file builds

- Python: `python3 txt2tags3_mod/bundle.py` writes `txt2tags3_mod/out/txt2tags.py`
  (module sources embedded + meta-path finder; behaves exactly like
  `python -m txt2tags3_mod`; `tests/test_regression.py` passes against it).
- Perl: `perl txt2tags_perl/bundle.pl` writes `txt2tags_perl/out/txt2tags.pl`
  (`make bundle` does the same; `bundle.pl -` prints to stdout).
- Regenerate after any change to the modules. `out/` is generated output.

### Titles close open lists (default) / `--legacy`

Upstream txt2tags (py2/py3) and this fork used to refuse titles while a list
was open (`and not BLOCK.block().endswith("list")`), so
`- item\n\n== Title ==` swallowed the title into the last item. Now a
**flush-left** title (or numtitle) always closes the open list(s), with one
blank line, a spaces-only line or none. Indented titles are still item
continuation text. `--legacy` restores the old behaviour. Nothing else
changes (paragraphs after a list still need two blank lines unless
`--blank-closes-list` is on).

Implementation: `Converter.pm` / `converter.py::convert()` title branch
(`title_ok` / `title_blocked_by_list`); in Python a one-line lookahead in the
blank-line branch closes the list early to avoid an empty trailing `<P></P>`.
Tests: `txt2tags_perl/t/09_list_title.t`, `tests/test_list_title.py`.

### `--skip-header-lines`

Without it, the first 1–3 lines of every document are reserved for
title/author/date (see "Key Concepts" above), even when the document never
meant to use that convention — e.g. a page whose real first line of content
is just consumed as an invisible "title" and dropped, or rendered as an
unwanted `<H1>`.

With the flag on, there is no Head area at all: the document body starts on
line 1, unconditionally.

**CLI/RC-file only — cannot be set via `%!options` inside the document.**
The flag decides where the document's own Head/Conf/Body areas begin, so it
must be resolved *before* the document is scanned; a `%!options` line living
*inside* the Conf area can't retroactively control where that same Conf
area starts. `process_source_file()` does a small early, document-independent
config parse (RC file + command line only) just to read this one flag before
constructing `SourceDocument`.

Implementation: `config.py::SourceDocument` / `Config.pm::SourceDocument` —
the `no_header_lines` constructor param, consumed in `scan()`. There is
also an existing native workaround with no code changes needed: starting a
document with a *blank first line* already makes txt2tags skip the header
(a pre-existing 1-line-head exception, see the `RULES` docstring); this new
flag generalizes that to zero lines and to documents whose first line isn't
blank.

### Testing

Both options are exercised by hand (no dedicated regression fixture yet —
existing `tests/test_regression.py` / `prove -l t/` suites all pass
unchanged since the flags default off):

```bash
# Python
python -m txt2tags3_mod -t html --blank-closes-list --skip-header-lines -o - input.t2t

# Perl (from the repo, not the system `txt2tags` binary — see caveat below)
cd txt2tags_perl && perl -Ilib bin/txt2tags -t html --blank-closes-list --skip-header-lines -o - input.t2t
```

**Caveat found while adding these options:** `/usr/local/bin/txt2tags` (the
system-installed Perl binary) was found to be built from an **older**
commit than `txt2tags_perl/` in this repo — it's missing features present
here (`onelinepara`, `onelinequote`, titleblocks targets, `%!include`,
table alignment improvements, etc.), confirmed by diffing
`/usr/local/share/perl*/Text/Txt2tags/Converter.pm` against
`txt2tags_perl/lib/Text/Txt2tags/Converter.pm`. Always test Perl changes
against the repo (`perl -Ilib bin/txt2tags` or `prove -l t/`), never assume
the system `txt2tags` command reflects the current state of this repo.
