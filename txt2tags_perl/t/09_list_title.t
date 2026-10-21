#!/usr/bin/perl
use strict;
use warnings;
use Test::More;

use Text::Txt2tags::Converter qw(convert);

sub conv {
    my ($src, %extra) = @_;
    my $cfg = {
        target => 'html', headers => 0, toc => 0, 'toc-level' => 3,
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

# A flush-left title ends an open list (one blank line, spaces-only line, none)
for my $sep ("\n\n", "\n \n", "\n") {
    (my $name = $sep) =~ s/\n/\\n/g;
    my $out = conv("- item\n  suite${sep}== Titre ==\n\ntexte\n");
    like $out, qr{</UL>\s*<H2>Titre</H2>}i, "title closes list (sep '$name')";
    unlike $out, qr/== Titre ==/, "title not swallowed (sep '$name')";
}

# numbered title too
like conv("- a\n\n+ T +\n"), qr{</UL>\s*<H1>1\. T</H1>}i, 'numtitle closes list';

# --legacy keeps the historical (swallowing) behaviour
like conv("- item\n\n== Titre ==\n\ntexte\n", legacy => 1),
    qr/== Titre ==/, '--legacy: title swallowed into the item';

# Non-regression: blank-separated items stay in one list
my $two = conv("- a\n\n- b\n");
is(scalar(() = $two =~ /<UL>/gi), 1, 'spaced items: a single list');

# Non-regression: multi-paragraph item still works
like conv("- a\n\n  more a\n"), qr{<LI>a\s*<P></P>\s*more a}i,
    'parainsidelist unchanged';

# An indented "title" inside an item is a continuation, not a title
unlike conv("- a\n\n  == x ==\n"), qr/<H2>/i, 'indented title stays in item';

done_testing;
