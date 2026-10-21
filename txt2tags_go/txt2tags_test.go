// Adapted from txt2tags_rust/tests/convert.rs (itself adapted from
// txt2tags_lua/t/01_convert.lua / txt2tags_perl/t/07_convert.t): same
// idea (convert a small snippet, check the HTML/LaTeX fragment it
// produces) applied to the Go port, covering the same ground as the Rust
// suite: the simple tier, the LaTeX target, the %%date/%%toc macros, and
// the advanced-tier additions (links, images, verbatim/raw blocks, block
// comments, definition lists, table alignment, %!preproc/%!postproc).
// Alternate targets (txt/md) and quotes don't exist in this port.
//
// Run: go test ./...
package txt2tags

import (
	"strings"
	"testing"
)

// convert() in the Perl tests takes body lines directly, past head
// parsing; ToHTML only exposes the full document, so wrap a minimal
// 3-line head around each body snippet.
func convert(body string) string {
	return ToHTML("T\nA\nD\n\n" + body)
}

func tocWith(body string, target Target) string {
	out, err := Convert("T\nA\nD\n\n"+body, target, Options{Toc: true})
	if err != nil {
		panic(err)
	}
	return out
}

func tocHTML(body string) string  { return tocWith(body, TargetHTML) }
func tocLatex(body string) string { return tocWith(body, TargetLatex) }
func tocMd(body string) string    { return tocWith(body, TargetMarkdown) }

func TestTocMacroAlonePrintsNothing(t *testing.T) {
	out := convert("%%toc\n\n= One =")
	if strings.Contains(out, "toc") || !strings.Contains(out, "<h1>One</h1>") {
		t.Errorf("got %q", out)
	}
}

func convertLatex(body string) string {
	return ToLatex("T\nA\nD\n\n" + body)
}

func TestBold(t *testing.T) {
	if out := convert("**bold text**"); !strings.Contains(out, "<b>bold text</b>") {
		t.Errorf("got %q", out)
	}
}

func TestItalic(t *testing.T) {
	if out := convert("//italic text//"); !strings.Contains(out, "<i>italic text</i>") {
		t.Errorf("got %q", out)
	}
}

func TestUnderline(t *testing.T) {
	if out := convert("__underline text__"); !strings.Contains(out, "<u>underline text</u>") {
		t.Errorf("got %q", out)
	}
}

func TestStrike(t *testing.T) {
	if out := convert("--strike text--"); !strings.Contains(out, "<s>strike text</s>") {
		t.Errorf("got %q", out)
	}
}

func TestEscaping(t *testing.T) {
	// as in txt2tags, a backslash is plain text: the marks after it apply
	out := convert(`\**bold**`)
	if !strings.Contains(out, `\<b>bold</b>`) {
		t.Errorf("got %q", out)
	}
}

func TestTitlesAllLevels(t *testing.T) {
	cases := []struct{ in, want string }{
		{"= Hello =", "<h1>Hello</h1>"},
		{"== World ==", "<h2>World</h2>"},
		{"=== Three ===", "<h3>Three</h3>"},
		{"==== Four ====", "<h4>Four</h4>"},
		{"===== Five =====", "<h5>Five</h5>"},
	}
	for _, c := range cases {
		if out := convert(c.in); !strings.Contains(out, c.want) {
			t.Errorf("convert(%q): got %q, want substring %q", c.in, out, c.want)
		}
	}
}

func TestTitleTolerateSpaces(t *testing.T) {
	out := convert("   ===  Padded Title  ===   ")
	if !strings.Contains(out, "<h3>Padded Title</h3>") {
		t.Errorf("got %q", out)
	}
}

func TestUnbalancedEqualsIsNotATitle(t *testing.T) {
	// The document's own head still renders an <h1> for the "T" title
	// above, so check the body text specifically, not the mere tag.
	out := convert("=Not Title")
	if strings.Contains(out, "<h1>Not Title") {
		t.Errorf("got %q", out)
	}
	if !strings.Contains(out, "=Not Title") {
		t.Errorf("got %q", out)
	}
}

func TestHorizontalBar(t *testing.T) {
	if out := convert("--------------------"); !strings.Contains(out, "<hr>") {
		t.Errorf("got %q", out)
	}
}

