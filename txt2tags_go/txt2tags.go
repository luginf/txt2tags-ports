// Package txt2tags is a from-scratch Go port of txt2tags. Started as a
// simple-tier prototype (structure mirroring the Lua/Tcl/Rust prototypes
// in this repo) and has since taken the same advanced-tier pass as the
// Rust port, per the repo's CLAUDE.md "Scope policy" section: the two
// tiers stay separable in the code (see the "advanced tier" markers
// below) rather than being interleaved through the simple-tier
// plain-string functions.
//
// Simple tier (plain substring search / manual rune scanning, no regexp):
//   - Head: title / author / date (first 3 lines)
//   - Comment lines (% ...) anywhere in the body, and config lines
//     (%! ...) in the head area, are skipped, not parsed
//   - Section headings: = h1 = .. ===== h5 =====
//   - Horizontal rule: a line of 4+ repeated -, =, _ or ~
//   - Paragraphs (blank-line separated)
//   - Unordered (- ) and ordered (+ ) lists, with indentation-based nesting
//   - Inline: **bold**, //italic//, __underline__, --strike--, double-backtick mono marks
//   - Escaping a mark with a backslash: \**not bold**
//   - Tables: "| cell | cell |" rows, "||" prefix marks a header row
//   - Macros: "%%date" (substituted anywhere in the raw text, before any
//     other parsing, with today's date as YYYY-MM-DD) and "%%toc", a
//     line on its own that expands to a flat table of contents (heading
//     anchors are only added when a "%%toc" is actually present, so
//     plain documents render exactly as before).
//
// Advanced tier (gated behind the stdlib regexp package, used only by
// the preproc/postproc rules; the rest is still plain scanning):
//   - Links: "[label URL]", bare "[URL]", and bare autolinks
//     (http://..., https://..., ftp://...) detected directly in text.
//     A bare URL stops at the reference URL character set (no brackets,
//     quotes or whitespace) and drops trailing ".,;:!?", so a "[label
//     URL]" inside other brackets or at the end of a sentence never
//     leaks a "]" or "." into the href.
//   - Images: "[path.ext]" for a handful of common extensions,
//     "[path.ext URL]" for a clickable image, and the classic nested
//     "[ [path.ext] URL ]" shape too. Any other kind of bracket nesting
//     (e.g. LionWiki's unrelated "[[label | URL]]" double-bracket
//     dialect) isn't parsed as a link; the outer brackets are left
//     literal and the inner one gets its own look, rather than
//     producing a mangled href. The reference regex would accept a "["
//     inside a label; this port deliberately does not.
//   - Verbatim blocks: a line of exactly ``` opens/closes one; content is
//     passed through with only entity-escaping (HTML) or none (LaTeX
//     verbatim environment), no inline marks applied.
//   - Raw blocks: a line of exactly """ opens/closes one; content is
//     passed through completely unmodified, not even entity-escaped.
//   - Block comments: a line of exactly %%% opens/closes one; everything
//     inside produces no output (checked ahead of the single-line "%"
//     rule, which would otherwise only skip the fence lines themselves).
//   - Definition lists: ": term" followed by indented definition line(s).
//   - Table column-alignment inference: a cell padded with 2+ spaces on
//     the left and none on the right is right-aligned; 2+ on both sides
//     is centered; anything else is left. Only inferred from rows that
//     close with a trailing "|". Applied per cell in HTML
//     (style="text-align:...") and per column in LaTeX (tabular spec
//     taken from the first row).
//   - "%!preproc: 'PATTERN' 'REPLACEMENT'" / "%!postproc: ..." config
//     lines in the head area: preproc rules run against each body line
//     before parsing, postproc rules against each rendered output line
//     before the final string is returned. Replacement syntax is
//     regexp's ($1, ${1}), not Perl's \1 -- a known deviation from the
//     classic txt2tags config-file dialect.
//   - Marks only trigger when glued to their content and not glued to a
//     word on the outside (nothing alphanumeric immediately before an
//     opening mark or immediately after a closing one), so e.g. two
//     "http://" URLs concatenated with no space don't have their "//"
//     runs misread as italic markup.
//
// Export targets: HTML (ToHTML) and LaTeX (ToLatex), per this repo's
// simple-tier priority order. The LaTeX target assumes a preamble with
// \usepackage[normalem]{ulem} (\sout, for --strike--), \usepackage{graphicx}
// (images) and \usepackage{hyperref} (links) -- see the top of renderLatex.
//
// NOT supported yet (left for a later pass): nested constructs inside
// table cells or definition-list entries beyond plain inline marks/links.
package txt2tags

import (
	"regexp"
	"strconv"
	"strings"
	"time"
	"unicode"
	"unicode/utf8"
)

// ListKind distinguishes unordered from ordered list items.
type ListKind int

const (
	Ul ListKind = iota
	Ol
)

// ListItem is one line of a list block.
type ListItem struct {
	Kind  ListKind
	Level int
	Text  string
}

// Align is the horizontal alignment inferred for a table cell.
type Align int

const (
	AlignLeft Align = iota
	AlignCenter
	AlignRight
)

// Cell is one table cell: its trimmed text plus its inferred alignment.
type Cell struct {
	Text  string
	Align Align
}

// TableRow is one row of a table block.
type TableRow struct {
	Header bool
	Cells  []Cell
}

// DefItem is one definition-list entry: a term and its definition lines.
type DefItem struct {
	Term string
	Defs []string
}

// lineRule is one %!preproc / %!postproc rewrite rule.
type lineRule struct {
	Re   *regexp.Regexp
	Repl string
}

