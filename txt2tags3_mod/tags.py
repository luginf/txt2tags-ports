# txt2tags - tag definitions per target
# getTags(config) -> dict of tag strings for the given target

from .constants import (
    _, re, os, sys, time, textwrap, csv, struct, unicodedata,
    base64, shlex, getopt, importlib, binascii,
    my_name, my_email, my_url, my_version, my_revision,
    USE_I18N, COLOR_DEBUG, BG_LIGHT, HTML_LOWER,
    FLAGS, OPTIONS, ACTIONS, MACROS, SETTINGS,
    NO_TARGET, NO_MULTI_INPUT, CONFIG_KEYWORDS,
    TARGET_NAMES, TARGET_TYPES, TARGETS, TARGETS_LIST, OTHER_TARGETS,
    NOT_LOADED, LOADED,
    AUTOTOC, DFT_TEXT_WIDTH, DFT_SLIDE_WIDTH, DFT_SLIDE_HEIGHT,
    DFT_SLIDE_WEB_WIDTH, DFT_SLIDE_WEB_HEIGHT,
    DFT_SLIDE_PRINT_WIDTH, DFT_SLIDE_PRINT_HEIGHT,
    AA_KEYS, AA_SIMPLE, AA_ADVANCED, AA, AA_QA,
    RST_KEYS, RST_VALUES, RST,
    CSV_KEYS, CSV_VALUES, CSV,
    STDIN, STDOUT, MODULEIN, MODULEOUT,
    ESCCHAR, SEPARATOR, LISTNAMES, LINEBREAK, ESCAPES, LB,
    VERSIONSTR, targets,
)
from . import state
from .utils import Error


