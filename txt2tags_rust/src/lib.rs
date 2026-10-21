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
//!   - Horizontal rule: a line of 4+ repeated -, =, _ or ~
//!   - Paragraphs (blank-line separated)
//!   - Unordered (- ) and ordered (+ ) lists, with indentation-based nesting
//!   - Inline: **bold**, //italic//, __underline__, --strike--, ``mono``
//!   - Escaping a mark with a backslash: \**not bold**
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
//!     passed through completely unmodified, not even entity-escaped --
//!     it's meant to already be valid markup in the target format.
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
//!   - Marks only trigger when glued to their content and not glued to a
//!     word on the outside (nothing alphanumeric immediately before an
//!     opening mark or immediately after a closing one), so e.g. `2**3**4`
//!     in a paragraph about exponents stays plain text instead of
//!     misreading the `**` pair as bold.
//!
//! Export targets: HTML (`to_html`) and LaTeX (`to_latex`), per this
//! repo's simple-tier priority order -- unchanged by the advanced-tier
//! pass, since the "HTML and LaTeX only" cap applies regardless of tier.
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
    Heading { level: usize, text: String },
    Hr,
    Para { lines: Vec<String> },
    List { items: Vec<ListItem> },
    Table { rows: Vec<TableRow> },
    Toc,
    Verbatim { lines: Vec<String> },
    Raw { lines: Vec<String> },
    DefList { items: Vec<(String, Vec<String>)> },
}

