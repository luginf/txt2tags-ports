#!/usr/bin/perl
use strict;
use warnings;
use Test::More;

use_ok 'Text::Txt2tags::Rules', 'getRules';

# HTML rules
{
    my $r = getRules({ target => 'html' });
    ok ref $r eq 'HASH', 'getRules returns hashref';
    ok $r->{linkable},       'html is linkable';
    ok $r->{tableable},      'html supports tables';
    ok $r->{escapexmlchars}, 'html escapes XML chars';
    ok $r->{imgalignable},   'html supports image alignment';
    ok $r->{blanksaroundtitle}, 'html puts blanks around titles';
}

# Plain text rules
{
    my $r = getRules({ target => 'txt' });
    ok $r->{iswrapped},     'txt is wrapped';
    ok $r->{plaintexttoc},  'txt has plain text TOC';
    ok !$r->{linkable},     'txt is not linkable';
}

# RST rules
{
    my $r = getRules({ target => 'rst' });
    ok $r->{imgalignable},  'rst supports image alignment';
    ok $r->{tableable},     'rst supports tables';
    ok $r->{blanksaroundpara}, 'rst puts blanks around paras';
}

# CSV (table-only)
{
    my $r = getRules({ target => 'csv' });
    ok $r->{tableable},  'csv is tableable';
    ok $r->{tableonly},  'csv is tableonly';
}

# HTML5 (inherits html + titleblocks)
{
    my $r = getRules({ target => 'html5' });
    ok $r->{linkable},    'html5 is linkable (inherited)';
    ok $r->{titleblocks}, 'html5 has titleblocks';
}

# Alias targets map to aat
{
    my $r_aat  = getRules({ target => 'aat'  });
    my $r_aap  = getRules({ target => 'aap'  });
    my $r_aatw = getRules({ target => 'aatw' });
    is_deeply $r_aat, $r_aap,  'aap rules == aat rules';
    is_deeply $r_aat, $r_aatw, 'aatw rules == aat rules';
}

# Unknown target: returns empty-ish hashref without dying
{
    my $r = getRules({ target => 'nonexistent' });
    ok ref $r eq 'HASH', 'unknown target returns hashref';
    ok !$r->{linkable}, 'unknown target: linkable is false';
}

done_testing;
