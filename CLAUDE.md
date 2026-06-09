# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains ports of [txt2tags](https://txt2tags.org) — a plain-text markup converter — to multiple languages. The original txt2tags is a monolithic Python 2 script; this repo refactors and ports it.

### Ports

- **`txt2tags3_mod/`** — Python 3 port, split into focused modules. This is the primary, actively developed port. Installable as `txt2tags3-mod` via pip (`pyproject.toml`).
- **`txt2tags3`** — The original monolithic Python 3 script (single file, ~416KB).
- **`txt2tags_perl/`** — Perl port (`Text::Txt2tags` module + `bin/txt2tags` CLI).

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
