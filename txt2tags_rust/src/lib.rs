//! txt2tags.rs
//!
//! Rust port of txt2tags. Started as a simple-tier prototype (structure
//! mirroring the Lua/Tcl ports in this repo) and has since taken its first
//! advanced-tier pass, per the repo's CLAUDE.md "Scope policy" section:
//! the two tiers stay separable in the code (see the "── advanced tier ──"
//! marker below) rather than being interleaved through the simple-tier
//! plain-string functions.
//!
//! Simple tier (plain substring search / manual char scanning, no regex):
//!   - Head: title / author / date (first 3 lines)
//!   - Comment lines (% ...) anywhere in the body, and config lines
//!     (%! ...) in the head area, are skipped, not parsed
//!   - Section headings: = h1 = .. ===== h5 =====
//!   - Horizontal rule: a line of 20+ repeated -, = or _
//!   - Paragraphs (blank-line separated)
//!   - Unordered (- ) and ordered (+ ) lists, with indentation-based nesting
//!   - Inline: **bold**, //italic//, __underline__, --strike--, ``mono``
//!   - A backslash is plain text (no escape): `\**x**` is a backslash then bold
//!   - Tables: "| cell | cell |" rows, "||" prefix marks a header row
//!   - Macros: `%%date` (substituted anywhere in the raw text, before any
//!     other parsing, with today's date as `YYYY-MM-DD`) and `%%toc`, a
//!     line on its own that expands to a flat table of contents (heading
//!     anchors are only added when a `%%toc` is actually present, so plain
//!     documents render exactly as before).
//!
//! ── advanced tier (gated behind the `regex` crate) ──────────────────────
//!   - Links: `[label URL]`, bare `[URL]`, and bare autolinks
//!     (`http://...`, `https://...`, `ftp://...`) detected directly in text.
//!   - Images: `[path.ext]` for a handful of common raster/vector
//!     extensions, `[path.ext URL]` for a clickable image, and the classic
//!     nested `[ [path.ext] URL ]` shape too (the one real txt2tags
//!     documents actually use). Any other kind of bracket nesting -- e.g.
//!     LionWiki's unrelated `[[label | URL]]` double-bracket dialect --
//!     isn't parsed as a link; the outer brackets are left literal and the
//!     inner one gets its own look, rather than producing a mangled href.
//!   - Verbatim blocks: a line of exactly ``` opens/closes one; content is
//!     passed through with only entity-escaping (HTML) or none (LaTeX
//!     `verbatim` environment), no inline marks applied.
//!   - Raw blocks: a line of exactly """ opens/closes one; content is
//!     escaped for the target but gets no inline marks (as in the reference).
//!   - Tagged blocks: a line of exactly ''' opens/closes one; content is
//!     passed through completely unmodified -- it's meant to already be
//!     valid markup in the target format.
//!   - Block comments: a line of exactly %%% opens/closes one; everything
//!     inside produces no output at all (checked ahead of the single-line
//!     `%` comment rule, which would otherwise only skip the fence lines
//!     themselves and leave the interior as a stray paragraph).
//!   - Definition lists: `: term` followed by indented definition line(s).
//!   - Table column-alignment inference: a cell padded with 2+ spaces on
//!     the left and none on the right (relative to the pipe delimiters) is
//!     right-aligned; 2+ on both sides is centered; anything else is left
//!     (the default). Only inferred from rows that close with a trailing
//!     `|` -- a row without one can't tell "intentional padding" from "the
//!     line was simply trimmed", so its last cell stays left-aligned.
//!     Alignment is applied per-cell in HTML (`style="text-align:..."`)
//!     and per-column in LaTeX (`tabular` spec derived from the first row).
//!   - `%!preproc: 'PATTERN' 'REPLACEMENT'` / `%!postproc: 'PATTERN'
//!     'REPLACEMENT'` config lines in the head area: preproc rules run
//!     against each body line before parsing, postproc rules against each
//!     rendered output line before the final string is returned. Patterns
//!     and replacements are single- or double-quoted; replacement syntax
//!     is the `regex` crate's (`$1`, `${1}`), not Perl's `\1` -- a known
//!     deviation from the classic txt2tags config-file dialect.
//!   - Marks only trigger when glued to their content (no space right
//!     after the opening mark or right before the closing one), as in the
//!     reference; what sits outside them does not matter (`a--b--c`).
//!
//! Export targets: HTML (`to_html`), LaTeX (`to_latex`) and Markdown
//! (`to_markdown`, GitHub-flavoured), all reachable through `convert` with a
//! `Target` and the `Options` that mirror the Python port's command line
//! (`-H`, `--toc`, `--toc-level`, `--toc-only`, `-n`, `--skip-header-lines`).
//! The LaTeX target assumes a preamble with `\usepackage[normalem]{ulem}`
//! (`\sout`, for `--strike--`), `\usepackage{graphicx}` (images) and
//! `\usepackage{hyperref}` (links) -- see the top of `render_latex`.
//!
//!   - Bare URLs stop at the reference URL character set (no brackets,
//!     quotes or whitespace) and drop trailing `.,;:!?`, so `[label URL]`
//!     inside other brackets or at the end of a sentence never leaks a `]`
//!     or `.` into the href.
//!
//! Bracket nesting: only the single-level `[label URL]` and the
//! image-as-link `[[img.ext] URL]` shapes are links. The reference regex
//! would also accept a `[` inside the label (`[a [b URL]`, and so the
//! LionWiki `[[label | URL]]` as a link labelled `[label |`); this port
//! deliberately leaves those brackets literal instead. Balanced nesting
//! such as `[see [1] URL]` is not a link in the reference either.
//!
//! NOT supported yet (left for a later pass): nested constructs
//! inside table cells or definition-list entries beyond plain inline
//! marks/links.

