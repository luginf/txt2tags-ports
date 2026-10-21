txt2tags manual
txt2tags-ports
2026-10-21


 * 1. Getting started
  * 1.1. Run it
  * 1.2. Your first document
 * 2. The three areas of a document
  * 2.1. Header area
  * 2.2. Config area
  * 2.3. Body area
 * 3. Marks
  * 3.1. Titles
  * 3.2. Inline marks
  * 3.3. Paragraphs, line breaks, comments
  * 3.4. Verbatim, raw and tagged text
  * 3.5. Horizontal lines
  * 3.6. Links and images
  * 3.7. Lists
  * 3.8. Quotes
  * 3.9. Tables
 * 4. Macros
 * 5. Settings
  * 5.1. Filters
  * 5.2. Include
 * 6. Command line
  * 6.1. Where options come from
 * 7. Targets
 * 8. The smaller ports


txt2tags turns a plain-text document into HTML, LaTeX, Markdown, DocBook,
man pages and 40 other formats. You write the text once, with a handful of
simple marks, and convert it as many times as you need.

This manual covers the language and the command line of the reference-like
ports in this repository (Python `txt2tags3_mod`, Perl, and the single-file
builds). The structure follows the official guide at
https://txt2tags.org/userguide/ ; the last chapter lists what the small Go,
Rust, Lua and Tcl ports support.

# 1. Getting started 

## 1.1. Run it 

Pick whichever form suits you; all of them take the same options.

| Form |Command|
|---|---|
|Python single file |`python3 txt2tags.py -t html file.t2t`|
|Python package |`python3 -m txt2tags3_mod -t html file.t2t`|
|Perl single file |`perl txt2tags.pl -t html file.t2t`|
|Perl from sources |`perl -Ilib bin/txt2tags -t html file.t2t`|

The single files `txt2tags.py` and `txt2tags.pl` are attached to each
GitHub release. They have no dependency besides Python 3 or Perl 5. Both are
generated: `python3 txt2tags3_mod/bundle.py` writes
`txt2tags3_mod/out/txt2tags.py` and `perl txt2tags_perl/bundle.pl` writes
`txt2tags_perl/out/txt2tags.pl`.

By default the output goes to the input name with the target extension
(`file.t2t` gives `file.html`). Use `-o OUTFILE` to choose another name,
or `-o -` to print on standard output. `-` as input reads standard input.

## 1.2. Your first document 

Save this as `first.t2t`:

    My first document
    Your Name
    2026-01-31
    
    = Introduction =
    
    This is a **bold** word, an //italic// one and a [link http://txt2tags.org].
    
    - first item
    - second item

Then run `txt2tags -t html first.t2t` and open `first.html`.

# 2. The three areas of a document 

A `.t2t` file has up to three areas, always in this order.

## 2.1. Header area 

The first three lines: title, author, date. All are optional, but they keep
their position, so leave a line empty to skip it. If the very first line is
empty, the document has no header. The date line accepts a macro:

    My title
    My name
    %%date(%Y-%m-%d)

With `--skip-header-lines` the header is not reserved at all and the body
starts on line 1 (useful for generated or snippet files).

## 2.2. Config area 