#[derive(Debug, Clone)]
pub struct Document {
    pub title: String,
    pub author: String,
    pub date: String,
    pub blocks: Vec<Block>,
    pub postproc: Vec<(Regex, String)>,
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

// Global substitution, before any other parsing -- matches the classic
// txt2tags idiom of a header date line that is literally just "%%date".
fn expand_date_macro(text: &str) -> String {
    text.replace("%%date", &today_string())
}

// ── head parsing ─────────────────────────────────────────────────────────

struct HeadInfo {
    title: String,
    author: String,
    date: String,
    body_start: usize,
    preproc: Vec<(Regex, String)>,
    postproc: Vec<(Regex, String)>,
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

fn parse_head(lines: &[&str]) -> HeadInfo {
    let title = lines.first().unwrap_or(&"").trim().to_string();
    let author = lines.get(1).unwrap_or(&"").trim().to_string();
    let date = lines.get(2).unwrap_or(&"").trim().to_string();

    let mut preproc = Vec::new();
    let mut postproc = Vec::new();

    let mut i = 3;
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
            if let Some((kind, pattern, replacement)) = parse_config_directive(t) {
                if let Ok(re) = Regex::new(&pattern) {
                    if kind == "preproc" {
                        preproc.push((re, replacement));
                    } else {
                        postproc.push((re, replacement));
                    }
                }
            }
            i += 1;
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
    if t.chars().count() < 4 {
        return false;
    }
    let c = t.chars().next().unwrap();
    if !matches!(c, '-' | '=' | '_' | '~') {
        return false;
    }
    t.chars().all(|ch| ch == c)
}

/// Level (1-5) and text, or `None` if `line` isn't a title.
fn is_heading(line: &str) -> Option<(usize, String)> {
    let t = line.trim();
    if !t.starts_with('=') {
        return None;
    }
    let chars: Vec<char> = t.chars().collect();
    let mut level = 0;
    while level < chars.len() && chars[level] == '=' {
        level += 1;
    }
    if level < 1 || level > 5 || chars.len() < 2 * level {
        return None;
    }
    if !chars[chars.len() - level..].iter().all(|&c| c == '=') {
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
    Some((level, text))
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
    Some((kind, spaces / 2, text))
}

fn cell_align(raw: &str) -> Align {
    let leading = raw.chars().take_while(|c| *c == ' ').count();
    let trailing = raw.chars().rev().take_while(|c| *c == ' ').count();
    if leading >= 2 && trailing == 0 {
        Align::Right
    } else if leading >= 2 && trailing >= 2 {
        Align::Center
    } else {
        Align::Left
    }
}

/// Is-header flag and (text, alignment) cells, or `None` if `line` isn't a
/// table row.
fn is_table_row(line: &str) -> Option<(bool, Vec<(String, Align)>)> {
    let t = line.trim();
    if !t.starts_with('|') {
        return None;
    }
    let chars: Vec<char> = t.chars().collect();
    let mut count = 0;
    while count < chars.len() && chars[count] == '|' {
        count += 1;
    }
    let is_header = count >= 2;
    let mut content: String = chars[count..].iter().collect();
    let had_trailing_pipe = content.ends_with('|');
    if had_trailing_pipe {
        content.pop();
    }
    let mut cells: Vec<(String, Align)> = content
        .split('|')
        .map(|raw| (raw.trim().to_string(), cell_align(raw)))
        .collect();
    // Without a closing pipe there's no reliable trailing-space signal for
    // the last cell (the line was already right-trimmed), so don't let an
    // accidental leading-space run right-align it.
    if !had_trailing_pipe {
        if let Some(last) = cells.last_mut() {
            last.1 = Align::Left;
        }
    }
    Some((is_header, cells))
}

/// A line whose trimmed content starts with "%" is a single-line comment,
/// stripped wherever it appears in the body (not just in the head area).
/// Block comments ("%%%" ... "%%%") are handled by parse_body.
fn is_comment(line: &str) -> bool {
    line.trim().starts_with('%')
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
    line.trim() == marker
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
        if c == '\\' && i + 1 < chars.len() {
            let nextc = chars[i + 1];
            escaped.push(nextc);
            out.push(PLACEHOLDER_MARK);
            out.push_str(&escaped.len().to_string());
            out.push(PLACEHOLDER_MARK);
            i += 2;
        } else {
            out.push(c);
            i += 1;
        }
    }
    (out, escaped)
}

fn restore_escapes(s: &str, escaped: &[char], escape_char: fn(char) -> String) -> String {
    let mut result = s.to_string();
    for (idx, ch) in escaped.iter().enumerate() {
        let token = format!("{PLACEHOLDER_MARK}{}{PLACEHOLDER_MARK}", idx + 1);
        if let Some(pos) = result.find(&token) {
            result.replace_range(pos..pos + token.len(), &escape_char(*ch));
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
// after it) and not glued to a word on the outside (nothing alphanumeric
// right before it) -- e.g. "2**3**4" (talking about exponents) must not
// read as bold, since both "**" occurrences sit right against a digit.
fn valid_open_boundary(before: Option<char>, after: Option<char>) -> bool {
    let before_ok = before.map_or(true, |c| !c.is_alphanumeric());
    let after_ok = after.map_or(false, |c| !c.is_whitespace());
    before_ok && after_ok
}

// Mirror of valid_open_boundary for the closing delimiter: glued to its
// content on the inside (no whitespace right before it), not glued to a
// word on the outside (nothing alphanumeric right after it).
fn valid_close_boundary(before: Option<char>, after: Option<char>) -> bool {
    let before_ok = before.map_or(false, |c| !c.is_whitespace());
    let after_ok = after.map_or(true, |c| !c.is_alphanumeric());
    before_ok && after_ok
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

const IMAGE_EXTS: &[&str] = &["png", "jpg", "jpeg", "gif", "svg", "bmp"];

fn looks_like_image(s: &str) -> bool {
    let lower = s.to_lowercase();
    IMAGE_EXTS
        .iter()
        .any(|ext| lower.ends_with(&format!(".{ext}")))
}

fn looks_like_url(s: &str) -> bool {
    s.starts_with("http://")
        || s.starts_with("https://")
        || s.starts_with("ftp://")
        || s.starts_with("mailto:")
}

fn starts_with_at(chars: &[char], i: usize, pat: &str) -> bool {
    let pchars: Vec<char> = pat.chars().collect();
    if i + pchars.len() > chars.len() {
        return false;
    }
    chars[i..i + pchars.len()] == pchars[..]
}

fn looks_like_autolink_start(chars: &[char], i: usize) -> bool {
    starts_with_at(chars, i, "http://")
        || starts_with_at(chars, i, "https://")
        || starts_with_at(chars, i, "ftp://")
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

// Runs the escape+mark pipeline (but not link/image extraction -- nested
// links aren't supported) over a link label or bare-URL text, reusing the
// same protect_escapes() lookup table as the surrounding text.
fn inline_label(
    protected_text: &str,
    escaped: &[char],
    escape_char: fn(char) -> String,
    delims: &[Delim],
) -> String {
    let esc: String = protected_text.chars().map(escape_char).collect();
    let marked = apply_marks(&esc, delims);
    restore_escapes(&marked, escaped, escape_char)
}

/// Content of a `[...]` span (already protect_escapes'd) -> fully rendered
/// link/image output, or `None` if it doesn't look like a link/image (the
/// brackets are then left as literal text).
fn render_bracket(
    content: &str,
    escaped: &[char],
    escape_char: fn(char) -> String,
    delims: &[Delim],
    render_link: fn(&str, &str) -> String,
    render_image: fn(&str) -> String,
) -> Option<String> {
    let content = content.trim();
    if content.is_empty() {
        return None;
    }
    let parts: Vec<&str> = content.rsplitn(2, ' ').collect();
    if parts.len() == 2 {
        let target = parts[0].trim();
        let label_part = parts[1].trim();
        if looks_like_image(label_part) && looks_like_url(target) {
            return Some(render_link(&render_image(label_part), target));
        }
        if looks_like_url(target) {
            let label = inline_label(label_part, escaped, escape_char, delims);
            return Some(render_link(&label, target));
        }
        None
    } else {
        let token = content;
        if looks_like_image(token) {
            Some(render_image(token))
        } else if looks_like_url(token) {
            let label = inline_label(token, escaped, escape_char, delims);
            Some(render_link(&label, token))
        } else {
            None
        }
    }
}

/// Tries to match `[ [image.ext] URL ]` starting at `chars[outer_open]`
/// (already confirmed to be `[` immediately followed by another `[`).
/// Returns the rendered image-link and the index just past the outer `]`
/// on success.
fn find_link_render(
    chars: &[char],
    outer_open: usize,
    render_link: fn(&str, &str) -> String,
    render_image: fn(&str) -> String,
) -> Option<(String, usize)> {
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
    Some((render_link(&render_image(inner_trim), target), outer_close + 1))
}

/// Scans (already protect_escapes'd) text for `[label URL]`/`[image.ext]`
/// brackets and bare autolinks, replacing each with a numbered
/// PLACEHOLDER_LINK token. Returns the token-substituted text plus the
/// list of fully rendered replacements, indexed by token number - 1.
fn extract_links_images(
    s: &str,
    escaped: &[char],
    escape_char: fn(char) -> String,
    delims: &[Delim],
    render_link: fn(&str, &str) -> String,
    render_image: fn(&str) -> String,
) -> (String, Vec<String>) {
    let chars: Vec<char> = s.chars().collect();
    let mut out = String::new();
    let mut items: Vec<String> = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        if c == '[' {
            // Classic txt2tags image-as-link: [ [image.png] URL ] -- a
            // single level of nesting with a very specific shape, checked
            // before the generic (single-level-only) bracket handling
            // below so it doesn't get rejected by the "no nested '['"
            // guard. Anything that doesn't match this exact shape (e.g.
            // LionWiki's unrelated [[label | URL]] double-bracket dialect)
            // falls through to that guard's graceful degradation.
            if i + 1 < chars.len() && chars[i + 1] == '[' {
                if let Some((rendered, consumed_to)) =
                    find_link_render(&chars, i, render_link, render_image)
                {
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
                    if let Some(rendered) = render_bracket(
                        &content,
                        escaped,
                        escape_char,
                        delims,
                        render_link,
                        render_image,
                    ) {
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
            let label = inline_label(&word, escaped, escape_char, delims);
            items.push(render_link(&label, &word));
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

fn inline_format_with(
    text: &str,
    escape_char: fn(char) -> String,
    delims: &[Delim],
    render_link: fn(&str, &str) -> String,
    render_image: fn(&str) -> String,
) -> String {
    let (protected, escaped) = protect_escapes(text);
    let (linked, items) =
        extract_links_images(&protected, &escaped, escape_char, delims, render_link, render_image);
    let escaped_text: String = linked.chars().map(escape_char).collect();
    let marked = apply_marks(&escaped_text, delims);
    let restored = restore_escapes(&marked, &escaped, escape_char);
    restore_link_placeholders(&restored, &items)
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

fn inline_format_html(text: &str) -> String {
    inline_format_with(text, html_escape_char, HTML_DELIMS, html_link, html_image)
}

fn inline_format_latex(text: &str) -> String {
    inline_format_with(text, latex_escape_char, LATEX_DELIMS, latex_link, latex_image)
}

// ── block parsing ────────────────────────────────────────────────────────

fn parse_body(lines: &[&str]) -> Vec<Block> {
    let mut blocks = Vec::new();
    let n = lines.len();
    let mut i = 0;

    while i < n {
        let line = lines[i];

        if line.trim().is_empty() {
            i += 1;
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
        } else if let Some((level, text)) = is_heading(line) {
            blocks.push(Block::Heading { level, text });
            i += 1;
        } else if is_hr(line) {
            blocks.push(Block::Hr);
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
                    def.push(lines[i].trim().to_string());
                    i += 1;
                } else {
                    break;
                }
            }
            items.push((term, def));
            blocks.push(Block::DefList { items });
        } else if is_list_item(line).is_some() {
            let mut items = Vec::new();
            while i < n {
                if lines[i].trim().is_empty() {
                    i += 1;
                } else if is_comment(lines[i]) {
                    i += 1;
                } else if let Some((kind, level, text)) = is_list_item(lines[i]) {
                    items.push(ListItem { kind, level, text });
                    i += 1;
                } else {
                    break;
                }
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
                    || is_deflist_term(l).is_some()
                    || is_list_item(l).is_some()
                    || is_table_row(l).is_some()
                {
                    break;
                } else {
                    plines.push(l.trim().to_string());
                    i += 1;
                }
            }
            blocks.push(Block::Para { lines: plines });
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
            out.push(format!("<li>{}", inline_format_html(&items[i].text)));
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

// A table of contents is only meaningful (and its heading anchors only
// added) when the document actually contains a %%toc -- so plain
// documents render byte-identical headings, same as before this feature
// existed.
fn render_toc_html(blocks: &[Block]) -> String {
    let mut out = vec!["<ul class=\"toc\">".to_string()];
    for (i, b) in blocks.iter().enumerate() {
        if let Block::Heading { level, text } = b {
            out.push(format!(
                "<li class=\"toc-h{level}\"><a href=\"#t2t-{i}\">{}</a></li>",
                inline_format_html(text)
            ));
        }
    }
    out.push("</ul>".to_string());
    out.join("\n")
}

fn render_block_html(block: &Block, index: usize, all_blocks: &[Block], has_toc: bool) -> String {
    match block {
        Block::Heading { level, text } => {
            if has_toc {
                format!(
                    "<h{level} id=\"t2t-{index}\">{}</h{level}>",
                    inline_format_html(text)
                )
            } else {
                format!("<h{level}>{}</h{level}>", inline_format_html(text))
            }
        }
        Block::Hr => "<hr>".to_string(),
        Block::Para { lines } => {
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
        Block::Toc => render_toc_html(all_blocks),
        Block::Verbatim { lines } => {
            let escaped: Vec<String> = lines.iter().map(|l| html_escape(l)).collect();
            format!("<pre>\n{}\n</pre>", escaped.join("\n"))
        }
        Block::Raw { lines } => lines.join("\n"),
        Block::DefList { items } => {
            let mut out = vec!["<dl>".to_string()];
            for (term, def) in items {
                out.push(format!("<dt>{}</dt>", inline_format_html(term)));
                for d in def {
                    out.push(format!("<dd>{}</dd>", inline_format_html(d)));
                }
            }
            out.push("</dl>".to_string());
            out.join("\n")
        }
    }
}

fn render_html(title: &str, author: &str, date: &str, blocks: &[Block]) -> String {
    let has_toc = blocks.iter().any(|b| matches!(b, Block::Toc));

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
        out.push(render_block_html(block, i, blocks, has_toc));
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
            out.push(format!("\\item {}", inline_format_latex(&items[i].text)));
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

fn render_block_latex(block: &Block) -> String {
    match block {
        Block::Heading { level, text } => {
            format!(
                "\\{}{{{}}}",
                heading_command(*level),
                inline_format_latex(text)
            )
        }
        Block::Hr => "\\par\\noindent\\hrulefill\\par".to_string(),
        Block::Para { lines } => {
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
        Block::Toc => "\\tableofcontents".to_string(),
        Block::Verbatim { lines } => {
            format!("\\begin{{verbatim}}\n{}\n\\end{{verbatim}}", lines.join("\n"))
        }
        Block::Raw { lines } => lines.join("\n"),
        Block::DefList { items } => {
            let mut out = vec!["\\begin{description}".to_string()];
            for (term, def) in items {
                let def_text: Vec<String> = def.iter().map(|d| inline_format_latex(d)).collect();
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

fn render_latex(title: &str, author: &str, date: &str, blocks: &[Block]) -> String {
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
    for block in blocks {
        out.push(render_block_latex(block));
    }
    out.push("\\end{document}".to_string());
    out.join("\n")
}

// ── public API ───────────────────────────────────────────────────────────

pub fn parse(text: &str) -> Document {
    let expanded = expand_date_macro(text);
    let lines: Vec<&str> = expanded.lines().collect();
    let head = parse_head(&lines);
    let body_start = head.body_start.min(lines.len());
    let body_text = lines[body_start..].join("\n");
    let preprocessed = apply_line_rules(&body_text, &head.preproc);
    let body: Vec<&str> = preprocessed.lines().collect();
    let blocks = parse_body(&body);
    Document {
        title: head.title,
        author: head.author,
        date: head.date,
        blocks,
        postproc: head.postproc,
    }
}

pub fn to_html(text: &str) -> String {
    let doc = parse(text);
    let out = render_html(&doc.title, &doc.author, &doc.date, &doc.blocks);
    apply_line_rules(&out, &doc.postproc)
}

pub fn to_latex(text: &str) -> String {
    let doc = parse(text);
    let out = render_latex(&doc.title, &doc.author, &doc.date, &doc.blocks);
    apply_line_rules(&out, &doc.postproc)
}