use regex::Regex;
use std::sync::OnceLock;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ListKind {
    Ul,
    Ol,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Align {
    Left,
    Center,
    Right,
}

#[derive(Debug, Clone)]
pub struct ListItem {
    /// a blank line separated this item from the previous one
    pub blank_before: bool,
    pub kind: ListKind,
    pub level: usize,
    pub text: String,
}

#[derive(Debug, Clone)]
pub struct TableRow {
    pub header: bool,
    pub cells: Vec<(String, Align)>,
}

#[derive(Debug, Clone)]
pub enum Block {
    /// `numbered`: a `+ title +` (always numbered), not a `= title =`.
    Heading { level: usize, text: String, numbered: bool },
    Hr,
    Para { lines: Vec<String> },
    List { items: Vec<ListItem> },
    Table { rows: Vec<TableRow> },
    Toc,
    Verbatim { lines: Vec<String> },
    Raw { lines: Vec<String> },
    Tagged { lines: Vec<String> },
    DefList { items: Vec<(String, Vec<String>)> },
    /// Lines indented with tabs: the depth is the number of tabs.
    Quote { lines: Vec<(usize, String)> },
    /// Plain text that goes on with the last list item after a verbatim,
    /// raw or tagged block interrupted it (Markdown indents it by `pad`).
    ListText { lines: Vec<String>, pad: usize },
}

#[derive(Debug, Clone)]
pub struct Document {
    pub title: String,
    pub author: String,
    pub date: String,
    pub blocks: Vec<Block>,
    pub postproc: Vec<(Regex, String)>,
    /// `%!options:` lines as (target, words)
    pub options: Vec<(Option<String>, Vec<String>)>,
}

// ── date macro ───────────────────────────────────────────────────────────

// Days-since-epoch -> (year, month, day), Howard Hinnant's civil_from_days
// algorithm (public domain) -- proleptic Gregorian, valid for any date this
// macro will ever actually see. No date/time crate needed.
fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719468;
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = (z - era * 146097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    let y = if m <= 2 { y + 1 } else { y };
    (y, m, d)
}

/// Today's date (UTC) as `YYYY-MM-DD`. Public mainly so callers/tests can
/// compare against what `%%date` expands to without duplicating the date
/// math.
pub fn today_string() -> String {
    let days = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64
        / 86400;
    let (y, m, d) = civil_from_days(days);
    format!("{y:04}-{m:02}-{d:02}")
}

/// What the `%%macro`s can say about the conversion in progress.
#[derive(Debug, Clone, Default)]
pub struct MacroEnv {
    /// input file name, `-` or empty for standard input
    pub infile: String,
    pub outfile: String,
    pub target: String,
    /// title, author and date of the document, for `%%header1` to `%%header3`
    pub headers: [String; 3],
}

const WEEKDAYS: [&str; 7] = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTHS: [&str; 12] = [
    "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
    "November", "December",
];

/// `strftime` for the flags that make sense in a UTC date (C locale).
fn strftime(fmt: &str, secs: i64) -> String {
    let days = secs.div_euclid(86400);
    let rem = secs.rem_euclid(86400);
    let (y, m, d) = civil_from_days(days);
    let (hh, mm, ss) = (rem / 3600, rem % 3600 / 60, rem % 60);
    let wday = (days + 4).rem_euclid(7) as usize; // 1970-01-01 was a Thursday
    let (jan1, _, _) = (days_from_civil(y, 1, 1), 0, 0);
    let yday = days - jan1 + 1;
    let mut out = String::new();
    let mut it = fmt.chars();
    while let Some(c) = it.next() {
        if c != '%' {
            out.push(c);
            continue;
        }
        match it.next() {
            None => out.push('%'),
            Some('Y') => out.push_str(&format!("{y}")),
            Some('y') => out.push_str(&format!("{:02}", y.rem_euclid(100))),
            Some('m') => out.push_str(&format!("{m:02}")),
            Some('d') => out.push_str(&format!("{d:02}")),
            Some('e') => out.push_str(&format!("{d:2}")),
            Some('H') => out.push_str(&format!("{hh:02}")),
            Some('I') => out.push_str(&format!("{:02}", if hh % 12 == 0 { 12 } else { hh % 12 })),
            Some('M') => out.push_str(&format!("{mm:02}")),
            Some('S') => out.push_str(&format!("{ss:02}")),
            Some('p') => out.push_str(if hh < 12 { "AM" } else { "PM" }),
            Some('j') => out.push_str(&format!("{yday:03}")),
            Some('a') => out.push_str(&WEEKDAYS[wday][..3]),
            Some('A') => out.push_str(WEEKDAYS[wday]),
            Some('b') | Some('h') => out.push_str(&MONTHS[m as usize - 1][..3]),
            Some('B') => out.push_str(MONTHS[m as usize - 1]),
            Some('u') => out.push_str(&format!("{}", if wday == 0 { 7 } else { wday })),
            Some('w') => out.push_str(&format!("{wday}")),
            Some('s') => out.push_str(&format!("{secs}")),
            Some('Z') => out.push_str("UTC"),
            Some('z') => out.push_str("+0000"),
            Some('F') => out.push_str(&format!("{y}-{m:02}-{d:02}")),
            Some('T') => out.push_str(&format!("{hh:02}:{mm:02}:{ss:02}")),
            Some('D') => out.push_str(&format!("{m:02}/{d:02}/{:02}", y.rem_euclid(100))),
            Some('n') => out.push('\n'),
            Some('t') => out.push('\t'),
            Some('%') => out.push('%'),
            Some(o) => {
                out.push('%');
                out.push(o);
            }
        }
    }
    out
}

fn days_from_civil(y: i64, m: u32, d: u32) -> i64 {
    let y = if m <= 2 { y - 1 } else { y };
    let era = if y >= 0 { y } else { y - 399 } / 400;
    let yoe = (y - era * 400) as u64;
    let mp = if m > 2 { m - 3 } else { m + 9 } as u64;
    let doy = (153 * mp + 2) / 5 + d as u64 - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146097 + doe as i64 - 719468
}

fn now_secs() -> i64 {
    if let Some(v) = std::env::var("SOURCE_DATE_EPOCH").ok().and_then(|v| v.parse::<i64>().ok()) {
        return v;
    }
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs() as i64
}

/// `%%infile(fmt)` and friends: %f name, %F name without extension,
/// %d directory, %D parent directory name only, %p path, %e extension.
fn file_macro(file: &str, fmt: &str) -> String {
    let (path, dir, name) = if file.is_empty() || file == "-" {
        (file.to_string(), String::new(), file.to_string())
    } else {
        let p = std::path::Path::new(file);
        let abs = if p.is_absolute() {
            p.to_path_buf()
        } else {
            std::env::current_dir().unwrap_or_default().join(p)
        };
        let dir = abs.parent().map(|d| d.to_string_lossy().to_string()).unwrap_or_default();
        let name = abs.file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default();
        (abs.to_string_lossy().to_string(), dir, name)
    };
    let stem = |n: &str| match n.rfind('.') {
        Some(at) if at > 0 => n[..at].to_string(),
        _ => n.to_string(),
    };
    let mut out = String::new();
    let mut it = fmt.chars();
    while let Some(c) = it.next() {
        if c != '%' {
            out.push(c);
            continue;
        }
        match it.next() {
            None => out.push('%'),
            Some('%') => out.push('%'),
            Some('f') => out.push_str(&name),
            Some('F') => out.push_str(&stem(&name)),
            Some('d') => out.push_str(&dir),
            Some('D') => out.push_str(dir.rsplit('/').next().unwrap_or("")),
            Some('p') => out.push_str(&path),
            Some('e') => out.push_str(match name.rfind('.') {
                Some(at) if at > 0 => &name[at + 1..],
                _ => "",
            }),
            Some(o) => {
                out.push('%');
                out.push(o);
            }
        }
    }
    out
}

/// Replaces the `%%macro` and `%%macro(format)` calls the Python port
/// knows (all but `%%cmdline` and `%%cc`) anywhere in `text`. The
/// `%%headerN` ones are left for `expand_header_macros`.
fn expand_macros(text: &str, env: &MacroEnv) -> String {
    static RGX: OnceLock<Regex> = OnceLock::new();
    let rgx = RGX.get_or_init(|| {
        Regex::new(r"(?i)%%(date|mtime|infile|currentfile|outfile|appurl|appname|appversion|target|encoding|header[123])\b(?:\((.*?)\))?")
            .unwrap()
    });
    rgx.replace_all(text, |c: &regex::Captures| {
        let name = c[1].to_lowercase();
        let fmt = c.get(2).map(|m| m.as_str());
        match name.as_str() {
            "date" => strftime(fmt.unwrap_or("%Y-%m-%d"), now_secs()),
            "mtime" => {
                let secs = if env.infile.is_empty() || env.infile == "-" {
                    now_secs()
                } else {
                    std::fs::metadata(&env.infile)
                        .and_then(|m| m.modified())
                        .ok()
                        .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                        .map_or_else(now_secs, |d| d.as_secs() as i64)
                };
                strftime(fmt.unwrap_or("%Y%m%d"), secs)
            }
            "infile" | "currentfile" => file_macro(&env.infile, fmt.unwrap_or("%f")),
            "outfile" => file_macro(&env.outfile, fmt.unwrap_or("%f")),
            "appurl" => "http://txt2tags.org".to_string(),
            "appname" => "txt2tags".to_string(),
            "appversion" => env!("CARGO_PKG_VERSION").to_string(),
            "target" => env.target.clone(),
            "encoding" => "UTF-8".to_string(),
            h => env.headers[h[6..].parse::<usize>().unwrap() - 1].clone(),
        }
    })
    .to_string()
}

thread_local! {
    /// The macros of the document being converted: set by `convert`, read by
    /// the inline formatter (macros are expanded in running text, not in
    /// verbatim, raw or tagged blocks, nor inside a ``mono`` span).
    static MACRO_ENV: std::cell::RefCell<MacroEnv> = std::cell::RefCell::new(MacroEnv::default());
}

fn expand_inline_macros(text: &str) -> String {
    if !text.contains("%%") {
        return text.to_string();
    }
    static MONO: OnceLock<Regex> = OnceLock::new();
    let mono = MONO.get_or_init(|| Regex::new(r"``[^\s](?:.*?[^\s])?`*``").unwrap());
    MACRO_ENV.with(|env| {
        let env = env.borrow();
        text.split('\n')
            .map(|line| {
                let mut out = String::new();
                let mut at = 0;
                for m in mono.find_iter(line) {
                    out.push_str(&expand_macros(&line[at..m.start()], &env));
                    out.push_str(m.as_str());
                    at = m.end();
                }
                out.push_str(&expand_macros(&line[at..], &env));
                out
            })
            .collect::<Vec<_>>()
            .join("\n")
    })
}

// ── head parsing ─────────────────────────────────────────────────────────

struct HeadInfo {
    title: String,
    author: String,
    date: String,
    body_start: usize,
    preproc: Vec<(Regex, String)>,
    postproc: Vec<(Regex, String)>,
    options: Vec<(Option<String>, Vec<String>)>,
}

/// Splits the value of a `%!options:` line into words, honouring quotes.
fn split_words(s: &str) -> Vec<String> {
    let mut words = Vec::new();
    let mut cur = String::new();
    let mut has = false;
    let mut quote: Option<char> = None;
    for c in s.chars() {
        match quote {
            Some(q) if c == q => quote = None,
            Some(_) => cur.push(c),
            None if c == '\'' || c == '"' => {
                quote = Some(c);
                has = true;
            }
            None if c.is_whitespace() => {
                if has || !cur.is_empty() {
                    words.push(std::mem::take(&mut cur));
                    has = false;
                }
            }
            None => cur.push(c),
        }
    }
    if has || !cur.is_empty() {
        words.push(cur);
    }
    words
}

/// `%!options: ...` or `%!options(target): ...`
fn parse_options_line(line: &str) -> Option<(Option<String>, Vec<String>)> {
    let rest = line.strip_prefix("%!options")?;
    let (target, rest) = if let Some(r) = rest.strip_prefix('(') {
        let end = r.find(')')?;
        (Some(r[..end].trim().to_string()), &r[end + 1..])
    } else {
        (None, rest)
    };
    let rest = rest.strip_prefix(':')?;
    Some((target, split_words(rest)))
}

// Reads one 'quoted' or "quoted" span at the start of `s`, returning its
// content and the remainder of `s` after the closing quote.
fn read_quoted(s: &str) -> Option<(String, &str)> {
    let q = s.chars().next()?;
    if q != '\'' && q != '"' {
        return None;
    }
    let rest = &s[q.len_utf8()..];
    let end = rest.find(q)?;
    Some((rest[..end].to_string(), &rest[end + q.len_utf8()..]))
}

/// Parses a `%!preproc:`/`%!postproc:` config line into
/// (kind, pattern, replacement), or `None` if it isn't one / is malformed.
fn parse_config_directive(line: &str) -> Option<(&'static str, String, String)> {
    let (kind, rest) = if let Some(r) = line.strip_prefix("%!preproc:") {
        ("preproc", r)
    } else if let Some(r) = line.strip_prefix("%!postproc:") {
        ("postproc", r)
    } else {
        return None;
    };
    let (pattern, rest2) = read_quoted(rest.trim_start())?;
    let (replacement, _) = read_quoted(rest2.trim_start())?;
    Some((kind, pattern, replacement))
}

fn parse_head(lines: &[&str], skip_header: bool) -> HeadInfo {
    let reserved = if skip_header { 0 } else { 3 };
    let field = |n: usize| {
        if skip_header {
            String::new()
        } else {
            lines.get(n).unwrap_or(&"").trim().to_string()
        }
    };
    let (title, author, date) = (field(0), field(1), field(2));

    let mut preproc = Vec::new();
    let mut postproc = Vec::new();
    let mut options = Vec::new();

    let mut i = reserved;
    while i < lines.len() {
        let t = lines[i].trim();
        if t == "%%" {
            i += 1;
            break;
        } else if t == "%%toc" {
            // A body macro, not a head comment/config line -- leave it for
            // parse_body rather than swallowing it here.
            break;
        } else if t.starts_with("%!") {
            if let Some(o) = parse_options_line(t) {
                options.push(o);
            } else if let Some((kind, pattern, replacement)) = parse_config_directive(t) {
                if let Ok(re) = Regex::new(&pattern) {
                    if kind == "preproc" {
                        preproc.push((re, replacement));
                    } else {
                        postproc.push((re, replacement));
                    }
                }
            }
            i += 1;
        } else if is_macro_line(lines[i]) {
            // a line that starts with a macro is where the body begins
            break;
        } else if t.starts_with('%') || t.is_empty() {
            i += 1;
        } else {
            break;
        }
    }
    HeadInfo {
        title,
        author,
        date,
        body_start: i,
        preproc,
        postproc,
        options,
    }
}

fn apply_line_rules(text: &str, rules: &[(Regex, String)]) -> String {
    if rules.is_empty() {
        return text.to_string();
    }
    text.lines()
        .map(|line| {
            let mut l = line.to_string();
            for (re, repl) in rules {
                l = re.replace_all(&l, repl.as_str()).to_string();
            }
            l
        })
        .collect::<Vec<_>>()
        .join("\n")
}

// ── line classifiers ─────────────────────────────────────────────────────

fn is_hr(line: &str) -> bool {
    let t = line.trim();
    // like the reference: 20 or more of - = _ (mixed allowed)
    t.chars().count() >= 20 && t.chars().all(|ch| matches!(ch, '-' | '=' | '_'))
}

/// Level (1-5) and text, or `None` if `line` isn't a title.
fn is_heading(line: &str) -> Option<(usize, String, bool)> {
    let mut t = line.trim();
    let mark = t.chars().next()?;
    if mark != '=' && mark != '+' {
        return None;
    }
    // an optional trailing [label], which the markdown output does not use
    if t.ends_with(']') {
        if let Some(open) = t.rfind('[') {
            let label = &t[open + 1..t.len() - 1];
            if label.chars().all(|c| c.is_alphanumeric() || c == '_' || c == '-') {
                t = &t[..open];
            }
        }
    }
    let chars: Vec<char> = t.chars().collect();
    let mut level = 0;
    while level < chars.len() && chars[level] == mark {
        level += 1;
    }
    if level < 1 || level > 5 || chars.len() < 2 * level {
        return None;
    }
    if !chars[chars.len() - level..].iter().all(|&c| c == mark) {
        return None;
    }
    let text: String = chars[level..chars.len() - level]
        .iter()
        .collect::<String>()
        .trim()
        .to_string();
    if text.is_empty() {
        return None;
    }
    // the text may not start or end with the mark itself
    if text.starts_with(mark) || text.ends_with(mark) {
        return None;
    }
    Some((level, text, mark == '+'))
}

/// Kind, 0-based nesting level, and text, or `None` if `line` isn't a list item.
fn is_list_item(line: &str) -> Option<(ListKind, usize, String)> {
    let spaces = line.chars().take_while(|&c| c == ' ').count();
    let rest: String = line.chars().skip(spaces).collect();
    let marker: String = rest.chars().take(2).collect();
    let kind = match marker.as_str() {
        "- " => ListKind::Ul,
        "+ " => ListKind::Ol,
        _ => return None,
    };
    let text: String = rest.chars().skip(2).collect::<String>().trim().to_string();
    if text.is_empty() {
        return None;
    }
    Some((kind, spaces, text))
}

/// Lines that start a block of their own and so end an open list.
fn starts_block(l: &str) -> bool {
    l.starts_with('\t')
        || one_line_block(l).is_some()
        || (!l.starts_with(' ') && is_heading(l).is_some())
        || is_hr(l)
        || is_fence(l, "```")
        || is_fence(l, "\"\"\"")
        || is_fence(l, "'''")
        || is_fence(l, "%%%")
        || is_toc_macro(l)
        || is_table_row(l).is_some()
        || is_deflist_term(l).is_some()
}

/// Indentation (in spaces) to nesting depth: an item indented more than the
/// previous one is nested in it, one indented less closes the deeper levels.
fn normalize_list_levels(items: &mut [ListItem]) {
    // (indent, kind of the list open at that indent)
    let mut stack: Vec<(usize, ListKind)> = Vec::new();
    for (n, item) in items.iter_mut().enumerate() {
        let mut dedented = false;
        while stack.last().map_or(false, |&(l, _)| item.level < l) {
            stack.pop();
            dedented = true;
        }
        match stack.last_mut() {
            // back on an open list, even at an odd indent: the item joins it
            Some((_, kind)) if dedented => item.kind = *kind,
            Some((l, kind)) if item.level == *l => {
                // same indent, other mark: a new list
                *kind = item.kind;
            }
            _ => {
                // a nested list, or a new one when the old one was left
                if dedented && n > 0 {
                    item.blank_before = true;
                }
                stack.push((item.level, item.kind));
            }
        }
        item.level = stack.len() - 1;
    }
}

fn cell_align(raw: &str) -> Align {
    // the whole cell, spaces included: " x " is centered, " x" right-aligned
    if raw.trim().is_empty() {
        Align::Left
    } else if raw.starts_with(' ') && raw.ends_with(' ') {
        Align::Center
    } else if raw.starts_with(' ') {
        Align::Right
    } else {
        Align::Left
    }
}

/// Is-header flag and (text, alignment) cells, or `None` if `line` isn't a
/// table row. Cells are separated by " | " (a bar with a space on each
/// side), so a bar inside a word stays text; `||` at the start marks a
/// title row and `||` at the end of a cell a column span (kept as one cell).
fn is_table_row(line: &str) -> Option<(bool, Vec<(String, Align)>)> {
    static MARK: OnceLock<Regex> = OnceLock::new();
    static BORDER: OnceLock<Regex> = OnceLock::new();
    static SPAN: OnceLock<Regex> = OnceLock::new();
    let mark = MARK.get_or_init(|| Regex::new(r"^ *\|([|_/])? ").unwrap());
    let border = BORDER.get_or_init(|| Regex::new(r" (\|+) *$").unwrap());
    let span = SPAN.get_or_init(|| Regex::new(r" (\|+)\| ").unwrap());
    let line = line.trim_end();
    if !mark.is_match(line) {
        return None;
    }
    let mut chars: Vec<char> = line.trim_start().chars().collect();
    if chars.get(1) == Some(&'_') {
        chars.remove(1);
    }
    if chars.get(1) == Some(&'/') {
        chars[1] = '|';
    }
    let is_header = chars.get(1) == Some(&'|');
    let mut s: String = chars.into_iter().collect();
    if border.is_match(&s) {
        s.push(' ');
    } else {
        s.push_str(" | ");
    }
    let s = mark.replace(&s, "").to_string();
    let s = span.replace_all(&s, "\u{7}${1} | ").to_string();
    let mut parts: Vec<&str> = s.split(" | ").collect();
    parts.pop();
    let cells = parts
        .into_iter()
        .map(|raw| {
            let raw = match raw.find('\u{7}') {
                Some(at) if raw[at + 1..].chars().all(|c| c == '|') => &raw[..at],
                _ => raw,
            };
            (raw.trim().to_string(), cell_align(raw))
        })
        .collect();
    Some((is_header, cells))
}

/// A line whose trimmed content starts with "%" (and is not a `%%macro`) is a single-line comment,
/// stripped wherever it appears in the body (not just in the head area).
/// Block comments ("%%%" ... "%%%") are handled by parse_body.
fn is_comment(line: &str) -> bool {
    // a line that starts with a macro is text, not a comment
    line.trim().starts_with('%') && !is_macro_line(line)
}

fn is_macro_line(line: &str) -> bool {
    static MACRO: OnceLock<Regex> = OnceLock::new();
    MACRO
        .get_or_init(|| {
            Regex::new(r"(?i)^%%(date|mtime|infile|currentfile|outfile|appurl|appname|appversion|target|cmdline|encoding|header[123]|cc)\b")
                .unwrap()
        })
        .is_match(line)
}

fn is_toc_macro(line: &str) -> bool {
    line.trim() == "%%toc"
}

fn is_deflist_term(line: &str) -> Option<String> {
    let text = line.strip_prefix(": ")?.trim();
    if text.is_empty() {
        None
    } else {
        Some(text.to_string())
    }
}

fn is_fence(line: &str, marker: &str) -> bool {
    line.trim_end() == marker
}

/// A fence mark, a space and some text on one line: that line alone is a
/// verbatim (` ``` `), raw (`"""`) or tagged (`'''`) block.
fn one_line_block(line: &str) -> Option<(&'static str, &str)> {
    for (mark, kind) in [("``` ", "verb"), ("\"\"\" ", "raw"), ("''' ", "tagged")] {
        if let Some(rest) = line.strip_prefix(mark) {
            if !rest.is_empty() {
                return Some((kind, rest));
            }
        }
    }
    None
}

// ── inline markup ────────────────────────────────────────────────────────

fn html_escape_char(c: char) -> String {
    match c {
        '&' => "&amp;".to_string(),
        '<' => "&lt;".to_string(),
        '>' => "&gt;".to_string(),
        other => other.to_string(),
    }
}

fn latex_escape_char(c: char) -> String {
    match c {
        '\\' => "\\textbackslash{}".to_string(),
        '&' => "\\&".to_string(),
        '%' => "\\%".to_string(),
        '$' => "\\$".to_string(),
        '#' => "\\#".to_string(),
        '_' => "\\_".to_string(),
        '{' => "\\{".to_string(),
        '}' => "\\}".to_string(),
        '~' => "\\textasciitilde{}".to_string(),
        '^' => "\\textasciicircum{}".to_string(),
        other => other.to_string(),
    }
}

fn html_escape(s: &str) -> String {
    s.chars().map(html_escape_char).collect()
}

fn latex_escape(s: &str) -> String {
    s.chars().map(latex_escape_char).collect()
}

fn html_attr_escape(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            '&' => "&amp;".to_string(),
            '"' => "&quot;".to_string(),
            other => other.to_string(),
        })
        .collect()
}

