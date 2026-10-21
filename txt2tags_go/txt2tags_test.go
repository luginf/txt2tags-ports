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
	out := convert(`\**not bold**`)
	if !strings.Contains(out, "**not bold**") {
		t.Errorf("escaped mark should be left literal, got %q", out)
	}
	if strings.Contains(out, "<b>") {
		t.Errorf("escaped mark should not open a tag, got %q", out)
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
	out := convert("|| head 1 | head 2\n|  cell 1 |  cell 2")
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

func TestImageAsLink(t *testing.T) {
	out := convert("[photo.png http://example.com]")
	want := "<a href=\"http://example.com\"><img src=\"photo.png\" alt=\"\"></a>"
	if !strings.Contains(out, want) {
		t.Errorf("got %q", out)
	}
}

func TestClassicNestedImageAsLink(t *testing.T) {
	out := convert("[[photo.jpg] http://example.com]")
	want := "<a href=\"http://example.com\"><img src=\"photo.jpg\" alt=\"\"></a>"
	if !strings.Contains(out, want) {
		t.Errorf("got %q", out)
	}
}

func TestBracketsThatAreNotALinkStayLiteral(t *testing.T) {
	out := convert("[just some text]")
	if !strings.Contains(out, "[just some text]") {
		t.Errorf("got %q", out)
	}
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

func TestGluedMarksAreNotTreatedAsInlineFormatting(t *testing.T) {
	out := convert("The value is 2**3**4 here.")
	if strings.Contains(out, "<b>") {
		t.Errorf("glued mark should not trigger bold, got %q", out)
	}
	if !strings.Contains(out, "2**3**4") {
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
	out := convert("%%toc\n\n= One =\n\n== Two ==")
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
	if out := convertLatex("%%toc\n\n= One ="); !strings.Contains(out, `\tableofcontents`) {
		t.Errorf("got %q", out)
	}
}

// --- raw blocks, definition lists -------------------------------------------

func TestRawBlockPassesThroughUnmodified(t *testing.T) {
	if out := convert("\"\"\"\n<b>already html</b>\n\"\"\""); !strings.Contains(out, "<b>already html</b>") {
		t.Errorf("got %q", out)
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
	out := convert("|  right|  center  |left |")
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
	if out := convertLatex("|  right|  center  |left |"); !strings.Contains(out, `\begin{tabular}{rcl}`) {
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