func TestUnorderedList(t *testing.T) {
	out := convert("- apple\n- banana\n- cherry")
	for _, want := range []string{"<ul>", "<li>apple", "<li>banana", "</ul>"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
}

func TestNumberedList(t *testing.T) {
	out := convert("+ one\n+ two")
	for _, want := range []string{"<ol>", "<li>one", "</ol>"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
}

func TestListRequiresExactlyOneSpaceAfterMarker(t *testing.T) {
	if out := convert("-This is not a list"); strings.Contains(out, "<ul>") {
		t.Errorf("got %q", out)
	}
}

func TestNestedSublist(t *testing.T) {
	out := convert("- Level 1\n  - Level 2\n- Level 1 again")
	if !strings.Contains(out, "<ul>\n<li>Level 1") {
		t.Errorf("got %q", out)
	}
	if !strings.Contains(out, "<li>Level 2") {
		t.Errorf("got %q", out)
	}
}

func TestMixedListsDoNotMerge(t *testing.T) {
	out := convert("- a\n- b\n\n+ one\n+ two")
	if !strings.Contains(out, "<ul>") || !strings.Contains(out, "<ol>") {
		t.Errorf("got %q", out)
	}
}

func TestTableSimpleNoHeader(t *testing.T) {
	out := convert("| col A | col B |\n| val 1 | val 2 |")
	for _, want := range []string{"<table>", "<tr>", "<td>col A</td>", "<td>val 2</td>", "</table>"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
	if strings.Contains(out, "<th>") {
		t.Errorf("no header cell expected without ||, got %q", out)
	}
}

func TestTableDoublePipeMarksHeaderRow(t *testing.T) {
	out := convert("|| head 1 | head 2\n| cell 1 | cell 2")
	if !strings.Contains(out, "<th>head 1</th>") {
		t.Errorf("got %q", out)
	}
	if !strings.Contains(out, "<td>cell 1</td>") {
		t.Errorf("got %q", out)
	}
}

func TestTableInlineMarkupInCells(t *testing.T) {
	if out := convert("| **bold cell** |"); !strings.Contains(out, "<td><b>bold cell</b></td>") {
		t.Errorf("got %q", out)
	}
}

func TestBlankLineSeparatesTwoTables(t *testing.T) {
	out := convert("| a | b |\n\n| c | d |")
	if n := strings.Count(out, "<table>"); n != 2 {
		t.Errorf("expected 2 <table> tags, got %d in %q", n, out)
	}
}

func TestCommentLineDoesNotBreakSurroundingParagraph(t *testing.T) {
	out := convert("real text before\n% this is a comment\nreal text after")
	if strings.Contains(out, "this is a comment") {
		t.Errorf("comment should be suppressed, got %q", out)
	}
	if !strings.Contains(out, "real text before") || !strings.Contains(out, "real text after") {
		t.Errorf("got %q", out)
	}
}

func TestStandaloneCommentLine(t *testing.T) {
	out := convert("% just a comment\nreal text")
	if strings.Contains(out, "just a comment") {
		t.Errorf("comment should be suppressed, got %q", out)
	}
	if !strings.Contains(out, "real text") {
		t.Errorf("got %q", out)
	}
}

// --- verbatim blocks -----------------------------------------------------

func TestVerbatimBlockPreservesLiteralText(t *testing.T) {
	out := convert("```\nlet x = 1 < 2;\n**not bold**\n```")
	if !strings.Contains(out, "<pre>") {
		t.Errorf("missing <pre>, got %q", out)
	}
	if !strings.Contains(out, "let x = 1 &lt; 2;") {
		t.Errorf("expected entity-escaped content, got %q", out)
	}
	if !strings.Contains(out, "**not bold**") {
		t.Errorf("expected marks left literal, got %q", out)
	}
	if strings.Contains(out, "<b>") {
		t.Errorf("marks should not be interpreted in verbatim, got %q", out)
	}
}

func TestLatexVerbatimBlock(t *testing.T) {
	out := convertLatex("```\ncode & stuff\n```")
	for _, want := range []string{"\\begin{verbatim}", "code & stuff", "\\end{verbatim}"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
}

// --- links & images ------------------------------------------------------

func TestLinkWithLabel(t *testing.T) {
	out := convert("[Google http://google.com]")
	if !strings.Contains(out, "<a href=\"http://google.com\">Google</a>") {
		t.Errorf("got %q", out)
	}
}

func TestBareURLAutolink(t *testing.T) {
	out := convert("Visit http://example.com today")
	if !strings.Contains(out, "<a href=\"http://example.com\">http://example.com</a>") {
		t.Errorf("got %q", out)
	}
}

func TestImageReference(t *testing.T) {
	out := convert("[photo.png]")
	if !strings.Contains(out, "<img src=\"photo.png\" alt=\"\">") {
		t.Errorf("got %q", out)
	}
}

func TestImageNameBeforeAURLIsJustTheLabel(t *testing.T) {
	out := convert("[photo.png http://example.com]")
	mustContain(t, out, `<a href="http://example.com">photo.png</a>`)
}

func TestClassicNestedImageAsLink(t *testing.T) {
	out := convert("[[photo.jpg] http://example.com]")
	want := "<a href=\"http://example.com\"><img src=\"photo.jpg\" alt=\"\"></a>"
	if !strings.Contains(out, want) {
		t.Errorf("got %q", out)
	}
}

func TestBracketsThatAreNotALinkStayLiteral(t *testing.T) {
	mustContain(t, convert("[just]"), "[just]")
	mustContain(t, convert("[http://only.org]"), `[<a href="http://only.org">http://only.org</a>]`)
}

func TestAnyWordOfURLCharactersIsALinkTarget(t *testing.T) {
	// as in the reference: a file, an anchor, an e-mail, a guessed address
	out := convert("[see this] [top #top] [me a@b.org] [w www.x.org] [f ftp.x.org]")
	mustContain(t, out, `<a href="this">see</a>`)
	mustContain(t, out, `<a href="#top">top</a>`)
	mustContain(t, out, `<a href="mailto:a@b.org">me</a>`)
	mustContain(t, out, `<a href="http://www.x.org">w</a>`)
	mustContain(t, out, `<a href="ftp://ftp.x.org">f</a>`)
}

func TestWwwAndFtpAddressesAreLinksWithoutAProtocol(t *testing.T) {
	out := convert("go to www.x.org/p and ftp.y.org now")
	mustContain(t, out, `<a href="http://www.x.org/p">www.x.org/p</a>`)
	mustContain(t, out, `<a href="ftp://ftp.y.org">ftp.y.org</a>`)
}

func TestNestedBracketsDegradeWithoutMangling(t *testing.T) {
	// LionWiki-style [[label | URL]] double brackets are a different,
	// unsupported dialect -- this must not produce a broken/truncated
	// href, even though it isn't parsed as a clean link either.
	out := convert("[[Wiki | http://en.wikipedia.org/wiki/Wiki]]")
	if strings.Contains(out, "href=\"http://en.wikipedia.org/wiki/Wiki]\"") {
		t.Errorf("got mangled href: %q", out)
	}
}

func TestLatexLinkWithLabel(t *testing.T) {
	out := convertLatex("[Google http://google.com]")
	if !strings.Contains(out, "\\href{http://google.com}{Google}") {
		t.Errorf("got %q", out)
	}
}

func TestLatexImageReference(t *testing.T) {
	out := convertLatex("[photo.png]")
	if !strings.Contains(out, "\\includegraphics{photo.png}") {
		t.Errorf("got %q", out)
	}
}

// --- glued/greedy mark matching --------------------------------------------

func TestMarksGluedToWordsStillApply(t *testing.T) {
	// as in the reference, only the inside of a mark matters
	out := convert("The value is 2**3**4 here.")
	if !strings.Contains(out, "2<b>3</b>4") {
		t.Errorf("got %q", out)
	}
}

func TestMarksNextToPunctuationStillWork(t *testing.T) {
	out := convert("(**bold**)")
	if !strings.Contains(out, "(<b>bold</b>)") {
		t.Errorf("got %q", out)
	}
}

func TestConcatenatedURLsDoNotMangleWithSlashMarks(t *testing.T) {
	// Two "http://" runs glued together with no space (real-world case
	// from a LionWiki sample doc) must not have the "//" inside them
	// misread as italic markup.
	out := convert("[http://a.example/x|link=http://b.example/]")
	if strings.Contains(out, "<i>") {
		t.Errorf("URL slashes should not be read as italic marks, got %q", out)
	}
}

// --- LaTeX target ------------------------------------------------------

func TestLatexDocumentWrapper(t *testing.T) {
	out := convertLatex("hello")
	for _, want := range []string{"\\documentclass", "\\begin{document}", "\\end{document}"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
}

func TestLatexInlineMarksAndEscaping(t *testing.T) {
	out := convertLatex("**bold** & 100% //italic//")
	for _, want := range []string{"\\textbf{bold}", "\\&", "\\%", "\\textit{italic}"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
}

func TestLatexHeadingLevels(t *testing.T) {
	out := convertLatex("= H1 =\n\n== H2 ==\n\n=== H3 ===")
	for _, want := range []string{"\\section{H1}", "\\subsection{H2}", "\\subsubsection{H3}"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
}

func TestLatexList(t *testing.T) {
	out := convertLatex("- a\n- b")
	for _, want := range []string{"\\begin{itemize}", "\\item a", "\\item b", "\\end{itemize}"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
}

func TestLatexNumberedList(t *testing.T) {
	out := convertLatex("+ one\n+ two")
	for _, want := range []string{"\\begin{enumerate}", "\\item one", "\\end{enumerate}"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
}

func TestLatexTableWithHeader(t *testing.T) {
	out := convertLatex("|| h1 | h2\n| c1 | c2")
	for _, want := range []string{
		"\\begin{tabular}{ll}",
		"\\textbf{h1} & \\textbf{h2}",
		"\\hline",
		"c1 & c2",
		"\\end{tabular}",
	} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
}

// --- bare URL extent (reference URL character set) --------------------------

func TestBareURLStopsBeforeClosingBracket(t *testing.T) {
	out := convert("[see [1] http://x.org/a] end")
	if !strings.Contains(out, `<a href="http://x.org/a">http://x.org/a</a>]`) {
		t.Errorf("got %q", out)
	}
	if strings.Contains(out, `a]"`) {
		t.Errorf("']' leaked into the href: %q", out)
	}
}

func TestBareURLStopsAtOpenBracket(t *testing.T) {
	out := convert("http://x.org/j?a[1]=2")
	if !strings.Contains(out, `<a href="http://x.org/j?a">http://x.org/j?a</a>[1]=2`) {
		t.Errorf("got %q", out)
	}
}

func TestBareURLDropsTrailingPunctuation(t *testing.T) {
	out := convert("See http://x.org/page.")
	if !strings.Contains(out, `<a href="http://x.org/page">http://x.org/page</a>.`) {
		t.Errorf("got %q", out)
	}
}

func TestLatexClassicNestedImageAsLink(t *testing.T) {
	out := convertLatex("[[photo.jpg] http://example.com]")
	if !strings.Contains(out, `\href{http://example.com}{\includegraphics{photo.jpg}}`) {
		t.Errorf("got %q", out)
	}
}

func TestTitleToleratesSurroundingAndInnerSpaces(t *testing.T) {
	if out := convert("   ===  Padded Title  ===   "); !strings.Contains(out, "<h3>Padded Title</h3>") {
		t.Errorf("got %q", out)
	}
}

// --- block comments ---------------------------------------------------------

func TestBlockCommentIsFullySuppressed(t *testing.T) {
	out := convert("before\n\n%%%\nhidden one\nhidden two\n%%%\n\nafter")
	if !strings.Contains(out, "before") || !strings.Contains(out, "after") {
		t.Errorf("surrounding text lost: %q", out)
	}
	if strings.Contains(out, "hidden one") || strings.Contains(out, "hidden two") {
		t.Errorf("block comment leaked: %q", out)
	}
}

func TestBlockCommentEndsAParagraph(t *testing.T) {
	out := convert("real text\n%%%\nhidden\n%%%")
	if !strings.Contains(out, "real text") || strings.Contains(out, "hidden") {
		t.Errorf("got %q", out)
	}
}

// --- macros -----------------------------------------------------------------

func TestDateMacroExpandsInline(t *testing.T) {
	out := convert("Today is %%date.")
	if strings.Contains(out, "%%date") || !strings.Contains(out, "Today is "+TodayString()+".") {
		t.Errorf("got %q", out)
	}
}

func TestDateMacroExpandsInHeaderDateField(t *testing.T) {
	// The classic txt2tags idiom: the 3rd header line is literally "%%date".
	if out := ToHTML("T\nA\n%%date\n\nbody"); !strings.Contains(out, TodayString()) {
		t.Errorf("got %q", out)
	}
}

func TestTocListsHeadingsWithAnchors(t *testing.T) {
	out := tocHTML("%%toc\n\n= One =\n\n== Two ==")
	for _, want := range []string{`<ul class="toc">`, "toc-h1", "toc-h2", `href="#t2t-`, `id="t2t-`} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
}

func TestTocDoesNotAddHeadingIDsWhenAbsent(t *testing.T) {
	if out := convert("= One ="); strings.Contains(out, `id="t2t-`) {
		t.Errorf("got %q", out)
	}
}

func TestLatexTocUsesTableOfContents(t *testing.T) {
	if out := tocLatex("%%toc\n\n= One ="); !strings.Contains(out, `\tableofcontents`) {
		t.Errorf("got %q", out)
	}
}

// --- raw blocks, definition lists -------------------------------------------

func TestRawBlockIsEscapedWithoutMarks(t *testing.T) {
	out := convert("\"\"\"\n<b>raw</b> **x**\n\"\"\"")
	if !strings.Contains(out, "&lt;b&gt;raw&lt;/b&gt; **x**") {
		t.Errorf("got %q", out)
	}
}

func TestTaggedBlockPassesThroughUnmodified(t *testing.T) {
	if out := convert("'''\n<b>already html</b>\n'''"); !strings.Contains(out, "<b>already html</b>") {
		t.Errorf("got %q", out)
	}
}

func TestShortRulesAreNotHorizontalRules(t *testing.T) {
	if strings.Contains(convert("----"), "<hr>") {
		t.Error("4 dashes should not be a rule")
	}
	if !strings.Contains(convert("--------------------"), "<hr>") {
		t.Error("20 dashes should be a rule")
	}
}

func TestDefinitionList(t *testing.T) {
	out := convert(": Rust\n  A systems programming language.\n: Go\n  A language by Google.")
	for _, want := range []string{"<dl>", "<dt>Rust</dt>", "<dd>A systems programming language.</dd>", "<dt>Go</dt>", "</dl>"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
}

func TestLatexDefinitionList(t *testing.T) {
	out := convertLatex(": Rust\n  A systems language.")
	for _, want := range []string{`\begin{description}`, `\item[Rust] A systems language.`, `\end{description}`} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
}

// --- table alignment --------------------------------------------------------

func TestTableAlignmentInference(t *testing.T) {
	out := convert("|  right |  center  | left |")
	for _, want := range []string{
		`<td style="text-align:right">right</td>`,
		`<td style="text-align:center">center</td>`,
		`<td>left</td>`,
	} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in %q", want, out)
		}
	}
}

func TestLatexTableAlignmentInference(t *testing.T) {
	if out := convertLatex("|  right |  center  | left |"); !strings.Contains(out, `\begin{tabular}{rcl}`) {
		t.Errorf("got %q", out)
	}
}

// --- %!preproc / %!postproc -------------------------------------------------

func TestPreprocRewritesSourceBeforeParsing(t *testing.T) {
	out := ToHTML("T\nA\nD\n%!preproc: 'TODO' 'DONE'\n\nTODO: fix this")
	if !strings.Contains(out, "DONE: fix this") || strings.Contains(out, "TODO") {
		t.Errorf("got %q", out)
	}
}

func TestPostprocRewritesRenderedOutput(t *testing.T) {
	out := ToHTML("T\nA\nD\n%!postproc: '<p>' '<p class=\"x\">'\n\nhello")
	if !strings.Contains(out, `<p class="x">`) {
		t.Errorf("got %q", out)
	}
}

// ── Markdown target and options (same cases as the Rust suite) ───────────

func md(body string) string {
	return ToMarkdown("T\nA\nD\n\n" + body)
}

func mdWith(body string, opts Options) string {
	out, err := Convert("T\nA\nD\n\n"+body, TargetMarkdown, opts)
	if err != nil {
		panic(err)
	}
	return out
}

func mustContain(t *testing.T, out, want string) {
	t.Helper()
	if !strings.Contains(out, want) {
		t.Errorf("output does not contain %q:\n%s", want, out)
	}
}

func TestMdHeaderIsAHeadingThenAuthorAndDate(t *testing.T) {
	if out := md("text"); !strings.HasPrefix(out, "# T\n\nA  \nD\n\ntext") {
		t.Errorf("got %q", out)
	}
}

func TestMdMarks(t *testing.T) {
	lines := strings.Split(md("**b** //i// --s-- ``c`` __u__"), "\n")
	if got := lines[len(lines)-1]; got != "**b** *i* ~~s~~ `c` u" {
		t.Errorf("got %q", got)
	}
}

func TestMdEscapesLiteralTextButNotMono(t *testing.T) {
	mustContain(t, md("2*3*4 a < b\n1. no\n# no\n``a*b_c<d``"),
		"2\\*3\\*4 a \\< b\n1\\. no\n\\# no\n`a*b_c<d`")
}

func TestMdBackslashProtectedMark(t *testing.T) {
	mustContain(t, md("\\**bold**"), "\\\\**bold**")
}

func TestMdLinksAndImages(t *testing.T) {
	out := md("[txt http://x.org/a] [pic.png] [[pic.png] http://y.org] http://z.org/q.")
	mustContain(t, out, "[txt](http://x.org/a)")
	mustContain(t, out, "![](pic.png)")
	mustContain(t, out, "[![](pic.png)](http://y.org)")
	mustContain(t, out, " http://z.org/q.")
}

func TestMdNestedListsUseFourSpaces(t *testing.T) {
	mustContain(t, md("- a\n  - b\n    - c\n- d"), "* a\n    * b\n        * c\n* d")
}

func TestMdListKindSwitchStartsANewList(t *testing.T) {
	mustContain(t, md("- a\n+ b"), "* a\n\n1. b")
}

func TestMdDefinitionList(t *testing.T) {
	mustContain(t, md(": Term\n def one\n def two"), "**Term**  \ndef one\ndef two")
}

func TestMdTableWithHeaderAndAlignment(t *testing.T) {
	mustContain(t, md("|| a | b | c |\n| 1  |  2  |  3 |"), "| a | b | c |\n|---|---|---|\n| 1 | 2 | 3 |")
	mustContain(t, md("||  a  |  b|\n|  1  |  2|"), "|:---:|---:|")
}

func TestMdTableWithoutHeaderGetsAnEmptyOne(t *testing.T) {
	mustContain(t, md("| x | y |\n| z | w |"), "|  |  |\n|---|---|\n| x | y |")
}

func TestMdVerbatimUsesAFenceLongerThanItsContent(t *testing.T) {
	mustContain(t, md("```\na ``` b\n```"), "````\na ``` b\n````")
}

func TestMdRawBlockIsEscapedAndTaggedBlockIsNot(t *testing.T) {
	mustContain(t, md("\"\"\"\n<b>x</b> *\n\"\"\""), "\\<b\\>x\\</b\\> \\*")
	mustContain(t, md("'''\n<b>x</b> *\n'''"), "<b>x</b> *")
}

func TestMdTocLinksUseGithubAnchors(t *testing.T) {
	mustContain(t, tocMd("%%toc\n\n= Intro =\n== Sub Title ==\n= Intro ="),
		"* [Intro](#intro)\n    * [Sub Title](#sub-title)\n* [Intro](#intro-1)")
}

func TestMdBlocksAreSeparatedByBlankLines(t *testing.T) {
	mustContain(t, md("= H =\ntext\n\n----\n"), "# H\n\ntext\n\n---")
}

func TestOptNoHeadersDropsTheWrapper(t *testing.T) {
	o := Options{NoHeaders: true}
	if got := mdWith("text", o); got != "text" {
		t.Errorf("md: %q", got)
	}
	if got, _ := Convert("T\nA\nD\n\ntext", TargetHTML, o); got != "<p>\ntext\n</p>" {
		t.Errorf("html: %q", got)
	}
	if got, _ := Convert("T\nA\nD\n\ntext", TargetLatex, o); got != "text" {
		t.Errorf("tex: %q", got)
	}
}

func TestOptTocAddsATocUnlessThereIsOne(t *testing.T) {
	o := Options{Toc: true, NoHeaders: true}
	if out := mdWith("= A =\n== B ==", o); !strings.HasPrefix(out, "* [A](#a)\n    * [B](#b)\n\n# A") {
		t.Errorf("got %q", out)
	}
	if out := mdWith("text\n\n%%toc\n\n= A =", o); strings.Count(out, "[A](#a)") != 1 {
		t.Errorf("got %q", out)
	}
}

func TestOptTocLevelLimitsTheToc(t *testing.T) {
	out := mdWith("= A =\n== B ==", Options{Toc: true, TocLevel: 1, NoHeaders: true})
	mustContain(t, out, "[A](#a)")
	if strings.Contains(out, "[B](#b)") {
		t.Errorf("level 2 listed:\n%s", out)
	}
}

func TestOptTocOnly(t *testing.T) {
	o := Options{TocOnly: true}
	if got := mdWith("= A =\ntext", o); got != "* [A](#a)" {
		t.Errorf("got %q", got)
	}
	if _, err := Convert("T\nA\nD\n\n= A =", TargetLatex, o); err == nil {
		t.Error("toc-only with tex should fail")
	}
}

func TestOptEnumTitleNumbersHTMLAndMd(t *testing.T) {
	o := Options{EnumTitle: true, NoHeaders: true}
	mustContain(t, mdWith("= A =\n== B ==\n== C ==\n= D =", o), "# 1. A\n\n## 1.1. B\n\n## 1.2. C\n\n# 2. D")
	html, _ := Convert("T\nA\nD\n\n= A =\n== B ==", TargetHTML, o)
	mustContain(t, html, "<h2>1.1. B</h2>")
}

func TestOptSkipHeaderLinesStartsTheBodyOnLineOne(t *testing.T) {
	out, _ := Convert("= A =\n\ntext", TargetMarkdown, Options{SkipHeaderLines: true})
	if out != "# A\n\ntext" {
		t.Errorf("got %q", out)
	}
}

func TestTargetNames(t *testing.T) {
	if tg, ok := TargetFromName("md"); !ok || tg != TargetMarkdown {
		t.Error("md")
	}
	if tg, ok := TargetFromName("latex"); !ok || tg != TargetLatex {
		t.Error("latex")
	}
	if _, ok := TargetFromName("rtf"); ok {
		t.Error("rtf should be unknown")
	}
}

func TestDocumentOptionsAreDefaults(t *testing.T) {
	out, _ := Convert("T\nA\nD\n%!options: --toc -n\n\n= One =\n\ntext", TargetMarkdown, Options{})
	mustContain(t, out, "* [1\\. One](#1-one)")
	mustContain(t, out, "# 1. One")
	// an option for another target does not apply
	out, _ = Convert("T\nA\nD\n%!options(html): --toc\n\n= One =\n\ntext", TargetMarkdown, Options{})
	if strings.Contains(out, "](#") {
		t.Errorf("got %q", out)
	}
}

func TestTitleLabelIsDropped(t *testing.T) {
	mustContain(t, md("= One =[lab]\n\n+ Two +[x-1]"), "# One\n\n# 1. Two")
}

func TestMdMonoSpanIsVerbatim(t *testing.T) {
	mustContain(t, md("``//i// \\n **b**``"), "`//i// \\n **b**`")
}

func TestMdDefinitionListSublist(t *testing.T) {
	mustContain(t, md(": term\n  - a\n    + b"), "**term**  \n    * a\n        1. b")
}

func TestMdQuote(t *testing.T) {
	mustContain(t, md("\tquoted\n\t\tdeeper"), "> quoted\n> > deeper")
}
