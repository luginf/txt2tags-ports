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
//   - Horizontal rule: a line of 20+ repeated -, = or _
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
//   - Raw blocks: a line of exactly """ opens/closes one; content is escaped
//     for the target but gets no inline marks (as in the reference).
//   - Tagged blocks: a line of exactly ”' opens/closes one; content is
//     passed through completely unmodified: it is meant to already be valid
//     markup in the target format.
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
//   - Marks only trigger when glued to their content (no space right
//     after the opening mark or right before the closing one), as in the
//     reference; what sits outside them does not matter ("a--b--c").
//
// Export targets: HTML (ToHTML), LaTeX (ToLatex) and Markdown (ToMarkdown,
// GitHub-flavoured), all reachable through Convert with a Target and the
// Options value, which mirrors the Python port's command line (-H, --toc,
// --toc-level, --toc-only, -n, --skip-header-lines). The LaTeX target assumes a preamble with
// \usepackage[normalem]{ulem} (\sout, for --strike--), \usepackage{graphicx}
// (images) and \usepackage{hyperref} (links) -- see the top of renderLatex.
//
// NOT supported yet (left for a later pass): nested constructs inside
// table cells or definition-list entries beyond plain inline marks/links.
package txt2tags

import (
	"fmt"
	"math"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
	"unicode"
	"unicode/utf8"
)

// DefaultTocLevel is the deepest title level a table of contents lists
// unless Options.TocLevel says otherwise.
const DefaultTocLevel = 3

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
	// BlankBefore: a blank line separated this item from the previous one
	BlankBefore bool
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
	blockTagged
	blockDefList
	blockQuote
	// blockListText is plain text that goes on with the last list item after
	// a verbatim, raw or tagged block interrupted it (Markdown indents it by
	// Pad)
	blockListText
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
	Quote []QuoteLine
	Pad   int
	// Numbered: a "+ title +" (always numbered), not a "= title ="
	Numbered bool
}

// QuoteLine is a tab-indented line: Depth is the number of tabs.
type QuoteLine struct {
	Depth int
	Text  string
}

// Document is a parsed txt2tags source file.
type Document struct {
	Title  string
	Author string
	Date   string
	Blocks []Block

	postproc []lineRule
	options  []docOption
}

// ── date macro ───────────────────────────────────────────────────────────

// TodayString returns today's date (UTC) as YYYY-MM-DD: what "%%date"
// expands to. Exported mainly so callers/tests can compare against it.
func TodayString() string {
	return time.Now().UTC().Format("2006-01-02")
}

// MacroEnv is what the %%macros can say about the conversion in progress.
type MacroEnv struct {
	// Infile is the input file name; "-" or empty is standard input
	Infile  string
	Outfile string
	Target  string
	// Headers are the title, author and date, for %%header1 to %%header3
	Headers [3]string
}

// Version is reported by %%appversion.
const Version = "1.1.0"

// strftime handles the flags that make sense in a UTC date (C locale).
func strftime(format string, t time.Time) string {
	t = t.UTC()
	var out strings.Builder
	r := []rune(format)
	for i := 0; i < len(r); i++ {
		if r[i] != '%' {
			out.WriteRune(r[i])
			continue
		}
		i++
		if i >= len(r) {
			out.WriteByte('%')
			break
		}
		switch r[i] {
		case 'Y':
			out.WriteString(strconv.Itoa(t.Year()))
		case 'y':
			out.WriteString(fmt.Sprintf("%02d", t.Year()%100))
		case 'm':
			out.WriteString(fmt.Sprintf("%02d", int(t.Month())))
		case 'd':
			out.WriteString(fmt.Sprintf("%02d", t.Day()))
		case 'e':
			out.WriteString(fmt.Sprintf("%2d", t.Day()))
		case 'H':
			out.WriteString(fmt.Sprintf("%02d", t.Hour()))
		case 'I':
			h := t.Hour() % 12
			if h == 0 {
				h = 12
			}
			out.WriteString(fmt.Sprintf("%02d", h))
		case 'M':
			out.WriteString(fmt.Sprintf("%02d", t.Minute()))
		case 'S':
			out.WriteString(fmt.Sprintf("%02d", t.Second()))
		case 'p':
			if t.Hour() < 12 {
				out.WriteString("AM")
			} else {
				out.WriteString("PM")
			}
		case 'j':
			out.WriteString(fmt.Sprintf("%03d", t.YearDay()))
		case 'a':
			out.WriteString(t.Weekday().String()[:3])
		case 'A':
			out.WriteString(t.Weekday().String())
		case 'b', 'h':
			out.WriteString(t.Month().String()[:3])
		case 'B':
			out.WriteString(t.Month().String())
		case 'u':
			wd := int(t.Weekday())
			if wd == 0 {
				wd = 7
			}
			out.WriteString(strconv.Itoa(wd))
		case 'w':
			out.WriteString(strconv.Itoa(int(t.Weekday())))
		case 's':
			out.WriteString(strconv.FormatInt(t.Unix(), 10))
		case 'Z':
			out.WriteString("UTC")
		case 'z':
			out.WriteString("+0000")
		case 'F':
			out.WriteString(t.Format("2006-01-02"))
		case 'T':
			out.WriteString(t.Format("15:04:05"))
		case 'D':
			out.WriteString(t.Format("01/02/06"))
		case 'n':
			out.WriteByte('\n')
		case 't':
			out.WriteByte('\t')
		case '%':
			out.WriteByte('%')
		default:
			out.WriteByte('%')
			out.WriteRune(r[i])
		}
	}
	return out.String()
}

func nowTime() time.Time {
	if v, err := strconv.ParseInt(os.Getenv("SOURCE_DATE_EPOCH"), 10, 64); err == nil {
		return time.Unix(v, 0)
	}
	return time.Now()
}

// fileMacro expands %%infile(fmt) and friends: %f name, %F name without
// extension, %d directory, %D parent directory name only, %p path, %e
// extension.
func fileMacro(file, format string) string {
	path, dir, name := file, "", file
	if file != "" && file != "-" {
		abs, err := filepath.Abs(file)
		if err != nil {
			abs = file
		}
		path, dir, name = abs, filepath.Dir(abs), filepath.Base(abs)
	}
	ext := filepath.Ext(name)
	if ext == name {
		ext = ""
	}
	var out strings.Builder
	r := []rune(format)
	for i := 0; i < len(r); i++ {
		if r[i] != '%' {
			out.WriteRune(r[i])
			continue
		}
		i++
		if i >= len(r) {
			out.WriteByte('%')
			break
		}
		switch r[i] {
		case '%':
			out.WriteByte('%')
		case 'f':
			out.WriteString(name)
		case 'F':
			out.WriteString(strings.TrimSuffix(name, ext))
		case 'd':
			out.WriteString(dir)
		case 'D':
			out.WriteString(filepath.Base(dir))
		case 'p':
			out.WriteString(path)
		case 'e':
			out.WriteString(strings.TrimPrefix(ext, "."))
		default:
			out.WriteByte('%')
			out.WriteRune(r[i])
		}
	}
	return out.String()
}

var (
	macroRe       = regexp.MustCompile(`(?i)%%(date|mtime|infile|currentfile|outfile|appurl|appname|appversion|target|encoding|header[123])\b(?:\((.*?)\))?`)
	headerMacroRe = regexp.MustCompile(`(?i)%%header([123])\b(?:\(.*?\))?`)
)