Lines starting with `%!` right after the header. They set options for this
document only (see [Settings](#settings)).

    %!target: html
    %!encoding: UTF-8
    %!options: --toc

## 2.3. Body area 

Everything else. A line holding only `%%` ends the config area explicitly.

# 3. Marks 

## 3.1. Titles 

    = Title level 1 =
    == Title level 2 ==
    ===== Title level 5 =====
    + Numbered title +
    ++ Numbered level 2 ++
    = Title with a label =[mylabel]

The `=` signs on both sides must match, and a title can't be indented.
Spaces around or inside the signs are ignored. Levels go from 1 to 5. A label
goes right after the title, with no space, between brackets, and may contain
letters, digits, `_` and `-`. Numbered titles (`+`) count on their own
(1, 1.1...); `-n` or `--enum-title` numbers all titles. A flush-left title
also closes an open list (see [Lists](#lists)).

## 3.2. Inline marks 

|Result |You write|
|bold |`**bold**`|
|italic |`//italic//`|
|underline |`__underline__`|
|strike |`--strike--`|
|monospaced |```mono```|

Marks must hug their text: `** not bold **` is left alone, and a mark glued
to a word on the outside (`2**3**4`) is not markup either. Marks can be
combined (`**//bold italic//**`).

## 3.3. Paragraphs, line breaks, comments 

A paragraph is a block of lines ended by a blank line (a list or a table
also ends it). Leading and trailing spaces are ignored. A line with `%` in
column 1 is a comment and never reaches the output, even inside a paragraph;
`%` anywhere else is plain text. A comment area is everything between two
lines holding only `%%%`.

## 3.4. Verbatim, raw and tagged text 

Verbatim keeps text exactly as typed (escaped for the target). Raw sends text
to the output untouched, and tagged text is like raw but marked as target
code. Each has a one-line form and an area form:

    ``` one verbatim line
    
    ```
    verbatim area
    **not bold here**
    ```
    
    """ one raw line
    
    """
    raw area, sent as is
    """
    
    ''' one tagged line
    
    '''
    tagged area
    '''

## 3.5. Horizontal lines 

A line of at least 20 characters among `-`, `=` and `_` is a line. If it
starts with `=` it is a strong line, otherwise a separator line. Leading and
trailing spaces are allowed.

## 3.6. Links and images 

    http://txt2tags.org                    bare URL, linked automatically
    name@example.org                       email address
    [label http://txt2tags.org]            named link
    [label page.html]                      local file link
    [photo.png]                            image
    [[photo.png] http://txt2tags.org]      image used as a link

Recognised image extensions are png, jpg/jpeg, gif, eps, bmp and svg. No
spaces are allowed inside the brackets of an image. A link label can itself be
an image, and a label may not contain a `]` (use `%!postproc` for that).
Addresses starting with `www.` or `ftp.` are linked too, the protocol being
added for you.

## 3.7. Lists 

    - bullet item
     - nested item (one more space)
    + numbered item
     + nested numbered item
    : term
     definition

There is exactly one space after the mark, and the indentation is free: a
deeper indentation starts a sublist. A list ends after two consecutive blank
lines, at the end of the file, or at an empty item (a line holding only the
mark: `-`, `+` or `:`), which closes the current sublist. One blank
line does not end a list: it lets an item contain several paragraphs, and
keeps `- a` / blank / `- b` in a single list.

In this fork, a flush-left title ends the list as well, even after a single
blank line or none:

    - last item
    
    == Next section ==

Upstream txt2tags swallowed such a title into the last item. Run with
`--legacy` to get that old behaviour back. A further option,
`--blank-closes-list`, closes a list on a single blank line unless the next
line is another item or is blank itself. Items with several paragraphs no
longer work with it.

## 3.8. Quotes 

A line starting with a tab is a quote. More tabs nest it deeper.

## 3.9. Tables 

    || Name | Qty |
    | apples | 3 |
    | pears | 12 |

`||` starts a header row, `|` a normal row. Keep a space around each pipe
(spaces, not tabs). A trailing pipe at the end of the row draws a border, and
spaces before the first pipe center the whole table. Extra pipes at the end of
a cell span it across columns (`| wide cell ||`). Padding decides alignment:
two or more spaces before a cell and none after right-aligns it, two or more
on both sides centers it. Targets with table
support (HTML, LaTeX, DocBook, the wikis...) render real tables; the others
get plain-text ones.

# 4. Macros 

|Macro |Expands to|
|`%%date` |today's date, `%%date(%Y-%m-%d)` takes a strftime format|
|`%%mtime` |modification time of the source, same format argument|
|`%%infile` |input file name|
|`%%outfile` |output file name|
|`%%toc` |the table of contents, at this position|

Macro names are case insensitive. A table of contents can also be requested with `--toc` (`--toc-level=N`
sets the depth, `--toc-title=S` the title, `--toc-only` prints only it).

# 5. Settings 

A config line is `%!KEY: value`. Spacing and capitalization of the key
are ignored (`%!Target:html` and `%! TARGET :html` are the same).

|Key |Meaning|
|`%!target` |default target when `-t` isn't given|
|`%!options` |extra command-line options, as if typed|
|`%!encoding` |encoding of the source file|
|`%!style` |style sheet file (HTML CSS, LaTeX package)|
|`%!preproc` |rewrite the source before conversion|
|`%!postproc` |rewrite the output after conversion|
|`%!include` |insert another file at this point|
|`%!includeconf` |load only the config lines of another file|

## 5.1. Filters 

`%!preproc` and `%!postproc` are "find and replace" rules, like sed.
They take exactly two arguments: a regular expression and a replacement,
quoted with `'...'` or `"..."` (or a single word with no spaces).

    %!preproc: 'TODO' 'DONE'
    %!postproc: '(</?)B>' '\1STRONG>'

 * Preprocessing runs on each source line as it is read; postprocessing runs
on the converted document.
 * Filters are cumulative and applied in the order defined; define as many as
needed.
 * `\n` and `\t` in the replacement are interpreted. To delete text,
replace it with an empty string.
 * The pattern is a regular expression (Python syntax in `txt2tags3_mod`,
Perl syntax in the Perl port). Escape `\* \+ \. \^ \$ \? \( \) \{ \[ \| \\`
to match them literally.

Any setting except `%!target` can be restricted to a target with
`%!key(target): value`. For filters, both the generic and the target ones
are used:

    %!style(html): fancy.css
    %!style(tex): amssymb
    %!postproc(html): '<body>' '<body class="manual">'
    %!options(sgml): --toc

When a postproc filter rewrites tags, prefer the explicit target form.

## 5.2. Include 

    %!include: chapter1.t2t
    %!include(html): only-for-html.t2t
    %!include: ``code.c``
    %!include: ""data.html""
    %!include: ''tags.txt''

Plain, backquoted, double-quoted and single-quoted file names include the file
as txt2tags text, as verbatim, as raw and as tagged text respectively. For a
txt2tags include, only the Body area of the file is used; its header and
config areas are ignored, so the chapter can also be converted on its own.
Use `--dump-source` to see the document with every include expanded.

`%!includeconf: shared.t2t` (Config area only, no target form) loads the
settings of another file, in the same format as the RC file.

# 6. Command line 

`txt2tags [OPTIONS] file.t2t`

|Option |Effect|
|`-t TARGET` |output format (`--targets` lists them)|
|`-o FILE` |output file, `-` for standard output|
|`-i FILE` |input file, `-` for standard input|
|`-H` |no header/footer, just the converted body|
|`-T FILE` |use FILE as the output template|
|`--encoding=ENC` |source encoding|
|`--toc`, `--toc-level=N`, `--toc-title=S`, `--toc-only` |table of contents|
|`-n` |number all titles|
|`--style=FILE` |style sheet; `--css-sugar` and `--css-inside` for HTML|
|`--embed-images` |embed images as data in HTML, RTF, aat, aap|
|`--mask-email` |hide addresses from spam robots|
|`--width=N`, `--height=N`, `--chars=S` |ASCII-art and rst output|
|`--fix-path` |fix relative paths of images, links and CSS|
|`-C FILE` |read extra configuration from FILE|
|`--blank-closes-list` |see [Lists](#lists)|
|`--legacy` |titles are swallowed by an open list, like upstream|
|`--skip-header-lines` |no 3-line header, body starts on line 1|
|`--dump-config` |print all configuration found and exit|
|`--dump-source` |print the source with includes expanded|
|`-q` / `-v` |quiet / verbose|
|`-V` / `-h` |version / help|

Any option turns off with a `no-` prefix (`--no-toc`).

## 6.1. Where options come from 

From lowest to highest priority, each one overriding the previous:

1. the user configuration file (RC file): `$HOME/.txt2tagsrc` on Unix, Linux
and Mac, `%HOMEPATH%\_t2trc` on Windows, or the file named by the
`T2TCONFIG` environment variable;
1. the Config area of the document (`%!` lines, including `%!options`);
1. the command line.

The RC file uses the same format as the Config area, for settings shared by
all your documents (for example `%!options: --toc-level 4`). Any line of it
that isn't blank, a comment or a valid config line is an error. `--no-rc`
ignores it for one run.

# 7. Targets 

Run `txt2tags --targets` for the exact list of your version.

| Family |Targets|
|---|---|
|Web |html, html5, xhtml, xhtmls, htmls, wp|
|Wiki |md, rst, adoc, bbcode, creole, doku, gmi, gwiki, moin, pmw, red, spip, tml, vimwiki, wiki, txt2t|
|Office |tex, texs, dbk, sgml, rtf, lout, mgp, mom, pm6, utmac, csv, csvs, ods, db|
|Text |txt, man, aat, aap, aas, aapp|

The ASCII-art targets (aa*) draw boxes and tables with plain characters.
The `*s` and `htmls` targets render spreadsheet-like output.

# 8. The smaller ports 

The Go, Rust, Lua and Tcl ports re-implement a subset of the language with
their own small code base. They read the same `.t2t` files but only produce
HTML and LaTeX (`-t html` or `-t tex`; Tcl does HTML only).

|Feature |Go |Rust |Lua |Tcl|
|Header, titles, paragraphs, lists, tables, inline marks |yes |yes |yes |yes|
|Links, bare URLs |yes |yes |yes |no|
|Images, verbatim blocks |yes |yes |no |no|
|Raw blocks, block comments |yes |yes |no |no|
|Definition lists, table alignment |yes |yes |definition lists only |no|
|`%%date`, `%%toc` |yes |yes |yes |no|
|`%!preproc` / `%!postproc` |yes |yes |no |no|

Go and Rust produce identical output. Their bare URLs follow the same rules as
the reference: a URL stops at brackets, quotes and spaces, and drops trailing
`.,;:!?`. They have no includes, quotes, numbered titles or other targets;
use the Python or Perl versions for those.

Binaries for Go and Rust are attached to the GitHub releases.