type blockKind int

const (
	blockHeading blockKind = iota
	blockHr
	blockPara
	blockList
	blockTable
	blockVerbatim
	blockToc
	blockRaw
	blockDefList
)

// Block is one top-level structural unit of the document body.
type Block struct {
	Kind  blockKind
	Level int
	Text  string
	Lines []string
	Items []ListItem
	Rows  []TableRow
	Defs  []DefItem
}

// Document is a parsed txt2tags source file.
type Document struct {
	Title  string
	Author string
	Date   string
	Blocks []Block

	postproc []lineRule
}

// ── date macro ───────────────────────────────────────────────────────────

// TodayString returns today's date (UTC) as YYYY-MM-DD: what "%%date"
// expands to. Exported mainly so callers/tests can compare against it.
func TodayString() string {
	return time.Now().UTC().Format("2006-01-02")
}

// Global substitution, before any other parsing -- matches the classic
// txt2tags idiom of a header date line that is literally just "%%date".
func expandDateMacro(text string) string {
	return strings.ReplaceAll(text, "%%date", TodayString())
}

// splitLines splits like Rust's str::lines: on "\n", dropping a "\r"
// before it and the empty element a trailing newline would leave.
func splitLines(text string) []string {
	lines := strings.Split(text, "\n")
	if n := len(lines); n > 0 && lines[n-1] == "" {
		lines = lines[:n-1]
	}
	for i, l := range lines {
		lines[i] = strings.TrimSuffix(l, "\r")
	}
	return lines
}

// ── head parsing ─────────────────────────────────────────────────────────

// readQuoted reads one 'quoted' or "quoted" span at the start of s,
// returning its content and the remainder after the closing quote.
func readQuoted(s string) (content, rest string, ok bool) {
	if s == "" || (s[0] != '\'' && s[0] != '"') {
		return "", "", false
	}
	q := s[0]
	end := strings.IndexByte(s[1:], q)
	if end < 0 {
		return "", "", false
	}
	return s[1 : 1+end], s[2+end:], true
}

// parseConfigDirective parses a "%!preproc:" / "%!postproc:" config line
// into (kind, pattern, replacement); ok is false if it isn't one or is
// malformed.
func parseConfigDirective(line string) (kind, pattern, replacement string, ok bool) {
	rest := ""
	if strings.HasPrefix(line, "%!preproc:") {
		kind, rest = "preproc", line[len("%!preproc:"):]
	} else if strings.HasPrefix(line, "%!postproc:") {
		kind, rest = "postproc", line[len("%!postproc:"):]
	} else {
		return "", "", "", false
	}
	pattern, rest2, ok := readQuoted(strings.TrimLeft(rest, " \t"))
	if !ok {
		return "", "", "", false
	}
	replacement, _, ok = readQuoted(strings.TrimLeft(rest2, " \t"))
	if !ok {
		return "", "", "", false
	}
	return kind, pattern, replacement, true
}

type headInfo struct {
	title, author, date string
	bodyStart           int
	preproc, postproc   []lineRule
}

func parseHead(lines []string) headInfo {
	get := func(i int) string {
		if i < len(lines) {
			return strings.TrimSpace(lines[i])
		}
		return ""
	}
	h := headInfo{title: get(0), author: get(1), date: get(2)}

	i := 3
loop:
	for i < len(lines) {
		t := strings.TrimSpace(lines[i])
		switch {
		case t == "%%":
			i++
			break loop
		case t == "%%toc":
			// A body macro, not a head comment/config line -- leave it
			// for parseBody rather than swallowing it here.
			break loop
		case strings.HasPrefix(t, "%!"):
			if kind, pattern, repl, ok := parseConfigDirective(t); ok {
				if re, err := regexp.Compile(pattern); err == nil {
					if kind == "preproc" {
						h.preproc = append(h.preproc, lineRule{re, repl})
					} else {
						h.postproc = append(h.postproc, lineRule{re, repl})
					}
				}
			}
			i++
		case strings.HasPrefix(t, "%") || t == "":
			i++
		default:
			break loop
		}
	}
	h.bodyStart = i
	return h
}

// applyLineRules runs each rule, in order, against every line of text.
func applyLineRules(text string, rules []lineRule) string {
	if len(rules) == 0 {
		return text
	}
	lines := splitLines(text)
	for i, l := range lines {
		for _, r := range rules {
			l = r.Re.ReplaceAllString(l, r.Repl)
		}
		lines[i] = l
	}
	return strings.Join(lines, "\n")
}

// ── line classifiers ─────────────────────────────────────────────────────

func isHr(line string) bool {
	t := strings.TrimSpace(line)
	if len(t) < 4 {
		return false
	}
	c := t[0]
	if c != '-' && c != '=' && c != '_' && c != '~' {
		return false
	}
	for i := 0; i < len(t); i++ {
		if t[i] != c {
			return false
		}
	}
	return true
}

// isHeading returns the level (1-5) and text, or ok=false if line isn't a title.
func isHeading(line string) (level int, text string, ok bool) {
	t := strings.TrimSpace(line)
	if !strings.HasPrefix(t, "=") {
		return 0, "", false
	}
	n := len(t)
	lvl := 0
	for lvl < n && t[lvl] == '=' {
		lvl++
	}
	if lvl < 1 || lvl > 5 || n < 2*lvl {
		return 0, "", false
	}
	closing := t[n-lvl:]
	for i := 0; i < len(closing); i++ {
		if closing[i] != '=' {
			return 0, "", false
		}
	}
	inner := strings.TrimSpace(t[lvl : n-lvl])
	if inner == "" {
		return 0, "", false
	}
	return lvl, inner, true
}