// \X anywhere in the raw text protects X from both escaping-driven
// surprises and from being read as part of a markup delimiter.
const PLACEHOLDER_MARK: char = '\u{1}';
// Marks a resolved link/image span, so mark-matching can't reach into its
// (already fully rendered) target-format output.
const PLACEHOLDER_LINK: char = '\u{2}';

fn protect_escapes(s: &str) -> (String, Vec<char>) {
    let chars: Vec<char> = s.chars().collect();
    let mut out = String::new();
    let mut escaped: Vec<char> = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        if c == '\\' {
            // txt2tags has no backslash escape: the backslash is plain text
            // and the marks after it still apply ("\**x**" is "\" + bold).
            escaped.push(c);
            out.push(PLACEHOLDER_MARK);
            out.push_str(&escaped.len().to_string());
            out.push(PLACEHOLDER_MARK);
            i += 1;
        } else {
            out.push(c);
            i += 1;
        }
    }
    (out, escaped)
}

fn restore_escapes(s: &str, escaped: &[char], literal: fn(char) -> String) -> String {
    let mut result = s.to_string();
    for (idx, ch) in escaped.iter().enumerate() {
        let token = format!("{PLACEHOLDER_MARK}{}{PLACEHOLDER_MARK}", idx + 1);
        if let Some(pos) = result.find(&token) {
            result.replace_range(pos..pos + token.len(), &literal(*ch));
        }
    }
    result
}

fn restore_link_placeholders(s: &str, items: &[String]) -> String {
    let mut result = s.to_string();
    for (idx, item) in items.iter().enumerate() {
        let token = format!("{PLACEHOLDER_LINK}{}{PLACEHOLDER_LINK}", idx + 1);
        if let Some(pos) = result.find(&token) {
            result.replace_range(pos..pos + token.len(), item);
        }
    }
    result
}