def getTags(config):
    "Returns all the known tags for the specified target"
    from .aa import aa_line
    from .output import maskEscapeChar

    keys = """
    title1              numtitle1
    title2              numtitle2
    title3              numtitle3
    title4              numtitle4
    title5              numtitle5
    title1Open          title1Close
    title2Open          title2Close
    title3Open          title3Close
    title4Open          title4Close
    title5Open          title5Close
    blocktitle1Open     blocktitle1Close
    blocktitle2Open     blocktitle2Close
    blocktitle3Open     blocktitle3Close

    paragraphOpen       paragraphClose
    blockVerbOpen       blockVerbClose  blockVerbLine
    blockQuoteOpen      blockQuoteClose blockQuoteLine
    blockVerbSep
    blockCommentOpen    blockCommentClose

    fontMonoOpen        fontMonoClose
    fontBoldOpen        fontBoldClose
    fontItalicOpen      fontItalicClose
    fontUnderlineOpen   fontUnderlineClose
    fontStrikeOpen      fontStrikeClose

    listOpen            listClose
    listOpenCompact     listCloseCompact
    listItemOpen        listItemClose     listItemLine
    numlistOpen         numlistClose
    numlistOpenCompact  numlistCloseCompact
    numlistItemOpen     numlistItemClose  numlistItemLine
    deflistOpen         deflistClose
    deflistOpenCompact  deflistCloseCompact
    deflistItem1Open    deflistItem1Close
    deflistItem2Open    deflistItem2Close deflistItem2LinePrefix

    bar1                bar2
    url                 urlMark      urlMarkAnchor   urlImg
    email               emailMark
    img                 imgAlignLeft  imgAlignRight  imgAlignCenter
                       _imgAlignLeft _imgAlignRight _imgAlignCenter

    tableOpen           tableClose
    _tableBorder        _tableAlignLeft      _tableAlignCenter
    tableRowOpen        tableRowClose        tableRowSep
    tableTitleRowOpen   tableTitleRowClose
    tableCellOpen       tableCellClose       tableCellSep
    tableTitleCellOpen  tableTitleCellClose  tableTitleCellSep
    _tableColAlignLeft  _tableColAlignRight  _tableColAlignCenter
    tableCellAlignLeft  tableCellAlignRight  tableCellAlignCenter
    _tableCellAlignLeft _tableCellAlignRight _tableCellAlignCenter
    _tableCellAlignLeftBorder _tableCellAlignRightBorder _tableCellAlignCenterBorder
    _tableCellColSpan   tableColAlignSep
    _tableCellColSpanChar tableCellCovered _tableCellBorder
    _tableCellMulticolOpen
    _tableCellMulticolClose
    tableCellHead       tableTitleCellHead

    bodyOpen            bodyClose
    cssOpen             cssClose
    tocOpen             tocClose             TOC
    anchor
    comment
    pageBreak
    EOD
    """.split()

    # TIP: \a represents the current text inside the mark
    # TIP: ~A~, ~B~ and ~C~ are expanded to other tags parts

    alltags = {
        "aat": {
            "title1": "\a",
            "title2": "\a",
            "title3": "\a",
            "title4": "\a",
            "title5": "\a",
            "blockQuoteLine": AA["quote"],
            "listItemOpen": AA["bullet"] + " ",
            "numlistItemOpen": "\a. ",
            "bar1": aa_line(AA["bar1"], config["width"]),
            "bar2": aa_line(AA["bar2"], config["width"]),
            "url": "\a",
            "urlMark": "\a[\a]",
            "email": "\a",
            "emailMark": "\a[\a]",
            "img": "[\a]",
            "imgEmbed": "\a",
            "fontBoldOpen": "*",
            "fontBoldClose": "*",
            "fontItalicOpen": "/",
            "fontItalicClose": "/",
            "fontUnderlineOpen": "_",
            "fontUnderlineClose": "_",
            "fontStrikeOpen": "-",
            "fontStrikeClose": "-",
        },
        "rst": {
            "title1": "\a",
            "title2": "\a",
            "title3": "\a",
            "title4": "\a",
            "title5": "\a",
            "blockVerbOpen": "::\n",
            "blockQuoteLine": "    ",
            "listItemOpen": RST["bullet"] + " ",
            "numlistItemOpen": "\a. ",
            "bar1": aa_line(RST["bar1"], 10),
            "url": "\a",
            "urlMark": "`\a <\a>`_",
            "email": "\a",
            "emailMark": "`\a <\a>`_",
            "img": "\n\n.. image:: \a\n   :align: ~A~\n\nENDIMG",
            "urlImg": "\n   :target: ",
            "_imgAlignLeft": "left",
            "_imgAlignCenter": "center",
            "_imgAlignRight": "right",
            "fontMonoOpen": "``",
            "fontMonoClose": "``",
            "fontBoldOpen": "**",
            "fontBoldClose": "**",
            "fontItalicOpen": "*",
            "fontItalicClose": "*",
            "comment": ".. \a",
            "TOC": "\n.. contents::",
        },
        "txt": {
            "title1": "  \a",
            "title2": "\t\a",
            "title3": "\t\t\a",
            "title4": "\t\t\t\a",
            "title5": "\t\t\t\t\a",
            "blockQuoteLine": "\t",
            "listItemOpen": "- ",
            "numlistItemOpen": "\a. ",
            "bar1": "\a",
            "url": "\a",
            "urlMark": "\a (\a)",
            "email": "\a",
            "emailMark": "\a (\a)",
            "img": "[\a]",
        },
        "csv": {
            "tableCellSep": CSV["separator"],
            "tableCellOpen": CSV.get("quotechar") or "",
            "tableCellClose": CSV.get("quotechar") or "",
        },
        "csvs": {
            # TIP csvs inherits all csv tags
        },
        "db": {},
        "txt2t": {
            "title1": "         = \a =~A~",
            "title2": "        == \a ==~A~",
            "title3": "       === \a ===~A~",
            "title4": "      ==== \a ====~A~",
            "title5": "     ===== \a =====~A~",
            "numtitle1": "         + \a +~A~",
            "numtitle2": "        ++ \a ++~A~",
            "numtitle3": "       +++ \a +++~A~",
            "numtitle4": "      ++++ \a ++++~A~",
            "numtitle5": "     +++++ \a +++++~A~",
            "anchor": "[\a]",
            "blockVerbOpen": "```",
            "blockVerbClose": "```",
            "blockQuoteLine": "\t",
            "blockCommentOpen": "%%%",
            "blockCommentClose": "%%%",
            "fontMonoOpen": "``",
            "fontMonoClose": "``",
            "fontBoldOpen": "**",
            "fontBoldClose": "**",
            "fontItalicOpen": "//",
            "fontItalicClose": "//",
            "fontUnderlineOpen": "__",
            "fontUnderlineClose": "__",
            "fontStrikeOpen": "--",
            "fontStrikeClose": "--",
            "listItemOpen": "- ",
            "numlistItemOpen": "+ ",
            "deflistItem1Open": ": ",
            "listClose": "-",
            "numlistClose": "+",
            "deflistClose": ":",
            "bar1": "-------------------------",
            "bar2": "=========================",
            "url": "\a",
            "urlMark": "[\a \a]",
            #'urlMarkAnchor' : '' ,
            "email": "\a",
            "emailMark": "[\a \a]",
            "img": "[\a]",
            "_tableBorder": "|",
            "_tableAlignLeft": "",
            "_tableAlignCenter": "   ",
            "tableRowOpen": "~A~",
            "tableRowClose": "~B~",
            #        'tableRowSep' : '' ,
            "tableTitleRowOpen": "~A~|",
            "tableCellOpen": "| ",
            "tableCellClose": " ~S~",
            #        'tableCellSep' : '' ,
            "tableCellAlignLeft": "\a  ",
            "tableCellAlignRight": "  \a",
            "tableCellAlignCenter": "  \a  ",
            #        '_tableCellColSpan' : '' ,
            "_tableCellColSpanChar": "|",
            "comment": "% \a",
        },
        "ods": {
            "tableOpen": '<table:table table:name="' + "table_name" + 'n_table">',
            "tableClose": "</table:table>",
            "tableRowOpen": "<table:table-row>",
            "tableRowClose": "</table:table-row>",
            "tableCellOpen": "<table:table-cell~A~~S~><text:p>",
            "tableCellClose": "</text:p></table:table-cell>",
            "tableTitleCellOpen": '<table:table-cell~A~~S~><text:p><text:span text:style-name="T1">',
            "tableTitleCellClose": "</text:span></text:p></table:table-cell>",
            "tableCellCovered": '<table:covered-table-cell table:number-columns-repeated="\a"/>',
            "_tableCellAlignCenter": ' table:style-name="ce1"',
            "_tableCellAlignRight": ' table:style-name="ce2"',
            "_tableCellAlignLeftBorder": ' table:style-name="ce3"',
            "_tableCellAlignCenterBorder": ' table:style-name="ce4"',
            "_tableCellAlignRightBorder": ' table:style-name="ce5"',
            "_tableCellColSpan": ' table:number-columns-spanned="\a"',
            "EOD": "</office:spreadsheet></office:body></office:document>",
        },
        "html": {
            "paragraphOpen": "<P>",
            "paragraphClose": "</P>",
            "title1": "<H1~A~>\a</H1>",
            "title2": "<H2~A~>\a</H2>",
            "title3": "<H3~A~>\a</H3>",
            "title4": "<H4~A~>\a</H4>",
            "title5": "<H5~A~>\a</H5>",
            "anchor": ' ID="\a"',
            "blockVerbOpen": "<PRE>",
            "blockVerbClose": "</PRE>",
            "blockQuoteOpen": "<BLOCKQUOTE>",
            "blockQuoteClose": "</BLOCKQUOTE>",
            "fontMonoOpen": "<CODE>",
            "fontMonoClose": "</CODE>",
            "fontBoldOpen": "<B>",
            "fontBoldClose": "</B>",
            "fontItalicOpen": "<I>",
            "fontItalicClose": "</I>",
            "fontUnderlineOpen": "<U>",
            "fontUnderlineClose": "</U>",
            "fontStrikeOpen": "<S>",
            "fontStrikeClose": "</S>",
            "listOpen": "<UL>",
            "listClose": "</UL>",
            "listItemOpen": "<LI>",
            "numlistOpen": "<OL>",
            "numlistClose": "</OL>",
            "numlistItemOpen": "<LI>",
            "deflistOpen": "<DL>",
            "deflistClose": "</DL>",
            "deflistItem1Open": "<DT>",
            "deflistItem1Close": "</DT>",
            "deflistItem2Open": "<DD>",
            "bar1": "<HR NOSHADE SIZE=1>",
            "bar2": "<HR NOSHADE SIZE=5>",
            "url": '<A HREF="\a">\a</A>',
            "urlMark": '<A HREF="\a">\a</A>',
            "email": '<A HREF="mailto:\a">\a</A>',
            "emailMark": '<A HREF="mailto:\a">\a</A>',
            "img": '<IMG~A~ SRC="\a" BORDER="0" ALT="">',
            "imgEmbed": '<IMG~A~ SRC="\a" BORDER="0" ALT="">',
            "_imgAlignLeft": ' ALIGN="left"',
            "_imgAlignCenter": ' ALIGN="middle"',
            "_imgAlignRight": ' ALIGN="right"',
            "tableOpen": '<TABLE~A~~B~ CELLPADDING="4">',
            "tableClose": "</TABLE>",
            "tableRowOpen": "<TR>",
            "tableRowClose": "</TR>",
            "tableCellOpen": "<TD~A~~S~>",
            "tableCellClose": "</TD>",
            "tableTitleCellOpen": "<TH~S~>",
            "tableTitleCellClose": "</TH>",
            "_tableBorder": ' BORDER="1"',
            "_tableAlignCenter": ' ALIGN="center"',
            "_tableCellAlignRight": ' ALIGN="right"',
            "_tableCellAlignCenter": ' ALIGN="center"',
            "_tableCellColSpan": ' COLSPAN="\a"',
            "cssOpen": '<STYLE TYPE="text/css">',
            "cssClose": "</STYLE>",
            "comment": "<!-- \a -->",
            "EOD": "</BODY></HTML>",
        },
        # TIP wp inherits all HTML tags
        "wp": {
            # Exclusions to let the WordPress code cleaner
            "bodyOpen": "",
            "bodyClose": "",
            "paragraphOpen": "",
            "paragraphClose": "",
            "comment": "",
            "EOD": "",
            # All list items must be closed
            "listItemClose": "</li>",
            "numlistItemClose": "</li>",
            "deflistItem2Close": "</dd>",
            # WP likes tags this way
            "bar1": "<hr>",
            "bar2": "<hr>",
            "fontBoldOpen": "<strong>",
            "fontBoldClose": "</strong>",
            "fontItalicOpen": "<em>",
            "fontItalicClose": "</em>",
        },
        # TIP xhtml inherits all HTML definitions (lowercased)
        # TIP http://www.w3.org/TR/xhtml1/#guidelines
        # TIP http://www.htmlref.com/samples/Chapt17/17_08.htm
        "xhtml": {
            "listItemClose": "</li>",
            "numlistItemClose": "</li>",
            "deflistItem2Close": "</dd>",
            "bar1": '<hr class="light" />',
            "bar2": '<hr class="heavy" />',
            "img": '<img~A~ src="\a" border="0" alt=""/>',
            "imgEmbed": '<img~A~ SRC="\a" border="0" alt=""/>',
        },
        "xhtmls": {
            "fontBoldOpen": "<strong>",
            "fontBoldClose": "</strong>",
            "fontItalicOpen": "<em>",
            "fontItalicClose": "</em>",
            "fontUnderlineOpen": '<span style="text-decoration:underline">',
            "fontUnderlineClose": "</span>",
            "fontStrikeOpen": '<span style="text-decoration:line-through">',  # use <del> instead ?
            "fontStrikeClose": "</span>",
            "listItemClose": "</li>",
            "numlistItemClose": "</li>",
            "deflistItem2Close": "</dd>",
            "bar1": '<hr class="light" />',
            "bar2": '<hr class="heavy" />',
            "img": '<img style="display: block;~a~" src="\a" alt=""/>',
            "imgEmbed": '<img~a~ src="\a" alt=""/>',
            "_imgAlignLeft": "margin: 0 auto 0 0;",
            "_imgAlignCenter": "margin: 0 auto 0 auto;",
            "_imgAlignRight": "margin: 0 0 0 auto;",
            "_tableAlignCenter": ' style="margin-left: auto; margin-right: auto;"',
            "_tableCellAlignRight": ' style="text-align:right"',
            "_tableCellAlignCenter": ' style="text-align:center"',
        },
        "html5": {
            "title1Open": "<section~A~>\n<h1>\a</h1>",
            "title1Close": "</section>",
            "title2Open": "<section~A~>\n<h2>\a</h2>",
            "title2Close": "</section>",
            "title3Open": "<section~A~>\n<h3>\a</h3>",
            "title3Close": "</section>",
            "title4Open": "<section~A~>\n<h4>\a</h4>",
            "title4Close": "</section>",
            "title5Open": "<section~A~>\n<h5>\a</h5>",
            "title5Close": "</section>",
            "fontBoldOpen": "<strong>",
            "fontBoldClose": "</strong>",
            "fontItalicOpen": "<em>",
            "fontItalicClose": "</em>",
            "fontUnderlineOpen": '<span class="underline">',
            "fontUnderlineClose": "</span>",
            "fontStrikeOpen": "<del>",
            "fontStrikeClose": "</del>",
            "listItemClose": "</li>",
            "numlistItemClose": "</li>",
            "deflistItem2Close": "</dd>",
            "bar1": '<hr class="light">',
            "bar2": '<hr class="heavy">',
            "img": '<img~a~ src="\a" alt="">',
            "imgEmbed": '<img~a~ src="\a" alt="">',
            "_imgAlignLeft": ' class="left"',
            "_imgAlignCenter": ' class="center"',
            "_imgAlignRight": ' class="right"',
            "tableOpen": "<table~a~~b~>",
            "_tableBorder": ' class="tableborder"',
            "_tableAlignCenter": ' style="margin-left: auto; margin-right: auto;"',
            "_tableCellAlignRight": ' class="right"',
            "_tableCellAlignCenter": ' class="center"',
            "cssOpen": "<style>",
            "tocOpen": "<nav>",
            "tocClose": "</nav>",
            "EOD": "</article></body></html>",
        },
        "htmls": {
            # TIP htmls inherits all html5 tags
        },
        "sgml": {
            "paragraphOpen": "<p>",
            "title1": "<sect>\a~A~<p>",
            "title2": "<sect1>\a~A~<p>",
            "title3": "<sect2>\a~A~<p>",
            "title4": "<sect3>\a~A~<p>",
            "title5": "<sect4>\a~A~<p>",
            "anchor": '<label id="\a">',
            "blockVerbOpen": "<tscreen><verb>",
            "blockVerbClose": "</verb></tscreen>",
            "blockQuoteOpen": "<quote>",
            "blockQuoteClose": "</quote>",
            "fontMonoOpen": "<tt>",
            "fontMonoClose": "</tt>",
            "fontBoldOpen": "<bf>",
            "fontBoldClose": "</bf>",
            "fontItalicOpen": "<em>",
            "fontItalicClose": "</em>",
            "fontUnderlineOpen": "<bf><em>",
            "fontUnderlineClose": "</em></bf>",
            "listOpen": "<itemize>",
            "listClose": "</itemize>",
            "listItemOpen": "<item>",
            "numlistOpen": "<enum>",
            "numlistClose": "</enum>",
            "numlistItemOpen": "<item>",
            "deflistOpen": "<descrip>",
            "deflistClose": "</descrip>",
            "deflistItem1Open": "<tag>",
            "deflistItem1Close": "</tag>",
            "bar1": "<!-- \a -->",
            "url": '<htmlurl url="\a" name="\a">',
            "urlMark": '<htmlurl url="\a" name="\a">',
            "email": '<htmlurl url="mailto:\a" name="\a">',
            "emailMark": '<htmlurl url="mailto:\a" name="\a">',
            "img": '<figure><ph vspace=""><img src="\a"></figure>',
            "tableOpen": '<table><tabular ca="~C~">',
            "tableClose": "</tabular></table>",
            "tableRowSep": "<rowsep>",
            "tableCellSep": "<colsep>",
            "_tableColAlignLeft": "l",
            "_tableColAlignRight": "r",
            "_tableColAlignCenter": "c",
            "comment": "<!-- \a -->",
            "TOC": "<toc>",
            "EOD": "</article>",
        },
        "dbk": {
            "paragraphOpen": "<para>",
            "paragraphClose": "</para>",
            "title1Open": "~A~<sect1><title>\a</title>",
            "title1Close": "</sect1>",
            "title2Open": "~A~  <sect2><title>\a</title>",
            "title2Close": "  </sect2>",
            "title3Open": "~A~    <sect3><title>\a</title>",
            "title3Close": "    </sect3>",
            "title4Open": "~A~      <sect4><title>\a</title>",
            "title4Close": "      </sect4>",
            "title5Open": "~A~        <sect5><title>\a</title>",
            "title5Close": "        </sect5>",
            "anchor": '<anchor id="\a"/>\n',
            "blockVerbOpen": "<programlisting>",
            "blockVerbClose": "</programlisting>",
            "blockQuoteOpen": "<blockquote><para>",
            "blockQuoteClose": "</para></blockquote>",
            "fontMonoOpen": "<code>",
            "fontMonoClose": "</code>",
            "fontBoldOpen": '<emphasis role="bold">',
            "fontBoldClose": "</emphasis>",
            "fontItalicOpen": "<emphasis>",
            "fontItalicClose": "</emphasis>",
            "fontUnderlineOpen": '<emphasis role="underline">',
            "fontUnderlineClose": "</emphasis>",
            # 'fontStrikeOpen'       : '<emphasis role="strikethrough">'   ,  # Don't know
            # 'fontStrikeClose'      : '</emphasis>'                       ,
            "listOpen": "<itemizedlist>",
            "listClose": "</itemizedlist>",
            "listItemOpen": "<listitem><para>",
            "listItemClose": "</para></listitem>",
            "numlistOpen": '<orderedlist numeration="arabic">',
            "numlistClose": "</orderedlist>",
            "numlistItemOpen": "<listitem><para>",
            "numlistItemClose": "</para></listitem>",
            "deflistOpen": "<variablelist>",
            "deflistClose": "</variablelist>",
            "deflistItem1Open": "<varlistentry><term>",
            "deflistItem1Close": "</term>",
            "deflistItem2Open": "<listitem><para>",
            "deflistItem2Close": "</para></listitem></varlistentry>",
            # 'bar1'                 : '<>'                                ,  # Don't know
            # 'bar2'                 : '<>'                                ,  # Don't know
            "url": '<ulink url="\a">\a</ulink>',
            "urlMark": '<ulink url="\a">\a</ulink>',
            "email": "<email>\a</email>",
            "emailMark": "<email>\a</email>",
            "img": '<mediaobject><imageobject><imagedata fileref="\a"/></imageobject></mediaobject>',
            # '_imgAlignLeft'        : ''                                 ,  # Don't know
            # '_imgAlignCenter'      : ''                                 ,  # Don't know
            # '_imgAlignRight'       : ''                                 ,  # Don't know
            "tableOpen": '<informaltable><tgroup cols="n_cols"><tbody>',
            "tableClose": "</tbody></tgroup></informaltable>",
            "tableRowOpen": "<row>",
            "tableRowClose": "</row>",
            "tableCellOpen": "<entry>",
            "tableCellClose": "</entry>",
            "tableTitleRowOpen": "<thead>",
            "tableTitleRowClose": "</thead>",
            "_tableBorder": ' frame="all"',
            "_tableAlignCenter": ' align="center"',
            "_tableCellAlignRight": ' align="right"',
            "_tableCellAlignCenter": ' align="center"',
            "_tableCellColSpan": ' COLSPAN="\a"',
            "TOC": "<index/>",
            "comment": "<!-- \a -->",
            "EOD": "</article>",
        },
        "tex": {
            "title1": "~A~\\section*{\a}",
            "title2": "~A~\\subsection*{\a}",
            "title3": "~A~\\subsubsection*{\a}",
            # title 4/5: DIRTY: para+BF+\\+\n
            "title4": "~A~\\paragraph{}\\textbf{\a}\\\\\n",
            "title5": "~A~\\paragraph{}\\textbf{\a}\\\\\n",
            "numtitle1": "\n~A~\\section{\a}",
            "numtitle2": "~A~\\subsection{\a}",
            "numtitle3": "~A~\\subsubsection{\a}",
            "anchor": "\\hypertarget{\a}{}\n",
            "blockVerbOpen": "\\begin{verbatim}",
            "blockVerbClose": "\\end{verbatim}",
            "blockQuoteOpen": "\\begin{quotation}",
            "blockQuoteClose": "\\end{quotation}",
            "fontMonoOpen": "\\texttt{",
            "fontMonoClose": "}",
            "fontBoldOpen": "\\textbf{",
            "fontBoldClose": "}",
            "fontItalicOpen": "\\textit{",
            "fontItalicClose": "}",
            "fontUnderlineOpen": "\\underline{",
            "fontUnderlineClose": "}",
            "fontStrikeOpen": "\\sout{",
            "fontStrikeClose": "}",
            "listOpen": "\\begin{itemize}",
            "listClose": "\\end{itemize}",
            "listOpenCompact": "\\begin{compactitem}",
            "listCloseCompact": "\\end{compactitem}",
            "listItemOpen": "\\item ",
            "numlistOpen": "\\begin{enumerate}",
            "numlistClose": "\\end{enumerate}",
            "numlistOpenCompact": "\\begin{compactenum}",
            "numlistCloseCompact": "\\end{compactenum}",
            "numlistItemOpen": "\\item ",
            "deflistOpen": "\\begin{description}",
            "deflistClose": "\\end{description}",
            "deflistOpenCompact": "\\blistItemOpenegin{compactdesc}",
            "deflistCloseCompact": "\\end{compactdesc}",
            "deflistItem1Open": "\\item[",
            "deflistItem1Close": "]",
            "bar1": "\\hrulefill{}",
            "bar2": "\\rule{\\linewidth}{1mm}",
            "url": "\\href{\a}{\a}",
            "urlMark": "\\href{\a}{\a}",
            "email": "\\href{mailto:\a}{\a}",
            "emailMark": "\\href{mailto:\a}{\a}",
            "img": "\\includegraphics{\a}",
            "tableOpen": "\\begin{center}\\begin{tabular}{|~C~|}",
            "tableClose": "\\end{tabular}\\end{center}",
            "tableRowOpen": "\\hline ",
            "tableRowClose": " \\\\",
            "tableCellSep": " & ",
            "_tableColAlignLeft": "l",
            "_tableColAlignRight": "r",
            "_tableColAlignCenter": "c",
            "_tableCellAlignLeft": "l",
            "_tableCellAlignRight": "r",
            "_tableCellAlignCenter": "c",
            "_tableCellColSpan": "\a",
            "_tableCellMulticolOpen": "\\multicolumn{\a}{|~C~|}{",
            "_tableCellMulticolClose": "}",
            "tableColAlignSep": "|",
            "comment": "% \a",
            "TOC": "\\tableofcontents",
            "pageBreak": "\\clearpage",
            "EOD": "\\end{document}",
        },
        "texs": {
            # TIP texs inherits all tex tags
        },
        "lout": {
            "paragraphOpen": "@LP",
            "blockTitle1Open": "@BeginSections",
            "blockTitle1Close": "@EndSections",
            "blockTitle2Open": " @BeginSubSections",
            "blockTitle2Close": " @EndSubSections",
            "blockTitle3Open": "  @BeginSubSubSections",
            "blockTitle3Close": "  @EndSubSubSections",
            "title1Open": "~A~@Section @Title { \a } @Begin",
            "title1Close": "@End @Section",
            "title2Open": "~A~ @SubSection @Title { \a } @Begin",
            "title2Close": " @End @SubSection",
            "title3Open": "~A~  @SubSubSection @Title { \a } @Begin",
            "title3Close": "  @End @SubSubSection",
            "title4Open": "~A~@LP @LeftDisplay @B { \a }",
            "title5Open": "~A~@LP @LeftDisplay @B { \a }",
            "anchor": "@Tag { \a }\n",
            "blockVerbOpen": "@LP @ID @F @RawVerbatim @Begin",
            "blockVerbClose": "@End @RawVerbatim",
            "blockQuoteOpen": "@QD {",
            "blockQuoteClose": "}",
            # enclosed inside {} to deal with joined**words**
            "fontMonoOpen": "{@F {",
            "fontMonoClose": "}}",
            "fontBoldOpen": "{@B {",
            "fontBoldClose": "}}",
            "fontItalicOpen": "{@II {",
            "fontItalicClose": "}}",
            "fontUnderlineOpen": "{@Underline{",
            "fontUnderlineClose": "}}",
            # the full form is more readable, but could be BL EL LI NL TL DTI
            "listOpen": "@BulletList",
            "listClose": "@EndList",
            "listItemOpen": "@ListItem{",
            "listItemClose": "}",
            "numlistOpen": "@NumberedList",
            "numlistClose": "@EndList",
            "numlistItemOpen": "@ListItem{",
            "numlistItemClose": "}",
            "deflistOpen": "@TaggedList",
            "deflistClose": "@EndList",
            "deflistItem1Open": "@DropTagItem {",
            "deflistItem1Close": "}",
            "deflistItem2Open": "{",
            "deflistItem2Close": "}",
            "bar1": "@DP @FullWidthRule",
            "url": "{blue @Colour { \a }}",
            "urlMark": "\a ({blue @Colour { \a }})",
            "email": "{blue @Colour { \a }}",
            "emailMark": "\a ({blue @Colour{ \a }})",
            "img": "~A~@IncludeGraphic { \a }",  # eps only!
            "_imgAlignLeft": "@LeftDisplay ",
            "_imgAlignRight": "@RightDisplay ",
            "_imgAlignCenter": "@CentredDisplay ",
            # Tables are centred, otherwise last cell spans to right page margin
            "tableOpen": "@LP\n~A~@CentredDisplay @Tbl~B~\n{",
            "tableClose": "\n}",
            "tableRowOpen": "@Row\n",
            "tableTitleRowOpen": "@HeaderRow\n",
            "tableTitleRowClose": "@EndHeaderRow\n",
            "tableCenterAlign": "@CentredDisplay ",
            "tableCellOpen": "\a { ",  # A, B, ...
            "tableCellClose": " }",
            "tableTitleCellOpen": " { @B { ",
            "tableTitleCellClose": " } }",
            "_tableCellAlignRight": " indent { right } ",
            "_tableCellAlignLeft": " indent { left } ",
            "_tableCellAlignCenter": " indent { ctr } ",
            "_tableAlign": "@CentredDisplay ",
            "_tableBorder": "\nrule {yes}",
            "comment": "# \a",
            # @MakeContents must be on the config file
            "TOC": "@DP @ContentsGoesHere @DP",
            "pageBreak": "@NP",
            "EOD": "@End @Text",
        },
        # http://moinmo.in/HelpOnMoinWikiSyntax
        "moin": {
            "title1": "= \a =",
            "title2": "== \a ==",
            "title3": "=== \a ===",
            "title4": "==== \a ====",
            "title5": "===== \a =====",
            "blockVerbOpen": "{{{",
            "blockVerbClose": "}}}",
            "blockQuoteLine": "  ",
            "fontMonoOpen": "{{{",
            "fontMonoClose": "}}}",
            "fontBoldOpen": "'''",
            "fontBoldClose": "'''",
            "fontItalicOpen": "''",
            "fontItalicClose": "''",
            "fontUnderlineOpen": "__",
            "fontUnderlineClose": "__",
            "fontStrikeOpen": "--(",
            "fontStrikeClose": ")--",
            "listItemOpen": " * ",
            "numlistItemOpen": " \a. ",
            "deflistItem1Open": " ",
            "deflistItem1Close": "::",
            "deflistItem2LinePrefix": " :: ",
            "bar1": "----",
            "bar2": "--------",
            "url": "[[\a]]",
            "urlMark": "[[\a|\a]]",
            "email": "\a",
            "emailMark": "[[mailto:\a|\a]]",
            "img": "{{\a}}",
            "tableRowOpen": "||",  # || one || two ||
            "tableCellOpen": "~S~~A~ ",
            "tableCellClose": " ||",
            "_tableCellAlignRight": "<)>",  # ||<)> right ||
            "_tableCellAlignCenter": "<:>",  # ||<:> center ||
            "_tableCellColSpanChar": "||",  # || cell |||| 2 cells spanned ||
            # Another option for span is ||<-2> two cells spanned ||
            # But mixing span+align is harder with the current code:
            # ||<-2:> two cells spanned and centered ||
            # ||<-2)> two cells spanned and right aligned ||
            # Just appending attributes doesn't work:
            # ||<-2><:> no no no ||
            "comment": "/* \a */",
            "TOC": "<<TableOfContents>>",
        },
        # http://code.google.com/p/support/wiki/WikiSyntax
        "gwiki": {
            "title1": "= \a =",
            "title2": "== \a ==",
            "title3": "=== \a ===",
            "title4": "==== \a ====",
            "title5": "===== \a =====",
            "blockVerbOpen": "{{{",
            "blockVerbClose": "}}}",
            "blockQuoteLine": "  ",
            "fontMonoOpen": "{{{",
            "fontMonoClose": "}}}",
            "fontBoldOpen": "*",
            "fontBoldClose": "*",
            "fontItalicOpen": "_",  # underline == italic
            "fontItalicClose": "_",
            "fontStrikeOpen": "~~",
            "fontStrikeClose": "~~",
            "listItemOpen": " * ",
            "numlistItemOpen": " # ",
            "url": "\a",
            "urlMark": "[\a \a]",
            "email": "mailto:\a",
            "emailMark": "[mailto:\a \a]",
            "img": "[\a]",
            "tableRowOpen": "|| ",
            "tableRowClose": " ||",
            "tableCellSep": " || ",
        },
        # http://asciidoc.org/asciidoc.css-embedded.html
        "adoc": {
            "title1": "== \a",
            "title2": "=== \a",
            "title3": "==== \a",
            "title4": "===== \a",
            "title5": "===== \a",
            "blockVerbOpen": "----",
            "blockVerbClose": "----",
            "deflistItem1Close": "::",
            "deflistClose": "",
            "deflistItem2Open": "	",
            "deflistItem2LinePrefix": "	",
            "fontMonoOpen": "+",
            "fontMonoClose": "+",
            "fontBoldOpen": "*",
            "fontBoldClose": "*",
            "fontItalicOpen": "_",
            "fontItalicClose": "_",
            "listItemOpen": " ",
            "listItemLine": "*",
            "numlistItemOpen": "1. ",
            "url": "\a",
            "urlMark": "\a[\a]",
            "email": "mailto:\a",
            "emailMark": "mailto:\a[\a]",
            "img": "image::\a[]",
        },
        # http://www.dokuwiki.org/syntax
        # http://www.dokuwiki.org/playground:playground
        # Hint: <br> is \\ $
        # Hint: You can add footnotes ((This is a footnote))
        "doku": {
            "title1": "===== \a =====",
            "title2": "==== \a ====",
            "title3": "=== \a ===",
            "title4": "== \a ==",
            "title5": "= \a =",
            # DokuWiki uses '  ' identation to mark verb blocks (see indentverbblock)
            "blockQuoteLine": ">",
            "fontMonoOpen": "''",
            "fontMonoClose": "''",
            "fontBoldOpen": "**",
            "fontBoldClose": "**",
            "fontItalicOpen": "//",
            "fontItalicClose": "//",
            "fontUnderlineOpen": "__",
            "fontUnderlineClose": "__",
            "fontStrikeOpen": "<del>",
            "fontStrikeClose": "</del>",
            "listItemOpen": "  * ",
            "numlistItemOpen": "  - ",
            "bar1": "----",
            "url": "[[\a]]",
            "urlMark": "[[\a|\a]]",
            "email": "[[\a]]",
            "emailMark": "[[\a|\a]]",
            "img": "{{\a}}",
            "imgAlignLeft": "{{\a }}",
            "imgAlignRight": "{{ \a}}",
            "imgAlignCenter": "{{ \a }}",
            "tableTitleRowOpen": "^ ",
            "tableTitleRowClose": " ^",
            "tableTitleCellSep": " ^ ",
            "tableRowOpen": "| ",
            "tableRowClose": " |",
            "tableCellSep": " | ",
            # DokuWiki has no attributes. The content must be aligned!
            # '_tableCellAlignRight' : '<)>'           ,  # ??
            # '_tableCellAlignCenter': '<:>'           ,  # ??
            # DokuWiki colspan is the same as txt2tags' with multiple |||
            # 'comment'             : '## \a'         ,  # ??
            # TOC is automatic
        },
        # http://www.pmwiki.org/wiki/PmWiki/TextFormattingRules
        # http://www.pmwiki.org/wiki/Main/WikiSandbox
        "pmw": {
            "title1": "~A~! \a ",
            "title2": "~A~!! \a ",
            "title3": "~A~!!! \a ",
            "title4": "~A~!!!! \a ",
            "title5": "~A~!!!!! \a ",
            "blockQuoteOpen": "->",
            "blockQuoteClose": "\n",
            # In-text font
            "fontLargeOpen": "[+",
            "fontLargeClose": "+]",
            "fontLargerOpen": "[++",
            "fontLargerClose": "++]",
            "fontSmallOpen": "[-",
            "fontSmallClose": "-]",
            "fontLargerOpen": "[--",
            "fontLargerClose": "--]",
            "fontMonoOpen": "@@",
            "fontMonoClose": "@@",
            "fontBoldOpen": "'''",
            "fontBoldClose": "'''",
            "fontItalicOpen": "''",
            "fontItalicClose": "''",
            "fontUnderlineOpen": "{+",
            "fontUnderlineClose": "+}",
            "fontStrikeOpen": "{-",
            "fontStrikeClose": "-}",
            # Lists
            "listItemLine": "*",
            "numlistItemLine": "#",
            "deflistItem1Open": ": ",
            "deflistItem1Close": ":",
            "deflistItem2LineOpen": "::",
            "deflistItem2LineClose": ":",
            # Verbatim block
            "blockVerbOpen": "[@",
            "blockVerbClose": "@]",
            "bar1": "----",
            # URL, email and anchor
            "url": "\a",
            "urlMark": "[[\a -> \a]]",
            "email": "\a",
            "emailMark": "[[\a -> mailto:\a]]",
            "anchor": "[[#\a]]\n",
            # Image markup
            "img": "\a",
            #'imgAlignLeft'         : '{{\a }}'       ,
            #'imgAlignRight'        : '{{ \a}}'       ,
            #'imgAlignCenter'       : '{{ \a }}'      ,
            # Table attributes
            "tableTitleRowOpen": "||! ",
            "tableTitleRowClose": "||",
            "tableTitleCellSep": " ||!",
            "tableRowOpen": "||",
            "tableRowClose": "||",
            "tableCellSep": " ||",
        },
        # http://en.wikipedia.org/wiki/Help:Editing
        # http://www.mediawiki.org/wiki/Sandbox
        "wiki": {
            "title1": "== \a ==",
            "title2": "=== \a ===",
            "title3": "==== \a ====",
            "title4": "===== \a =====",
            "title5": "====== \a ======",
            "blockVerbOpen": "<pre>",
            "blockVerbClose": "</pre>",
            "blockQuoteOpen": "<blockquote>",
            "blockQuoteClose": "</blockquote>",
            "fontMonoOpen": "<tt>",
            "fontMonoClose": "</tt>",
            "fontBoldOpen": "'''",
            "fontBoldClose": "'''",
            "fontItalicOpen": "''",
            "fontItalicClose": "''",
            "fontUnderlineOpen": "<u>",
            "fontUnderlineClose": "</u>",
            "fontStrikeOpen": "<s>",
            "fontStrikeClose": "</s>",
            # XXX Mixed lists not working: *#* list inside numlist inside list
            "listItemLine": "*",
            "numlistItemLine": "#",
            "deflistItem1Open": "; ",
            "deflistItem2LinePrefix": ": ",
            "bar1": "----",
            "url": "[\a]",
            "urlMark": "[\a \a]",
            "urlMarkAnchor": "[[\a|\a]]",
            "email": "mailto:\a",
            "emailMark": "[mailto:\a \a]",
            # [[Image:foo.png|right|Optional alt/caption text]] (right, left, center, none)
            "img": "[[Image:\a~A~]]",
            "_imgAlignLeft": "|left",
            "_imgAlignCenter": "|center",
            "_imgAlignRight": "|right",
            # {| border="1" cellspacing="0" cellpadding="4" align="center"
            "tableOpen": "{|~A~~B~",
            "tableClose": "|}",
            "tableRowOpen": "|-",
            "tableTitleRowOpen": "|-",
            # Note: using one cell per line syntax
            "tableCellOpen": "\n|~A~~S~~Z~ ",
            "tableTitleCellOpen": "\n!~A~~S~~Z~ ",
            "_tableBorder": ' border="1"',
            "_tableAlignCenter": ' align="center"',
            "_tableCellAlignRight": ' align="right"',
            "_tableCellAlignCenter": ' align="center"',
            "_tableCellColSpan": ' colspan="\a"',
            "_tableAttrDelimiter": " |",
            "comment": "<!-- \a -->",
            "TOC": "__TOC__",
        },
        # http://demo.redmine.org/help/wiki_syntax.html
        # http://demo.redmine.org/help/wiki_syntax_detailed.html
        # Sandbox: http://demo.redmine.org - create account, add new project
        "red": {
            "title1": "h1. \a",
            "title2": "h2. \a",
            "title3": "h3. \a",
            "title4": "h4. \a",
            "title5": "h5. \a",
            "fontBoldOpen": "*",
            "fontBoldClose": "*",
            "fontItalicOpen": "_",
            "fontItalicClose": "_",
            "fontStrikeOpen": "-",
            "fontStrikeClose": "-",
            "fontUnderlineOpen": "+",
            "fontUnderlineClose": "+",
            "blockVerbOpen": "<pre>",
            "blockVerbClose": "</pre>",
            "blockQuoteLine": "bq. ",  # XXX It's a *paragraph* prefix. (issues 64, 65)
            "fontMonoOpen": "@",
            "fontMonoClose": "@",
            "listItemLine": "*",
            "numlistItemLine": "#",
            "deflistItem1Open": "* ",
            "url": "\a",
            "urlMark": '"\a":\a',  # "Google":http://www.google.com
            "email": "\a",
            "emailMark": '"\a":\a',
            "img": "!~A~\a!",
            "_imgAlignLeft": "",  # !image.png! (no align == left)
            "_imgAlignCenter": "=",  # !=image.png!
            "_imgAlignRight": ">",  # !>image.png!
            "tableTitleCellOpen": "_.",  # Table header is |_.header|
            "tableTitleCellSep": "|",
            "tableCellOpen": "~S~~A~. ",
            "tableCellSep": "|",
            "tableRowOpen": "|",
            "tableRowClose": "|",
            "_tableCellColSpan": "\\\a",
            "bar1": "---",
            "bar2": "---",
            "TOC": "{{toc}}",
        },
        "vimwiki": {
            "title1": "= \a =",
            "title2": "== \a ==",
            "title3": "=== \a ===",
            "title4": "==== \a ====",
            "title5": "===== \a =====",
            "blockVerbOpen": "{{{",
            "blockVerbClose": "}}}",
            "blockQuoteOpen": "{{{",
            "blockQuoteClose": "}}}",
            "fontMonoOpen": "`",
            "fontMonoClose": "`",
            "fontBoldOpen": " *",
            "fontBoldClose": "* ",
            "fontItalicOpen": " _",
            "fontItalicClose": "_ ",
            #'fontUnderlineOpen'     : '<u>'             ,
            #'fontUnderlineClose'    : '</u>'            ,
            "fontStrikeOpen": " ~~",
            "fontStrikeClose": "~~ ",
            "listItemOpen": "- ",
            "listItemLine": "\t",
            "numlistItemOpen": "# ",
            "numlistItemLine": "\t",
            "bar1": "----",
            "url": "[\a]",
            "urlMark": "[\a \a]",
            "email": "mailto:\a",
            "emailMark": "[mailto:\a \a]",
            "img": "[\a]",
            #'_imgAlignLeft'         : '|left'           ,
            #'_imgAlignCenter'       : '|center'         ,
            #'_imgAlignRight'        : '|right'          ,
            "tableRowOpen": "| ",
            "tableRowClose": " |",
            #'tableTitleRowOpen'     : '|-\n! '          ,
            "tableCellSep": " | ",
            #'tableTitleCellSep'     : ' | '            ,
            #'_tableBorder'          : ' border="1"'     ,
            #'_tableAlignCenter'     : ' align="center"' ,
            "comment": "%% \a",
            "TOC": "%toc",
        },
        # http://www.inference.phy.cam.ac.uk/mackay/mgp/SYNTAX
        # http://en.wikipedia.org/wiki/MagicPoint
        "mgp": {
            "paragraphOpen": '%font "normal", size 5',
            "title1": "%page\n\n\a\n",
            "title2": "%page\n\n\a\n",
            "title3": "%page\n\n\a\n",
            "title4": "%page\n\n\a\n",
            "title5": "%page\n\n\a\n",
            "blockVerbOpen": '%font "mono"',
            "blockVerbClose": '%font "normal"',
            "blockQuoteOpen": '%prefix "       "',
            "blockQuoteClose": '%prefix "  "',
            "fontMonoOpen": '\n%cont, font "mono"\n',
            "fontMonoClose": '\n%cont, font "normal"\n',
            "fontBoldOpen": '\n%cont, font "normal-b"\n',
            "fontBoldClose": '\n%cont, font "normal"\n',
            "fontItalicOpen": '\n%cont, font "normal-i"\n',
            "fontItalicClose": '\n%cont, font "normal"\n',
            "fontUnderlineOpen": '\n%cont, fore "cyan"\n',
            "fontUnderlineClose": '\n%cont, fore "white"\n',
            "listItemLine": "\t",
            "numlistItemLine": "\t",
            "numlistItemOpen": "\a. ",
            "deflistItem1Open": '\t\n%cont, font "normal-b"\n',
            "deflistItem1Close": '\n%cont, font "normal"\n',
            "bar1": '%bar "white" 5',
            "bar2": "%pause",
            "url": '\n%cont, fore "cyan"\n\a' + '\n%cont, fore "white"\n',
            "urlMark": '\a \n%cont, fore "cyan"\n\a' + '\n%cont, fore "white"\n',
            "email": '\n%cont, fore "cyan"\n\a' + '\n%cont, fore "white"\n',
            "emailMark": '\a \n%cont, fore "cyan"\n\a' + '\n%cont, fore "white"\n',
            "img": '~A~\n%newimage "\a"\n%left\n',
            "_imgAlignLeft": "\n%left",
            "_imgAlignRight": "\n%right",
            "_imgAlignCenter": "\n%center",
            "comment": "%% \a",
            "pageBreak": "%page\n\n\n",
            "EOD": "%%EOD",
        },
        # man groff_man ; man 7 groff
        "man": {
            "paragraphOpen": ".P",
            "title1": ".SH \a",
            "title2": ".SS \a",
            "title3": ".SS \a",
            "title4": ".SS \a",
            "title5": ".SS \a",
            "blockVerbOpen": ".nf",
            "blockVerbClose": ".fi\n",
            "blockQuoteOpen": ".RS",
            "blockQuoteClose": ".RE",
            "fontBoldOpen": "\\fB",
            "fontBoldClose": "\\fR",
            "fontItalicOpen": "\\fI",
            "fontItalicClose": "\\fR",
            "listOpen": ".RS",
            "listItemOpen": r".IP \(bu 3\n",
            "listClose": ".RE\n.IP",
            "numlistOpen": ".RS",
            "numlistItemOpen": ".IP \a. 3\n",
            "numlistClose": ".RE\n.IP",
            "deflistItem1Open": ".TP\n",
            "bar1": "\n\n",
            "url": "\a",
            "urlMark": "\a (\a)",
            "email": "\a",
            "emailMark": "\a (\a)",
            "img": "\a",
            "tableOpen": ".TS\n~A~~B~tab(^); ~C~.",
            "tableClose": ".TE",
            "tableRowOpen": " ",
            "tableCellSep": "^",
            "_tableAlignCenter": "center, ",
            "_tableBorder": "allbox, ",
            "_tableColAlignLeft": "l",
            "_tableColAlignRight": "r",
            "_tableColAlignCenter": "c",
            "comment": '.\\" \a',
        },
        # see http://utroff.org
        "utmac": {
            "paragraphOpen": ".PP",
            "title1": ".\n.H2 \a",
            "title2": ".\n.H3 \a",
            "title3": ".\n.H4 \a",
            "title4": ".PP\n\\*B\a\\*R\n.br\n",
            "title5": ".PP\n\\*B\a\\*R",
            "blockVerbOpen": ".PX",
            "blockQuoteOpen": ".PQ",
            "fontBoldOpen": "\\*B",
            "fontBoldClose": "\\*R",
            "fontItalicOpen": "\\*I",
            "fontItalicClose": "\\*R",
            "fontUnderlineOpen": "\\*[underl ",
            "fontUnderlineClose": "]",
            "fontStrikeOpen": "\\*[strike ",
            "fontStrikeClose": "]",
            "listItemOpen": ".PI \n",
            "numlistItemOpen": ".PI \a\n",
            "deflistItem1Open": ".PI ",
            "bar1": ".sp 2v",
            "bar2": ".bp",
            "anchor": '\a\\A"\a"',
            "url": '\\*[url "\a" "\a"]',
            "urlMark": '\\*[url "\a" "\a"]',
            "email": '\\*[mail "\a" "\a"]',
            "emailMark": '\\*[mail "\a" "\a"]',
            "img": '\n.\\" \a',
            "tableOpen": ".TS\n~A~~B~tab(^); ~C~.",
            "tableClose": ".TE",
            "tableRowOpen": " ",
            "tableCellSep": "^",
            "_tableAlignCenter": "center, ",
            "_tableBorder": "allbox, ",
            "_tableColAlignLeft": "l",
            "_tableColAlignRight": "r",
            "_tableColAlignCenter": "c",
            "comment": '.\\" \a',
            "blockCommentOpen": ".ig",
            "blockCommentClose": "..",
            "pageBreak": ".bp",
            "TOC": ".XT",
        },
        # http://www.spip-contrib.net/Les-raccourcis-typographiques-en
        # http://www.spip-contrib.net/Carnet-Bac-a-Sable
        # some tags are not implemented by spip tags, but spip accept html tags.
        "spip": {
            "title1": "{{{ \a }}}",
            "title2": "<h4>\a</h4>",
            "title3": "<h5>\a</h5>",
            "blockVerbOpen": "<cadre>",
            "blockVerbClose": "</cadre>",
            "blockQuoteOpen": "<quote>",
            "blockQuoteClose": "</quote>",
            "fontMonoOpen": "<code>",
            "fontMonoClose": "</code>",
            "fontBoldOpen": "{{",
            "fontBoldClose": "}}",
            "fontItalicOpen": "{",
            "fontItalicClose": "}",
            "fontUnderlineOpen": "<u>",
            "fontUnderlineClose": "</u>",
            "fontStrikeOpen": "<del>",
            "fontStrikeClose": "</del>",
            "listItemOpen": "-",  # -* list, -** sublist, -*** subsublist
            "listItemLine": "*",
            "numlistItemOpen": "-",  # -# list, -## sublist, -### subsublist
            "numlistItemLine": "#",
            "bar1": "----",
            "url": "[->\a]",
            "urlMark": "[\a->\a]",
            "email": "[->\a]",
            "emailMark": "[\a->\a]",
            "img": '<img src="\a" />',
            "imgAlignLeft": '<img src="\a" align="left" />',
            "imgAlignRight": '<img src="\a" align="right" />',
            "imgAlignCenter": '<img src="\a" align="center" />',
            "tableTitleRowOpen": "| {{",
            "tableTitleRowClose": "}} |",
            "tableTitleCellSep": "}} | {{",
            "tableRowOpen": "| ",
            "tableRowClose": " |",
            "tableCellSep": " | ",
            # TOC is automatic whith title1 when plugin "couteau suisse" is activate and the option "table des matieres" activate.
        },
        "pm6": {
            "paragraphOpen": "<@Normal:>",
            "title1": "<@Title1:>\a",
            "title2": "<@Title2:>\a",
            "title3": "<@Title3:>\a",
            "title4": "<@Title4:>\a",
            "title5": "<@Title5:>\a",
            "blockVerbOpen": "<@PreFormat:>",
            "blockQuoteLine": "<@Quote:>",
            "fontMonoOpen": '<FONT "Lucida Console"><SIZE 9>',
            "fontMonoClose": "<SIZE$><FONT$>",
            "fontBoldOpen": "<B>",
            "fontBoldClose": "<P>",
            "fontItalicOpen": "<I>",
            "fontItalicClose": "<P>",
            "fontUnderlineOpen": "<U>",
            "fontUnderlineClose": "<P>",
            "listOpen": "<@Bullet:>",
            "listItemOpen": "\x95\t",  # \x95 == ~U
            "numlistOpen": "<@Bullet:>",
            "numlistItemOpen": "\x95\t",
            "bar1": "\a",
            "url": "<U>\a<P>",  # underline
            "urlMark": "\a <U>\a<P>",
            "email": "\a",
            "emailMark": "\a \a",
            "img": "\a",
        },
        # http://www.wikicreole.org/wiki/AllMarkup
        "creole": {
            "title1": "= \a =",
            "title2": "== \a ==",
            "title3": "=== \a ===",
            "title4": "==== \a ====",
            "title5": "===== \a =====",
            "blockVerbOpen": "{{{",
            "blockVerbClose": "}}}",
            "blockQuoteLine": "  ",
            #   'fontMonoOpen'         : '##'            ,  # planned for 2.0,
            #   'fontMonoClose'        : '##'            ,  # meanwhile we disable it
            "fontBoldOpen": "**",
            "fontBoldClose": "**",
            "fontItalicOpen": "//",
            "fontItalicClose": "//",
            "fontUnderlineOpen": "//",  # no underline in 1.0, planned for 2.0,
            "fontUnderlineClose": "//",  # meanwhile we can use italic (emphasized)
            #   'fontStrikeOpen'       : '--'            ,  # planned for 2.0,
            #   'fontStrikeClose'      : '--'            ,  # meanwhile we disable it
            "listItemLine": "*",
            "numlistItemLine": "#",
            "deflistItem2LinePrefix": ":",
            "bar1": "----",
            "url": "[[\a]]",
            "urlMark": "[[\a|\a]]",
            "img": "{{\a}}",
            "tableTitleRowOpen": "|= ",
            "tableTitleRowClose": "|",
            "tableTitleCellSep": " |= ",
            "tableRowOpen": "| ",
            "tableRowClose": " |",
            "tableCellSep": " | ",
            # TODO: placeholder (mark for unknown syntax)
            # if possible: http://www.wikicreole.org/wiki/Placeholder
        },
        # regular markdown: http://daringfireball.net/projects/markdown/syntax
        # markdown extra:   http://michelf.com/projects/php-markdown/extra/
        # sandbox:
        # http://daringfireball.net/projects/markdown/dingus
        # http://michelf.com/projects/php-markdown/dingus/
        "md": {
            "title1": "# \a ",
            "title2": "## \a ",
            "title3": "### \a ",
            "title4": "#### \a ",
            "title5": "##### \a ",
            "blockVerbLine": "    ",
            "blockQuoteLine": "> ",
            "fontMonoOpen": "`",
            "fontMonoClose": "`",
            "fontBoldOpen": "**",
            "fontBoldClose": "**",
            "fontItalicOpen": "*",
            "fontItalicClose": "*",
            "fontUnderlineOpen": "",
            "fontUnderlineClose": "",
            "fontStrikeOpen": "~~",
            "fontStrikeClose": "~~",
            # Lists
            #'listOpenCompact'     : '*'             ,
            "listItemLine": " ",
            "listItemOpen": "*",
            #'numlistItemLine'     : '1.'            ,
            "numlistItemOpen": "1.",
            "deflistItem1Open": ": ",
            #'deflistItem1Close'     : ':'           ,
            #'deflistItem2LineOpen'  : '::'          ,
            #'deflistItem2LineClose' : ':'           ,
            # Verbatim block
            #'blockVerbOpen'        : ''             ,
            #'blockVerbClose'       : ''             ,
            "bar1": "---",
            "bar2": "---",
            # URL, email and anchor
            "url": "\a",
            "urlMark": "[\a](\a)",
            "email": "\a",
            #'emailMark'             : '[[\a -> mailto:\a]]',
            #'anchor'                : '[[#\a]]\n'   ,
            # Image markup
            "img": "![](\a)",
            #'imgAlignLeft'         : '{{\a }}'      ,
            #'imgAlignRight'        : '{{ \a}}'      ,
            #'imgAlignCenter'       : '{{ \a }}'     ,
            # Table attributes
            "tableTitleRowOpen": "| ",
            "tableTitleRowClose": "|\n|---------------|",
            "tableTitleCellSep": " |",
            "tableRowOpen": "|",
            "tableRowClose": "|",
            "tableCellSep": " |",
        },
        # gemtext (gemini) https://gemini.circumlunar.space/docs/gemtext.gmi
        "gmi": {
            "title1": "# \a ",
            "title2": "## \a ",
            "title3": "### \a ",
            "title4": "### \a ",
            "title5": "### \a ",
            "blockVerbLine": "    ",
            "blockQuoteLine": "> ",
            "fontMonoOpen": "",
            "fontMonoClose": "",
            "fontBoldOpen": "",
            "fontBoldClose": "",
            "fontItalicOpen": "",
            "fontItalicClose": "",
            "fontUnderlineOpen": "",
            "fontUnderlineClose": "",
            "fontStrikeOpen": "",
            "fontStrikeClose": "",
            # Lists
            #'listOpenCompact'     : '*'             ,
            "listItemLine": "",
            "listItemOpen": "*",
            #'numlistItemLine'     : '1.'            ,
            "numlistItemOpen": "*",
            "deflistItem1Open": "*",
            #'deflistItem1Close'     : ':'           ,
            #'deflistItem2LineOpen'  : '::'          ,
            #'deflistItem2LineClose' : ':'           ,
            # Verbatim block
            #'blockVerbOpen'        : ''             ,
            #'blockVerbClose'       : ''             ,
            "bar1": "```================```",
            "bar2": "```----------------```",
            # URL, email and anchor
            "url": "=> \a",
            "urlMark": "=> \a \a",
            "email": "\a",
            #'emailMark'             : '[[\a -> mailto:\a]]',
            #'anchor'                : '[[#\a]]\n'   ,
            # Image markup
            "img": "=> \a",
            #'imgAlignLeft'         : '{{\a }}'      ,
            #'imgAlignRight'        : '{{ \a}}'      ,
            #'imgAlignCenter'       : '{{ \a }}'     ,
            # Table attributes
            "tableTitleRowOpen": "| ",
            "tableTitleRowClose": "|\n|---------------|",
            "tableTitleCellSep": " |",
            "tableRowOpen": "|",
            "tableRowClose": "|",
            "tableCellSep": " |",
        },
        # http://www.phpbb.com/community/faq.php?mode=bbcode
        # http://www.bbcode.org/reference.php (but seldom implemented)
        "bbcode": {
            "title1": "[size=200]\a[/size]",
            "title2": "[size=170]\a[/size]",
            "title3": "[size=150]\a[/size]",
            "title4": "[size=130]\a[/size]",
            "title5": "[size=120]\a[/size]",
            "blockQuoteOpen": "[quote]",
            "blockQuoteClose": "[/quote]",
            "fontMonoOpen": "[code]",
            "fontMonoClose": "[/code]",
            "fontBoldOpen": "[b]",
            "fontBoldClose": "[/b]",
            "fontItalicOpen": "[i]",
            "fontItalicClose": "[/i]",
            "fontUnderlineOpen": "[u]",
            "fontUnderlineClose": "[/u]",
            #'fontStrikeOpen'       : '[s]'            , (not supported by phpBB)
            #'fontStrikeClose'      : '[/s]'           ,
            "listOpen": "[list]",
            "listClose": "[/list]",
            "listItemOpen": "[*]",
            #'listItemClose'        : '[/li]'          ,
            "numlistOpen": "[list=1]",
            "numlistClose": "[/list]",
            "numlistItemOpen": "[*]",
            "url": "[url]\a[/url]",
            "urlMark": "[url=\a]\a[/url]",
            #'urlMark'              : '[url]\a[/url]',
            "img": "[img]\a[/img]",
            #'tableOpen'            : '[table]',
            #'tableClose'           : '[/table]'       ,
            #'tableRowOpen'         : '[tr]'           ,
            #'tableRowClose'        : '[/tr]'          ,
            #'tableCellOpen'        : '[td]'           ,
            #'tableCellClose'       : '[/td]'          ,
            #'tableTitleCellOpen'   : '[th]'           ,
            #'tableTitleCellClose'  : '[/th]'          ,
        },
        # http://en.wikipedia.org/wiki/Rich_Text_Format
        # Based on RTF Version 1.5 specification
        # Should be compatible with MS Word 97 and newer
        # ~D~ and ~L~ are used to encode depth and nesting level formatting
        "rtf": {
            "title1": "~A~{\\pard\\plain\\s11\\keepn{\\*\\txttags title1}\\f1\\fs24\\qc\\sb240\\sa240\\sl480\\slmult1\\li0\\ri0\\fi0{\\b{\a}}\\par}",
            "title2": "~A~{\\pard\\plain\\s12\\keepn{\\*\\txttags title2}\\f1\\fs24\\ql\\sb240\\sa240\\sl480\\slmult1\\li0\\ri0\\fi0{\\b{\a}}\\par}",
            "title3": "~A~{\\pard\\plain\\s13\\keepn{\\*\\txttags title3}\\f1\\fs24\\ql\\sb240\\sa240\\sl480\\slmult1\\li360\\ri0\\fi0{\\b{\a}}\\par}",
            "title4": "~A~{\\pard\\plain\\s14\\keepn{\\*\\txttags title4}\\f1\\fs24\\ql\\sb240\\sa240\\sl480\\slmult1\\li360\\ri0\\fi0{\\b\\i{\a}}\\par}",
            "title5": "~A~{\\pard\\plain\\s15\\keepn{\\*\\txttags title5}\\f1\\fs24\\ql\\sb240\\sa240\\sl480\\slmult1\\li360\\ri0\\fi0{\\i{\a}}\\par}",
            "numtitle1": "~A~{\\pard\\plain\\s11\\keepn{\\*\\txttags title1}\\f1\\fs24\\qc\\sb240\\sa240\\sl480\\slmult1\\li0\\ri0\\fi0\\ls3\\ilvl0{\\b{\a}}\\par}",
            "numtitle2": "~A~{\\pard\\plain\\s12\\keepn{\\*\\txttags title2}\\f1\\fs24\\ql\\sb240\\sa240\\sl480\\slmult1\\li0\\ri0\\fi0\\ls3\\ilvl1{\\b{\a}}\\par}",
            "numtitle3": "~A~{\\pard\\plain\\s13\\keepn{\\*\\txttags title3}\\f1\\fs24\\ql\\sb240\\sa240\\sl480\\slmult1\\li360\\ri0\\fi0\\ls3\\ilvl2{\\b{\a}}\\par}",
            "numtitle4": "~A~{\\pard\\plain\\s14\\keepn{\\*\\txttags title4}\\f1\\fs24\\ql\\sb240\\sa240\\sl480\\slmult1\\li360\\ri0\\fi0\\ls3\\ilvl3{\\b\\i{\a}}\\par}",
            "numtitle5": "~A~{\\pard\\plain\\s15\\keepn{\\*\\txttags title5}\\f1\\fs24\\ql\\sb240\\sa240\\sl480\\slmult1\\li360\\ri0\\fi0\\ls3\\ilvl4{\\i{\a}}\\par}",
            "paragraphOpen": "{\\pard\\plain\\s2{\\*\\txttags paragraph}\\f0\\fs24\\qj\\sb0\\sa0\\sl480\\slmult1\\li~D~\\ri0\\fi360",
            "paragraphClose": "\\par}",
            "blockVerbOpen": "{\\pard\\plain\\s3{\\*\\txttags verbatim}\\f2\\fs20\\ql\\sb0\\sa240\\sl240\\slmult1\\li720\\ri720\\fi0",
            "blockVerbSep": "\\line",
            "blockVerbClose": "\\par}",
            "blockQuoteOpen": "{\\pard\\plain\\s4{\\*\\txttags quote}\\f0\\fs24\\qj\\sb0\\sa0\\sl480\\slmult1\\li~D~\\ri720\\fi0",
            "blockQuoteClose": "\\par}",
            "fontMonoOpen": "{\\f2\\fs20{",
            "fontMonoClose": "}}",
            "fontBoldOpen": "{\\b{",
            "fontBoldClose": "}}",
            "fontItalicOpen": "{\\i{",
            "fontItalicClose": "}}",
            "fontUnderlineOpen": "{\\ul{",
            "fontUnderlineClose": "}}",
            "fontStrikeOpen": "{\\strike{",
            "fontStrikeClose": "}}",
            "anchor": "{\\*\\bkmkstart \a}{\\*\\bkmkend \a}",
            # 'comment'               : '{\\v \a }',  # doesn't hide text in all readers
            "pageBreak": "\\page\n",
            "EOD": "}",
            "url": '{\\field{\\*\\fldinst{HYPERLINK "\a"}}{\\fldrslt{\\ul\\cf1 \a}}}',
            "urlMark": '{\\field{\\*\\fldinst{HYPERLINK "\a"}}{\\fldrslt{\\ul\\cf1 \a}}}',
            "email": '{\\field{\\*\\fldinst{HYPERLINK "mailto:\a"}}{\\fldrslt{\\ul\\cf1 \a}}}',
            "emailMark": '{\\field{\\*\\fldinst{HYPERLINK "mailto:\a"}}{\\fldrslt{\\ul\\cf1 \a}}}',
            "img": '{\\field{\\*\\fldinst{INCLUDEPICTURE "\a" \\\\* MERGEFORMAT \\\\d}}{\\fldrslt{(\a)}}}',
            "imgEmbed": r"{\*\shppict{\pict\a}}",
            "listOpen": "{\\pard\\plain\\s21{\\*\\txttags list}\\f0\\fs24\\qj\\sb0\\sa0\\sl480\\slmult1",
            "listClose": "}",
            "listItemOpen": "{\\*\\listtext{\\*\\txttags list indent}\\li~D~\\ri0\\fi-360\\'95\\tab}\\ls1\\ilvl~L~{\\*\\txttags list indent}\\li~D~\\ri0\\fi-360\n",
            "listItemClose": "\\par",
            "numlistOpen": "{\\pard\\plain\\s21{\\*\\txttags list}\\f0\\fs24\\qj\\sb0\\sa0\\sl480\\slmult1",
            "numlistClose": "}",
            "numlistItemOpen": "{\\*\\listtext{\\*\\txttags list indent}\\li~D~\\ri0\\fi-360 \a.\\tab}\\ls2\\ilvl~L~{\\*\\txttags list indent}\\li~D~\\ri0\\fi-360\n",
            "numlistItemClose": "\\par",
            "deflistOpen": "{\\pard\\plain\\s21{\\*\\txttags list}\\f0\\fs24\\qj\\sb0\\sa0\\sl480\\slmult1",
            "deflistClose": "}",
            "deflistItem1Open": "{\\*\\txttags list indent}\\li~D~\\ri0\\fi-360{\\b\n",
            "deflistItem1Close": ":}\\tab",
            "deflistItem2Open": "",
            "deflistItem2Close": "\\par",
            "tableOpen": "{\\pard\\plain",
            "tableClose": "\\par}",
            "tableRowOpen": "{\\trowd\\trgaph60~A~~B~",
            "tableRowClose": "\\row}",
            "tableRowSep": "",
            "tableTitleRowOpen": "{\\trowd\\trgaph60\\trhdr~A~~B~\\trbrdrt\\brdrs\\brdrw20\\trbrdrb\\brdrs\\brdrw20",
            "tableTitleRowClose": "",
            "tableCellOpen": "{\\intbl\\itap1\\f0\\fs20~A~ ",
            "tableCellClose": "\\cell}",
            "tableCellHead": "~B~~S~",
            "tableTitleCellOpen": "{\\intbl\\itap1\\f0\\fs20~A~\\b ",
            "tableTitleCellClose": "\\cell}",
            "tableTitleCellHead": "~B~\\clbrdrt\\brdrs\\brdrw20\\clbrdrb\\brdrs\\brdrw20~S~",
            "_tableCellColSpan": "\\cellx\a",
            "_tableAlignLeft": "\\trql",
            "_tableAlignCenter": "\\trqc",
            "_tableBorder": "\\trbrdrt\\brdrs\\brdrw10\\trbrdrb\\brdrs\\brdrw10\\trbrdrl\\brdrs\\brdrw10\\trbrdrr\\brdrs\\brdrw10",
            "_tableCellAlignLeft": "\\ql",
            "_tableCellAlignRight": "\\qr",
            "_tableCellAlignCenter": "\\qc",
            "_tableCellBorder": "\\clbrdrt\\brdrs\\brdrw10\\clbrdrb\\brdrs\\brdrw10\\clbrdrl\\brdrs\\brdrw10\\clbrdrr\\brdrs\\brdrw10",
            "bar1": "{\\pard\\plain\\s1\\brdrt\\brdrs\\brdrw10\\li1400\\sb120\\sa120\\ri1400\\fs12\\par}",
            "bar2": "{\\pard\\plain\\s1\\brdrt\\brdrs\\brdrdb\\brdrw10\\sb120\\sa120\\li1400\\ri1400\\fs12\\par}",
        },
        # http://foswiki.org/System/TextFormattingRules
        # http://twiki.org/cgi-bin/view/TWiki/TextFormattingRules
        "tml": {
            "title1": "---++ \a",
            "title2": "---+++ \a",
            "title3": "---++++ \a",
            "title4": "---+++++ \a",
            "title5": "---++++++ \a",
            "blockVerbOpen": "<verbatim>",
            "blockVerbClose": "</verbatim>",
            "blockQuoteOpen": "<blockquote>",
            "blockQuoteClose": "</blockquote>",
            "fontMonoOpen": "=",
            "fontMonoClose": "=",
            "fontBoldOpen": "*",
            "fontBoldClose": "*",
            "fontItalicOpen": "_",
            "fontItalicClose": "_",
            "fontUnderlineOpen": "<u>",
            "fontUnderlineClose": "</u>",
            "fontStrikeOpen": "<del>",
            "fontStrikeClose": "</del>",
            "listItemLine": "   ",
            "listItemOpen": "* ",
            "numlistItemLine": "   ",
            "numlistItemOpen": "1. ",
            "deflistItemLine": "   ",
            "deflistItem1Open": "$ ",
            "deflistItem2Open": ": ",
            "bar1": "---",
            "bar2": "---",
            "img": '<img~A~ src="%ATTACHURL%/\a" border="0" alt="">',
            "urlImg": '[[\a][<img~A~ src="%ATTACHURL%/\a" border="0" alt="">]]',
            "imgEmbed": '<img~A~ src="%ATTACHURL%/\a" border="0" alt="">',
            "_imgAlignLeft": ' align="left"',
            "_imgAlignCenter": ' align="middle"',
            "_imgAlignRight": ' align="right"',
            "url": "[[\a]]",
            "urlMark": "[[\a][\a]]",
            "anchor": "[[#\a]]\n",
            "urlMarkAnchor": "[[\a][\a]]",
            "email": "\a",
            "emailMark": "[[mailto:\a][\a]]",
            "tableRowOpen": "|",
            "tableRowClose": "|",
            "tableTitleCellOpen": " *",
            "tableTitleCellClose": "* ",
            "tableTitleCellSep": "|",
            "tableCellOpen": " ",
            "tableCellClose": " ~S~",
            "tableCellSep": "|",
            "_tableCellColSpan": "|",
            "comment": "<!-- \a -->",
            "TOC": "%TOC%",
        },
        #
        ## MOM ##
        #
        # for mom macros documentation see: http://www.schaffter.ca/mom/mom-01.html
        # I commented the difficult parts...
        "mom": {
            "paragraphOpen": ".PP",
            "title1": '.HEAD "\a"',
            "title2": '.SUBHEAD "\a"',
            "title3": '.SUBSUBHEAD "\a"',
            "title4": '.PP\n.PARAHEAD "\a"',
            "title5": '.PP\n.PARAHEAD "\\*[UL]\a\\f[R]\\"',  # my choice
            # NB for mom ALL heads of a level after the first numbered are numbered!
            # The "NUMBER_*" macros are toggle ones
            "numtitle1": '.NUMBER_HEADS\n.HEAD "\a"',
            "numtitle2": '.NUMBER_SUBHEADS\n.SUBHEAD "\a"',
            "numtitle3": '.NUMBER_SUBSUBHEADS\n.SUBSUBHEAD "\a"',
            "numtitle4": '.NUMBER_PARAHEADS\n.PP\nPARAHEAD "\a"',
            "numtitle5": '.NUMBER_PARAHEADS\n.PP\n.PARAHEAD "\\*[UL]\a\\f[R]\\"',  # my choice
            #        'anchor'               : '"\a"', # not supported
            "blockVerbOpen": ".QUOTE\n.CODE",  # better for quoting code
            "blockVerbClose": ".CODE OFF\n.QUOTE OFF",
            "blockVerbLine ": ".QUOTE\n.CODE\n\a\n.CODE OFF\n.QUOTE OFF",
            "blockQuoteOpen": ".BLOCKQUOTE",
            "blockQuoteClose": ".BLOCKQUOTE OFF",
            #        'blockQuoteLine'       : '.BLOCKQUOTE\n\a\.BLOCKQUOTE OFF' ,
            "fontMonoOpen": "\\f[CR]",
            "fontMonoClose": "\\f[]",
            "fontBoldOpen": "\\f[B]",
            "fontBoldClose": "\\f[]",
            "fontItalicOpen": "\\f[I]",
            "fontItalicClose": "\\f[]",
            "fontUnderlineOpen": "\\*[FWD 8p]\\*[UL]",  # dirty trick for a bug(?) in mom!
            "fontUnderlineClose": "\\*[ULX]",
            # Strike. Not directly supported. A groff geek could do a macro for that, not me! :-(
            # Use this tricks to emulate "a sort of" strike through word.
            # It strikes start and end of a word.
            # Not good for less than 3 chars word
            # For 4 or 5 chars word is not bad!
            # Beware of escapes trying to change it!
            # No! It's too ugly!
            #        'fontStrikeOpen'       : '\\v\'-0.25m\'\\l\'1P\'\\h\'-1P\'\\v\'0.25m\'' ,
            #        'fontStrikeClose'      : '\\v\'-0.25m\'\\l\'-1P\'\\v\'0.25m\'' ,
            # Prefer a sort of tag to point out situation
            "fontStrikeOpen": r"[\(mi",
            "fontStrikeClose": r"\(mi]",
            "listOpen": ".LIST BULLET",  # other kinds of lists are possible, see mom documentation at site
            "listClose": ".LIST OFF",
            "listItemOpen": ".ITEM\n",
            "numlistOpen": ".LIST DIGIT",
            "numlistClose": ".LIST OFF",
            "numlistItemOpen": ".ITEM\n",
            "deflistOpen": "\\# DEF LIST ON",  # deflist non supported but "permitted" using PARAHEAD macro or some other hack
            "deflistClose": "\\# DEF LIST OFF",
            #        'deflistItem1Open'     : '.BR\n.PT_SIZE +1\n\\f[B]' , # trick 1
            #        'deflistItem1Close'    : '\\f[P]\n.PT_SIZE -1'      , # trick 2 for deflist
            "deflistItem1Open": '.PP\n.PARAHEAD "',  # using PARAHEAD is better, it needs PP before.
            "deflistItem1Close": ': "',  # "colon" is a personal choice...
            "bar1": ".LINEBREAK",  # section break
            "bar2": ".NEWPAGE",  # new page
            "url": "\a",
            # urlMark outputs like this: "label (http://ser.erfg.gov)". Needs a
            # preproc rule to transform #anchor links, not used by mom, in
            # labels only. Like this one: '\[(.+) #.+\]' '\1'   without that
            # one obtains: label (#anchor)
            "urlMark": "\a (\a)",
            "email": "\a",
            "emailMark": "\a (\a)",  # like urlMark
            "urlImg": '.PSPIC "\a"\n.(\a)\n.SHIM\n',  # Mmmh...
            # NB images: works only with .ps and .eps images (postscript and
            # encapsulated postscript) easily obtained with "convert" (in
            # ImageMagick suite) from *jpg, *png ecc. It's groff!
            "img": '.PSPIC "\a"\n.SHIM\n',
            "imgAlignLeft": '.PSPIC -L "\a"\n.SHIM\n',
            "imgAlignCenter": '.PSPIC "\a"\n.SHIM\n',
            "imgAlignRight": '.PSPIC -R "\a"\n.SHIM\n',
            # All table stuff copied from man target! Tables need
            # preprocessing with "tbl" using option "-t" with groff
            "tableOpen": ".TS\n~A~~B~tab(^); ~C~.",
            "tableClose": ".TE",
            "tableRowOpen": " ",
            "tableCellSep": "^",
            "_tableAlignCenter": "center, ",
            "_tableBorder": "allbox, ",
            "_tableColAlignLeft": "l",
            "_tableColAlignRight": "r",
            "_tableColAlignCenter": "c",
            #        'cssOpen'              : '<STYLE TYPE="text/css">',
            #        'cssClose'             : '</STYLE>',
            "comment": "\\# \a",
            "blockCommentOpen": ".COMMENT",
            "blockCommentClose": ".COMMENT OFF",
            "TOC": ".TOC",  # NB: it must be the last macro in file!
            "EOD": ".FINIS",
        },
    }
    for target in TARGETS_LIST:
        if getattr(getattr(targets, target), "RULES", {}).get("confdependenttags"):
            importlib.reload(getattr(targets, target))
        alltags[target] = getattr(getattr(targets, target), "state.TAGS", {})

    # Exceptions for --css-sugar
    if (
        config["css-sugar"] and config["target"] in ("html", "xhtml", "xhtmls")
    ) or config["target"] == "wp":
        # Change just HTML because XHTML inherits it
        htmltags = alltags["html"]
        # Table with no cellpadding
        htmltags["tableOpen"] = htmltags["tableOpen"].replace(' CELLPADDING="4"', "")
        # DIVs
        htmltags["tocOpen"] = '<DIV CLASS="toc">'
        htmltags["tocClose"] = "</DIV>"
        htmltags["bodyOpen"] = '<DIV CLASS="body" ID="body">'
        htmltags["bodyClose"] = "</DIV>"

    # Make the HTML -> XHTML inheritance
    xhtml = alltags["html"].copy()
    for key in list(xhtml.keys()):
        xhtml[key] = xhtml[key].lower()
    # Some like HTML tags as lowercase, some don't... (headers out)
    if HTML_LOWER:
        alltags["html"] = xhtml.copy()
    if config["target"] == "htmls":
        alltags["htmls"] = alltags["html5"].copy()
    if config["target"] == "texs":
        alltags["texs"] = alltags["tex"].copy()
    if config["target"] == "csvs":
        alltags["csvs"] = alltags["csv"].copy()
    if config["target"] in ("xhtml", "xhtmls", "html5", "htmls", "wp"):
        xhtml.update(alltags[config["target"]])
        alltags[config["target"]] = xhtml.copy()

    if config["target"] == "aat" and config["slides"]:
        alltags["aat"]["urlMark"] = alltags["aat"]["emailMark"] = "\a (\a)"
        alltags["aat"]["bar1"] = aa_line(AA["bar1"], config["width"] - 2)
        alltags["aat"]["bar2"] = aa_line(AA["bar2"], config["width"] - 2)
        if not config["chars"]:
            alltags["aat"]["listItemOpen"] = "* "
    if config["target"] == "aat" and config["web"]:
        alltags["aat"]["url"] = alltags["aat"]["urlMark"] = '<a href="\a">\a</a>'
        alltags["aat"]["email"] = alltags["aat"]["emailMark"] = (
            '<a href="mailto:\a">\a</a>'
        )
        alltags["aat"]["img"] = '<img src="\a" alt=""/>'
        alltags["aat"]["anchor"] = '<a id="\a">'
        alltags["aat"]["comment"] = "<!-- \a -->"
        for beautifier in ["Bold", "Italic", "Underline", "Strike"]:
            _open, close = "font" + beautifier + "Open", "font" + beautifier + "Close"
            alltags["aat"][_open], alltags["aat"][close] = (
                alltags["html"][_open].lower(),
                alltags["html"][close].lower(),
            )

    # Compose the target tags dictionary
    tags = {}
    target_tags = alltags[config["target"]].copy()

    for key in keys:
        tags[key] = ""  # create empty keys
    for key in list(target_tags.keys()):
        tags[key] = maskEscapeChar(target_tags[key])  # populate

    # Map strong line to pagebreak
    if state.rules["mapbar2pagebreak"] and tags["pageBreak"]:
        tags["bar2"] = tags["pageBreak"]

    # Change img tag if embedding images in RTF
    if config["embed-images"]:
        if tags.get("imgEmbed"):
            tags["img"] = tags["imgEmbed"]
        else:
            Error(
                _("Invalid --embed-images option with target '%s'." % config["target"])
            )

    # Map strong line to separator if not defined
    if not tags["bar2"] and tags["bar1"]:
        tags["bar2"] = tags["bar1"]

    return tags


##############################################################################