// isListItem returns the kind, 0-based nesting level and text, or ok=false
// if line isn't a list item.
func isListItem(line string) (kind ListKind, level int, text string, ok bool) {
	spaces := 0
	for spaces < len(line) && line[spaces] == ' ' {
		spaces++
	}
	rest := line[spaces:]
	marker := rest
	if len(marker) > 2 {
		marker = marker[:2]
	}
	switch marker {
	case "- ":
		kind = Ul
	case "+ ":
		kind = Ol
	default:
		return 0, 0, "", false
	}
	txt := ""
	if len(rest) > 2 {
		txt = strings.TrimSpace(rest[2:])
	}
	if txt == "" {
		return 0, 0, "", false
	}
	return kind, spaces / 2, txt, true
}

// cellAlign infers a cell's alignment from the padding around its raw
// (untrimmed) text.
func cellAlign(raw string) Align {
	leading := len(raw) - len(strings.TrimLeft(raw, " "))
	trailing := len(raw) - len(strings.TrimRight(raw, " "))
	switch {
	case leading >= 2 && trailing == 0:
		return AlignRight
	case leading >= 2 && trailing >= 2:
		return AlignCenter
	}
	return AlignLeft
}

// isTableRow returns the header flag and cells, or ok=false if line isn't a
// table row.
func isTableRow(line string) (header bool, cells []Cell, ok bool) {
	t := strings.TrimSpace(line)
	if !strings.HasPrefix(t, "|") {
		return false, nil, false
	}
	count := 0
	for count < len(t) && t[count] == '|' {
		count++
	}
	header = count >= 2
	content := t[count:]
	hadTrailingPipe := strings.HasSuffix(content, "|")
	content = strings.TrimSuffix(content, "|")
	parts := strings.Split(content, "|")
	cells = make([]Cell, len(parts))
	for i, raw := range parts {
		cells[i] = Cell{Text: strings.TrimSpace(raw), Align: cellAlign(raw)}
	}
	// Without a closing pipe there's no reliable trailing-space signal for
	// the last cell (the line was already right-trimmed), so don't let an
	// accidental leading-space run right-align it.
	if !hadTrailingPipe {
		cells[len(cells)-1].Align = AlignLeft
	}
	return header, cells, true
}

// isComment reports whether line's trimmed content starts with "%": a
// single-line comment, stripped wherever it appears in the body (not just
// the head area). Block comments are handled by parseBody.
func isComment(line string) bool {
	return strings.HasPrefix(strings.TrimSpace(line), "%")
}

func isTocMacro(line string) bool {
	return strings.TrimSpace(line) == "%%toc"
}

// isFence reports whether line is exactly the given block marker.
func isFence(line, marker string) bool {
	return strings.TrimSpace(line) == marker
}

// isDeflistTerm returns the term of a ": term" line.
func isDeflistTerm(line string) (string, bool) {
	if !strings.HasPrefix(line, ": ") {
		return "", false
	}
	text := strings.TrimSpace(line[2:])
	if text == "" {
		return "", false
	}
	return text, true
}

// ── inline markup ────────────────────────────────────────────────────────

func htmlEscapeChar(c rune) string {
	switch c {
	case '&':
		return "&amp;"
	case '<':
		return "&lt;"
	case '>':
		return "&gt;"
	default:
		return string(c)
	}
}

func htmlEscape(s string) string {
	var b strings.Builder
	for _, c := range s {
		b.WriteString(htmlEscapeChar(c))
	}
	return b.String()
}

func latexEscapeChar(c rune) string {
	switch c {
	case '\\':
		return "\\textbackslash{}"
	case '&':
		return "\\&"
	case '%':
		return "\\%"
	case '$':
		return "\\$"
	case '#':
		return "\\#"
	case '_':
		return "\\_"
	case '{':
		return "\\{"
	case '}':
		return "\\}"
	case '~':
		return "\\textasciitilde{}"
	case '^':
		return "\\textasciicircum{}"
	default:
		return string(c)
	}
}

func latexEscape(s string) string {
	var b strings.Builder
	for _, c := range s {
		b.WriteString(latexEscapeChar(c))
	}
	return b.String()
}

// \X anywhere in the raw text protects X from both escaping-driven
// surprises and from being read as part of a markup delimiter.
const placeholderMark = "\x01"

func protectEscapes(s string) (string, []rune) {
	runes := []rune(s)
	var out strings.Builder
	var escaped []rune
	i := 0
	for i < len(runes) {
		c := runes[i]
		if c == '\\' && i+1 < len(runes) {
			next := runes[i+1]
			escaped = append(escaped, next)
			out.WriteString(placeholderMark)
			out.WriteString(strconv.Itoa(len(escaped)))
			out.WriteString(placeholderMark)
			i += 2
		} else {
			out.WriteRune(c)
			i++
		}
	}
	return out.String(), escaped
}

func restoreEscapes(s string, escaped []rune, escapeChar func(rune) string) string {
	result := s
	for idx, ch := range escaped {
		token := placeholderMark + strconv.Itoa(idx+1) + placeholderMark
		if pos := strings.Index(result, token); pos >= 0 {
			result = result[:pos] + escapeChar(ch) + result[pos+len(token):]
		}
	}
	return result
}

// delim is (mark, open, close) -- a symmetric HTML tag is just
// open="<x>"/close="</x>", but LaTeX commands need distinct open/close
// strings, hence three parts rather than assuming a tag name.
type delim struct {
	mark, open, close string
}

