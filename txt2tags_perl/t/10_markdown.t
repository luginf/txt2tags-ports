#!/usr/bin/perl
# Markdown (GFM) output: constructs that used to come out broken.
use strict;
use warnings;
use Test::More;

use Text::Txt2tags::Converter qw(convert);

sub conv {
    my ($src, %extra) = @_;
    my $cfg = {
        target => 'md', headers => 0, toc => 0, 'toc-level' => 3,
        'mask-email' => 0, 'css-sugar' => 0, 'css-inside' => 0,
        'fix-path' => 0, 'embed-images' => 0, encoding => '',
        style => [], preproc => [], postproc => [], postvoodoo => [],
        realcmdline => [], infile => '-', outfile => '-',
        sourcefile => '-', currentsourcefile => '-',
        'skip-header-lines' => 1,
        %extra,
    };
    my ($lines) = convert([split /\n/, $src, -1], $cfg);
    return join "\n", @$lines;
}

# nested lists are indented 4 spaces per level
like conv("- a\n - b\n  - c\n"), qr/\* a\n    \* b\n        \* c/, 'nested bullets';
like conv("+ n\n + m\n"), qr/1\. n\n    1\. m/, 'nested numbered list';

# a second paragraph stays inside its list item
like conv("- a\n\n  more a\n\n- b\n"), qr/\* a\n\n  more a\n/, 'list item paragraph';

# definition list: bold term, then the definition on the next line
like conv(": Term\n def one\n def two\n"), qr/\*\*Term\*\*  \ndef one\ndef two/, 'deflist';

# table: separator has one cell per column, with alignment
like conv("|| a | b |\n| 1 | 2 |\n"), qr/\| a \| b \|\n\|---\|---\|/, 'table separator per column';
like conv("||  a  | b |\n| 1 | 2 |\n"), qr/\|:---:\|---\|/, 'table alignment';
like conv("| x | y |\n| z | w |\n"), qr/^\s*\|  \|  \|\n\|---\|---\|/, 'empty header when none';

# literal text is not read as markdown
my $esc = conv("2*3*4 and a < b\n\n1. not a list\n# not a title\n> not a quote\n");
like $esc, qr/2\\\*3\\\*4/, 'lone * escaped';
like $esc, qr/a \\< b/, '< escaped';
like $esc, qr/1\\\. not a list/, 'N. escaped';
like $esc, qr/\\# not a title/, '# escaped';
like $esc, qr/\\> not a quote/, '> escaped';

# marks and inline code
like conv("**bold** //it// ``a*b_c<d``\n"), qr/\*\*bold\*\* \*it\* `a\*b_c<d`/, 'marks and mono';

# The header and the %%toc placeholder are handled by the command line tool
use File::Temp qw(tempfile);
sub cli {
    my ($src, @args) = @_;
    my ($fh, $file) = tempfile(SUFFIX => '.t2t', UNLINK => 1);
    print $fh $src;
    close $fh;
    open my $p, '-|', $^X, '-Ilib', 'bin/txt2tags', '-t', 'md', '-o', '-', @args, $file
        or die "cannot run bin/txt2tags: $!";
    local $/;
    my $out = <$p>;
    close $p;
    return $out;
}

# title, author, date become a heading then a line-broken byline
my $doc = cli("Title\nAuthor\n2026-01-01\n\ntext\n");
like $doc, qr/^# Title\n/, 'document title is a heading';
like $doc, qr/Author  \n2026-01-01/, 'author and date on two lines';

# --enum-title numbers every title
like conv("= A =\n== B ==\n", 'enum-title' => 1), qr/# 1\. A\s+## 1\.1\. B/, 'enum-title';

# %%toc leaves no placeholder, with or without --toc
unlike cli("T\nA\nD\n\n%%toc\n\n= A =\n"), qr/vvvTOCvvv/, '%%toc leaves no placeholder';
my $toc = cli("T\nA\nD\n\nintro\n\n%%toc\n\n= A =\n", '--toc');
unlike $toc, qr/vvvTOCvvv/, '%%toc with --toc leaves no placeholder';
like $toc, qr/intro\n\n.*A/s, '--toc puts the list where %%toc is';

# several marks on one line stay separate marks
like conv("**a** and **b** //c// and //d//\n"), qr/(?:^|\n)\*\*a\*\* and \*\*b\*\* \*c\* and \*d\*/, 'marks do not merge';

# a mono span is copied as it is
like cli("T\nA\nD\n\n``//i// \\n **b**``\n"), qr/(?:^|\n)`\/\/i\/\/ \\n \*\*b\*\*`/, 'mono is verbatim';

# a backslash is plain text, so the mark after it still applies
like cli("T\nA\nD\n\n\\**bold**\n"), qr/(?:^|\n)\\\\\*\*bold\*\*/, 'backslash is plain text';

# a label after a title is dropped
like conv("= One =[lab]\n"), qr/(?:^|\n)# One\n/, 'title label';

# quotes
like conv("\tquoted\n\t\tdeeper\n"), qr/(?:^|\n)> quoted\n> > deeper/, 'quote';

# %!options: in the document are defaults
my $opt = cli("T\nA\nD\n%!options: --toc -n\n\n= One =\n\ntext\n");
like $opt, qr/\* \[1\\\. One\]\(#1-one\)/, '%!options --toc';
like $opt, qr/(?:^|\n)# 1\. One$/m, '%!options -n';

# a list item under a definition term is a sublist
like conv(": term\n  - a\n    + b\n"), qr/\*\*term\*\*  \n    \* a\n        1\. b/, 'deflist sublist';

# a list right after a paragraph is separated by a blank line
like conv("== L ==\n\nIntro :\n- a\n- b\n"), qr/Intro :\n\n\* a\n\* b/, 'blank before list';

done_testing;
