//! Adapted from txt2tags_lua/t/01_convert.lua (itself adapted from
//! txt2tags_perl/t/07_convert.t): same idea (convert a small snippet,
//! check the HTML fragment it produces) applied to the Rust prototype,
//! kept to the subset of cases txt2tags::to_html actually supports (see
//! the scope comment at the top of src/lib.rs). Alternate targets
//! (txt/md) are skipped here since they don't exist in this port. The
//! `%%date`/`%%toc` macros, the LaTeX target, and the advanced-tier
//! additions (links, images, verbatim/raw blocks, block comments,
//! definition lists, table alignment,
//! %!preproc/%!postproc) have their own sections below.
//!
//! Run:  cargo test

// convert() in the Perl tests takes body lines directly, past head
// parsing; txt2tags::to_html only exposes the full document, so wrap a
// minimal 3-line head around each body snippet.
fn convert(body: &str) -> String {
    txt2tags::to_html(&format!("T\nA\nD\n\n{body}"))
}

fn convert_latex(body: &str) -> String {
    txt2tags::to_latex(&format!("T\nA\nD\n\n{body}"))
}

#[test]
fn bold() {
    assert!(convert("**bold text**").contains("<b>bold text</b>"));
}

#[test]
fn italic() {
    assert!(convert("//italic text//").contains("<i>italic text</i>"));
}

#[test]
fn underline() {
    assert!(convert("__underline text__").contains("<u>underline text</u>"));
}

#[test]
fn strike() {
    assert!(convert("--strike text--").contains("<s>strike text</s>"));
}

#[test]
fn escaping() {
    let out = convert("\\**not bold**");
    assert!(out.contains("**not bold**"), "escaped mark is left literal");
    assert!(!out.contains("<b>"), "escaped mark does not open a tag");
}

#[test]
fn titles_all_levels() {
    assert!(convert("= Hello =").contains("<h1>Hello</h1>"));
    assert!(convert("== World ==").contains("<h2>World</h2>"));
    assert!(convert("=== Three ===").contains("<h3>Three</h3>"));
    assert!(convert("==== Four ====").contains("<h4>Four</h4>"));
    assert!(convert("===== Five =====").contains("<h5>Five</h5>"));
}

#[test]
fn title_tolerates_surrounding_and_inner_spaces() {
    assert!(convert("   ===  Padded Title  ===   ").contains("<h3>Padded Title</h3>"));
}

#[test]
fn unbalanced_equals_is_not_a_title() {
    // The document's own head still renders an <h1> for the "T" title
    // above, so check the body text specifically, not the mere tag.
    let out = convert("=Not Title");
    assert!(!out.contains("<h1>Not Title"));
    assert!(out.contains("=Not Title"));
}

#[test]
fn horizontal_bar() {
    assert!(convert("--------------------").contains("<hr>"));
}

#[test]
fn unordered_list() {
    let out = convert("- apple\n- banana\n- cherry");
    assert!(out.contains("<ul>"));
    assert!(out.contains("<li>apple"));
    assert!(out.contains("<li>banana"));
    assert!(out.contains("</ul>"));
}

#[test]
fn numbered_list() {
    let out = convert("+ one\n+ two");
    assert!(out.contains("<ol>"));
    assert!(out.contains("<li>one"));
    assert!(out.contains("</ol>"));
}

#[test]
fn list_requires_exactly_one_space_after_marker() {
    assert!(!convert("-This is not a list").contains("<ul>"));
}

#[test]
fn nested_sublist() {
    let out = convert("- Level 1\n  - Level 2\n- Level 1 again");
    assert!(out.contains("<ul>\n<li>Level 1"));
    assert!(out.contains("<li>Level 2"));
}

#[test]
fn mixed_lists_do_not_merge() {
    let out = convert("- a\n- b\n\n+ one\n+ two");
    assert!(out.contains("<ul>"));
    assert!(out.contains("<ol>"));
}