var htmlDelims = []delim{
	{"**", "<b>", "</b>"},
	{"//", "<i>", "</i>"},
	{"__", "<u>", "</u>"},
	{"--", "<s>", "</s>"},
	{"``", "<tt>", "</tt>"},
}

var latexDelims = []delim{
	{"**", "\\textbf{", "}"},
	{"//", "\\textit{", "}"},
	{"__", "\\underline{", "}"},
	{"--", "\\sout{", "}"},
	{"``", "\\texttt{", "}"},
}

// A mark only opens when it's glued to its content (no whitespace right
// after it) and not glued to a word on the outside (nothing alphanumeric
// right before it) -- e.g. two URLs concatenated with no space, each
// containing "//", must not misread the "//" run as italic markup.
func validOpenBoundary(before, after rune, hasBefore, hasAfter bool) bool {
	beforeOK := !hasBefore || !unicode.IsLetter(before) && !unicode.IsDigit(before)
	afterOK := hasAfter && !unicode.IsSpace(after)
	return beforeOK && afterOK
}

// Mirror of validOpenBoundary for the closing delimiter: glued to its
// content on the inside (no whitespace right before it), not glued to a
// word on the outside (nothing alphanumeric right after it).
func validCloseBoundary(before, after rune, hasBefore, hasAfter bool) bool {
	beforeOK := hasBefore && !unicode.IsSpace(before)
	afterOK := !hasAfter || !unicode.IsLetter(after) && !unicode.IsDigit(after)
	return beforeOK && afterOK
}

func findBoundary(s string, mark string, valid func(before, after rune, hasBefore, hasAfter bool) bool) int {
	start := 0
	for {
		rel := strings.Index(s[start:], mark)
		if rel == -1 {
			return -1
		}
		pos := start + rel
		beforeRune, sizeBefore := utf8.DecodeLastRuneInString(s[:pos])
		afterRune, sizeAfter := utf8.DecodeRuneInString(s[pos+len(mark):])
		if valid(beforeRune, afterRune, sizeBefore > 0, sizeAfter > 0) {
			return pos
		}
		start = pos + len(mark)
	}
}

// applyMarks is a leftmost-delimiter, recursive-descent inline formatter
// (no patterns).
func applyMarks(s string, delims []delim) string {
	bestPos := -1
	var bestMark, bestOpen, bestClose string
	for _, d := range delims {
		if p := findBoundary(s, d.mark, validOpenBoundary); p >= 0 && (bestPos == -1 || p < bestPos) {
			bestPos, bestMark, bestOpen, bestClose = p, d.mark, d.open, d.close
		}
	}
	if bestPos == -1 {
		return s
	}

	before := s[:bestPos]
	afterOpen := bestPos + len(bestMark)
	rel := findBoundary(s[afterOpen:], bestMark, validCloseBoundary)
	if rel == -1 {
		return before + bestMark + applyMarks(s[afterOpen:], delims)
	}
	closePos := afterOpen + rel
	inner := s[afterOpen:closePos]
	rest := s[closePos+len(bestMark):]
	return before + bestOpen + applyMarks(inner, delims) + bestClose + applyMarks(rest, delims)
}

// \002 marks a resolved link/image span, so mark-matching can't reach
// into its (already fully rendered) target-format output.
const placeholderLink = "\x02"

var imageExts = []string{"png", "jpg", "jpeg", "gif", "svg", "bmp"}

func looksLikeImage(s string) bool {
	lower := strings.ToLower(s)
	for _, ext := range imageExts {
		if strings.HasSuffix(lower, "."+ext) {
			return true
		}
	}
	return false
}

func looksLikeURL(s string) bool {
	return strings.HasPrefix(s, "http://") || strings.HasPrefix(s, "https://") ||
		strings.HasPrefix(s, "ftp://") || strings.HasPrefix(s, "mailto:")
}

func htmlAttrEscape(s string) string {
	var b strings.Builder
	for _, c := range s {
		switch c {
		case '&':
			b.WriteString("&amp;")
		case '"':
			b.WriteString("&quot;")
		default:
			b.WriteRune(c)
		}
	}
	return b.String()
}

func htmlLink(label, url string) string {
	return "<a href=\"" + htmlAttrEscape(url) + "\">" + label + "</a>"
}

func htmlImage(src string) string {
	return "<img src=\"" + htmlAttrEscape(src) + "\" alt=\"\">"
}

func latexLink(label, url string) string {
	return "\\href{" + url + "}{" + label + "}"
}

func latexImage(src string) string {
	return "\\includegraphics{" + src + "}"
}

// Runs the escape+mark pipeline (but not link/image extraction -- nested
// links aren't supported) over a link label or bare-URL text, reusing the
// same protectEscapes() lookup table as the surrounding text.
func inlineLabel(protectedText string, escaped []rune, escapeChar func(rune) string, delims []delim) string {
	var b strings.Builder
	for _, c := range protectedText {
		b.WriteString(escapeChar(c))
	}
	marked := applyMarks(b.String(), delims)
	return restoreEscapes(marked, escaped, escapeChar)
}

func indexRune(rs []rune, target rune) int {
	for i, r := range rs {
		if r == target {
			return i
		}
	}
	return -1
}