/// (mark, open, close) -- a symmetric HTML tag is just open="<x>"/close="</x>",
/// but LaTeX commands need distinct open/close strings, hence three parts
/// rather than assuming a tag name.
type Delim = (&'static str, &'static str, &'static str);

const HTML_DELIMS: &[Delim] = &[
    ("**", "<b>", "</b>"),
    ("//", "<i>", "</i>"),
    ("__", "<u>", "</u>"),
    ("--", "<s>", "</s>"),
    ("``", "<tt>", "</tt>"),
];

const LATEX_DELIMS: &[Delim] = &[
    ("**", "\\textbf{", "}"),
    ("//", "\\textit{", "}"),
    ("__", "\\underline{", "}"),
    ("--", "\\sout{", "}"),
    ("``", "\\texttt{", "}"),
];

// A mark only opens when it's glued to its content (no whitespace right
// after it). Like the reference regexes, it does not matter what sits on the
// outside: "a--b--c" has a struck "b".
fn valid_open_boundary(before: Option<char>, after: Option<char>) -> bool {
    let _ = before;
    after.map_or(false, |c| !c.is_whitespace())
}

// Mirror of valid_open_boundary for the closing delimiter: glued to its
// content on the inside (no whitespace right before it).
fn valid_close_boundary(before: Option<char>, after: Option<char>) -> bool {
    let _ = after;
    before.map_or(false, |c| !c.is_whitespace())
}

fn find_boundary(
    s: &str,
    mark: &str,
    valid: fn(Option<char>, Option<char>) -> bool,
) -> Option<usize> {
    let mut start = 0;
    while let Some(rel) = s[start..].find(mark) {
        let pos = start + rel;
        let before = s[..pos].chars().next_back();
        let after = s[pos + mark.len()..].chars().next();
        if valid(before, after) {
            return Some(pos);
        }
        start = pos + mark.len();
    }
    None
}

/// Leftmost-delimiter, recursive-descent inline formatter (no patterns).
fn apply_marks(s: &str, delims: &[Delim]) -> String {
    let mut best: Option<(usize, &str, &str, &str)> = None;
    for &(mark, open, close) in delims {
        if let Some(p) = find_boundary(s, mark, valid_open_boundary) {
            if best.map_or(true, |(bp, ..)| p < bp) {
                best = Some((p, mark, open, close));
            }
        }
    }
    let Some((pos, mark, open, close)) = best else {
        return s.to_string();
    };

    let before = &s[..pos];
    let after_open = pos + mark.len();
    match find_boundary(&s[after_open..], mark, valid_close_boundary) {
        None => format!("{before}{mark}{}", apply_marks(&s[after_open..], delims)),
        Some(rel_close) => {
            let close_pos = after_open + rel_close;
            let inner = &s[after_open..close_pos];
            let rest = &s[close_pos + mark.len()..];
            format!(
                "{before}{open}{}{close}{}",
                apply_marks(inner, delims),
                apply_marks(rest, delims)
            )
        }
    }
}

const IMAGE_EXTS: &[&str] = &["png", "jpg", "jpeg", "gif", "eps", "bmp", "svg"];

/// `image.EXT`: a path of word characters and `,.+%$#@!?~/-` ending in an
/// image extension, as the reference accepts it between brackets.
fn looks_like_image(s: &str) -> bool {
    let lower = s.to_lowercase();
    s.chars()
        .all(|c| c.is_alphanumeric() || "_,.+%$#@!?~/-".contains(c))
        && IMAGE_EXTS
            .iter()
            .any(|ext| lower.ends_with(&format!(".{ext}")) && lower.len() > ext.len() + 1)
}

const URL_CHARS: &str = "A-Za-z0-9%._/~:,=$@&+-";

/// What may follow the label in `[label target]`: an address with a
/// protocol (and its query and anchor), an e-mail, or a file name or
/// `#anchor` -- the reference calls anything made of URL characters a link.
fn looks_like_url(s: &str) -> bool {
    static RE: OnceLock<Regex> = OnceLock::new();
    let re = RE.get_or_init(|| {
        Regex::new(&format!(
            r"(?i)^(?:(?:https?|ftp|news|telnet|gopher|wais)://[{c}]+/*(?:\?[A-Za-z0-9/%&=+:;.,$@*_-]+)?(?:#[\w%.-]*)?|[{c}]+|[{c}]*#[\w%.-]*)$",
            c = URL_CHARS
        ))
        .unwrap()
    });
    re.is_match(s)
}

/// The address a link really points to: `www.x.org` is `http://www.x.org`,
/// `ftp.x.org` is `ftp://ftp.x.org`, `a@b.org` is `mailto:a@b.org`.
fn link_url(target: &str) -> String {
    static GUESS: OnceLock<Regex> = OnceLock::new();
    static EMAIL: OnceLock<Regex> = OnceLock::new();
    let guess = GUESS.get_or_init(|| Regex::new(r"(?i)^(?:(www[23]?)|ftp)\.").unwrap());
    let email = EMAIL.get_or_init(|| {
        Regex::new(r"(?i)^[A-Za-z0-9_.-]+@(?:[A-Za-z0-9_-]+\.)+[A-Za-z]{2,4}(?:\?[A-Za-z0-9/%&=+:;.,$@*_-]+)?$").unwrap()
    });
    if let Some(m) = guess.captures(target) {
        if m.get(1).is_some() {
            format!("http://{target}")
        } else {
            format!("ftp://{target}")
        }
    } else if email.is_match(target) {
        format!("mailto:{target}")
    } else {
        target.to_string()
    }
}

fn starts_with_at(chars: &[char], i: usize, pat: &str) -> bool {
    let pchars: Vec<char> = pat.chars().collect();
    if i + pchars.len() > chars.len() {
        return false;
    }
    chars[i..i + pchars.len()] == pchars[..]
}

fn looks_like_autolink_start(chars: &[char], i: usize) -> bool {
    if i > 0 && (chars[i - 1].is_alphanumeric() || chars[i - 1] == '_') {
        return false;
    }
    let after = |n: usize| chars.get(i + n).map_or(false, |c| c.is_ascii_alphanumeric());
    ["http://", "https://", "ftp://", "news://", "telnet://", "gopher://", "wais://"]
        .iter()
        .any(|p| starts_with_at(chars, i, p) && after(p.len()))
        // www.x.org and ftp.x.org, without a protocol
        || ["www.", "www2.", "www3.", "ftp."]
            .iter()
            .any(|p| starts_with_at(chars, i, p) && after(p.len()))
}

// Characters a bare URL may contain: the reference txt2tags URL character
// classes (path chars, form-data chars, `?` and `#` markers), notably
// without brackets, quotes, `<`/`>` or whitespace.
fn is_url_char(c: char) -> bool {
    c.is_ascii_alphanumeric() || "%._/~:,=$@&+-;*?#".contains(c)
}

// End (exclusive) of the bare URL starting at `start`: the longest run of
// URL characters, minus trailing sentence punctuation (`.,;:!?`), so that
// "see http://x.org." or "[label http://x.org]" don't pull the "." or "]"
// into the href.
fn autolink_end(chars: &[char], start: usize) -> usize {
    let mut end = start;
    while end < chars.len() && is_url_char(chars[end]) {
        end += 1;
    }
    while end > start && ".,;:!?".contains(chars[end - 1]) {
        end -= 1;
    }
    end
}

/// Everything the inline pipeline needs to know about one output format.
/// `escape` is applied to ordinary text before marks are matched, `literal`
/// to a character the author protected with a backslash (so the two differ
/// for Markdown, where "*" must survive until the marks are applied but a
/// protected "\*" must come out escaped), and `post` runs last.
struct Fmt {
    escape: fn(&str) -> String,
    literal: fn(char) -> String,
    delims: &'static [Delim],
    link: fn(&str, &str) -> String,
    /// a link found in the text without a label of its own
    autolink: fn(&str, &str) -> String,
    image: fn(&str) -> String,
    post: fn(&str) -> String,
    /// ``mono`` spans are copied as they are (no marks, no escapes inside)
    mono_verbatim: bool,
}

// Runs the escape+mark pipeline (but not link/image extraction -- nested
// links aren't supported) over a link label or bare-URL text, reusing the
// same protect_escapes() lookup table as the surrounding text.
/// Bare addresses in the text are kept out of the marks ("//" in a URL is
/// not italic).
fn inline_label(protected_text: &str, escaped: &[char], fmt: &Fmt) -> String {
    const URL_TOKEN: char = '\u{3}';
    let chars: Vec<char> = protected_text.chars().collect();
    let mut masked = String::new();
    let mut urls: Vec<String> = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        if looks_like_autolink_start(&chars, i) {
            let j = autolink_end(&chars, i);
            urls.push(chars[i..j].iter().collect());
            masked.push(URL_TOKEN);
            masked.push_str(&urls.len().to_string());
            masked.push(URL_TOKEN);
            i = j;
        } else {
            masked.push(chars[i]);
            i += 1;
        }
    }
    let esc = (fmt.escape)(&masked);
    let mut out = apply_marks(&esc, fmt.delims);
    for (n, url) in urls.iter().enumerate() {
        let token = format!("{URL_TOKEN}{}{URL_TOKEN}", n + 1);
        out = out.replace(&token, &(fmt.escape)(url));
    }
    restore_escapes(&out, escaped, fmt.literal)
}

/// Content of a `[...]` span (already protect_escapes'd) -> fully rendered
/// link/image output, or `None` if it doesn't look like a link/image (the
/// brackets are then left as literal text).
fn render_bracket(content: &str, escaped: &[char], fmt: &Fmt) -> Option<String> {
    let content = content.trim();
    if content.is_empty() {
        return None;
    }
    match content.rsplit_once(' ') {
        // [label target]
        Some((label_part, target)) => {
            let (label_part, target) = (label_part.trim(), target.trim());
            if !looks_like_url(target) {
                return None;
            }
            let label = inline_label(label_part, escaped, fmt);
            Some((fmt.link)(&label, &link_url(target)))
        }
        // [image.ext]
        None if looks_like_image(content) => Some((fmt.image)(content)),
        None => None,
    }
}

/// Tries to match `[ [image.ext] URL ]` starting at `chars[outer_open]`
/// (already confirmed to be `[` immediately followed by another `[`).
/// Returns the rendered image-link and the index just past the outer `]`
/// on success.
fn find_link_render(chars: &[char], outer_open: usize, fmt: &Fmt) -> Option<(String, usize)> {
    let (render_link, render_image) = (fmt.link, fmt.image);
    let inner_open = outer_open + 1;
    let rel_inner_close = chars[inner_open + 1..].iter().position(|&ch| ch == ']')?;
    let inner_close = inner_open + 1 + rel_inner_close;
    let inner: String = chars[inner_open + 1..inner_close].iter().collect();
    if inner.contains('[') {
        return None;
    }
    let rel_outer_close = chars[inner_close + 1..].iter().position(|&ch| ch == ']')?;
    let outer_close = inner_close + 1 + rel_outer_close;
    let target: String = chars[inner_close + 1..outer_close].iter().collect();
    let target = target.trim();
    let inner_trim = inner.trim();
    if target.contains('[') || !looks_like_image(inner_trim) || !looks_like_url(target) {
        return None;
    }
    Some((render_link(&render_image(inner_trim), &link_url(target)), outer_close + 1))
}

/// Scans (already protect_escapes'd) text for `[label URL]`/`[image.ext]`
/// brackets and bare autolinks, replacing each with a numbered
/// PLACEHOLDER_LINK token. Returns the token-substituted text plus the
/// list of fully rendered replacements, indexed by token number - 1.
fn plain_char(c: char) -> String {
    c.to_string()
}

/// `""raw""` (escaped for the target, no marks) and `''tagged''` (passed
/// through) spans starting at `i`, with the index just after the span. The
/// text between the marks may not start or end with a space; extra marker
/// characters next to the closing mark belong to the text.
fn literal_span(chars: &[char], i: usize, escaped: &[char], fmt: &Fmt) -> Option<(String, usize)> {
    let q = chars[i];
    if (q != '"' && q != '\'') || chars.get(i + 1) != Some(&q) {
        return None;
    }
    let mut j = i + 3;
    while j + 1 < chars.len() {
        if chars[j] == q && chars[j + 1] == q {
            let first = chars[i + 2];
            let last = chars[j - 1];
            if !first.is_whitespace() && !last.is_whitespace() {
                while chars.get(j + 2) == Some(&q) {
                    j += 1;
                }
                let content: String = chars[i + 2..j].iter().collect();
                let rendered = if q == '"' {
                    restore_escapes(&(fmt.escape)(&content), escaped, fmt.literal)
                } else {
                    restore_escapes(&content, escaped, plain_char)
                };
                return Some((rendered, j + 2));
            }
        }
        j += 1;
    }
    None
}

/// A ``mono`` span starting at `i`, copied as it is, and the index after it.
fn mono_span(chars: &[char], i: usize, escaped: &[char]) -> Option<(String, usize)> {
    if chars[i] != '`' || chars.get(i + 1) != Some(&'`') {
        return None;
    }
    let mut j = i + 3;
    while j + 1 < chars.len() {
        if chars[j] == '`' && chars[j + 1] == '`' {
            let first = chars[i + 2];
            let last = chars[j - 1];
            if !first.is_whitespace() && !last.is_whitespace() {
                while chars.get(j + 2) == Some(&'`') {
                    j += 1;
                }
                let content: String = chars[i + 2..j].iter().collect();
                let body = restore_escapes(&content, escaped, plain_char);
                return Some((format!("`{body}`"), j + 2));
            }
        }
        j += 1;
    }
    None
}