#[test]
fn table_simple_no_header() {
    let out = convert("| col A | col B |\n| val 1 | val 2 |");
    assert!(out.contains("<table>"));
    assert!(out.contains("<tr>"));
    assert!(out.contains("<td>col A</td>"));
    assert!(out.contains("<td>val 2</td>"));
    assert!(!out.contains("<th>"));
    assert!(out.contains("</table>"));
}

#[test]
fn table_double_pipe_marks_header_row() {
    let out = convert("|| head 1 | head 2\n|  cell 1 |  cell 2");
    assert!(out.contains("<th>head 1</th>"));
    assert!(out.contains("<td>cell 1</td>"));
}

#[test]
fn table_inline_markup_in_cells() {
    assert!(convert("| **bold cell** |").contains("<td><b>bold cell</b></td>"));
}

#[test]
fn blank_line_separates_two_tables() {
    let out = convert("| a | b |\n\n| c | d |");
    assert_eq!(out.matches("<table>").count(), 2);
}

#[test]
fn comment_line_does_not_break_surrounding_paragraph() {
    let out = convert("real text before\n% this is a comment\nreal text after");
    assert!(!out.contains("this is a comment"));
    assert!(out.contains("real text before"));
    assert!(out.contains("real text after"));
}

#[test]
fn standalone_comment_line() {
    let out = convert("% just a comment\nreal text");
    assert!(!out.contains("just a comment"));
    assert!(out.contains("real text"));
}

#[test]
fn block_comment_is_fully_suppressed() {
    let out = convert("before\n\n%%%\nhidden one\nhidden two\n%%%\n\nafter");
    assert!(out.contains("before"));
    assert!(out.contains("after"));
    assert!(!out.contains("hidden one"));
    assert!(!out.contains("hidden two"));
}

#[test]
fn block_comment_ends_a_paragraph() {
    let out = convert("real text\n%%%\nhidden\n%%%");
    assert!(out.contains("real text"));
    assert!(!out.contains("hidden"));
}

// --- %%date macro ---------------------------------------------------------

#[test]
fn date_macro_expands_inline() {
    let out = convert("Today is %%date.");
    assert!(!out.contains("%%date"));
    assert!(out.contains(&format!("Today is {}.", txt2tags::today_string())));
}

#[test]
fn date_macro_expands_in_header_date_field() {
    // The classic txt2tags idiom: the 3rd header line is literally "%%date".
    let out = txt2tags::to_html("T\nA\n%%date\n\nbody");
    assert!(out.contains(&txt2tags::today_string()));
}

// --- %%toc macro -----------------------------------------------------------

#[test]
fn toc_lists_headings_with_anchors() {
    let out = convert("%%toc\n\n= One =\n\n== Two ==");
    assert!(out.contains("<ul class=\"toc\">"));
    assert!(out.contains("toc-h1"));
    assert!(out.contains("toc-h2"));
    assert!(out.contains("href=\"#t2t-"));
    assert!(out.contains("id=\"t2t-"));
}

#[test]
fn toc_does_not_add_heading_ids_when_absent() {
    let out = convert("= One =");
    assert!(!out.contains("id=\"t2t-"));
}

// --- LaTeX target ------------------------------------------------------

#[test]
fn latex_document_wrapper() {
    let out = convert_latex("hello");
    assert!(out.contains("\\documentclass"));
    assert!(out.contains("\\begin{document}"));
    assert!(out.contains("\\end{document}"));
}

#[test]
fn latex_inline_marks_and_escaping() {
    let out = convert_latex("**bold** & 100% //italic//");
    assert!(out.contains("\\textbf{bold}"));
    assert!(out.contains("\\&"));
    assert!(out.contains("\\%"));
    assert!(out.contains("\\textit{italic}"));
}