// Content of a "[...]" span (already protectEscapes'd) -> fully rendered
// link/image output, or ok=false if it doesn't look like a link/image
// (the brackets are then left as literal text).
func renderBracket(
	content string,
	escaped []rune,
	escapeChar func(rune) string,
	delims []delim,
	renderLink func(string, string) string,
	renderImage func(string) string,
) (string, bool) {
	content = strings.TrimSpace(content)
	if content == "" {
		return "", false
	}
	if idx := strings.LastIndex(content, " "); idx >= 0 {
		target := strings.TrimSpace(content[idx+1:])
		labelPart := strings.TrimSpace(content[:idx])
		if looksLikeImage(labelPart) && looksLikeURL(target) {
			return renderLink(renderImage(labelPart), target), true
		}
		if looksLikeURL(target) {
			label := inlineLabel(labelPart, escaped, escapeChar, delims)
			return renderLink(label, target), true
		}
		return "", false
	}
	token := content
	if looksLikeImage(token) {
		return renderImage(token), true
	}
	if looksLikeURL(token) {
		label := inlineLabel(token, escaped, escapeChar, delims)
		return renderLink(label, token), true
	}
	return "", false
}

// Tries to match "[ [image.ext] URL ]" starting at chars[outerOpen]
// (already confirmed to be '[' immediately followed by another '['). This
// is the classic txt2tags image-as-link shape, checked before the generic
// (single-level-only) bracket handling in extractLinksImages so it isn't
// rejected by that function's "no nested '['" guard. Anything that
// doesn't match this exact shape (e.g. LionWiki's unrelated
// "[[label | URL]]" double-bracket dialect) falls through to that
// guard's graceful degradation.
func findLinkRender(
	chars []rune,
	outerOpen int,
	renderLink func(string, string) string,
	renderImage func(string) string,
) (rendered string, consumedTo int, ok bool) {
	innerOpen := outerOpen + 1
	relInnerClose := indexRune(chars[innerOpen+1:], ']')
	if relInnerClose < 0 {
		return "", 0, false
	}
	innerClose := innerOpen + 1 + relInnerClose
	inner := string(chars[innerOpen+1 : innerClose])
	if strings.Contains(inner, "[") {
		return "", 0, false
	}
	relOuterClose := indexRune(chars[innerClose+1:], ']')
	if relOuterClose < 0 {
		return "", 0, false
	}
	outerClose := innerClose + 1 + relOuterClose
	target := strings.TrimSpace(string(chars[innerClose+1 : outerClose]))
	innerTrim := strings.TrimSpace(inner)
	if strings.Contains(target, "[") || !looksLikeImage(innerTrim) || !looksLikeURL(target) {
		return "", 0, false
	}
	return renderLink(renderImage(innerTrim), target), outerClose + 1, true
}

// isURLChar reports whether c may appear in a bare URL: the reference
// txt2tags URL character classes (path chars, form-data chars, "?" and
// "#" markers), notably without brackets, quotes, "<"/">" or whitespace.
func isURLChar(c rune) bool {
	return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
		strings.ContainsRune("%._/~:,=$@&+-;*?#", c)
}

// autolinkEnd returns the end (exclusive) of the bare URL starting at
// start: the longest run of URL characters, minus trailing sentence
// punctuation (".,;:!?"), so "see http://x.org." or "[label http://x.org]"
// don't pull the "." or "]" into the href.
func autolinkEnd(chars []rune, start int) int {
	end := start
	for end < len(chars) && isURLChar(chars[end]) {
		end++
	}
	for end > start && strings.ContainsRune(".,;:!?", chars[end-1]) {
		end--
	}
	return end
}

func looksLikeAutolinkStart(chars []rune, i int) bool {
	return startsWithAt(chars, i, "http://") || startsWithAt(chars, i, "https://") || startsWithAt(chars, i, "ftp://")
}

func startsWithAt(chars []rune, i int, pat string) bool {
	p := []rune(pat)
	if i+len(p) > len(chars) {
		return false
	}
	for j, r := range p {
		if chars[i+j] != r {
			return false
		}
	}
	return true
}

// Scans (already protectEscapes'd) text for "[label URL]"/"[image.ext]"
// brackets and bare autolinks, replacing each with a numbered
// placeholderLink token. Returns the token-substituted text plus the list
// of fully rendered replacements, indexed by token number - 1.
func extractLinksImages(
	s string,
	escaped []rune,
	escapeChar func(rune) string,
	delims []delim,
	renderLink func(string, string) string,
	renderImage func(string) string,
) (string, []string) {
	chars := []rune(s)
	var out strings.Builder
	var items []string
	i := 0
	for i < len(chars) {
		c := chars[i]
		if c == '[' {
			if i+1 < len(chars) && chars[i+1] == '[' {
				if rendered, consumedTo, ok := findLinkRender(chars, i, renderLink, renderImage); ok {
					items = append(items, rendered)
					out.WriteString(placeholderLink)
					out.WriteString(strconv.Itoa(len(items)))
					out.WriteString(placeholderLink)
					i = consumedTo
					continue
				}
			}
			if relClose := indexRune(chars[i+1:], ']'); relClose >= 0 {
				closeIdx := i + 1 + relClose
				content := string(chars[i+1 : closeIdx])
				// A nested '[' means this isn't a single-level [label URL]
				// span -- leave the outer bracket as literal text and let
				// the inner one get its own look on a later loop
				// iteration, rather than mis-parsing the whole span into
				// a mangled link.
				if !strings.Contains(content, "[") {
					if rendered, ok := renderBracket(content, escaped, escapeChar, delims, renderLink, renderImage); ok {
						items = append(items, rendered)
						out.WriteString(placeholderLink)
						out.WriteString(strconv.Itoa(len(items)))
						out.WriteString(placeholderLink)
						i = closeIdx + 1
						continue
					}
				}
			}
			out.WriteRune(c)
			i++
		} else if looksLikeAutolinkStart(chars, i) {
			start := i
			j := autolinkEnd(chars, i)
			word := string(chars[start:j])
			label := inlineLabel(word, escaped, escapeChar, delims)
			items = append(items, renderLink(label, word))
			out.WriteString(placeholderLink)
			out.WriteString(strconv.Itoa(len(items)))
			out.WriteString(placeholderLink)
			i = j
		} else {
			out.WriteRune(c)
			i++
		}
	}
	return out.String(), items
}

