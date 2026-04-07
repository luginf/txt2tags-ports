#!/usr/bin/perl
use strict;
use warnings;
use Test::More;

use_ok 'Text::Txt2tags::Tags', 'getTags';

# HTML tags
{
    my $t = getTags({ target => 'html' });
    ok ref $t eq 'HASH', 'getTags returns hashref';

    is $t->{fontBoldOpen},      '<B>',    'html fontBoldOpen';
    is $t->{fontBoldClose},     '</B>',   'html fontBoldClose';
    is $t->{fontItalicOpen},    '<I>',    'html fontItalicOpen';
    is $t->{fontItalicClose},   '</I>',   'html fontItalicClose';
    is $t->{fontMonoOpen},      '<CODE>', 'html fontMonoOpen';
    is $t->{fontMonoClose},     '</CODE>','html fontMonoClose';
    is $t->{fontUnderlineOpen}, '<U>',    'html fontUnderlineOpen';
    is $t->{fontStrikeOpen},    '<S>',    'html fontStrikeOpen';

    is $t->{listOpen},          '<UL>',   'html listOpen';
    is $t->{listClose},         '</UL>',  'html listClose';
    is $t->{listItemOpen},      '<LI>',   'html listItemOpen';

    is $t->{numlistOpen},       '<OL>',   'html numlistOpen';
    is $t->{numlistClose},      '</OL>',  'html numlistClose';

    is $t->{deflistOpen},       '<DL>',   'html deflistOpen';
    is $t->{deflistClose},      '</DL>',  'html deflistClose';

    is $t->{paragraphOpen},     '<P>',    'html paragraphOpen';
    is $t->{paragraphClose},    '</P>',   'html paragraphClose';

    is $t->{blockVerbOpen},     '<PRE>',  'html blockVerbOpen';
    is $t->{blockVerbClose},    '</PRE>', 'html blockVerbClose';

    like $t->{bar1}, qr/HR/,    'html bar1 is an HR tag';
    like $t->{EOD},  qr/HTML/i, 'html EOD closes HTML';
}

# Markdown tags
{
    my $t = getTags({ target => 'md' });
    is $t->{fontBoldOpen},  '**', 'md fontBoldOpen';
    is $t->{fontBoldClose}, '**', 'md fontBoldClose';
    is $t->{fontItalicOpen}, '*', 'md fontItalicOpen';
    like $t->{title1}, qr/#/, 'md title1 uses #';
    like $t->{title2}, qr/##/, 'md title2 uses ##';
}

# reStructuredText
{
    my $t = getTags({ target => 'rst' });
    is $t->{fontBoldOpen},  '**', 'rst fontBoldOpen';
    is $t->{fontMonoOpen},  '``', 'rst fontMonoOpen';
    is $t->{blockQuoteLine},'    ','rst blockQuoteLine is 4 spaces';
}

# LaTeX
{
    my $t = getTags({ target => 'tex' });
    like $t->{fontBoldOpen},  qr/textbf/, 'tex fontBoldOpen uses \\textbf';
    like $t->{fontItalicOpen},qr/textit/, 'tex fontItalicOpen uses \\textit';
    like $t->{listOpen},      qr/itemize/,'tex listOpen uses itemize';
    like $t->{EOD},           qr/end.*document/i, 'tex EOD ends document';
}

# XHTML
{
    my $t = getTags({ target => 'xhtml' });
    is $t->{fontBoldOpen},   '<strong>', 'xhtml fontBoldOpen';
    is $t->{fontItalicOpen}, '<em>',     'xhtml fontItalicOpen';
    is $t->{listItemOpen},   '<li>',     'xhtml listItemOpen';
    is $t->{listItemClose},  '</li>',    'xhtml listItemClose';
}

# Plain text: all required keys present, no crashes
{
    my $t = getTags({ target => 'txt' });
    ok exists $t->{fontBoldOpen}, 'txt has fontBoldOpen key (empty is ok)';
    ok exists $t->{listItemOpen}, 'txt has listItemOpen key';
    is $t->{listItemOpen}, '- ', 'txt listItemOpen is "- "';
}

# Unknown target: returns zeroed hashref without dying
{
    my $t = getTags({ target => 'nonexistent_target' });
    ok ref $t eq 'HASH', 'unknown target returns hashref';
    is $t->{fontBoldOpen}, '', 'unknown target fontBoldOpen is empty';
}

done_testing;