fn extract_links_images(s: &str, escaped: &[char], fmt: &Fmt) -> (String, Vec<String>) {
    let chars: Vec<char> = s.chars().collect();
    let mut out = String::new();
    let mut items: Vec<String> = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        let span = literal_span(&chars, i, escaped, fmt).or_else(|| {
            if fmt.mono_verbatim {
                mono_span(&chars, i, escaped)
            } else {
                None
            }
        });
        if let Some((rendered, next)) = span {
            items.push(rendered);
            out.push(PLACEHOLDER_LINK);
            out.push_str(&items.len().to_string());
            out.push(PLACEHOLDER_LINK);
            i = next;
            continue;
        }
        if c == '[' {
            // Classic txt2tags image-as-link: [ [image.png] URL ] -- a
            // single level of nesting with a very specific shape, checked
            // before the generic (single-level-only) bracket handling
            // below so it doesn't get rejected by the "no nested '['"
            // guard. Anything that doesn't match this exact shape (e.g.
            // LionWiki's unrelated [[label | URL]] double-bracket dialect)
            // falls through to that guard's graceful degradation.
            if i + 1 < chars.len() && chars[i + 1] == '[' {
                if let Some((rendered, consumed_to)) = find_link_render(&chars, i, fmt) {
                    items.push(rendered);
                    out.push(PLACEHOLDER_LINK);
                    out.push_str(&items.len().to_string());
                    out.push(PLACEHOLDER_LINK);
                    i = consumed_to;
                    continue;
                }
            }
            if let Some(close_rel) = chars[i + 1..].iter().position(|&ch| ch == ']') {
                let close = i + 1 + close_rel;
                let content: String = chars[i + 1..close].iter().collect();
                // A nested '[' means this isn't a single-level [label URL]
                // span (e.g. LionWiki-style [[label | URL]] double
                // brackets, a different, unsupported dialect) -- leave the
                // outer bracket as literal text and let the inner one get
                // its own look on a later loop iteration, rather than
                // mis-parsing the whole span into a mangled link.
                if !content.contains('[') {
                    if let Some(rendered) = render_bracket(&content, escaped, fmt) {
                        items.push(rendered);
                        out.push(PLACEHOLDER_LINK);
                        out.push_str(&items.len().to_string());
                        out.push(PLACEHOLDER_LINK);
                        i = close + 1;
                        continue;
                    }
                }
            }
            out.push(c);
            i += 1;
        } else if looks_like_autolink_start(&chars, i) {
            let start = i;
            let j = autolink_end(&chars, i);
            let word: String = chars[start..j].iter().collect();
            let label = inline_label(&word, escaped, fmt);
            items.push((fmt.autolink)(&label, &link_url(&word)));
            out.push(PLACEHOLDER_LINK);
            out.push_str(&items.len().to_string());
            out.push(PLACEHOLDER_LINK);
            i = j;
        } else {
            out.push(c);
            i += 1;
        }
    }
    (out, items)
}

fn inline_format_with(text: &str, fmt: &Fmt) -> String {
    let text = expand_inline_macros(text);
    let (protected, escaped) = protect_escapes(&text);
    let (linked, items) = extract_links_images(&protected, &escaped, fmt);
    let escaped_text = (fmt.escape)(&linked);
    let marked = apply_marks(&escaped_text, fmt.delims);
    let restored = restore_escapes(&marked, &escaped, fmt.literal);
    (fmt.post)(&restore_link_placeholders(&restored, &items))
}

fn html_link(label: &str, url: &str) -> String {
    format!("<a href=\"{}\">{label}</a>", html_attr_escape(url))
}

fn html_image(src: &str) -> String {
    format!("<img src=\"{}\" alt=\"\">", html_attr_escape(src))
}

fn latex_link(label: &str, url: &str) -> String {
    format!("\\href{{{url}}}{{{label}}}")
}

fn latex_image(src: &str) -> String {
    format!("\\includegraphics{{{src}}}")
}

const MD_DELIMS: &[Delim] = &[
    ("**", "**", "**"),
    ("//", "*", "*"),
    ("__", "", ""),
    ("--", "~~", "~~"),
    ("``", "`", "`"),
];

fn is_word_char(c: Option<char>) -> bool {
    c.map_or(false, |c| c.is_alphanumeric() || c == '_')
}

/// Keeps literal text from being read as Markdown. The doubled marks
/// (`**`, `` `` ``) are txt2tags marks, so only the single characters are
/// escaped; the content of a `` ``mono`` `` span is left alone. Runs on one
/// line at a time, before the marks are turned into Markdown syntax.
fn md_escape(s: &str) -> String {
    let chars: Vec<char> = s.chars().collect();
    let mut out = String::new();
    let mut i = 0;
    // line-start escapes: "# " headings and "1. " lists
    let lead = chars.iter().take_while(|c| c.is_whitespace()).count();
    let mut j = lead;
    let hashes = chars[j..].iter().take_while(|&&c| c == '#').count();
    let mut line_start_escape: Option<(usize, usize)> = None;
    if (1..=6).contains(&hashes) && chars.get(j + hashes).map_or(true, |c| c.is_whitespace()) {
        line_start_escape = Some((j, hashes));
    } else {
        let digits = chars[j..].iter().take_while(|c| c.is_ascii_digit()).count();
        j += digits;
        if digits > 0
            && chars.get(j) == Some(&'.')
            && chars.get(j + 1).map_or(false, |c| c.is_whitespace())
        {
            line_start_escape = Some((j, 0));
        }
    }
    while i < chars.len() {
        let c = chars[i];
        let prev = if i > 0 { Some(chars[i - 1]) } else { None };
        let next = chars.get(i + 1).copied();
        if let Some((at, n)) = line_start_escape {
            if i == at && n > 0 {
                out.push('\\');
                out.extend(std::iter::repeat('#').take(n));
                i += n;
                continue;
            }
            if i == at && n == 0 {
                out.push_str("\\.");
                i += 1;
                continue;
            }
        }
        if c == '`' && next == Some('`') {
            // copy a ``mono`` span untouched
            let mut k = i + 2;
            let mut close = None;
            while k + 1 < chars.len() {
                if chars[k] == '`' && chars[k + 1] == '`' && k > i + 2 {
                    close = Some(k);
                    break;
                }
                k += 1;
            }
            match close {
                Some(k) => {
                    out.extend(&chars[i..k + 2]);
                    i = k + 2;
                }
                None => {
                    out.push_str("``");
                    i += 2;
                }
            }
            continue;
        }
        match c {
            '*' if prev != Some('*') && next != Some('*') => out.push_str("\\*"),
            '`' if prev != Some('`') && next != Some('`') => out.push_str("\\`"),
            '_' if prev != Some('_')
                && next != Some('_')
                && (!is_word_char(prev) || !is_word_char(next)) =>
            {
                out.push_str("\\_")
            }
            '<' | '>' => {
                out.push('\\');
                out.push(c);
            }
            _ => out.push(c),
        }
        i += 1;
    }
    out
}

/// A character the author protected with a backslash, as Markdown.
fn md_literal(c: char) -> String {
    if "\\`*_[]()#<>~|!".contains(c) {
        format!("\\{c}")
    } else {
        c.to_string()
    }
}

fn md_url(url: &str) -> String {
    url.replace(' ', "%20").replace('(', "%28").replace(')', "%29")
}

fn md_link(label: &str, url: &str) -> String {
    format!("[{label}]({})", md_url(url))
}

fn md_autolink(label: &str, url: &str) -> String {
    if label == url || label == md_escape(url) {
        // a bare address is a link by itself
        return url.to_string();
    }
    md_link(label, url)
}

fn md_image(src: &str) -> String {
    format!("![]({})", md_url(src))
}

fn identity(s: &str) -> String {
    s.to_string()
}

const HTML_FMT: Fmt = Fmt {
    escape: html_escape,
    literal: html_escape_char,
    delims: HTML_DELIMS,
    link: html_link,
    autolink: html_link,
    image: html_image,
    post: identity,
    mono_verbatim: false,
};

const LATEX_FMT: Fmt = Fmt {
    escape: latex_escape,
    literal: latex_escape_char,
    delims: LATEX_DELIMS,
    link: latex_link,
    autolink: latex_link,
    image: latex_image,
    post: identity,
    mono_verbatim: false,
};

const MD_FMT: Fmt = Fmt {
    escape: md_escape,
    literal: md_literal,
    delims: MD_DELIMS,
    link: md_link,
    autolink: md_autolink,
    image: md_image,
    post: identity,
    mono_verbatim: true,
};

fn inline_format_md(text: &str) -> String {
    inline_format_with(text, &MD_FMT)
}

fn inline_format_html(text: &str) -> String {
    inline_format_with(text, &HTML_FMT)
}

fn inline_format_latex(text: &str) -> String {
    inline_format_with(text, &LATEX_FMT)
}

// ── block parsing ────────────────────────────────────────────────────────