#[test]
fn latex_heading_levels() {
    let out = convert_latex("= H1 =\n\n== H2 ==\n\n=== H3 ===");
    assert!(out.contains("\\section{H1}"));
    assert!(out.contains("\\subsection{H2}"));
    assert!(out.contains("\\subsubsection{H3}"));
}

#[test]
fn latex_list() {
    let out = convert_latex("- a\n- b");
    assert!(out.contains("\\begin{itemize}"));
    assert!(out.contains("\\item a"));
    assert!(out.contains("\\item b"));
    assert!(out.contains("\\end{itemize}"));
}

#[test]
fn latex_numbered_list() {
    let out = convert_latex("+ one\n+ two");
    assert!(out.contains("\\begin{enumerate}"));
    assert!(out.contains("\\item one"));
    assert!(out.contains("\\end{enumerate}"));
}

#[test]
fn latex_table_with_header() {
    let out = convert_latex("|| h1 | h2\n| c1 | c2");
    assert!(out.contains("\\begin{tabular}{ll}"));
    assert!(out.contains("\\textbf{h1} & \\textbf{h2}"));
    assert!(out.contains("\\hline"));
    assert!(out.contains("c1 & c2"));
    assert!(out.contains("\\end{tabular}"));
}

#[test]
fn latex_toc_uses_tableofcontents() {
    let out = convert_latex("%%toc\n\n= One =");
    assert!(out.contains("\\tableofcontents"));
}

// --- links & images ----------------------------------------------------

#[test]
fn link_with_label() {
    let out = convert("[Google http://google.com]");
    assert!(out.contains("<a href=\"http://google.com\">Google</a>"));
}

#[test]
fn bare_url_autolink() {
    let out = convert("Visit http://example.com today");
    assert!(out.contains("<a href=\"http://example.com\">http://example.com</a>"));
}

#[test]
fn bare_url_stops_before_closing_bracket() {
    // Reference URL charset has no brackets: the "]" is not part of the href.
    let out = convert("[see [1] http://x.org/a] end");
    assert!(out.contains("<a href=\"http://x.org/a\">http://x.org/a</a>]"));
    assert!(!out.contains("a]\""));
}

#[test]
fn bare_url_stops_at_open_bracket() {
    let out = convert("http://x.org/j?a[1]=2");
    assert!(out.contains("<a href=\"http://x.org/j?a\">http://x.org/j?a</a>[1]=2"));
}

#[test]
fn bare_url_drops_trailing_punctuation() {
    let out = convert("See http://x.org/page.");
    assert!(out.contains("<a href=\"http://x.org/page\">http://x.org/page</a>."));
}

#[test]
fn image_reference() {
    let out = convert("[photo.png]");
    assert!(out.contains("<img src=\"photo.png\" alt=\"\">"));
}

#[test]
fn image_as_link() {
    let out = convert("[photo.png http://example.com]");
    assert!(out.contains("<a href=\"http://example.com\"><img src=\"photo.png\" alt=\"\"></a>"));
}

#[test]
fn brackets_that_are_not_a_link_stay_literal() {
    let out = convert("[just some text]");
    assert!(out.contains("[just some text]"));
}

#[test]
fn nested_brackets_degrade_without_mangling() {
    // LionWiki-style [[label | URL]] double brackets are a different,
    // unsupported dialect -- this must not produce a broken/truncated
    // href, even though it isn't parsed as a clean link either.
    let out = convert("[[Wiki | http://en.wikipedia.org/wiki/Wiki]]");
    assert!(!out.contains("href=\"http://en.wikipedia.org/wiki/Wiki]\""));
}

#[test]
fn classic_nested_image_as_link() {
    // The real txt2tags shape for a clickable image: [ [image.ext] URL ].
    let out = convert("[[photo.jpg] http://example.com]");
    assert!(out.contains("<a href=\"http://example.com\"><img src=\"photo.jpg\" alt=\"\"></a>"));
}