func restoreLinkPlaceholders(s string, items []string) string {
	result := s
	for idx, item := range items {
		token := placeholderLink + strconv.Itoa(idx+1) + placeholderLink
		if pos := strings.Index(result, token); pos >= 0 {
			result = result[:pos] + item + result[pos+len(token):]
		}
	}
	return result
}

func inlineFormatWith(
	text string,
	escapeChar func(rune) string,
	delims []delim,
	renderLink func(string, string) string,
	renderImage func(string) string,
) string {
	protected, escaped := protectEscapes(text)
	linked, items := extractLinksImages(protected, escaped, escapeChar, delims, renderLink, renderImage)
	var b strings.Builder
	for _, c := range linked {
		b.WriteString(escapeChar(c))
	}
	marked := applyMarks(b.String(), delims)
	restored := restoreEscapes(marked, escaped, escapeChar)
	return restoreLinkPlaceholders(restored, items)
}

func inlineFormatHTML(text string) string {
	return inlineFormatWith(text, htmlEscapeChar, htmlDelims, htmlLink, htmlImage)
}

func inlineFormatLatex(text string) string {
	return inlineFormatWith(text, latexEscapeChar, latexDelims, latexLink, latexImage)
}

// ── block parsing ────────────────────────────────────────────────────────

func parseBody(lines []string) []Block {
	var blocks []Block
	n := len(lines)
	i := 0

	for i < n {
		line := lines[i]

		if strings.TrimSpace(line) == "" {
			i++
			continue
		}
		if isTocMacro(line) {
			blocks = append(blocks, Block{Kind: blockToc})
			i++
			continue
		}
		if isFence(line, "%%%") {
			// Block comment: everything up to the matching "%%%" produces
			// no output at all (checked before isComment, which would
			// otherwise treat "%%%" itself as an ordinary single-line "%"
			// comment and only skip that one line).
			i++
			for i < n && !isFence(lines[i], "%%%") {
				i++
			}
			if i < n {
				i++
			}
			continue
		}
		if isComment(line) {
			i++
			continue
		}
		if level, text, ok := isHeading(line); ok {
			blocks = append(blocks, Block{Kind: blockHeading, Level: level, Text: text})
			i++
			continue
		}
		if isHr(line) {
			blocks = append(blocks, Block{Kind: blockHr})
			i++
			continue
		}
		if strings.TrimSpace(line) == "```" {
			i++
			var vlines []string
			for i < n && strings.TrimSpace(lines[i]) != "```" {
				vlines = append(vlines, lines[i])
				i++
			}
			if i < n {
				i++
			}
			blocks = append(blocks, Block{Kind: blockVerbatim, Lines: vlines})
			continue
		}
		if isFence(line, `"""`) {
			i++
			var rlines []string
			for i < n && !isFence(lines[i], `"""`) {
				rlines = append(rlines, lines[i])
				i++
			}
			if i < n {
				i++
			}
			blocks = append(blocks, Block{Kind: blockRaw, Lines: rlines})
			continue
		}
		if firstTerm, ok := isDeflistTerm(line); ok {
			var items []DefItem
			term := firstTerm
			var def []string
			i++
			for i < n && strings.TrimSpace(lines[i]) != "" {
				if nextTerm, ok2 := isDeflistTerm(lines[i]); ok2 {
					items = append(items, DefItem{Term: term, Defs: def})
					term = nextTerm
					def = nil
					i++
				} else if strings.HasPrefix(lines[i], " ") || strings.HasPrefix(lines[i], "\t") {
					def = append(def, strings.TrimSpace(lines[i]))
					i++
				} else {
					break
				}
			}
			items = append(items, DefItem{Term: term, Defs: def})
			blocks = append(blocks, Block{Kind: blockDefList, Defs: items})
			continue
		}
		if _, _, _, ok := isListItem(line); ok {
			var items []ListItem
			for i < n {
				if strings.TrimSpace(lines[i]) == "" {
					i++
					continue
				}
				if isComment(lines[i]) {
					i++
					continue
				}
				kind, lvl, txt, ok2 := isListItem(lines[i])
				if !ok2 {
					break
				}
				items = append(items, ListItem{Kind: kind, Level: lvl, Text: txt})
				i++
			}
			blocks = append(blocks, Block{Kind: blockList, Items: items})
			continue
		}
		if _, _, ok := isTableRow(line); ok {
			var rows []TableRow
			for i < n {
				header, cells, ok2 := isTableRow(lines[i])
				if !ok2 {
					break
				}
				rows = append(rows, TableRow{Header: header, Cells: cells})
				i++
			}
			blocks = append(blocks, Block{Kind: blockTable, Rows: rows})
			continue
		}

		var plines []string
		for i < n && strings.TrimSpace(lines[i]) != "" {
			l := lines[i]
			if isTocMacro(l) || isFence(l, "%%%") {
				break
			}
			if isComment(l) {
				i++
				continue
			}
			if _, _, ok := isHeading(l); ok {
				break
			}
			if isHr(l) {
				break
			}
			if isFence(l, "```") || isFence(l, `"""`) {
				break
			}
			if _, ok := isDeflistTerm(l); ok {
				break
			}
			if _, _, _, ok := isListItem(l); ok {
				break
			}
			if _, _, ok := isTableRow(l); ok {
				break
			}
			plines = append(plines, strings.TrimSpace(l))
			i++
		}
		blocks = append(blocks, Block{Kind: blockPara, Lines: plines})
	}

	return blocks
}