fn parse_body(lines: &[&str]) -> Vec<Block> {
    let mut blocks = Vec::new();
    let n = lines.len();
    let mut i = 0;
    // After a verbatim, raw or tagged block interrupts a list, the plain text
    // that follows (one blank line at most) still belongs to its last item.
    let mut list_ctx: Option<usize> = None;
    let mut blank_run = 0;

    while i < n {
        let line = lines[i];
        let blocks_before = blocks.len();
        let mut ended_by_block: Option<usize> = None;

        if line.trim().is_empty() {
            blank_run += 1;
            if blank_run >= 2 {
                list_ctx = None;
            }
            i += 1;
            continue;
        } else if is_toc_macro(line) {
            blocks.push(Block::Toc);
            i += 1;
        } else if is_fence(line, "%%%") {
            // Block comment: everything up to the matching "%%%" produces
            // no output at all (checked before is_comment, which would
            // otherwise treat "%%%" itself as an ordinary single-line "%"
            // comment and only skip that one line).
            i += 1;
            while i < n && !is_fence(lines[i], "%%%") {
                i += 1;
            }
            if i < n {
                i += 1;
            }
        } else if is_comment(line) {
            i += 1;
        } else if let Some((level, text, numbered)) = is_heading(line) {
            blocks.push(Block::Heading { level, text, numbered });
            i += 1;
        } else if is_hr(line) {
            blocks.push(Block::Hr);
            i += 1;
        } else if let Some((kind, rest)) = one_line_block(line) {
            let lines = vec![rest.to_string()];
            blocks.push(match kind {
                "verb" => Block::Verbatim { lines },
                "raw" => Block::Raw { lines },
                _ => Block::Tagged { lines },
            });
            i += 1;
        } else if is_fence(line, "```") {
            i += 1;
            let mut vlines = Vec::new();
            while i < n && !is_fence(lines[i], "```") {
                vlines.push(lines[i].to_string());
                i += 1;
            }
            if i < n {
                i += 1;
            }
            blocks.push(Block::Verbatim { lines: vlines });
        } else if is_fence(line, "\"\"\"") {
            i += 1;
            let mut rlines = Vec::new();
            while i < n && !is_fence(lines[i], "\"\"\"") {
                rlines.push(lines[i].to_string());
                i += 1;
            }
            if i < n {
                i += 1;
            }
            blocks.push(Block::Raw { lines: rlines });
        } else if is_fence(line, "'''") {
            i += 1;
            let mut tlines = Vec::new();
            while i < n && !is_fence(lines[i], "'''") {
                tlines.push(lines[i].to_string());
                i += 1;
            }
            if i < n {
                i += 1;
            }
            blocks.push(Block::Tagged { lines: tlines });
        } else if line.starts_with('\t') {
            let mut qlines = Vec::new();
            while i < n && lines[i].starts_with('\t') {
                let depth = lines[i].chars().take_while(|&c| c == '\t').count();
                qlines.push((depth, lines[i].trim().to_string()));
                i += 1;
            }
            blocks.push(Block::Quote { lines: qlines });
        } else if let Some(first_term) = is_deflist_term(line) {
            let mut items: Vec<(String, Vec<String>)> = Vec::new();
            let mut term = first_term;
            let mut def: Vec<String> = Vec::new();
            i += 1;
            loop {
                if i >= n || lines[i].trim().is_empty() {
                    break;
                } else if let Some(next_term) = is_deflist_term(lines[i]) {
                    items.push((term, def));
                    term = next_term;
                    def = Vec::new();
                    i += 1;
                } else if lines[i].starts_with(' ') || lines[i].starts_with('\t') {
                    // a list item keeps its indent: it opens a sublist
                    if lines[i].starts_with(' ') && is_list_item(lines[i]).is_some() {
                        def.push(lines[i].trim_end().to_string());
                    } else {
                        def.push(lines[i].trim().to_string());
                    }
                    i += 1;
                } else {
                    break;
                }
            }
            items.push((term, def));
            blocks.push(Block::DefList { items });
        } else if is_list_item(line).is_some() {
            let mut items: Vec<ListItem> = Vec::new();
            let mut blanks = 0;
            while i < n {
                let l = lines[i];
                if l.trim().is_empty() {
                    blanks += 1;
                    i += 1;
                    // two blank lines end a list
                    if blanks >= 2 {
                        break;
                    }
                } else if is_comment(l) {
                    i += 1;
                } else if !l.starts_with(' ') && is_heading(l).is_some() {
                    break;
                } else if let Some((kind, level, text)) = is_list_item(l) {
                    items.push(ListItem { kind, level, text, blank_before: blanks > 0 });
                    blanks = 0;
                    i += 1;
                } else if starts_block(l) {
                    if is_fence(l, "```")
                        || is_fence(l, "\"\"\"")
                        || is_fence(l, "'''")
                        || one_line_block(l).is_some()
                    {
                        ended_by_block = Some(0);
                    }
                    break;
                } else {
                    // plain text keeps the item going (after one blank line
                    // it is a new paragraph of the item), as in the reference
                    let last = items.last_mut().unwrap();
                    last.text.push('\n');
                    if blanks > 0 {
                        last.text.push('\n');
                    }
                    last.text.push_str(l.trim());
                    blanks = 0;
                    i += 1;
                }
            }
            normalize_list_levels(&mut items);
            if ended_by_block.is_some() {
                let last = items.last().unwrap();
                let width = if last.kind == ListKind::Ol { 3 } else { 2 };
                ended_by_block = Some(4 * last.level + width);
            }
            blocks.push(Block::List { items });
        } else if is_table_row(line).is_some() {
            let mut rows = Vec::new();
            while i < n {
                match is_table_row(lines[i]) {
                    Some((header, cells)) => {
                        rows.push(TableRow { header, cells });
                        i += 1;
                    }
                    None => break,
                }
            }
            blocks.push(Block::Table { rows });
        } else {
            let mut plines = Vec::new();
            while i < n && !lines[i].trim().is_empty() {
                let l = lines[i];
                if is_toc_macro(l) || is_fence(l, "%%%") {
                    break;
                } else if is_comment(l) {
                    i += 1;
                } else if is_heading(l).is_some()
                    || is_hr(l)
                    || is_fence(l, "```")
                    || is_fence(l, "\"\"\"")
                    || is_fence(l, "'''")
                    || one_line_block(l).is_some()
                    || is_deflist_term(l).is_some()
                    || is_list_item(l).is_some()
                    || is_table_row(l).is_some()
                    || l.starts_with('\t')
                {
                    break;
                } else {
                    plines.push(l.trim().to_string());
                    i += 1;
                }
            }
            blocks.push(match list_ctx {
                Some(pad) => Block::ListText { lines: plines, pad },
                None => Block::Para { lines: plines },
            });
        }
        // what the block that was just read means for the text after it
        if blocks.len() > blocks_before {
            list_ctx = match blocks.last() {
                Some(Block::Verbatim { .. }) | Some(Block::Raw { .. }) | Some(Block::Tagged { .. }) => list_ctx,
                Some(Block::ListText { pad, .. }) => Some(*pad),
                Some(Block::List { .. }) => ended_by_block,
                _ => None,
            };
            blank_run = 0;
        }
    }

    blocks
}

// ── HTML rendering ───────────────────────────────────────────────────────

fn align_style(a: Align) -> &'static str {
    match a {
        Align::Left => "",
        Align::Center => " style=\"text-align:center\"",
        Align::Right => " style=\"text-align:right\"",
    }
}

// Consecutive same-level items are grouped by kind, so a ul/ol switch at
// the same nesting level closes one list and opens another instead of
// silently merging (e.g. a "- " list directly followed by a "+ " list).
/// An item's text with its paragraph breaks folded away (HTML and LaTeX
/// keep one block per item).
fn flat_item_text(text: &str) -> String {
    text.split('\n').filter(|l| !l.is_empty()).collect::<Vec<_>>().join("\n")
}

fn render_list_items_html(items: &[ListItem], mut i: usize, level: usize) -> (String, usize) {
    let mut out: Vec<String> = Vec::new();
    while i < items.len() && items[i].level == level {
        let kind = items[i].kind;
        let tag = match kind {
            ListKind::Ul => "ul",
            ListKind::Ol => "ol",
        };
        out.push(format!("<{tag}>"));
        while i < items.len() && items[i].level == level && items[i].kind == kind {
            out.push(format!("<li>{}", inline_format_html(&flat_item_text(&items[i].text))));
            i += 1;
            if i < items.len() && items[i].level > level {
                let (nested, ni) = render_list_items_html(items, i, items[i].level);
                out.push(nested);
                i = ni;
            }
            out.push("</li>".to_string());
        }
        out.push(format!("</{tag}>"));
    }
    (out.join("\n"), i)
}

/// What the renderers need to know beyond the block itself.
struct Ctx<'a> {
    blocks: &'a [Block],
    has_toc: bool,
    /// "1. ", "1.1. " ... per block index (empty when titles aren't numbered)
    numbers: Vec<String>,
    /// deepest heading level listed in the table of contents
    toc_level: usize,
    toc_title: &'a str,
    /// GitHub-style heading anchors per block index (Markdown only)
    slugs: Vec<String>,
}

impl Ctx<'_> {
    fn number(&self, index: usize) -> &str {
        self.numbers.get(index).map_or("", |s| s.as_str())
    }
}

fn heading_numbers(blocks: &[Block], all: bool) -> Vec<String> {
    let mut counters = [0usize; 6];
    blocks
        .iter()
        .map(|b| match b {
            Block::Heading { level, numbered, .. } if all || *numbered => {
                let l = (*level).clamp(1, 6);
                counters[l - 1] += 1;
                for c in counters.iter_mut().skip(l) {
                    *c = 0;
                }
                let parts: Vec<String> = counters[..l].iter().map(|n| n.to_string()).collect();
                format!("{}. ", parts.join("."))
            }
            _ => String::new(),
        })
        .collect()
}

// A table of contents is only meaningful (and its heading anchors only
// added) when the document actually contains a %%toc -- so plain
// documents render byte-identical headings, same as before this feature
// existed.
fn render_toc_html(ctx: &Ctx) -> String {
    let mut out = Vec::new();
    if !ctx.toc_title.is_empty() {
        out.push(format!(
            "<p class=\"toc-title\">{}</p>",
            html_escape(ctx.toc_title)
        ));
    }
    out.push("<ul class=\"toc\">".to_string());
    for (i, b) in ctx.blocks.iter().enumerate() {
        if let Block::Heading { level, text, .. } = b {
            if *level > ctx.toc_level {
                continue;
            }
            out.push(format!(
                "<li class=\"toc-h{level}\"><a href=\"#t2t-{i}\">{}{}</a></li>",
                ctx.number(i),
                inline_format_html(text)
            ));
        }
    }
    out.push("</ul>".to_string());
    out.join("\n")
}

fn render_block_html(block: &Block, index: usize, ctx: &Ctx) -> String {
    match block {
        Block::Heading { level, text, .. } => {
            let num = ctx.number(index);
            if ctx.has_toc {
                format!(
                    "<h{level} id=\"t2t-{index}\">{num}{}</h{level}>",
                    inline_format_html(text)
                )
            } else {
                format!("<h{level}>{num}{}</h{level}>", inline_format_html(text))
            }
        }
        Block::Hr => "<hr>".to_string(),
        Block::Quote { lines } => {
            let mut out = Vec::new();
            let mut cur = 0;
            for (depth, text) in lines {
                while cur < *depth {
                    out.push("<blockquote>".to_string());
                    cur += 1;
                }
                while cur > *depth {
                    out.push("</blockquote>".to_string());
                    cur -= 1;
                }
                out.push(inline_format_html(text));
            }
            while cur > 0 {
                out.push("</blockquote>".to_string());
                cur -= 1;
            }
            out.join("\n")
        }
        Block::Para { lines } | Block::ListText { lines, .. } => {
            let formatted: Vec<String> = lines.iter().map(|l| inline_format_html(l)).collect();
            format!("<p>\n{}\n</p>", formatted.join("\n"))
        }
        Block::List { items } => {
            if items.is_empty() {
                return String::new();
            }
            render_list_items_html(items, 0, items[0].level).0
        }
        Block::Table { rows } => {
            let mut out = vec!["<table>".to_string()];
            for row in rows {
                out.push("<tr>".to_string());
                let tag = if row.header { "th" } else { "td" };
                for (text, align) in &row.cells {
                    out.push(format!(
                        "<{tag}{}>{}</{tag}>",
                        align_style(*align),
                        inline_format_html(text)
                    ));
                }
                out.push("</tr>".to_string());
            }
            out.push("</table>".to_string());
            out.join("\n")
        }
        Block::Toc => render_toc_html(ctx),
        Block::Verbatim { lines } => {
            let escaped: Vec<String> = lines.iter().map(|l| html_escape(l)).collect();
            format!("<pre>\n{}\n</pre>", escaped.join("\n"))
        }
        Block::Raw { lines } => lines.iter().map(|l| html_escape(l)).collect::<Vec<_>>().join("\n"),
        Block::Tagged { lines } => lines.join("\n"),
        Block::DefList { items } => {
            let mut out = vec!["<dl>".to_string()];
            for (term, def) in items {
                out.push(format!("<dt>{}</dt>", inline_format_html(term)));
                for d in def {
                    out.push(format!("<dd>{}</dd>", inline_format_html(d.trim())));
                }
            }
            out.push("</dl>".to_string());
            out.join("\n")
        }
    }
}

fn render_html(title: &str, author: &str, date: &str, ctx: &Ctx, headers: bool) -> String {
    let blocks = ctx.blocks;
    if !headers {
        let body: Vec<String> = blocks
            .iter()
            .enumerate()
            .map(|(i, b)| render_block_html(b, i, ctx))
            .collect();
        return body.join("\n");
    }
    let mut out = Vec::new();
    out.push("<!DOCTYPE html>".to_string());
    out.push("<html>".to_string());
    out.push(format!(
        "<head><meta charset=\"utf-8\"><title>{}</title></head>",
        html_escape(title)
    ));
    out.push("<body>".to_string());
    if !title.is_empty() {
        out.push(format!("<h1>{}</h1>", html_escape(title)));
    }
    if !author.is_empty() || !date.is_empty() {
        let sep = if !author.is_empty() && !date.is_empty() {
            " - "
        } else {
            ""
        };
        out.push(format!(
            "<p class=\"header\">{}{sep}{}</p>",
            html_escape(author),
            html_escape(date)
        ));
    }
    for (i, block) in blocks.iter().enumerate() {
        out.push(render_block_html(block, i, ctx));
    }
    out.push("</body>".to_string());
    out.push("</html>".to_string());
    out.join("\n")
}