// expandMacros replaces the %%macro and %%macro(format) calls the Python
// port knows (all but %%cmdline and %%cc) anywhere in text. The %%headerN
// ones are left for expandHeaderMacros.
func expandMacros(text string, env MacroEnv) string {
	return macroRe.ReplaceAllStringFunc(text, func(m string) string {
		sub := macroRe.FindStringSubmatch(m)
		name := strings.ToLower(sub[1])
		format := ""
		hasFormat := strings.Contains(m, "(")
		if hasFormat {
			format = sub[2]
		}
		pick := func(def string) string {
			if hasFormat {
				return format
			}
			return def
		}
		switch name {
		case "date":
			return strftime(pick("%Y-%m-%d"), nowTime())
		case "mtime":
			t := nowTime()
			if env.Infile != "" && env.Infile != "-" {
				if st, err := os.Stat(env.Infile); err == nil {
					t = st.ModTime()
				}
			}
			return strftime(pick("%Y%m%d"), t)
		case "infile", "currentfile":
			return fileMacro(env.Infile, pick("%f"))
		case "outfile":
			return fileMacro(env.Outfile, pick("%f"))
		case "appurl":
			return "http://txt2tags.org"
		case "appname":
			return "txt2tags"
		case "appversion":
			return Version
		case "target":
			return env.Target
		case "encoding":
			return "UTF-8"
		}
		if strings.HasPrefix(name, "header") {
			n, _ := strconv.Atoi(name[6:])
			return env.Headers[n-1]
		}
		return m
	})
}

var (
	// the macros of the document being converted: set by Convert (which
	// serializes conversions), read by the inline formatter. Macros are
	// expanded in running text, not in verbatim, raw or tagged blocks, nor
	// inside a ``mono`` span.
	currentMacros MacroEnv
	convertMu     sync.Mutex
	monoSpanRe    = regexp.MustCompile("``[^\\s](?:.*?[^\\s])?`*``")
)

func expandInlineMacros(text string) string {
	if !strings.Contains(text, "%%") {
		return text
	}
	lines := strings.Split(text, "\n")
	for i, line := range lines {
		var out strings.Builder
		at := 0
		for _, m := range monoSpanRe.FindAllStringIndex(line, -1) {
			out.WriteString(expandMacros(line[at:m[0]], currentMacros))
			out.WriteString(line[m[0]:m[1]])
			at = m[1]
		}
		out.WriteString(expandMacros(line[at:], currentMacros))
		lines[i] = out.String()
	}
	return strings.Join(lines, "\n")
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
	options             []docOption
}

// docOption is one %!options: line: the words, for a target ("" = all).
type docOption struct {
	target string
	words  []string
}

// splitWords splits the value of a %!options: line into words, honouring quotes.
func splitWords(s string) []string {
	var words []string
	var cur strings.Builder
	has := false
	var quote rune
	for _, c := range s {
		switch {
		case quote != 0 && c == quote:
			quote = 0
		case quote != 0:
			cur.WriteRune(c)
		case c == '\'' || c == '"':
			quote = c
			has = true
		case unicode.IsSpace(c):
			if has || cur.Len() > 0 {
				words = append(words, cur.String())
				cur.Reset()
				has = false
			}
		default:
			cur.WriteRune(c)
		}
	}
	if has || cur.Len() > 0 {
		words = append(words, cur.String())
	}
	return words
}

// parseOptionsLine reads "%!options: ..." or "%!options(target): ...".
func parseOptionsLine(line string) (docOption, bool) {
	rest, ok := strings.CutPrefix(line, "%!options")
	if !ok {
		return docOption{}, false
	}
	target := ""
	if r, ok := strings.CutPrefix(rest, "("); ok {
		end := strings.Index(r, ")")
		if end < 0 {
			return docOption{}, false
		}
		target = strings.TrimSpace(r[:end])
		rest = r[end+1:]
	}
	rest, ok = strings.CutPrefix(rest, ":")
	if !ok {
		return docOption{}, false
	}
	return docOption{target, splitWords(rest)}, true
}

// mergeDocOptions applies the document's %!options: as defaults under opts:
// flags are OR-ed, valued options only fill what was left at its default.
func mergeDocOptions(opts Options, doc []docOption, target string) Options {
	o := opts
	setTitle := false
	for _, d := range doc {
		if d.target != "" && d.target != target {
			continue
		}
		for k := 0; k < len(d.words); k++ {
			w := d.words[k]
			name, inline, hasInline := w, "", false
			if strings.HasPrefix(w, "--") {
				if n, v, ok := strings.Cut(w, "="); ok {
					name, inline, hasInline = n, v, true
				}
			}
			value := func() string {
				if hasInline {
					return inline
				}
				if k+1 < len(d.words) {
					k++
					return d.words[k]
				}
				return ""
			}
			switch name {
			case "--toc":
				o.Toc = true
			case "--no-toc":
				o.Toc = false
			case "--toc-only":
				o.TocOnly = true
			case "-n", "--enum-title":
				o.EnumTitle = true
			case "-H", "--no-headers":
				o.NoHeaders = true
			case "--headers":
				o.NoHeaders = false
			case "--toc-level":
				if n, err := strconv.Atoi(value()); err == nil && opts.TocLevel == 0 {
					o.TocLevel = n
				}
			case "--toc-title":
				v := value()
				if opts.TocTitle == "" && !setTitle {
					o.TocTitle = v
					setTitle = true
				}
			}
		}
	}
	return o
}

func parseHead(lines []string, skipHeader bool) headInfo {
	get := func(i int) string {
		if !skipHeader && i < len(lines) {
			return strings.TrimSpace(lines[i])
		}
		return ""
	}
	h := headInfo{title: get(0), author: get(1), date: get(2)}

	i := 3
	if skipHeader {
		i = 0
	}
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
			if o, ok := parseOptionsLine(t); ok {
				h.options = append(h.options, o)
			} else if kind, pattern, repl, ok := parseConfigDirective(t); ok {
				if re, err := regexp.Compile(pattern); err == nil {
					if kind == "preproc" {
						h.preproc = append(h.preproc, lineRule{re, repl})
					} else {
						h.postproc = append(h.postproc, lineRule{re, repl})
					}
				}
			}
			i++
		case macroLineRe.MatchString(lines[i]):
			// a line that starts with a macro is where the body begins
			break loop
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
	// like the reference: 20 or more of - = _ (mixed allowed)
	if len(t) < 20 {
		return false
	}
	for i := 0; i < len(t); i++ {
		if t[i] != '-' && t[i] != '=' && t[i] != '_' {
			return false
		}
	}
	return true
}

func isHeadingLine(l string) bool {
	_, _, ok := isHeading(l)
	return ok
}