// ── HTML rendering ───────────────────────────────────────────────────────

// Consecutive same-level items are grouped by kind, so a ul/ol switch at
// the same nesting level closes one list and opens another instead of
// silently merging (e.g. a "- " list directly followed by a "+ " list).
func renderListItemsHTML(items []ListItem, i int, level int) (string, int) {
	var out []string
	for i < len(items) && items[i].Level == level {
		kind := items[i].Kind
		tag := "ul"
		if kind == Ol {
			tag = "ol"
		}
		out = append(out, "<"+tag+">")
		for i < len(items) && items[i].Level == level && items[i].Kind == kind {
			out = append(out, "<li>"+inlineFormatHTML(items[i].Text))
			i++
			if i < len(items) && items[i].Level > level {
				nested, ni := renderListItemsHTML(items, i, items[i].Level)
				out = append(out, nested)
				i = ni
			}
			out = append(out, "</li>")
		}
		out = append(out, "</"+tag+">")
	}
	return strings.Join(out, "\n"), i
}

func alignStyle(a Align) string {
	switch a {
	case AlignCenter:
		return ` style="text-align:center"`
	case AlignRight:
		return ` style="text-align:right"`
	}
	return ""
}

// A table of contents is only meaningful (and its heading anchors only
// added) when the document actually contains a %%toc -- so plain
// documents render byte-identical headings.
func renderTocHTML(blocks []Block) string {
	out := []string{`<ul class="toc">`}
	for i, b := range blocks {
		if b.Kind == blockHeading {
			h := strconv.Itoa(b.Level)
			out = append(out, `<li class="toc-h`+h+`"><a href="#t2t-`+strconv.Itoa(i)+`">`+inlineFormatHTML(b.Text)+`</a></li>`)
		}
	}
	out = append(out, "</ul>")
	return strings.Join(out, "\n")
}

func renderBlockHTML(b Block, index int, all []Block, hasToc bool) string {
	switch b.Kind {
	case blockHeading:
		h := strconv.Itoa(b.Level)
		if hasToc {
			return "<h" + h + ` id="t2t-` + strconv.Itoa(index) + `">` + inlineFormatHTML(b.Text) + "</h" + h + ">"
		}
		return "<h" + h + ">" + inlineFormatHTML(b.Text) + "</h" + h + ">"
	case blockHr:
		return "<hr>"
	case blockPara:
		formatted := make([]string, len(b.Lines))
		for i, l := range b.Lines {
			formatted[i] = inlineFormatHTML(l)
		}
		return "<p>\n" + strings.Join(formatted, "\n") + "\n</p>"
	case blockList:
		if len(b.Items) == 0 {
			return ""
		}
		html, _ := renderListItemsHTML(b.Items, 0, b.Items[0].Level)
		return html
	case blockTable:
		out := []string{"<table>"}
		for _, row := range b.Rows {
			out = append(out, "<tr>")
			tag := "td"
			if row.Header {
				tag = "th"
			}
			for _, cell := range row.Cells {
				out = append(out, "<"+tag+alignStyle(cell.Align)+">"+inlineFormatHTML(cell.Text)+"</"+tag+">")
			}
			out = append(out, "</tr>")
		}
		out = append(out, "</table>")
		return strings.Join(out, "\n")
	case blockVerbatim:
		escapedLines := make([]string, len(b.Lines))
		for i, l := range b.Lines {
			escapedLines[i] = htmlEscape(l)
		}
		return "<pre>\n" + strings.Join(escapedLines, "\n") + "\n</pre>"
	case blockToc:
		return renderTocHTML(all)
	case blockRaw:
		return strings.Join(b.Lines, "\n")
	case blockDefList:
		out := []string{"<dl>"}
		for _, d := range b.Defs {
			out = append(out, "<dt>"+inlineFormatHTML(d.Term)+"</dt>")
			for _, line := range d.Defs {
				out = append(out, "<dd>"+inlineFormatHTML(line)+"</dd>")
			}
		}
		out = append(out, "</dl>")
		return strings.Join(out, "\n")
	}
	return ""
}

func renderHTML(title, author, date string, blocks []Block) string {
	var out []string
	out = append(out, "<!DOCTYPE html>")
	out = append(out, "<html>")
	out = append(out, "<head><meta charset=\"utf-8\"><title>"+htmlEscape(title)+"</title></head>")
	out = append(out, "<body>")
	if title != "" {
		out = append(out, "<h1>"+htmlEscape(title)+"</h1>")
	}
	if author != "" || date != "" {
		sep := ""
		if author != "" && date != "" {
			sep = " - "
		}
		out = append(out, "<p class=\"header\">"+htmlEscape(author)+sep+htmlEscape(date)+"</p>")
	}
	hasToc := false
	for _, b := range blocks {
		if b.Kind == blockToc {
			hasToc = true
		}
	}
	for i, b := range blocks {
		out = append(out, renderBlockHTML(b, i, blocks, hasToc))
	}
	out = append(out, "</body>")
	out = append(out, "</html>")
	return strings.Join(out, "\n")
}

// ── LaTeX rendering ──────────────────────────────────────────────────────