// ── LaTeX rendering ──────────────────────────────────────────────────────

fn render_list_items_latex(items: &[ListItem], mut i: usize, level: usize) -> (String, usize) {
    let mut out: Vec<String> = Vec::new();
    while i < items.len() && items[i].level == level {
        let kind = items[i].kind;
        let env = match kind {
            ListKind::Ul => "itemize",
            ListKind::Ol => "enumerate",
        };
        out.push(format!("\\begin{{{env}}}"));
        while i < items.len() && items[i].level == level && items[i].kind == kind {
            out.push(format!("\\item {}", inline_format_latex(&flat_item_text(&items[i].text))));
            i += 1;
            if i < items.len() && items[i].level > level {
                let (nested, ni) = render_list_items_latex(items, i, items[i].level);
                out.push(nested);
                i = ni;
            }
        }
        out.push(format!("\\end{{{env}}}"));
    }
    (out.join("\n"), i)
}

fn heading_command(level: usize) -> &'static str {
    match level {
        1 => "section",
        2 => "subsection",
        3 => "subsubsection",
        4 => "paragraph",
        5 => "subparagraph",
        _ => "paragraph",
    }
}

fn render_block_latex(block: &Block, ctx: &Ctx) -> String {
    match block {
        Block::Heading { level, text, .. } => {
            format!(
                "\\{}{{{}}}",
                heading_command(*level),
                inline_format_latex(text)
            )
        }
        Block::Hr => "\\par\\noindent\\hrulefill\\par".to_string(),
        Block::Quote { lines } => {
            let mut out = Vec::new();
            let mut cur = 0;
            for (depth, text) in lines {
                while cur < *depth {
                    out.push("\\begin{quote}".to_string());
                    cur += 1;
                }
                while cur > *depth {
                    out.push("\\end{quote}".to_string());
                    cur -= 1;
                }
                out.push(inline_format_latex(text));
            }
            while cur > 0 {
                out.push("\\end{quote}".to_string());
                cur -= 1;
            }
            out.join("\n")
        }
        Block::Para { lines } | Block::ListText { lines, .. } => {
            let formatted: Vec<String> = lines.iter().map(|l| inline_format_latex(l)).collect();
            formatted.join("\n")
        }
        Block::List { items } => {
            if items.is_empty() {
                return String::new();
            }
            render_list_items_latex(items, 0, items[0].level).0
        }
        Block::Table { rows } => {
            let ncols = rows.iter().map(|r| r.cells.len()).max().unwrap_or(0);
            let first_aligns: Vec<Align> = rows
                .first()
                .map(|r| r.cells.iter().map(|(_, a)| *a).collect())
                .unwrap_or_default();
            let spec: String = (0..ncols)
                .map(|c| match first_aligns.get(c).copied().unwrap_or(Align::Left) {
                    Align::Left => 'l',
                    Align::Center => 'c',
                    Align::Right => 'r',
                })
                .collect();
            let mut out = vec![format!("\\begin{{tabular}}{{{spec}}}")];
            for row in rows {
                let cells: Vec<String> = row
                    .cells
                    .iter()
                    .map(|(text, _)| {
                        let formatted = inline_format_latex(text);
                        if row.header {
                            format!("\\textbf{{{formatted}}}")
                        } else {
                            formatted
                        }
                    })
                    .collect();
                out.push(format!("{} \\\\", cells.join(" & ")));
                if row.header {
                    out.push("\\hline".to_string());
                }
            }
            out.push("\\end{tabular}".to_string());
            out.join("\n")
        }
        // LaTeX builds its own table of contents from the \section-family
        // commands above -- no manual anchor bookkeeping needed here.
        Block::Toc => {
            let mut out = Vec::new();
            if !ctx.toc_title.is_empty() {
                out.push(format!(
                    "\\renewcommand{{\\contentsname}}{{{}}}",
                    latex_escape(ctx.toc_title)
                ));
            }
            if ctx.toc_level != usize::MAX {
                out.push(format!("\\setcounter{{tocdepth}}{{{}}}", ctx.toc_level));
            }
            out.push("\\tableofcontents".to_string());
            out.join("\n")
        }
        Block::Verbatim { lines } => {
            format!("\\begin{{verbatim}}\n{}\n\\end{{verbatim}}", lines.join("\n"))
        }
        Block::Raw { lines } => lines.iter().map(|l| latex_escape(l)).collect::<Vec<_>>().join("\n"),
        Block::Tagged { lines } => lines.join("\n"),
        Block::DefList { items } => {
            let mut out = vec!["\\begin{description}".to_string()];
            for (term, def) in items {
                let def_text: Vec<String> = def.iter().map(|d| inline_format_latex(d.trim())).collect();
                out.push(format!(
                    "\\item[{}] {}",
                    inline_format_latex(term),
                    def_text.join(" ")
                ));
            }
            out.push("\\end{description}".to_string());
            out.join("\n")
        }
    }
}

fn render_latex(title: &str, author: &str, date: &str, ctx: &Ctx, headers: bool) -> String {
    if !headers {
        let body: Vec<String> = ctx.blocks.iter().map(|b| render_block_latex(b, ctx)).collect();
        return body.join("\n");
    }
    let mut out = Vec::new();
    out.push("\\documentclass{article}".to_string());
    out.push("\\usepackage[utf8]{inputenc}".to_string());
    out.push("\\usepackage[normalem]{ulem}".to_string()); // \sout, for --strike--
    out.push("\\usepackage{graphicx}".to_string()); // \includegraphics, for images
    out.push("\\usepackage{hyperref}".to_string()); // \href, for links
    out.push(format!("\\title{{{}}}", latex_escape(title)));
    out.push(format!("\\author{{{}}}", latex_escape(author)));
    out.push(format!("\\date{{{}}}", latex_escape(date)));
    out.push("\\begin{document}".to_string());
    out.push("\\maketitle".to_string());
    for block in ctx.blocks {
        out.push(render_block_latex(block, ctx));
    }
    out.push("\\end{document}".to_string());
    out.join("\n")
}

// ── Markdown rendering ───────────────────────────────────────────────────

/// Link text for the table of contents: keeps the marks, drops nested
/// links (a link cannot contain a link).
fn md_strip_links(s: &str) -> String {
    let img = Regex::new(r"!\[\]\([^)]*\)").unwrap();
    let link = Regex::new(r"\[([^\]]*)\]\([^)]*\)").unwrap();
    link.replace_all(&img.replace_all(s, ""), "$1").to_string()
}

/// GitHub's anchor for a heading: lowercase, spaces to hyphens, anything
/// but letters, digits, `-` and `_` dropped.
fn github_slug(heading_md: &str) -> String {
    md_strip_links(heading_md)
        .chars()
        .filter(|c| !"\\*`~".contains(*c))
        .flat_map(|c| c.to_lowercase())
        .filter_map(|c| {
            if c.is_alphanumeric() || c == '-' || c == '_' {
                Some(c)
            } else if c.is_whitespace() {
                Some('-')
            } else {
                None
            }
        })
        .collect()
}

fn markdown_slugs(blocks: &[Block], numbers: &[String]) -> Vec<String> {
    let mut seen: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    blocks
        .iter()
        .enumerate()
        .map(|(i, b)| match b {
            Block::Heading { text, .. } => {
                let num = numbers.get(i).map_or("", |s| s.as_str());
                let base = github_slug(&format!("{num}{}", inline_format_md(text)));
                let n = seen.entry(base.clone()).or_insert(0);
                let slug = if *n == 0 { base } else { format!("{base}-{n}") };
                *n += 1;
                slug
            }
            _ => String::new(),
        })
        .collect()
}

fn render_toc_md(ctx: &Ctx) -> String {
    let entries: Vec<(usize, usize, &String)> = ctx
        .blocks
        .iter()
        .enumerate()
        .filter_map(|(i, b)| match b {
            Block::Heading { level, text, .. } if *level <= ctx.toc_level => Some((i, *level, text)),
            _ => None,
        })
        .collect();
    // the entries are a list indented by title level, so they nest the way
    // the list rules nest items (a title level skipped or left halfway
    // joins the list that is open)
    let mut shape: Vec<ListItem> = entries
        .iter()
        .map(|e| ListItem { blank_before: false, kind: ListKind::Ul, level: e.1 * 2, text: String::new() })
        .collect();
    normalize_list_levels(&mut shape);
    let mut out = Vec::new();
    for ((i, _level, text), item) in entries.into_iter().zip(&shape) {
        let depth = item.level;
        if item.blank_before {
            out.push(String::new());
        }
        out.push(format!(
            "{}* [{}{}](#{})",
            "    ".repeat(depth),
            toc_number(ctx.number(i)),
            md_strip_links(&inline_format_md(text)),
            ctx.slugs[i]
        ));
    }
    let list = out.join("\n");
    if ctx.toc_title.is_empty() {
        list
    } else {
        format!("**{}**\n\n{list}", inline_format_md(ctx.toc_title))
    }
}

/// A single-level number ("1. ") would read as a list marker for the
/// other ports' escaper, so its dot is escaped the same way.
fn toc_number(n: &str) -> String {
    match n.strip_suffix(". ") {
        Some(d) if !d.is_empty() && d.bytes().all(|b| b.is_ascii_digit()) => format!("{d}\\. "),
        _ => n.to_string(),
    }
}

fn md_cell(text: &str) -> String {
    inline_format_md(text).replace('|', "\\|")
}

fn render_table_md(rows: &[TableRow]) -> String {
    let ncols = rows.first().map_or(0, |r| r.cells.len());
    if ncols == 0 {
        return String::new();
    }
    let line = |cells: Vec<String>| {
        format!("| {} |", cells.join(" | "))
    };
    let first_header = rows.first().map_or(false, |r| r.header);
    let aligns: Vec<Align> = rows
        .first()
        .map(|r| r.cells.iter().map(|(_, a)| *a).collect())
        .unwrap_or_default();
    let sep: Vec<String> = (0..ncols)
        .map(|c| match aligns.get(c).copied().unwrap_or(Align::Left) {
            Align::Left => "---",
            Align::Center => ":---:",
            Align::Right => "---:",
        }
        .to_string())
        .collect();
    let mut out = Vec::new();
    let body_from;
    if first_header {
        out.push(line(rows[0].cells.iter().map(|(t, _)| md_cell(t)).collect()));
        body_from = 1;
    } else {
        // GFM needs a header row; an empty one keeps the table a table
        out.push(line(vec![String::new(); ncols]));
        body_from = 0;
    }
    out.push(format!("|{}|", sep.join("|")));
    for row in &rows[body_from..] {
        out.push(line(row.cells.iter().map(|(t, _)| md_cell(t)).collect()));
    }
    out.join("\n")
}

fn render_list_md(items: &[ListItem]) -> String {
    render_list_md_at(items, 0)
}