#[test]
fn latex_classic_nested_image_as_link() {
    let out = convert_latex("[[photo.jpg] http://example.com]");
    assert!(out.contains("\\href{http://example.com}{\\includegraphics{photo.jpg}}"));
}

// --- glued/greedy mark matching --------------------------------------------

#[test]
fn glued_marks_are_not_treated_as_inline_formatting() {
    // A mark immediately glued to word characters on both outer sides is
    // not real markup -- classic false positive: "2**3**4" as plain text
    // about exponents, not bold.
    let out = convert("The value is 2**3**4 here.");
    assert!(!out.contains("<b>"));
    assert!(out.contains("2**3**4"));
}

#[test]
fn marks_next_to_punctuation_still_work() {
    let out = convert("(**bold**)");
    assert!(out.contains("(<b>bold</b>)"));
}

#[test]
fn latex_link_with_label() {
    let out = convert_latex("[Google http://google.com]");
    assert!(out.contains("\\href{http://google.com}{Google}"));
}

#[test]
fn latex_image_reference() {
    let out = convert_latex("[photo.png]");
    assert!(out.contains("\\includegraphics{photo.png}"));
}

// --- verbatim & raw blocks -----------------------------------------------

#[test]
fn verbatim_block_preserves_literal_text() {
    let out = convert("```\nlet x = 1 < 2;\n**not bold**\n```");
    assert!(out.contains("<pre>"));
    assert!(out.contains("let x = 1 &lt; 2;"));
    assert!(out.contains("**not bold**"));
    assert!(!out.contains("<b>"));
}

#[test]
fn latex_verbatim_block() {
    let out = convert_latex("```\ncode & stuff\n```");
    assert!(out.contains("\\begin{verbatim}"));
    assert!(out.contains("code & stuff"));
    assert!(out.contains("\\end{verbatim}"));
}

#[test]
fn raw_block_passes_through_unmodified() {
    let out = convert("\"\"\"\n<b>already html</b>\n\"\"\"");
    assert!(out.contains("<b>already html</b>"));
}

// --- definition lists ----------------------------------------------------

#[test]
fn definition_list() {
    let out = convert(": Rust\n  A systems programming language.\n: Go\n  A language by Google.");
    assert!(out.contains("<dl>"));
    assert!(out.contains("<dt>Rust</dt>"));
    assert!(out.contains("<dd>A systems programming language.</dd>"));
    assert!(out.contains("<dt>Go</dt>"));
    assert!(out.contains("</dl>"));
}

#[test]
fn latex_definition_list() {
    let out = convert_latex(": Rust\n  A systems language.");
    assert!(out.contains("\\begin{description}"));
    assert!(out.contains("\\item[Rust] A systems language."));
    assert!(out.contains("\\end{description}"));
}

// --- table column-alignment inference -------------------------------------

#[test]
fn table_alignment_inference() {
    let out = convert("|  right|  center  |left |");
    assert!(out.contains("<td style=\"text-align:right\">right</td>"));
    assert!(out.contains("<td style=\"text-align:center\">center</td>"));
    assert!(out.contains("<td>left</td>"));
}

#[test]
fn latex_table_alignment_inference() {
    let out = convert_latex("|  right|  center  |left |");
    assert!(out.contains("\\begin{tabular}{rcl}"));
}

// --- %!preproc / %!postproc ------------------------------------------------

#[test]
fn preproc_rewrites_source_before_parsing() {
    let src = "T\nA\nD\n%!preproc: 'TODO' 'DONE'\n\nTODO: fix this";
    let out = txt2tags::to_html(src);
    assert!(out.contains("DONE: fix this"));
    assert!(!out.contains("TODO"));
}

#[test]
fn postproc_rewrites_rendered_output() {
    let src = "T\nA\nD\n%!postproc: '<p>' '<p class=\"x\">'\n\nhello";
    let out = txt2tags::to_html(src);
    assert!(out.contains("<p class=\"x\">"));
}