// isHeading returns the level (1-5) and text, or ok=false if line isn't a title.
func isHeading(line string) (level int, text string, ok bool) {
	t := strings.TrimSpace(line)
	if !strings.HasPrefix(t, "=") && !strings.HasPrefix(t, "+") {
		return 0, "", false
	}
	mark := t[0]
	// an optional trailing [label], which the markdown output does not use
	if strings.HasSuffix(t, "]") {
		if open := strings.LastIndex(t, "["); open >= 0 {
			label := t[open+1 : len(t)-1]
			if strings.IndexFunc(label, func(r rune) bool {
				return !(unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-')
			}) < 0 {
				t = t[:open]
			}
		}
	}
	n := len(t)
	lvl := 0
	for lvl < n && t[lvl] == mark {
		lvl++
	}
	if lvl < 1 || lvl > 5 || n < 2*lvl {
		return 0, "", false
	}
	closing := t[n-lvl:]
	for i := 0; i < len(closing); i++ {
		if closing[i] != mark {
			return 0, "", false
		}
	}
	inner := strings.TrimSpace(t[lvl : n-lvl])
	// the text may not start or end with the mark itself
	if inner == "" || inner[0] == mark || inner[len(inner)-1] == mark {
		return 0, "", false
	}
	return lvl, inner, true
}

// isListItem returns the kind, 0-based nesting level and text, or ok=false
// if line isn't a list item.
func mapLines(lines []string, f func(string) string) []string {
	out := make([]string, len(lines))
	for i, l := range lines {
		out[i] = f(l)
	}
	return out
}

// startsBlock reports lines that start a block of their own and so end an
// open list.
func startsBlock(l string) bool {
	if strings.HasPrefix(l, "\t") {
		return true
	}
	if _, _, ok := oneLineBlock(l); ok {
		return true
	}
	if _, _, ok := isHeading(l); ok && !strings.HasPrefix(l, " ") {
		return true
	}
	if isHr(l) || isFence(l, "```") || isFence(l, `"""`) || isFence(l, `'''`) || isFence(l, "%%%") || isTocMacro(l) {
		return true
	}
	if _, _, ok := isTableRow(l); ok {
		return true
	}
	_, ok := isDeflistTerm(l)
	return ok
}

// flatItemText is an item's text with its paragraph breaks folded away
// (HTML and LaTeX keep one block per item).
func flatItemText(text string) string {
	var out []string
	for _, l := range strings.Split(text, "\n") {
		if l != "" {
			out = append(out, l)
		}
	}
	return strings.Join(out, "\n")
}

// normalizeListLevels turns indentation (in spaces) into nesting depth, as
// the reference does: an item indented more than the previous one is nested
// in it; one indented less closes the deeper levels and joins the list it
// lands on (even at an odd indent, and whatever its own mark); a change of
// mark at the same indent starts a new list.
func normalizeListLevels(items []ListItem) {
	type open struct {
		indent int
		kind   ListKind
	}
	var stack []open
	for n := range items {
		it := &items[n]
		dedented := false
		for len(stack) > 0 && it.Level < stack[len(stack)-1].indent {
			stack = stack[:len(stack)-1]
			dedented = true
		}
		switch {
		case len(stack) > 0 && dedented:
			it.Kind = stack[len(stack)-1].kind
		case len(stack) > 0 && it.Level == stack[len(stack)-1].indent:
			stack[len(stack)-1].kind = it.Kind
		default:
			if dedented && n > 0 {
				it.BlankBefore = true
			}
			stack = append(stack, open{it.Level, it.Kind})
		}
		it.Level = len(stack) - 1
	}
}

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
	return kind, spaces, txt, true
}

// cellAlign infers a cell's alignment from the padding around its raw
// (untrimmed) text.
func cellAlign(raw string) Align {
	switch {
	case strings.TrimSpace(raw) == "":
		return AlignLeft
	case strings.HasPrefix(raw, " ") && strings.HasSuffix(raw, " "):
		return AlignCenter
	case strings.HasPrefix(raw, " "):
		return AlignRight
	}
	return AlignLeft
}

var (
	tableMarkRe   = regexp.MustCompile(`^ *\|([|_/])? `)
	tableBorderRe = regexp.MustCompile(` (\|+) *$`)
	tableSpanRe   = regexp.MustCompile(` (\|+)\| `)
)

// isTableRow returns the header flag and cells, or ok=false if line isn't a
// table row. Cells are separated by " | " (a bar with a space on each
// side), so a bar inside a word stays text; "||" at the start marks a title
// row and "||" at the end of a cell a column span (kept as one cell).
func isTableRow(line string) (header bool, cells []Cell, ok bool) {
	line = strings.TrimRight(line, " \t\r\n")
	if !tableMarkRe.MatchString(line) {
		return false, nil, false
	}
	r := []rune(strings.TrimLeft(line, " "))
	if len(r) > 1 && r[1] == '_' {
		r = append(r[:1], r[2:]...)
	}
	if len(r) > 1 && r[1] == '/' {
		r[1] = '|'
	}
	header = len(r) > 1 && r[1] == '|'
	s := string(r)
	if tableBorderRe.MatchString(s) {
		s += " "
	} else {
		s += " | "
	}
	s = tableMarkRe.ReplaceAllString(s, "")
	s = tableSpanRe.ReplaceAllString(s, "\a${1} | ")
	parts := strings.Split(s, " | ")
	parts = parts[:len(parts)-1]
	cells = make([]Cell, len(parts))
	for i, raw := range parts {
		if at := strings.IndexByte(raw, 7); at >= 0 && strings.Trim(raw[at+1:], "|") == "" {
			raw = raw[:at]
		}
		cells[i] = Cell{Text: strings.TrimSpace(raw), Align: cellAlign(raw)}
	}
	return header, cells, true
}

// isComment reports whether line's trimmed content starts with "%": a
// single-line comment, stripped wherever it appears in the body (not just
// the head area). Block comments are handled by parseBody.
func isComment(line string) bool {
	// a line that starts with a macro is text, not a comment
	return strings.HasPrefix(strings.TrimSpace(line), "%") && !macroLineRe.MatchString(line)
}

var macroLineRe = regexp.MustCompile(`(?i)^%%(date|mtime|infile|currentfile|outfile|appurl|appname|appversion|target|cmdline|encoding|header[123]|cc)\b`)

func isTocMacro(line string) bool {
	return strings.TrimSpace(line) == "%%toc"
}

// isFence reports whether line is exactly the given block marker.
func isFence(line, marker string) bool {
	return strings.TrimRight(line, " \t\r\n") == marker
}

