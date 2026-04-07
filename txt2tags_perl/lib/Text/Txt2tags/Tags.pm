package Text::Txt2tags::Tags;

# txt2tags - tag strings per output target
# Port of txt2tags3_mod/tags.py to Perl 5
#
# Convention (same as Python original):
#   \a  – placeholder for the current text inside the mark
#   ~A~ – image/table alignment expansion
#   ~B~ – table border expansion
#   ~S~ – cell colspan expansion
#   ~C~ – column alignment expansion

use strict;
use warnings;
use Exporter 'import';

our $VERSION = '3.9.0';

use Text::Txt2tags::Constants qw(%AA %RST %CSV);

# All tag key names (used to zero-initialise the returned hash)
my @TAG_KEYS = split ' ', <<'END';
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
    blockVerbOpen       blockVerbClose      blockVerbLine
    blockQuoteOpen      blockQuoteClose     blockQuoteLine
    blockVerbSep
    blockCommentOpen    blockCommentClose

    fontMonoOpen        fontMonoClose
    fontBoldOpen        fontBoldClose
    fontItalicOpen      fontItalicClose
    fontUnderlineOpen   fontUnderlineClose
    fontStrikeOpen      fontStrikeClose

    listOpen            listClose
    listOpenCompact     listCloseCompact
    listItemOpen        listItemClose       listItemLine
    numlistOpen         numlistClose
    numlistOpenCompact  numlistCloseCompact
    numlistItemOpen     numlistItemClose    numlistItemLine
    deflistOpen         deflistClose
    deflistOpenCompact  deflistCloseCompact
    deflistItem1Open    deflistItem1Close
    deflistItem2Open    deflistItem2Close   deflistItem2LinePrefix

    bar1                bar2
    url                 urlMark             urlMarkAnchor       urlImg
    email               emailMark
    img                 imgAlignLeft        imgAlignRight       imgAlignCenter
                        _imgAlignLeft       _imgAlignRight      _imgAlignCenter

    tableOpen           tableClose
    _tableBorder        _tableAlignLeft     _tableAlignCenter
    tableRowOpen        tableRowClose       tableRowSep
    tableTitleRowOpen   tableTitleRowClose
    tableCellOpen       tableCellClose      tableCellSep
    tableTitleCellOpen  tableTitleCellClose tableTitleCellSep
    _tableColAlignLeft  _tableColAlignRight _tableColAlignCenter
    tableCellAlignLeft  tableCellAlignRight tableCellAlignCenter
    _tableCellAlignLeft _tableCellAlignRight _tableCellAlignCenter
    _tableCellAlignLeftBorder _tableCellAlignRightBorder _tableCellAlignCenterBorder
    _tableCellColSpan   tableColAlignSep
    _tableCellColSpanChar tableCellCovered  _tableCellBorder
    _tableCellMulticolOpen
    _tableCellMulticolClose
    tableCellHead       tableTitleCellHead

    bodyOpen            bodyClose
    cssOpen             cssClose
    tocOpen             tocClose            TOC
    anchor
    comment
    pageBreak
    EOD
END

# ---------------------------------------------------------------------------
# Per-target tag tables
# ---------------------------------------------------------------------------