/// `base`: how many levels the whole list is nested already
fn render_list_md_at(items: &[ListItem], base: usize) -> String {
    let mut stack: Vec<usize> = Vec::new();
    let mut prev: Option<(ListKind, usize)> = None;
    let mut out = Vec::new();
    for item in items {
        while stack.last().map_or(false, |&l| item.level < l) {
            stack.pop();
        }
        if stack.last().map_or(true, |&l| item.level > l) {
            stack.push(item.level);
        }
        let depth = stack.len() - 1;
        let (marker, width) = match item.kind {
            ListKind::Ul => ("* ", 2),
            ListKind::Ol => ("1. ", 3),
        };
        // a blank line in the source stays one, and so does a change of
        // list kind at the top level (two lists)
        let kind_switch = depth == 0 && prev.map_or(false, |(k, d)| d == 0 && k != item.kind);
        if (item.blank_before && prev.is_some()) || kind_switch {
            out.push(String::new());
        }
        prev = Some((item.kind, depth));
        let pad = "    ".repeat(depth + base);
        let mut lines = item.text.split('\n');
        out.push(format!("{pad}{marker}{}", inline_format_md(lines.next().unwrap_or(""))));
        for l in lines {
            if l.is_empty() {
                out.push(String::new());
            } else {
                out.push(format!("{pad}{}{}", " ".repeat(width), inline_format_md(l)));
            }
        }
    }
    out.join("\n")
}

/// The definition lines of a deflist item; list items among them form a
/// sublist of the deflist, one level down.
fn render_def_md(def: &[String]) -> String {
    let mut out: Vec<String> = Vec::new();
    let mut k = 0;
    while k < def.len() {
        if def[k].starts_with(' ') && is_list_item(&def[k]).is_some() {
            let mut items = Vec::new();
            while k < def.len() && def[k].starts_with(' ') {
                match is_list_item(&def[k]) {
                    Some((kind, level, text)) => {
                        items.push(ListItem { kind, level, text, blank_before: false })
                    }
                    None => break,
                }
                k += 1;
            }
            normalize_list_levels(&mut items);
            out.push(render_list_md_at(&items, 1));
        } else {
            out.push(inline_format_md(&def[k]));
            k += 1;
        }
    }
    out.join("\n")
}

fn render_block_md(block: &Block, index: usize, ctx: &Ctx) -> String {
    match block {
        Block::Heading { level, text, .. } => format!(
            "{} {}{}",
            "#".repeat((*level).clamp(1, 6)),
            ctx.number(index),
            inline_format_md(text)
        ),
        Block::Hr => "---".to_string(),
        Block::Quote { lines } => lines
            .iter()
            .map(|(depth, text)| format!("{}{}", "> ".repeat(*depth), inline_format_md(text)))
            .collect::<Vec<_>>()
            .join("\n"),
        Block::Para { lines } => lines
            .iter()
            .map(|l| inline_format_md(l))
            .collect::<Vec<_>>()
            .join("\n"),
        Block::ListText { lines, pad } => lines
            .iter()
            .map(|l| format!("{}{}", " ".repeat(*pad), inline_format_md(l)))
            .collect::<Vec<_>>()
            .join("\n"),
        Block::List { items } => render_list_md(items),
        Block::Table { rows } => render_table_md(rows),
        Block::Toc => render_toc_md(ctx),
        Block::Verbatim { lines } => {
            // a fence longer than any backtick run inside, so nothing in the
            // code can close it (and a list before it cannot swallow it)
            let longest = lines
                .iter()
                .map(|l| {
                    l.split(|c| c != '`').map(|r| r.len()).max().unwrap_or(0)
                })
                .max()
                .unwrap_or(0);
            let fence = "`".repeat(longest.max(2) + 1);
            format!("{fence}\n{}\n{fence}", lines.join("\n"))
        }
        Block::Raw { lines } => lines.iter().map(|l| md_escape(l)).collect::<Vec<_>>().join("\n"),
        Block::Tagged { lines } => lines.join("\n"),
        Block::DefList { items } => items
            .iter()
            .map(|(term, def)| {
                let head = format!("**{}**", inline_format_md(term));
                if def.is_empty() {
                    format!("{head}  ")
                } else {
                    format!("{head}  \n{}", render_def_md(def))
                }
            })
            .collect::<Vec<_>>()
            .join("\n\n"),
    }
}

fn render_markdown(title: &str, author: &str, date: &str, ctx: &Ctx, headers: bool) -> String {
    let mut parts: Vec<String> = Vec::new();
    if headers {
        if !title.is_empty() {
            parts.push(format!("# {}", inline_format_md(title)));
        }
        let by: Vec<String> = [author, date]
            .iter()
            .filter(|s| !s.is_empty())
            .map(|s| inline_format_md(s))
            .collect();
        if !by.is_empty() {
            parts.push(by.join("  \n"));
        }
    }
    for (i, block) in ctx.blocks.iter().enumerate() {
        let rendered = render_block_md(block, i, ctx);
        if !rendered.is_empty() {
            parts.push(rendered);
        }
    }
    parts.join("\n\n")
}

// ── public API ───────────────────────────────────────────────────────────

/// Output format of [`convert`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Target {
    Html,
    Latex,
    Markdown,
}

impl Target {
    /// `html`, `tex` (or `latex`), `md` (or `markdown`).
    pub fn from_name(name: &str) -> Option<Target> {
        match name {
            "html" => Some(Target::Html),
            "tex" | "latex" => Some(Target::Latex),
            "md" | "markdown" => Some(Target::Markdown),
            _ => None,
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Target::Html => "html",
            Target::Latex => "tex",
            Target::Markdown => "md",
        }
    }

    /// File extension of the converted document.
    pub fn extension(self) -> &'static str {
        self.name()
    }
}

/// Deepest title level listed in a table of contents unless `--toc-level`
/// says otherwise.
pub const DEFAULT_TOC_LEVEL: usize = 3;

/// The Python port's options that make sense here.
#[derive(Debug, Clone, Default)]
pub struct Options {
    /// `-H`: no document wrapper, title or author/date, body only
    pub no_headers: bool,
    /// `--toc`: add a table of contents at the top unless there is a `%%toc`
    pub toc: bool,
    /// `--toc-level N`: deepest heading level listed (3 when `None`)
    pub toc_level: Option<usize>,
    /// `--toc-title S`
    pub toc_title: String,
    /// `--toc-only`: print the table of contents and nothing else
    pub toc_only: bool,
    /// `-n`: number the titles 1, 1.1, 1.1.1 (html and md)
    pub enum_title: bool,
    /// `--skip-header-lines`: no title/author/date, the body starts on line 1
    pub skip_header_lines: bool,
    /// names the macros `%%infile`, `%%outfile` and `%%mtime` can report
    pub infile: String,
    pub outfile: String,
}

pub fn parse_with(text: &str, skip_header: bool) -> Document {
    parse_with_env(text, skip_header, &MacroEnv::default())
}

pub fn parse_with_env(text: &str, skip_header: bool, env: &MacroEnv) -> Document {
    let lines: Vec<&str> = text.lines().collect();
    let head = parse_head(&lines, skip_header);
    let body_start = head.body_start.min(lines.len());
    let body_text = lines[body_start..].join("\n");
    let preprocessed = apply_line_rules(&body_text, &head.preproc);
    let body: Vec<&str> = preprocessed.lines().collect();
    let blocks = parse_body(&body);
    Document {
        title: expand_macros(&head.title, env),
        author: expand_macros(&head.author, env),
        date: expand_macros(&head.date, env),
        blocks,
        postproc: head.postproc,
        options: head.options,
    }
}

pub fn parse(text: &str) -> Document {
    parse_with(text, false)
}

/// Applies the document's `%!options:` as defaults under the given options:
/// flags are OR-ed, valued options only fill what was left at its default.
fn merge_doc_options(
    opts: &Options,
    doc: &[(Option<String>, Vec<String>)],
    target: &str,
) -> Options {
    let mut o = opts.clone();
    let mut set_title = false;
    for (t, words) in doc {
        if let Some(t) = t {
            if t != target {
                continue;
            }
        }
        let mut it = words.iter();
        while let Some(w) = it.next() {
            let (name, inline) = match w.split_once('=') {
                Some((n, v)) if w.starts_with("--") => (n, Some(v.to_string())),
                _ => (w.as_str(), None),
            };
            match name {
                "--toc" => o.toc = true,
                "--no-toc" => o.toc = false,
                "--toc-only" => o.toc_only = true,
                "-n" | "--enum-title" => o.enum_title = true,
                "-H" | "--no-headers" => o.no_headers = true,
                "--headers" => o.no_headers = false,
                "--toc-level" => {
                    let v = inline.or_else(|| it.next().cloned());
                    if opts.toc_level.is_none() {
                        if let Some(n) = v.and_then(|v| v.parse().ok()) {
                            o.toc_level = Some(n);
                        }
                    }
                }
                "--toc-title" => {
                    let v = inline.or_else(|| it.next().cloned());
                    if opts.toc_title.is_empty() && !set_title {
                        if let Some(v) = v {
                            o.toc_title = v;
                            set_title = true;
                        }
                    }
                }
                _ => {}
            }
        }
    }
    o
}

/// Converts a txt2tags document. Fails only for an option that the target
/// cannot honour (`--toc-only` with LaTeX).
pub fn convert(text: &str, target: Target, opts: &Options) -> Result<String, String> {
    let env = MacroEnv {
        infile: opts.infile.clone(),
        outfile: opts.outfile.clone(),
        target: match target {
            Target::Html => "html",
            Target::Latex => "tex",
            Target::Markdown => "md",
        }
        .to_string(),
        headers: Default::default(),
    };
    let mut doc = parse_with_env(text, opts.skip_header_lines, &env);
    let merged = merge_doc_options(opts, &doc.options, &env.target);
    let opts = &merged;
    MACRO_ENV.with(|e| {
        *e.borrow_mut() = MacroEnv {
            headers: [doc.title.clone(), doc.author.clone(), doc.date.clone()],
            ..env.clone()
        }
    });
    if opts.toc_only && target == Target::Latex {
        return Err("--toc-only is not supported for the tex target".to_string());
    }
    // as in the Python port, %%toc only says where the table of contents goes
    // when --toc (or --toc-only) asks for one
    if !opts.toc && !opts.toc_only {
        doc.blocks.retain(|b| !matches!(b, Block::Toc));
    } else if !doc.blocks.iter().any(|b| matches!(b, Block::Toc)) {
        doc.blocks.insert(0, Block::Toc);
    }
    let numbers = if target != Target::Latex {
        heading_numbers(&doc.blocks, opts.enum_title)
    } else {
        Vec::new()
    };
    let slugs = if target == Target::Markdown {
        markdown_slugs(&doc.blocks, &numbers)
    } else {
        Vec::new()
    };
    let ctx = Ctx {
        blocks: &doc.blocks,
        has_toc: doc.blocks.iter().any(|b| matches!(b, Block::Toc)) || opts.toc_only,
        numbers,
        toc_level: opts.toc_level.unwrap_or(DEFAULT_TOC_LEVEL),
        toc_title: &opts.toc_title,
        slugs,
    };
    let headers = !opts.no_headers;
    let out = if opts.toc_only {
        match target {
            Target::Html => render_toc_html(&ctx),
            Target::Markdown => render_toc_md(&ctx),
            Target::Latex => unreachable!(),
        }
    } else {
        match target {
            Target::Html => render_html(&doc.title, &doc.author, &doc.date, &ctx, headers),
            Target::Latex => render_latex(&doc.title, &doc.author, &doc.date, &ctx, headers),
            Target::Markdown => render_markdown(&doc.title, &doc.author, &doc.date, &ctx, headers),
        }
    };
    Ok(apply_line_rules(&out, &doc.postproc))
}

pub fn to_html(text: &str) -> String {
    convert(text, Target::Html, &Options::default()).unwrap()
}

pub fn to_latex(text: &str) -> String {
    convert(text, Target::Latex, &Options::default()).unwrap()
}

pub fn to_markdown(text: &str) -> String {
    convert(text, Target::Markdown, &Options::default()).unwrap()
}