// oneLineBlock reports a fence mark, a space and some text on one line:
// that line alone is a verbatim (```), raw (""") or tagged (”') block.
func oneLineBlock(line string) (kind blockKind, rest string, ok bool) {
	for _, m := range []struct {
		mark string
		kind blockKind
	}{{"``` ", blockVerbatim}, {`""" `, blockRaw}, {"''' ", blockTagged}} {
		if r, found := strings.CutPrefix(line, m.mark); found && r != "" {
			return m.kind, r, true
		}
	}
	return 0, "", false
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
		if c == '\\' {
			// txt2tags has no backslash escape: the backslash is plain text
			// and the marks after it still apply ("\**x**" is "\" + bold).
			escaped = append(escaped, c)
			out.WriteString(placeholderMark)
			out.WriteString(strconv.Itoa(len(escaped)))
			out.WriteString(placeholderMark)
			i++
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
// after it). As in the reference regexes, what sits on the outside does not
// matter: "a--b--c" has a struck "b".
func validOpenBoundary(before, after rune, hasBefore, hasAfter bool) bool {
	return hasAfter && !unicode.IsSpace(after)
}

// Mirror of validOpenBoundary for the closing delimiter: glued to its
// content on the inside (no whitespace right before it).
func validCloseBoundary(before, after rune, hasBefore, hasAfter bool) bool {
	return hasBefore && !unicode.IsSpace(before)
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

var imageExts = []string{"png", "jpg", "jpeg", "gif", "eps", "bmp", "svg"}

// looksLikeImage reports "image.EXT": a path of word characters and
// ",.+%$#@!?~/-" ending in an image extension, as the reference accepts it
// between brackets.
func looksLikeImage(s string) bool {
	for _, c := range s {
		if !(unicode.IsLetter(c) || unicode.IsNumber(c) || strings.ContainsRune("_,.+%$#@!?~/-", c)) {
			return false
		}
	}
	lower := strings.ToLower(s)
	for _, ext := range imageExts {
		if strings.HasSuffix(lower, "."+ext) && len(lower) > len(ext)+1 {
			return true
		}
	}
	return false
}

const urlChars = "A-Za-z0-9%._/~:,=$@&+-"

var (
	linkTargetRe = regexp.MustCompile(`(?i)^(?:(?:https?|ftp|news|telnet|gopher|wais)://[` + urlChars + `]+/*(?:\?[A-Za-z0-9/%&=+:;.,$@*_-]+)?(?:#[\p{L}\p{N}_%.-]*)?|[` + urlChars + `]+|[` + urlChars + `]*#[\p{L}\p{N}_%.-]*)$`)
	guessURLRe   = regexp.MustCompile(`(?i)^(?:(www[23]?)|ftp)\.`)
	emailRe      = regexp.MustCompile(`(?i)^[A-Za-z0-9_.-]+@(?:[A-Za-z0-9_-]+\.)+[A-Za-z]{2,4}(?:\?[A-Za-z0-9/%&=+:;.,$@*_-]+)?$`)
)

// looksLikeURL reports what may follow the label in "[label target]": an
// address with a protocol (and its query and anchor), an e-mail, or a file
// name or "#anchor" -- the reference calls anything made of URL characters
// a link.
func looksLikeURL(s string) bool { return linkTargetRe.MatchString(s) }

// linkURL is the address a link really points to: www.x.org is
// http://www.x.org, ftp.x.org is ftp://ftp.x.org, a@b.org is mailto:a@b.org.
func linkURL(target string) string {
	if m := guessURLRe.FindStringSubmatch(target); m != nil {
		if m[1] != "" {
			return "http://" + target
		}
		return "ftp://" + target
	}
	if emailRe.MatchString(target) {
		return "mailto:" + target
	}
	return target
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

// inlineFmt is everything the inline pipeline needs to know about one output
// format. escape is applied to ordinary text before marks are matched,
// literal to a character the author protected with a backslash (the two
// differ for Markdown, where "*" must survive until the marks are applied
// but a protected "\*" must come out escaped).
type inlineFmt struct {
	escape  func(string) string
	literal func(rune) string
	delims  []delim
	link    func(label, url string) string
	// autolink is for a link found in the text without a label of its own
	autolink func(label, url string) string
	image    func(src string) string
	// monoVerbatim: ``mono`` spans are copied as they are (no marks, no
	// escapes inside)
	monoVerbatim bool
}

// Runs the escape+mark pipeline (but not link/image extraction -- nested
// links aren't supported) over a link label or bare-URL text, reusing the
// same protectEscapes() lookup table as the surrounding text.
//
// Bare addresses in the text are kept out of the marks ("//" in a URL is not
// italic).
func inlineLabel(protectedText string, escaped []rune, f *inlineFmt) string {
	const urlToken = "\x03"
	chars := []rune(protectedText)
	var masked strings.Builder
	var urls []string
	for i := 0; i < len(chars); {
		if looksLikeAutolinkStart(chars, i) {
			j := autolinkEnd(chars, i)
			urls = append(urls, string(chars[i:j]))
			masked.WriteString(urlToken + strconv.Itoa(len(urls)) + urlToken)
			i = j
		} else {
			masked.WriteRune(chars[i])
			i++
		}
	}
	out := applyMarks(f.escape(masked.String()), f.delims)
	for n, url := range urls {
		out = strings.Replace(out, urlToken+strconv.Itoa(n+1)+urlToken, f.escape(url), 1)
	}
	return restoreEscapes(out, escaped, f.literal)
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
func renderBracket(content string, escaped []rune, f *inlineFmt) (string, bool) {
	content = strings.TrimSpace(content)
	if content == "" {
		return "", false
	}
	// [label target]
	if idx := strings.LastIndex(content, " "); idx >= 0 {
		target := strings.TrimSpace(content[idx+1:])
		labelPart := strings.TrimSpace(content[:idx])
		if !looksLikeURL(target) {
			return "", false
		}
		return f.link(inlineLabel(labelPart, escaped, f), linkURL(target)), true
	}
	// [image.ext]
	if looksLikeImage(content) {
		return f.image(content), true
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
func findLinkRender(chars []rune, outerOpen int, f *inlineFmt) (rendered string, consumedTo int, ok bool) {
	renderLink, renderImage := f.link, f.image
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
	return renderLink(renderImage(innerTrim), linkURL(target)), outerClose + 1, true
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
	if i > 0 && (unicode.IsLetter(chars[i-1]) || unicode.IsNumber(chars[i-1]) || chars[i-1] == '_') {
		return false
	}
	// the address must go on with at least one more character
	more := func(n int) bool {
		if i+n >= len(chars) {
			return false
		}
		c := chars[i+n]
		return c < 128 && (unicode.IsLetter(c) || unicode.IsNumber(c))
	}
	for _, p := range []string{"http://", "https://", "ftp://", "news://", "telnet://", "gopher://", "wais://",
		// www.x.org and ftp.x.org, without a protocol
		"www.", "www2.", "www3.", "ftp."} {
		if startsWithAt(chars, i, p) && more(len(p)) {
			return true
		}
	}
	return false
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

// literalSpan finds a ""raw"" (escaped for the target, no marks) or
// ”tagged” (passed through) span starting at i, and the index just after
// it. The text between the marks may not start or end with a space; extra
// marker characters next to the closing mark belong to the text.
func literalSpan(chars []rune, i int, escaped []rune, f *inlineFmt) (string, int, bool) {
	q := chars[i]
	if (q != '"' && q != '\'') || i+1 >= len(chars) || chars[i+1] != q {
		return "", 0, false
	}
	for j := i + 3; j+1 < len(chars); j++ {
		if chars[j] != q || chars[j+1] != q {
			continue
		}
		if unicode.IsSpace(chars[i+2]) || unicode.IsSpace(chars[j-1]) {
			continue
		}
		for j+2 < len(chars) && chars[j+2] == q {
			j++
		}
		content := string(chars[i+2 : j])
		var rendered string
		if q == '"' {
			rendered = restoreEscapes(f.escape(content), escaped, f.literal)
		} else {
			rendered = restoreEscapes(content, escaped, func(r rune) string { return string(r) })
		}
		return rendered, j + 2, true
	}
	return "", 0, false
}

// monoSpan finds a “mono“ span starting at i, copied as it is, and the
// index just after it.
func monoSpan(chars []rune, i int, escaped []rune) (string, int, bool) {
	if chars[i] != '`' || i+1 >= len(chars) || chars[i+1] != '`' {
		return "", 0, false
	}
	for j := i + 3; j+1 < len(chars); j++ {
		if chars[j] != '`' || chars[j+1] != '`' {
			continue
		}
		if unicode.IsSpace(chars[i+2]) || unicode.IsSpace(chars[j-1]) {
			continue
		}
		for j+2 < len(chars) && chars[j+2] == '`' {
			j++
		}
		body := restoreEscapes(string(chars[i+2:j]), escaped, func(r rune) string { return string(r) })
		return "`" + body + "`", j + 2, true
	}
	return "", 0, false
}

// Scans (already protectEscapes'd) text for "[label URL]"/"[image.ext]"
// brackets and bare autolinks, replacing each with a numbered
// placeholderLink token. Returns the token-substituted text plus the list
// of fully rendered replacements, indexed by token number - 1.
func extractLinksImages(s string, escaped []rune, f *inlineFmt) (string, []string) {
	chars := []rune(s)
	var out strings.Builder
	var items []string
	i := 0
	for i < len(chars) {
		c := chars[i]
		rendered, next, ok := literalSpan(chars, i, escaped, f)
		if !ok && f.monoVerbatim {
			rendered, next, ok = monoSpan(chars, i, escaped)
		}
		if ok {
			items = append(items, rendered)
			out.WriteString(placeholderLink)
			out.WriteString(strconv.Itoa(len(items)))
			out.WriteString(placeholderLink)
			i = next
			continue
		}
		if c == '[' {
			if i+1 < len(chars) && chars[i+1] == '[' {
				if rendered, consumedTo, ok := findLinkRender(chars, i, f); ok {
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
					if rendered, ok := renderBracket(content, escaped, f); ok {
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
			label := inlineLabel(word, escaped, f)
			items = append(items, f.autolink(label, linkURL(word)))
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

func inlineFormatWith(text string, f *inlineFmt) string {
	protected, escaped := protectEscapes(expandInlineMacros(text))
	linked, items := extractLinksImages(protected, escaped, f)
	marked := applyMarks(f.escape(linked), f.delims)
	restored := restoreEscapes(marked, escaped, f.literal)
	return restoreLinkPlaceholders(restored, items)
}

var htmlFmt = &inlineFmt{htmlEscape, htmlEscapeChar, htmlDelims, htmlLink, htmlLink, htmlImage, false}
var latexFmt = &inlineFmt{latexEscape, latexEscapeChar, latexDelims, latexLink, latexLink, latexImage, false}
var mdFmt = &inlineFmt{mdEscape, mdLiteral, mdDelims, mdLink, mdAutolink, mdImage, true}

func inlineFormatHTML(text string) string  { return inlineFormatWith(text, htmlFmt) }
func inlineFormatLatex(text string) string { return inlineFormatWith(text, latexFmt) }
func inlineFormatMD(text string) string    { return inlineFormatWith(text, mdFmt) }

// ── Markdown inline ──────────────────────────────────────────────────────

var mdDelims = []delim{
	{"**", "**", "**"},
	{"//", "*", "*"},
	{"__", "", ""},
	{"--", "~~", "~~"},
	{"``", "`", "`"},
}

func isWordRune(r rune, ok bool) bool {
	return ok && (unicode.IsLetter(r) || unicode.IsNumber(r) || r == '_')
}

// mdEscape keeps literal text from being read as Markdown. The doubled
// marks (**, “) are txt2tags marks, so only the single characters are
// escaped; the content of a “mono“ span is left alone. Runs on one line
// at a time, before the marks are turned into Markdown syntax.
func mdEscape(s string) string {
	chars := []rune(s)
	var out strings.Builder
	at := func(i int) (rune, bool) {
		if i >= 0 && i < len(chars) {
			return chars[i], true
		}
		return 0, false
	}
	// line-start escapes: "# " headings and "1. " lists
	lead := 0
	for lead < len(chars) && unicode.IsSpace(chars[lead]) {
		lead++
	}
	escAt, escHashes := -1, 0
	hashes := 0
	for lead+hashes < len(chars) && chars[lead+hashes] == '#' {
		hashes++
	}
	if next, ok := at(lead + hashes); hashes >= 1 && hashes <= 6 && (!ok || unicode.IsSpace(next)) {
		escAt, escHashes = lead, hashes
	} else {
		j := lead
		for j < len(chars) && chars[j] >= '0' && chars[j] <= '9' {
			j++
		}
		dot, okDot := at(j)
		after, okAfter := at(j + 1)
		if j > lead && okDot && dot == '.' && okAfter && unicode.IsSpace(after) {
			escAt = j
		}
	}
	i := 0
	for i < len(chars) {
		c := chars[i]
		prev, hasPrev := at(i - 1)
		next, hasNext := at(i + 1)
		if i == escAt {
			if escHashes > 0 {
				out.WriteString("\\")
				out.WriteString(strings.Repeat("#", escHashes))
				i += escHashes
			} else {
				out.WriteString("\\.")
				i++
			}
			continue
		}
		if c == '`' && hasNext && next == '`' {
			// copy a ``mono`` span untouched
			closeAt := -1
			for k := i + 3; k+1 < len(chars); k++ {
				if chars[k] == '`' && chars[k+1] == '`' {
					closeAt = k
					break
				}
			}
			if closeAt >= 0 {
				out.WriteString(string(chars[i : closeAt+2]))
				i = closeAt + 2
			} else {
				out.WriteString("``")
				i += 2
			}
			continue
		}
		switch {
		case c == '*' && !(hasPrev && prev == '*') && !(hasNext && next == '*'):
			out.WriteString("\\*")
		case c == '`' && !(hasPrev && prev == '`') && !(hasNext && next == '`'):
			out.WriteString("\\`")
		case c == '_' && !(hasPrev && prev == '_') && !(hasNext && next == '_') &&
			(!isWordRune(prev, hasPrev) || !isWordRune(next, hasNext)):
			out.WriteString("\\_")
		case c == '<' || c == '>':
			out.WriteRune('\\')
			out.WriteRune(c)
		default:
			out.WriteRune(c)
		}
		i++
	}
	return out.String()
}

// mdLiteral is a character the author protected with a backslash, as Markdown.
func mdLiteral(c rune) string {
	if strings.ContainsRune("\\`*_[]()#<>~|!", c) {
		return "\\" + string(c)
	}
	return string(c)
}

func mdURL(url string) string {
	return strings.NewReplacer(" ", "%20", "(", "%28", ")", "%29").Replace(url)
}

func mdLink(label, url string) string {
	return "[" + label + "](" + mdURL(url) + ")"
}

func mdAutolink(label, url string) string {
	if label == url || label == mdEscape(url) {
		// a bare address is a link by itself
		return url
	}
	return mdLink(label, url)
}
func mdImage(src string) string { return "![](" + mdURL(src) + ")" }

// ── block parsing ────────────────────────────────────────────────────────

func parseBody(lines []string) []Block {
	var blocks []Block
	n := len(lines)
	i := 0
	// After a verbatim, raw or tagged block interrupts a list, the plain text
	// that follows (one blank line at most) still belongs to its last item.
	listCtx := -1 // indent of that text, -1 when no list is waiting
	endedByBlock := -1
	blankRun := 0
	seen := 0

	for i < n {
		if len(blocks) > seen {
			// what the block that was just read means for the text after it
			switch blocks[len(blocks)-1].Kind {
			case blockVerbatim, blockRaw, blockTagged:
			case blockListText:
				listCtx = blocks[len(blocks)-1].Pad
			case blockList:
				listCtx = endedByBlock
			default:
				listCtx = -1
			}
			endedByBlock = -1
			blankRun = 0
			seen = len(blocks)
		}
		line := lines[i]

		if strings.TrimSpace(line) == "" {
			blankRun++
			if blankRun >= 2 {
				listCtx = -1
			}
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
			blocks = append(blocks, Block{Kind: blockHeading, Level: level, Text: text, Numbered: strings.HasPrefix(strings.TrimSpace(line), "+")})
			i++
			continue
		}
		if isHr(line) {
			blocks = append(blocks, Block{Kind: blockHr})
			i++
			continue
		}
		if kind, rest, ok := oneLineBlock(line); ok {
			blocks = append(blocks, Block{Kind: kind, Lines: []string{rest}})
			i++
			continue
		}
		if isFence(line, "```") {
			i++
			var vlines []string
			for i < n && !isFence(lines[i], "```") {
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
		if isFence(line, `'''`) {
			i++
			var tlines []string
			for i < n && !isFence(lines[i], `'''`) {
				tlines = append(tlines, lines[i])
				i++
			}
			if i < n {
				i++
			}
			blocks = append(blocks, Block{Kind: blockTagged, Lines: tlines})
			continue
		}
		if strings.HasPrefix(line, "\t") {
			var q []QuoteLine
			for i < n && strings.HasPrefix(lines[i], "\t") {
				depth := len(lines[i]) - len(strings.TrimLeft(lines[i], "\t"))
				q = append(q, QuoteLine{Depth: depth, Text: strings.TrimSpace(lines[i])})
				i++
			}
			blocks = append(blocks, Block{Kind: blockQuote, Quote: q})
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
					// a list item keeps its indent: it opens a sublist
					if _, _, _, isItem := isListItem(lines[i]); isItem && strings.HasPrefix(lines[i], " ") {
						def = append(def, strings.TrimRight(lines[i], " \t"))
					} else {
						def = append(def, strings.TrimSpace(lines[i]))
					}
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
			blanks := 0
		listLoop:
			for i < n {
				l := lines[i]
				switch {
				case strings.TrimSpace(l) == "":
					blanks++
					i++
					// two blank lines end a list
					if blanks >= 2 {
						break listLoop
					}
				case isComment(l):
					i++
				case !strings.HasPrefix(l, " ") && isHeadingLine(l):
					break listLoop
				default:
					if kind, lvl, txt, ok2 := isListItem(l); ok2 {
						items = append(items, ListItem{Kind: kind, Level: lvl, Text: txt, BlankBefore: blanks > 0})
						blanks = 0
						i++
					} else if startsBlock(l) {
						if _, _, ok := oneLineBlock(l); ok || isFence(l, "```") || isFence(l, `"""`) || isFence(l, `'''`) {
							endedByBlock = 0
						}
						break listLoop
					} else {
						// plain text keeps the item going (after one blank
						// line it is a new paragraph of the item), as in the
						// reference
						last := &items[len(items)-1]
						last.Text += "\n"
						if blanks > 0 {
							last.Text += "\n"
						}
						last.Text += strings.TrimSpace(l)
						blanks = 0
						i++
					}
				}
			}
			normalizeListLevels(items)
			if endedByBlock >= 0 {
				last := items[len(items)-1]
				width := 2
				if last.Kind == Ol {
					width = 3
				}
				endedByBlock = 4*last.Level + width
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
			if isFence(l, "```") || isFence(l, `"""`) || isFence(l, `'''`) {
				break
			}
			if _, _, ok := oneLineBlock(l); ok {
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
			if strings.HasPrefix(l, "\t") {
				break
			}
			plines = append(plines, strings.TrimSpace(l))
			i++
		}
		if listCtx >= 0 {
			blocks = append(blocks, Block{Kind: blockListText, Lines: plines, Pad: listCtx})
		} else {
			blocks = append(blocks, Block{Kind: blockPara, Lines: plines})
		}
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
			out = append(out, "<li>"+inlineFormatHTML(flatItemText(items[i].Text)))
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

// renderCtx is what the renderers need to know beyond the block itself.
type renderCtx struct {
	blocks []Block
	hasToc bool
	// "1. ", "1.1. " ... per block index (empty when titles aren't numbered)
	numbers []string
	// deepest heading level listed in the table of contents
	tocLevel int
	tocTitle string
	// GitHub-style heading anchors per block index (Markdown only)
	slugs []string
}

func (c *renderCtx) number(i int) string {
	if i < len(c.numbers) {
		return c.numbers[i]
	}
	return ""
}

func headingNumbers(blocks []Block, all bool) []string {
	var counters [6]int
	out := make([]string, len(blocks))
	for i, b := range blocks {
		if b.Kind != blockHeading || !(all || b.Numbered) {
			continue
		}
		l := b.Level
		if l < 1 {
			l = 1
		}
		if l > 6 {
			l = 6
		}
		counters[l-1]++
		for k := l; k < 6; k++ {
			counters[k] = 0
		}
		parts := make([]string, l)
		for k := 0; k < l; k++ {
			parts[k] = strconv.Itoa(counters[k])
		}
		out[i] = strings.Join(parts, ".") + ". "
	}
	return out
}

// A table of contents is only meaningful (and its heading anchors only
// added) when the document actually contains a %%toc -- so plain
// documents render byte-identical headings.
func renderTocHTML(ctx *renderCtx) string {
	var out []string
	if ctx.tocTitle != "" {
		out = append(out, `<p class="toc-title">`+htmlEscape(ctx.tocTitle)+`</p>`)
	}
	out = append(out, `<ul class="toc">`)
	for i, b := range ctx.blocks {
		if b.Kind == blockHeading && b.Level <= ctx.tocLevel {
			h := strconv.Itoa(b.Level)
			out = append(out, `<li class="toc-h`+h+`"><a href="#t2t-`+strconv.Itoa(i)+`">`+ctx.number(i)+inlineFormatHTML(b.Text)+`</a></li>`)
		}
	}
	out = append(out, "</ul>")
	return strings.Join(out, "\n")
}

func renderBlockHTML(b Block, index int, ctx *renderCtx) string {
	switch b.Kind {
	case blockHeading:
		h := strconv.Itoa(b.Level)
		num := ctx.number(index)
		if ctx.hasToc {
			return "<h" + h + ` id="t2t-` + strconv.Itoa(index) + `">` + num + inlineFormatHTML(b.Text) + "</h" + h + ">"
		}
		return "<h" + h + ">" + num + inlineFormatHTML(b.Text) + "</h" + h + ">"
	case blockHr:
		return "<hr>"
	case blockQuote:
		var out []string
		cur := 0
		for _, q := range b.Quote {
			for cur < q.Depth {
				out = append(out, "<blockquote>")
				cur++
			}
			for cur > q.Depth {
				out = append(out, "</blockquote>")
				cur--
			}
			out = append(out, inlineFormatHTML(q.Text))
		}
		for cur > 0 {
			out = append(out, "</blockquote>")
			cur--
		}
		return strings.Join(out, "\n")
	case blockPara, blockListText:
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
		return renderTocHTML(ctx)
	case blockRaw:
		return strings.Join(mapLines(b.Lines, htmlEscape), "\n")
	case blockTagged:
		return strings.Join(b.Lines, "\n")
	case blockDefList:
		out := []string{"<dl>"}
		for _, d := range b.Defs {
			out = append(out, "<dt>"+inlineFormatHTML(d.Term)+"</dt>")
			for _, line := range d.Defs {
				out = append(out, "<dd>"+inlineFormatHTML(strings.TrimSpace(line))+"</dd>")
			}
		}
		out = append(out, "</dl>")
		return strings.Join(out, "\n")
	}
	return ""
}

func renderHTML(title, author, date string, ctx *renderCtx, headers bool) string {
	var out []string
	if !headers {
		for i, b := range ctx.blocks {
			out = append(out, renderBlockHTML(b, i, ctx))
		}
		return strings.Join(out, "\n")
	}
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
	for i, b := range ctx.blocks {
		out = append(out, renderBlockHTML(b, i, ctx))
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
			out = append(out, "\\item "+inlineFormatLatex(flatItemText(items[i].Text)))
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

func renderBlockLatex(b Block, ctx *renderCtx) string {
	switch b.Kind {
	case blockHeading:
		cmd := headingCommand(b.Level)
		return "\\" + cmd + "{" + inlineFormatLatex(b.Text) + "}"
	case blockHr:
		return "\\par\\noindent\\hrulefill\\par"
	case blockQuote:
		var out []string
		cur := 0
		for _, q := range b.Quote {
			for cur < q.Depth {
				out = append(out, "\\begin{quote}")
				cur++
			}
			for cur > q.Depth {
				out = append(out, "\\end{quote}")
				cur--
			}
			out = append(out, inlineFormatLatex(q.Text))
		}
		for cur > 0 {
			out = append(out, "\\end{quote}")
			cur--
		}
		return strings.Join(out, "\n")
	case blockPara, blockListText:
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
		var out []string
		if ctx.tocTitle != "" {
			out = append(out, "\\renewcommand{\\contentsname}{"+latexEscape(ctx.tocTitle)+"}")
		}
		if ctx.tocLevel != math.MaxInt {
			out = append(out, "\\setcounter{tocdepth}{"+strconv.Itoa(ctx.tocLevel)+"}")
		}
		out = append(out, "\\tableofcontents")
		return strings.Join(out, "\n")
	case blockRaw:
		return strings.Join(mapLines(b.Lines, latexEscape), "\n")
	case blockTagged:
		return strings.Join(b.Lines, "\n")
	case blockDefList:
		out := []string{"\\begin{description}"}
		for _, d := range b.Defs {
			defs := make([]string, len(d.Defs))
			for i, line := range d.Defs {
				defs[i] = inlineFormatLatex(strings.TrimSpace(line))
			}
			out = append(out, "\\item["+inlineFormatLatex(d.Term)+"] "+strings.Join(defs, " "))
		}
		out = append(out, "\\end{description}")
		return strings.Join(out, "\n")
	}
	return ""
}

func renderLatex(title, author, date string, ctx *renderCtx, headers bool) string {
	var out []string
	if !headers {
		for _, b := range ctx.blocks {
			out = append(out, renderBlockLatex(b, ctx))
		}
		return strings.Join(out, "\n")
	}
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
	for _, b := range ctx.blocks {
		out = append(out, renderBlockLatex(b, ctx))
	}
	out = append(out, "\\end{document}")
	return strings.Join(out, "\n")
}

// ── Markdown rendering ───────────────────────────────────────────────────

var (
	mdImageRe = regexp.MustCompile(`!\[\]\([^)]*\)`)
	mdLinkRe  = regexp.MustCompile(`\[([^\]]*)\]\([^)]*\)`)
)

// mdStripLinks gives link text for the table of contents: keeps the marks,
// drops nested links (a link cannot contain a link).
func mdStripLinks(s string) string {
	return mdLinkRe.ReplaceAllString(mdImageRe.ReplaceAllString(s, ""), "${1}")
}

// githubSlug is GitHub's anchor for a heading: lowercase, spaces to
// hyphens, anything but letters, digits, "-" and "_" dropped.
func githubSlug(headingMD string) string {
	var b strings.Builder
	for _, c := range mdStripLinks(headingMD) {
		if strings.ContainsRune("\\*`~", c) {
			continue
		}
		c = unicode.ToLower(c)
		switch {
		case unicode.IsLetter(c) || unicode.IsNumber(c) || c == '-' || c == '_':
			b.WriteRune(c)
		case unicode.IsSpace(c):
			b.WriteRune('-')
		}
	}
	return b.String()
}

func markdownSlugs(blocks []Block, numbers []string) []string {
	seen := map[string]int{}
	out := make([]string, len(blocks))
	for i, b := range blocks {
		if b.Kind != blockHeading {
			continue
		}
		num := ""
		if i < len(numbers) {
			num = numbers[i]
		}
		base := githubSlug(num + inlineFormatMD(b.Text))
		n := seen[base]
		out[i] = base
		if n > 0 {
			out[i] = base + "-" + strconv.Itoa(n)
		}
		seen[base] = n + 1
	}
	return out
}

func renderTocMD(ctx *renderCtx) string {
	var idx []int
	min := math.MaxInt
	for i, b := range ctx.blocks {
		if b.Kind == blockHeading && b.Level <= ctx.tocLevel {
			idx = append(idx, i)
			if b.Level < min {
				min = b.Level
			}
		}
	}
	// the entries are a list indented by title level, so they nest the way
	// the list rules nest items (a title level skipped or left halfway
	// joins the list that is open)
	shape := make([]ListItem, len(idx))
	for k, i := range idx {
		shape[k] = ListItem{Kind: Ul, Level: ctx.blocks[i].Level * 2}
	}
	normalizeListLevels(shape)
	var out []string
	for k, i := range idx {
		b := ctx.blocks[i]
		if shape[k].BlankBefore {
			out = append(out, "")
		}
		out = append(out, strings.Repeat("    ", shape[k].Level)+"* ["+tocNumber(ctx.number(i))+mdStripLinks(inlineFormatMD(b.Text))+"](#"+ctx.slugs[i]+")")
	}
	list := strings.Join(out, "\n")
	if ctx.tocTitle == "" {
		return list
	}
	return "**" + inlineFormatMD(ctx.tocTitle) + "**\n\n" + list
}

func mdCell(text string) string {
	return strings.ReplaceAll(inlineFormatMD(text), "|", "\\|")
}

func renderTableMD(rows []TableRow) string {
	ncols := 0
	if len(rows) > 0 {
		ncols = len(rows[0].Cells)
	}
	if ncols == 0 {
		return ""
	}
	line := func(cells []string) string {
		return "| " + strings.Join(cells, " | ") + " |"
	}
	sep := make([]string, ncols)
	for c := range sep {
		sep[c] = "---"
		if c < len(rows[0].Cells) {
			switch rows[0].Cells[c].Align {
			case AlignCenter:
				sep[c] = ":---:"
			case AlignRight:
				sep[c] = "---:"
			}
		}
	}
	var out []string
	bodyFrom := 0
	if rows[0].Header {
		cells := make([]string, len(rows[0].Cells))
		for i, c := range rows[0].Cells {
			cells[i] = mdCell(c.Text)
		}
		out = append(out, line(cells))
		bodyFrom = 1
	} else {
		// GFM needs a header row; an empty one keeps the table a table
		out = append(out, line(make([]string, ncols)))
	}
	out = append(out, "|"+strings.Join(sep, "|")+"|")
	for _, row := range rows[bodyFrom:] {
		cells := make([]string, len(row.Cells))
		for i, c := range row.Cells {
			cells[i] = mdCell(c.Text)
		}
		out = append(out, line(cells))
	}
	return strings.Join(out, "\n")
}

func renderListMD(items []ListItem) string { return renderListMDAt(items, 0) }

// renderListMDAt renders a list that is already nested base levels deep.
func renderListMDAt(items []ListItem, base int) string {
	var stack []int
	var out []string
	havePrev := false
	var prevKind ListKind
	prevDepth := 0
	for _, item := range items {
		for len(stack) > 0 && item.Level < stack[len(stack)-1] {
			stack = stack[:len(stack)-1]
		}
		if len(stack) == 0 || item.Level > stack[len(stack)-1] {
			stack = append(stack, item.Level)
		}
		depth := len(stack) - 1
		marker, width := "* ", 2
		if item.Kind == Ol {
			marker, width = "1. ", 3
		}
		// a blank line in the source stays one, and so does a change of
		// list kind at the top level (two lists)
		kindSwitch := depth == 0 && havePrev && prevDepth == 0 && prevKind != item.Kind
		if (item.BlankBefore && havePrev) || kindSwitch {
			out = append(out, "")
		}
		prevKind, prevDepth, havePrev = item.Kind, depth, true
		pad := strings.Repeat("    ", depth+base)
		lines := strings.Split(item.Text, "\n")
		out = append(out, pad+marker+inlineFormatMD(lines[0]))
		for _, l := range lines[1:] {
			if l == "" {
				out = append(out, "")
			} else {
				out = append(out, pad+strings.Repeat(" ", width)+inlineFormatMD(l))
			}
		}
	}
	return strings.Join(out, "\n")
}

// renderDefMD renders the definition lines of a deflist item; list items
// among them form a sublist of the deflist, one level down.
func renderDefMD(defs []string) string {
	var out []string
	for k := 0; k < len(defs); {
		if _, _, _, ok := isListItem(defs[k]); ok && strings.HasPrefix(defs[k], " ") {
			var items []ListItem
			for k < len(defs) && strings.HasPrefix(defs[k], " ") {
				kind, level, text, ok := isListItem(defs[k])
				if !ok {
					break
				}
				items = append(items, ListItem{Kind: kind, Level: level, Text: text})
				k++
			}
			normalizeListLevels(items)
			out = append(out, renderListMDAt(items, 1))
		} else {
			out = append(out, inlineFormatMD(defs[k]))
			k++
		}
	}
	return strings.Join(out, "\n")
}

func renderBlockMD(b Block, index int, ctx *renderCtx) string {
	switch b.Kind {
	case blockHeading:
		level := b.Level
		if level < 1 {
			level = 1
		}
		if level > 6 {
			level = 6
		}
		return strings.Repeat("#", level) + " " + ctx.number(index) + inlineFormatMD(b.Text)
	case blockHr:
		return "---"
	case blockQuote:
		var out []string
		for _, q := range b.Quote {
			out = append(out, strings.Repeat("> ", q.Depth)+inlineFormatMD(q.Text))
		}
		return strings.Join(out, "\n")
	case blockPara:
		formatted := make([]string, len(b.Lines))
		for i, l := range b.Lines {
			formatted[i] = inlineFormatMD(l)
		}
		return strings.Join(formatted, "\n")
	case blockListText:
		formatted := make([]string, len(b.Lines))
		for i, l := range b.Lines {
			formatted[i] = strings.Repeat(" ", b.Pad) + inlineFormatMD(l)
		}
		return strings.Join(formatted, "\n")
	case blockList:
		return renderListMD(b.Items)
	case blockTable:
		return renderTableMD(b.Rows)
	case blockToc:
		return renderTocMD(ctx)
	case blockVerbatim:
		// a fence longer than any backtick run inside, so nothing in the
		// code can close it (and a list before it cannot swallow it)
		longest := 0
		for _, l := range b.Lines {
			run := 0
			for _, c := range l {
				if c == '`' {
					run++
					if run > longest {
						longest = run
					}
				} else {
					run = 0
				}
			}
		}
		if longest < 2 {
			longest = 2
		}
		fence := strings.Repeat("`", longest+1)
		return fence + "\n" + strings.Join(b.Lines, "\n") + "\n" + fence
	case blockRaw:
		return strings.Join(mapLines(b.Lines, mdEscape), "\n")
	case blockTagged:
		return strings.Join(b.Lines, "\n")
	case blockDefList:
		var items []string
		for _, d := range b.Defs {
			head := "**" + inlineFormatMD(d.Term) + "**"
			if len(d.Defs) == 0 {
				items = append(items, head+"  ")
				continue
			}
			items = append(items, head+"  \n"+renderDefMD(d.Defs))
		}
		return strings.Join(items, "\n\n")
	}
	return ""
}

func renderMarkdown(title, author, date string, ctx *renderCtx, headers bool) string {
	var parts []string
	if headers {
		if title != "" {
			parts = append(parts, "# "+inlineFormatMD(title))
		}
		var by []string
		for _, f := range []string{author, date} {
			if f != "" {
				by = append(by, inlineFormatMD(f))
			}
		}
		if len(by) > 0 {
			parts = append(parts, strings.Join(by, "  \n"))
		}
	}
	for i, b := range ctx.blocks {
		if r := renderBlockMD(b, i, ctx); r != "" {
			parts = append(parts, r)
		}
	}
	return strings.Join(parts, "\n\n")
}

// ── public API ───────────────────────────────────────────────────────────

// Target is an output format of Convert.
type Target int

const (
	TargetHTML Target = iota
	TargetLatex
	TargetMarkdown
)

// TargetFromName understands "html", "tex" (or "latex"), "md" (or "markdown").
func TargetFromName(name string) (Target, bool) {
	switch name {
	case "html":
		return TargetHTML, true
	case "tex", "latex":
		return TargetLatex, true
	case "md", "markdown":
		return TargetMarkdown, true
	}
	return TargetHTML, false
}

// Name is the short target name: html, tex or md.
func (t Target) Name() string {
	switch t {
	case TargetLatex:
		return "tex"
	case TargetMarkdown:
		return "md"
	}
	return "html"
}

// Extension is the file extension of the converted document.
func (t Target) Extension() string { return t.Name() }

// Options are the Python port's options that make sense here.
type Options struct {
	// NoHeaders (-H): no document wrapper, title or author/date, body only
	NoHeaders bool
	// Toc (--toc): add a table of contents at the top unless there is a %%toc
	Toc bool
	// TocLevel (--toc-level N): deepest heading level listed (0 = DefaultTocLevel)
	TocLevel int
	// TocTitle (--toc-title S)
	TocTitle string
	// TocOnly (--toc-only): print the table of contents and nothing else
	TocOnly bool
	// EnumTitle (-n): number the titles 1, 1.1, 1.1.1 (html and md)
	EnumTitle bool
	// SkipHeaderLines (--skip-header-lines): no title/author/date, the body
	// starts on line 1
	SkipHeaderLines bool
	// Infile and Outfile name the files %%infile, %%outfile and %%mtime
	// report
	Infile  string
	Outfile string
}

// ParseWith parses raw txt2tags source; with skipHeader the first three
// lines are not reserved for title/author/date.
func ParseWith(text string, skipHeader bool) Document {
	return parseWithEnv(text, skipHeader, MacroEnv{})
}

func parseWithEnv(text string, skipHeader bool, env MacroEnv) Document {
	lines := splitLines(text)
	head := parseHead(lines, skipHeader)
	bodyStart := head.bodyStart
	if bodyStart > len(lines) {
		bodyStart = len(lines)
	}
	bodyText := strings.Join(lines[bodyStart:], "\n")
	body := splitLines(applyLineRules(bodyText, head.preproc))
	return Document{
		Title: expandMacros(head.title, env), Author: expandMacros(head.author, env), Date: expandMacros(head.date, env),
		Blocks:   parseBody(body),
		postproc: head.postproc,
		options:  head.options,
	}
}

// Parse parses raw txt2tags source into a Document.
func Parse(text string) Document { return ParseWith(text, false) }

// Convert converts a txt2tags document. It fails only for an option the
// target cannot honour (TocOnly with LaTeX).
func Convert(text string, target Target, opts Options) (string, error) {
	targetName := map[Target]string{TargetHTML: "html", TargetLatex: "tex", TargetMarkdown: "md"}[target]
	convertMu.Lock()
	defer convertMu.Unlock()
	env := MacroEnv{Infile: opts.Infile, Outfile: opts.Outfile, Target: targetName}
	doc := parseWithEnv(text, opts.SkipHeaderLines, env)
	opts = mergeDocOptions(opts, doc.options, targetName)
	env.Headers = [3]string{doc.Title, doc.Author, doc.Date}
	currentMacros = env
	if opts.TocOnly && target == TargetLatex {
		return "", fmt.Errorf("--toc-only is not supported for the tex target")
	}
	hasTocBlock := func() bool {
		for _, b := range doc.Blocks {
			if b.Kind == blockToc {
				return true
			}
		}
		return false
	}
	// as in the Python port, %%toc only says where the table of contents goes
	// when --toc (or --toc-only) asks for one
	if !opts.Toc && !opts.TocOnly {
		kept := doc.Blocks[:0:0]
		for _, b := range doc.Blocks {
			if b.Kind != blockToc {
				kept = append(kept, b)
			}
		}
		doc.Blocks = kept
	} else if !hasTocBlock() {
		doc.Blocks = append([]Block{{Kind: blockToc}}, doc.Blocks...)
	}
	var numbers []string
	if target != TargetLatex {
		numbers = headingNumbers(doc.Blocks, opts.EnumTitle)
	}
	var slugs []string
	if target == TargetMarkdown {
		slugs = markdownSlugs(doc.Blocks, numbers)
	}
	tocLevel := opts.TocLevel
	if tocLevel <= 0 {
		tocLevel = DefaultTocLevel
	}
	ctx := &renderCtx{
		blocks:   doc.Blocks,
		hasToc:   hasTocBlock() || opts.TocOnly,
		numbers:  numbers,
		tocLevel: tocLevel,
		tocTitle: opts.TocTitle,
		slugs:    slugs,
	}
	headers := !opts.NoHeaders
	var out string
	switch {
	case opts.TocOnly && target == TargetHTML:
		out = renderTocHTML(ctx)
	case opts.TocOnly:
		out = renderTocMD(ctx)
	case target == TargetHTML:
		out = renderHTML(doc.Title, doc.Author, doc.Date, ctx, headers)
	case target == TargetLatex:
		out = renderLatex(doc.Title, doc.Author, doc.Date, ctx, headers)
	default:
		out = renderMarkdown(doc.Title, doc.Author, doc.Date, ctx, headers)
	}
	return applyLineRules(out, doc.postproc), nil
}

func mustConvert(text string, target Target) string {
	out, err := Convert(text, target, Options{})
	if err != nil {
		panic(err)
	}
	return out
}

// ToHTML converts raw txt2tags source directly to an HTML document string.
func ToHTML(text string) string { return mustConvert(text, TargetHTML) }

// ToLatex converts raw txt2tags source directly to a LaTeX document string.
func ToLatex(text string) string { return mustConvert(text, TargetLatex) }

// ToMarkdown converts raw txt2tags source directly to a Markdown string.
func ToMarkdown(text string) string { return mustConvert(text, TargetMarkdown) }

// tocNumber escapes the dot of a single-level number ("1. "), which would
// read as a list marker for the other ports' escaper.
func tocNumber(n string) string {
	if d, ok := strings.CutSuffix(n, ". "); ok && d != "" && strings.Trim(d, "0123456789") == "" {
		return d + "\\. "
	}
	return n
}