my %ALL_TAGS = (

    # --- Plain text --------------------------------------------------------
    txt => {
        title1          => "  \a",
        title2          => "\t\a",
        title3          => "\t\t\a",
        title4          => "\t\t\t\a",
        title5          => "\t\t\t\t\a",
        blockQuoteLine  => "\t",
        listItemOpen    => '- ',
        numlistItemOpen => '\a. ',
        bar1            => '\a',
        url             => '\a',
        urlMark         => '\a (\a)',
        email           => '\a',
        emailMark       => '\a (\a)',
        img             => '[\a]',
    },

    # --- HTML --------------------------------------------------------------
    html => {
        paragraphOpen       => '<P>',
        paragraphClose      => '</P>',
        title1              => '<H1~A~>\a</H1>',
        title2              => '<H2~A~>\a</H2>',
        title3              => '<H3~A~>\a</H3>',
        title4              => '<H4~A~>\a</H4>',
        title5              => '<H5~A~>\a</H5>',
        anchor              => ' ID="\a"',
        blockVerbOpen       => '<PRE>',
        blockVerbClose      => '</PRE>',
        blockQuoteOpen      => '<BLOCKQUOTE>',
        blockQuoteClose     => '</BLOCKQUOTE>',
        fontMonoOpen        => '<CODE>',
        fontMonoClose       => '</CODE>',
        fontBoldOpen        => '<B>',
        fontBoldClose       => '</B>',
        fontItalicOpen      => '<I>',
        fontItalicClose     => '</I>',
        fontUnderlineOpen   => '<U>',
        fontUnderlineClose  => '</U>',
        fontStrikeOpen      => '<S>',
        fontStrikeClose     => '</S>',
        listOpen            => '<UL>',
        listClose           => '</UL>',
        listItemOpen        => '<LI>',
        numlistOpen         => '<OL>',
        numlistClose        => '</OL>',
        numlistItemOpen     => '<LI>',
        deflistOpen         => '<DL>',
        deflistClose        => '</DL>',
        deflistItem1Open    => '<DT>',
        deflistItem1Close   => '</DT>',
        deflistItem2Open    => '<DD>',
        bar1                => '<HR NOSHADE SIZE=1>',
        bar2                => '<HR NOSHADE SIZE=5>',
        url                 => '<A HREF="\a">\a</A>',
        urlMark             => '<A HREF="\a">\a</A>',
        email               => '<A HREF="mailto:\a">\a</A>',
        emailMark           => '<A HREF="mailto:\a">\a</A>',
        img                 => '<IMG~A~ SRC="\a" BORDER="0" ALT="">',
        imgEmbed            => '<IMG~A~ SRC="\a" BORDER="0" ALT="">',
        _imgAlignLeft       => ' ALIGN="left"',
        _imgAlignCenter     => ' ALIGN="middle"',
        _imgAlignRight      => ' ALIGN="right"',
        tableOpen           => '<TABLE~A~~B~ CELLPADDING="4">',
        tableClose          => '</TABLE>',
        tableRowOpen        => '<TR>',
        tableRowClose       => '</TR>',
        tableCellOpen       => '<TD~A~~S~>',
        tableCellClose      => '</TD>',
        tableTitleCellOpen  => '<TH~S~>',
        tableTitleCellClose => '</TH>',
        _tableBorder        => ' BORDER="1"',
        _tableAlignCenter   => ' ALIGN="center"',
        _tableCellAlignRight  => ' ALIGN="right"',
        _tableCellAlignCenter => ' ALIGN="center"',
        _tableCellColSpan   => ' COLSPAN="\a"',
        cssOpen             => '<STYLE TYPE="text/css">',
        cssClose            => '</STYLE>',
        comment             => '<!-- \a -->',
        EOD                 => '</BODY></HTML>',
    },

    # --- XHTML (inherits HTML, override as needed) -------------------------
    xhtml => {
        paragraphOpen       => '<p>',
        paragraphClose      => '</p>',
        title1              => '<h1~A~>\a</h1>',
        title2              => '<h2~A~>\a</h2>',
        title3              => '<h3~A~>\a</h3>',
        title4              => '<h4~A~>\a</h4>',
        title5              => '<h5~A~>\a</h5>',
        anchor              => ' id="\a"',
        blockVerbOpen       => '<pre>',
        blockVerbClose      => '</pre>',
        blockQuoteOpen      => '<blockquote>',
        blockQuoteClose     => '</blockquote>',
        fontMonoOpen        => '<code>',
        fontMonoClose       => '</code>',
        fontBoldOpen        => '<strong>',
        fontBoldClose       => '</strong>',
        fontItalicOpen      => '<em>',
        fontItalicClose     => '</em>',
        fontUnderlineOpen   => '<u>',
        fontUnderlineClose  => '</u>',
        fontStrikeOpen      => '<del>',
        fontStrikeClose     => '</del>',
        listOpen            => '<ul>',
        listClose           => '</ul>',
        listItemOpen        => '<li>',
        listItemClose       => '</li>',
        numlistOpen         => '<ol>',
        numlistClose        => '</ol>',
        numlistItemOpen     => '<li>',
        numlistItemClose    => '</li>',
        deflistOpen         => '<dl>',
        deflistClose        => '</dl>',
        deflistItem1Open    => '<dt>',
        deflistItem1Close   => '</dt>',
        deflistItem2Open    => '<dd>',
        deflistItem2Close   => '</dd>',
        bar1                => '<hr/>',
        bar2                => '<hr class="heavy"/>',
        url                 => '<a href="\a">\a</a>',
        urlMark             => '<a href="\a">\a</a>',
        email               => '<a href="mailto:\a">\a</a>',
        emailMark           => '<a href="mailto:\a">\a</a>',
        img                 => '<img~A~ src="\a" border="0" alt=""/>',
        imgEmbed            => '<img~A~ src="\a" border="0" alt=""/>',
        _imgAlignLeft       => ' align="left"',
        _imgAlignCenter     => ' align="middle"',
        _imgAlignRight      => ' align="right"',
        tableOpen           => '<table~A~~B~ cellpadding="4">',
        tableClose          => '</table>',
        tableRowOpen        => '<tr>',
        tableRowClose       => '</tr>',
        tableCellOpen       => '<td~A~~S~>',
        tableCellClose      => '</td>',
        tableTitleCellOpen  => '<th~S~>',
        tableTitleCellClose => '</th>',
        _tableBorder        => ' border="1"',
        _tableAlignCenter   => ' align="center"',
        _tableCellAlignRight  => ' align="right"',
        _tableCellAlignCenter => ' align="center"',
        _tableCellColSpan   => ' colspan="\a"',
        cssOpen             => '<style type="text/css">',
        cssClose            => '</style>',
        comment             => '<!-- \a -->',
        EOD                 => '</body></html>',
    },

    # --- HTML5 (inherits xhtml) -------------------------------------------
    html5 => {
        title1Open          => '<section><h1>',
        title1Close         => '</h1>',
        title2Open          => '<section><h2>',
        title2Close         => '</h2>',
        title3Open          => '<section><h3>',
        title3Close         => '</h3>',
        title4Open          => '<section><h4>',
        title4Close         => '</h4>',
        title5Open          => '<section><h5>',
        title5Close         => '</h5>',
    },

    # --- Markdown ----------------------------------------------------------
    md => {
        title1          => '# \a',
        title2          => '## \a',
        title3          => '### \a',
        title4          => '#### \a',
        title5          => '##### \a',
        blockVerbOpen   => '```',
        blockVerbClose  => '```',
        blockQuoteLine  => '> ',
        listItemOpen    => '- ',
        numlistItemOpen => '\a. ',
        bar1            => '---',
        url             => '\a',
        urlMark         => '[\a](\a)',
        email           => '\a',
        emailMark       => '[\a](mailto:\a)',
        img             => '![](\a)',
        fontMonoOpen    => '`',
        fontMonoClose   => '`',
        fontBoldOpen    => '**',
        fontBoldClose   => '**',
        fontItalicOpen  => '*',
        fontItalicClose => '*',
        fontStrikeOpen  => '~~',
        fontStrikeClose => '~~',
        tableOpen       => '',
        tableClose      => '',
        tableRowOpen    => '|',
        tableRowClose   => '',
        tableCellOpen   => ' ',
        tableCellClose  => ' |',
        tableTitleCellOpen  => ' ',
        tableTitleCellClose => ' |',
        comment         => '<!-- \a -->',
    },

    # --- reStructuredText -------------------------------------------------
    rst => {
        title1          => '\a',
        title2          => '\a',
        title3          => '\a',
        title4          => '\a',
        title5          => '\a',
        blockVerbOpen   => "::\n",
        blockQuoteLine  => '    ',
        listItemOpen    => '- ',
        numlistItemOpen => '\a. ',
        url             => '\a',
        urlMark         => '`\a <\a>`_',
        email           => '\a',
        emailMark       => '`\a <\a>`_',
        img             => "\n\n.. image:: \a\n   :align: ~A~\n\nENDIMG",
        urlImg          => "\n   :target: ",
        _imgAlignLeft   => 'left',
        _imgAlignCenter => 'center',
        _imgAlignRight  => 'right',
        fontMonoOpen    => '``',
        fontMonoClose   => '``',
        fontBoldOpen    => '**',
        fontBoldClose   => '**',
        fontItalicOpen  => '*',
        fontItalicClose => '*',
        comment         => '.. \a',
        TOC             => "\n.. contents::",
    },

    # --- AsciiDoc ---------------------------------------------------------
    adoc => {
        title1          => '= \a',
        title2          => '== \a',
        title3          => '=== \a',
        title4          => '==== \a',
        title5          => '===== \a',
        blockVerbOpen   => '----',
        blockVerbClose  => '----',
        blockQuoteLine  => '',
        listItemOpen    => '- ',
        numlistItemOpen => '. ',
        bar1            => "'''\n",
        url             => '\a',
        urlMark         => '\a[\a]',
        email           => '\a',
        emailMark       => 'mailto:\a[\a]',
        img             => 'image::\a[]',
        fontMonoOpen    => '`',
        fontMonoClose   => '`',
        fontBoldOpen    => '*',
        fontBoldClose   => '*',
        fontItalicOpen  => '_',
        fontItalicClose => '_',
        comment         => '// \a',
    },

    # --- LaTeX -------------------------------------------------------------
    tex => {
        paragraphOpen   => '',
        title1          => '\section{\a}',
        title2          => '\subsection{\a}',
        title3          => '\subsubsection{\a}',
        title4          => '\paragraph{\a}',
        title5          => '\subparagraph{\a}',
        blockVerbOpen   => '\begin{verbatim}',
        blockVerbClose  => '\end{verbatim}',
        blockQuoteOpen  => '\begin{quote}',
        blockQuoteClose => '\end{quote}',
        fontMonoOpen    => '\texttt{',
        fontMonoClose   => '}',
        fontBoldOpen    => '\textbf{',
        fontBoldClose   => '}',
        fontItalicOpen  => '\textit{',
        fontItalicClose => '}',
        fontUnderlineOpen  => '\underline{',
        fontUnderlineClose => '}',
        fontStrikeOpen  => '\sout{',
        fontStrikeClose => '}',
        listOpen        => '\begin{itemize}',
        listClose       => '\end{itemize}',
        listItemOpen    => '\item ',
        numlistOpen     => '\begin{enumerate}',
        numlistClose    => '\end{enumerate}',
        numlistItemOpen => '\item ',
        deflistOpen     => '\begin{description}',
        deflistClose    => '\end{description}',
        deflistItem1Open    => '\item[',
        deflistItem1Close   => ']',
        deflistItem2Open    => '',
        bar1            => '\hrulefill',
        bar2            => '\noindent\hrulefill\hrulefill',
        url             => '\url{\a}',
        urlMark         => '\href{\a}{\a}',
        email           => '\href{mailto:\a}{\a}',
        emailMark       => '\href{mailto:\a}{\a}',
        img             => '\includegraphics{\a}',
        comment         => '% \a',
        EOD             => '\end{document}',
    },

    # --- csv / csvs -------------------------------------------------------
    csv => {
        tableCellSep    => ',',
        tableCellOpen   => '"',
        tableCellClose  => '"',
    },
    csvs => {},   # inherits csv

    # --- txt2t (round-trip) -----------------------------------------------
    txt2t => {
        title1              => '         = \a =~A~',
        title2              => '        == \a ==~A~',
        title3              => '       === \a ===~A~',
        title4              => '      ==== \a ====~A~',
        title5              => '     ===== \a =====~A~',
        numtitle1           => '         + \a +~A~',
        numtitle2           => '        ++ \a ++~A~',
        numtitle3           => '       +++ \a +++~A~',
        numtitle4           => '      ++++ \a ++++~A~',
        numtitle5           => '     +++++ \a +++++~A~',
        anchor              => '[\a]',
        blockVerbOpen       => '```',
        blockVerbClose      => '```',
        blockQuoteLine      => "\t",
        blockCommentOpen    => '%%%',
        blockCommentClose   => '%%%',
        fontMonoOpen        => '``',
        fontMonoClose       => '``',
        fontBoldOpen        => '**',
        fontBoldClose       => '**',
        fontItalicOpen      => '//',
        fontItalicClose     => '//',
        fontUnderlineOpen   => '__',
        fontUnderlineClose  => '__',
        fontStrikeOpen      => '--',
        fontStrikeClose     => '--',
        listItemOpen        => '- ',
        numlistItemOpen     => '+ ',
        deflistItem1Open    => ': ',
        listClose           => '-',
        numlistClose        => '+',
        deflistClose        => ':',
        bar1                => '-------------------------',
        bar2                => '=========================',
        url                 => '\a',
        urlMark             => '[\a \a]',
        email               => '\a',
        emailMark           => '[\a \a]',
        img                 => '[\a]',
        _tableBorder        => '|',
        _tableAlignLeft     => '',
        _tableAlignCenter   => '   ',
        tableRowOpen        => '~A~',
        tableRowClose       => '~B~',
        tableTitleRowOpen   => '~A~|',
        tableCellOpen       => '| ',
        tableCellClose      => ' ~S~',
        tableCellAlignLeft  => '\a  ',
        tableCellAlignRight => '  \a',
        tableCellAlignCenter=> '  \a  ',
        _tableCellColSpanChar => '|',
        comment             => '% \a',
    },
);

