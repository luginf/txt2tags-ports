# txt2tags-ports

Ports of [txt2tags](https://txt2tags.org) — a plain-text markup converter — to multiple languages. See `CLAUDE.md` for the full scope policy and design notes; this is just the quick "how do I run it" reference.

## Download

Each [GitHub release](https://github.com/luginf/txt2tags-ports/releases) attaches:

- `txt2tags.py` - single-file Python 3 build (no dependency)
- `txt2tags.pl` - single-file Perl 5 build (no dependency)
- `txt2tags-go-linux-amd64` and `txt2tags-rust-linux-amd64` - HTML/LaTeX/Markdown binaries of the small Go and Rust ports

```bash
python3 txt2tags.py -t html input.t2t
perl txt2tags.pl -t html input.t2t
```

The single files are generated from the modular sources:
`python3 txt2tags3_mod/bundle.py` (to `txt2tags3_mod/out/`) and
`perl txt2tags_perl/bundle.pl` (to `txt2tags_perl/out/`).

## Documentation

The manual is published at https://luginf.github.io/txt2tags-ports/ and lives in
[`docs/`](docs/): [Markdown](docs/manual.md) (readable on GitHub), [HTML](docs/index.html)
and its source [`manual.t2t`](docs/manual.t2t) (built with `-t html5` / `-t md`).
Markup syntax, config lines, command line, targets, and what each port supports.

## Which port?

| Port | Targets | Language coverage |
|---|---|---|
| `txt2tags3_mod` (Python), `txt2tags_perl` | 45 targets | full |
| `txt2tags_go`, `txt2tags_rust` | html, tex, md | subset, identical output between the two; Markdown identical to the Python and Perl ports |
| `txt2tags_lua`, `txt2tags_tcl` | html, tex (Lua) / html (Tcl) | simpler subset |

## Differences from upstream txt2tags

- A flush-left title always ends an open list. Upstream swallows it into the
  last item when only one blank line separates them; `--legacy` restores that.
- `--blank-closes-list`: a single blank line closes a list (unless the next
  line continues it).
- `--skip-header-lines`: no 3-line header, the body starts on line 1.
- Markdown output (`-t md`) is GitHub-flavoured and escapes literal `*`, `_`, `<`, `>`, `#` and `1.`;
  nested lists, definition lists, table alignment and the title/author/date header render correctly.
- All four ports that export Markdown (Python, Perl, Go, Rust) give the same
  `-t md` output on the common subset.
  HTML and LaTeX are only the same between the full ports, and between Go and Rust.
- `-n` / `--enum-title` works in the Perl port too, and `%%toc` no longer leaves a `vvvTOCvvv`
  placeholder in the output of the Python port.

## Go and Rust command line

The Go and Rust binaries take the same options as the Python port, within what they support
(`txt2tags --help` lists them, `txt2tags --targets` shows `html`, `md` and `tex`):

```bash
txt2tags-go-linux-amd64 -t md --toc -n file.t2t     # writes file.md
txt2tags-rust-linux-amd64 -t html -H -o - file.t2t  # body only, on stdout
```

Supported: `-t`, `-o`, `-i`, `-H`, `--toc`, `--toc-level`, `--toc-title`, `--toc-only`, `-n`,
`--skip-header-lines`, `--encoding` (UTF-8 only), `--dump-source`, `--dump-config`, `-q`, `-v`,
`-V`, `-h`, `--no-` prefix, `--no-rc`. Options that need CSS, templates, rc files or other
targets (`--style`, `-T`, `-C`, `--mask-email`, `--width`...) stop with an error.
As in the Python port the result goes to `file.<target>` unless `-o` says otherwise.

## txt2tags3_mod (Python 3, primary port)

```bash
python -m txt2tags3_mod -t html input.t2t       # writes input.html
python -m txt2tags3_mod -t html -o - input.t2t   # prints to stdout instead
```

## txt2tags3 (original monolithic Python script)

```bash
python3 txt2tags3 -t html input.t2t              # writes input.html
```

## txt2tags_perl

```bash
cd txt2tags_perl
perl Makefile.PL && make            # or: cpanm --installdeps .
perl -Ilib bin/txt2tags -t html input.t2t        # writes input.html
perl -Ilib bin/txt2tags -t html -o - input.t2t   # prints to stdout instead
```

## txt2tags_lua

```bash
lua5.4 txt2tags_lua/bin/txt2tags -t html input.t2t [output.html]
# or -t tex for LaTeX
```

## txt2tags_tcl

```bash
tclsh txt2tags_tcl/bin/txt2tags input.t2t [output.html]
```

## txt2tags_rust

```bash
cd txt2tags_rust
cargo build --release
./target/release/txt2tags -t html input.t2t [output.html]
# or -t tex for LaTeX; `cargo run -- -t html input.t2t` also works without a separate build step
```

## txt2tags_go

```bash
cd txt2tags_go
go build -o txt2tags ./cmd/txt2tags
./txt2tags -t html input.t2t [output.html]
# or -t tex for LaTeX; `go run ./cmd/txt2tags -t html input.t2t` also works without a separate build step
```