func renderListItemsLatex(items []ListItem, i int, level int) (string, int) {
	var out []string
	for i < len(items) && items[i].Level == level {
		kind := items[i].Kind
		env := "itemize"
		if kind == Ol {
			env = "enumerate"
		}
		out = append(out, "\\begin{"+env+"}")
		for i < len(items) && items[i].Level == level && items[i].Kind == kind {
			out = append(out, "\\item "+inlineFormatLatex(items[i].Text))
			i++
			if i < len(items) && items[i].Level > level {
				nested, ni := renderListItemsLatex(items, i, items[i].Level)
				out = append(out, nested)
				i = ni
			}
		}
		out = append(out, "\\end{"+env+"}")
	}
	return strings.Join(out, "\n"), i
}

func headingCommand(level int) string {
	switch level {
	case 1:
		return "section"
	case 2:
		return "subsection"
	case 3:
		return "subsubsection"
	case 4:
		return "paragraph"
	case 5:
		return "subparagraph"
	default:
		return "paragraph"
	}
}

func renderBlockLatex(b Block) string {
	switch b.Kind {
	case blockHeading:
		cmd := headingCommand(b.Level)
		return "\\" + cmd + "{" + inlineFormatLatex(b.Text) + "}"
	case blockHr:
		return "\\par\\noindent\\hrulefill\\par"
	case blockPara:
		formatted := make([]string, len(b.Lines))
		for i, l := range b.Lines {
			formatted[i] = inlineFormatLatex(l)
		}
		return strings.Join(formatted, "\n")
	case blockList:
		if len(b.Items) == 0 {
			return ""
		}
		latex, _ := renderListItemsLatex(b.Items, 0, b.Items[0].Level)
		return latex
	case blockTable:
		ncols := 0
		for _, row := range b.Rows {
			if len(row.Cells) > ncols {
				ncols = len(row.Cells)
			}
		}
		spec := make([]byte, ncols)
		for c := range spec {
			spec[c] = 'l'
			if len(b.Rows[0].Cells) > c {
				switch b.Rows[0].Cells[c].Align {
				case AlignCenter:
					spec[c] = 'c'
				case AlignRight:
					spec[c] = 'r'
				}
			}
		}
		out := []string{"\\begin{tabular}{" + string(spec) + "}"}
		for _, row := range b.Rows {
			cells := make([]string, len(row.Cells))
			for i, cell := range row.Cells {
				formatted := inlineFormatLatex(cell.Text)
				if row.Header {
					formatted = "\\textbf{" + formatted + "}"
				}
				cells[i] = formatted
			}
			out = append(out, strings.Join(cells, " & ")+" \\\\")
			if row.Header {
				out = append(out, "\\hline")
			}
		}
		out = append(out, "\\end{tabular}")
		return strings.Join(out, "\n")
	case blockVerbatim:
		return "\\begin{verbatim}\n" + strings.Join(b.Lines, "\n") + "\n\\end{verbatim}"
	case blockToc:
		// LaTeX builds its own table of contents from the \section-family
		// commands above -- no manual anchor bookkeeping needed here.
		return "\\tableofcontents"
	case blockRaw:
		return strings.Join(b.Lines, "\n")
	case blockDefList:
		out := []string{"\\begin{description}"}
		for _, d := range b.Defs {
			defs := make([]string, len(d.Defs))
			for i, line := range d.Defs {
				defs[i] = inlineFormatLatex(line)
			}
			out = append(out, "\\item["+inlineFormatLatex(d.Term)+"] "+strings.Join(defs, " "))
		}
		out = append(out, "\\end{description}")
		return strings.Join(out, "\n")
	}
	return ""
}

func renderLatex(title, author, date string, blocks []Block) string {
	var out []string
	out = append(out, "\\documentclass{article}")
	out = append(out, "\\usepackage[utf8]{inputenc}")
	out = append(out, "\\usepackage[normalem]{ulem}") // \sout, for --strike--
	out = append(out, "\\usepackage{graphicx}")       // \includegraphics, for images
	out = append(out, "\\usepackage{hyperref}")       // \href, for links
	out = append(out, "\\title{"+latexEscape(title)+"}")
	out = append(out, "\\author{"+latexEscape(author)+"}")
	out = append(out, "\\date{"+latexEscape(date)+"}")
	out = append(out, "\\begin{document}")
	out = append(out, "\\maketitle")
	for _, b := range blocks {
		out = append(out, renderBlockLatex(b))
	}
	out = append(out, "\\end{document}")
	return strings.Join(out, "\n")
}

// ── public API ───────────────────────────────────────────────────────────

// Parse parses raw txt2tags source into a Document.
func Parse(text string) Document {
	lines := splitLines(expandDateMacro(text))
	head := parseHead(lines)
	bodyStart := head.bodyStart
	if bodyStart > len(lines) {
		bodyStart = len(lines)
	}
	bodyText := strings.Join(lines[bodyStart:], "\n")
	body := splitLines(applyLineRules(bodyText, head.preproc))
	return Document{
		Title: head.title, Author: head.author, Date: head.date,
		Blocks:   parseBody(body),
		postproc: head.postproc,
	}
}

// ToHTML converts raw txt2tags source directly to an HTML document string.
func ToHTML(text string) string {
	doc := Parse(text)
	return applyLineRules(renderHTML(doc.Title, doc.Author, doc.Date, doc.Blocks), doc.postproc)
}

// ToLatex converts raw txt2tags source directly to a LaTeX document string.
func ToLatex(text string) string {
	doc := Parse(text)
	return applyLineRules(renderLatex(doc.Title, doc.Author, doc.Date, doc.Blocks), doc.postproc)
}