# xhtmls = xhtml
$ALL_TAGS{xhtmls} = { %{ $ALL_TAGS{xhtml} } };

# html5 inherits xhtml, then overrides
{
    my %h5 = ( %{ $ALL_TAGS{xhtml} }, %{ $ALL_TAGS{html5} } );
    $ALL_TAGS{html5} = \%h5;
}

# csvs inherits csv
$ALL_TAGS{csvs} = { %{ $ALL_TAGS{csv} } };

# ---------------------------------------------------------------------------
# getTags($config) → hashref
# ---------------------------------------------------------------------------

sub getTags {
    my ($config) = @_;
    my $target = $config->{target} // '';

    # Normalise alias targets
    my %alias = (
        aap  => 'aat', aas  => 'aat', aatw => 'aat',
        aapw => 'aat', aasw => 'aat', aapp => 'aat',
    );
    $target = $alias{$target} if exists $alias{$target};

    # Zero-initialise all keys
    my %ret = map { $_ => '' } @TAG_KEYS;

    # Layer target-specific tags on top
    if (exists $ALL_TAGS{$target}) {
        my $bank = $ALL_TAGS{$target};
        for my $k (keys %$bank) {
            $ret{$k} = $bank->{$k};
        }
    }

    return \%ret;
}

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
our @EXPORT_OK = qw(getTags);

1;
__END__

=head1 NAME

Text::Txt2tags::Tags - Per-target tag strings for Text::Txt2tags

=head1 SYNOPSIS

  use Text::Txt2tags::Tags qw(getTags);
  my $tags = getTags({ target => 'html' });
  print $tags->{fontBoldOpen};   # <B>

=head1 DESCRIPTION

Port of C<txt2tags3_mod/tags.py> to Perl 5.
Returns a hashref of tag strings (with C<\a> placeholders) for the
requested output target.

=cut
