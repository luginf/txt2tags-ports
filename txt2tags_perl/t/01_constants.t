#!/usr/bin/perl
use strict;
use warnings;
use Test::More;

use_ok 'Text::Txt2tags::Constants';

# Program info
{
    no warnings 'once';
    ok $Text::Txt2tags::Constants::MY_NAME, 'MY_NAME defined';
    like $Text::Txt2tags::Constants::MY_VERSION, qr/^\d+\.\d+/, 'MY_VERSION looks like a version';
    like $Text::Txt2tags::Constants::MY_URL, qr/txt2tags/, 'MY_URL contains txt2tags';
}

# FLAGS
{
    my %f = %Text::Txt2tags::Constants::FLAGS;
    ok exists $f{headers},  'FLAGS has headers';
    ok exists $f{toc},      'FLAGS has toc';
    is $f{headers}, 1, 'headers default is 1';
    is $f{toc},     0, 'toc default is 0';
}

# OPTIONS
{
    my %o = %Text::Txt2tags::Constants::OPTIONS;
    ok exists $o{target},    'OPTIONS has target';
    ok exists $o{'toc-level'}, 'OPTIONS has toc-level';
    is $o{'toc-level'}, 3, 'toc-level default is 3';
}

# TARGETS
{
    my @tgts = @Text::Txt2tags::Constants::TARGETS;
    ok scalar @tgts > 30, 'at least 30 targets';
    ok grep { $_ eq 'html' }  @tgts, 'html in TARGETS';
    ok grep { $_ eq 'rst'  }  @tgts, 'rst in TARGETS';
    ok grep { $_ eq 'tex'  }  @tgts, 'tex in TARGETS';
    ok grep { $_ eq 'md'   }  @tgts, 'md in TARGETS';
}

# TARGET_NAMES
{
    my %tn = %Text::Txt2tags::Constants::TARGET_NAMES;
    ok $tn{html},  'html has a name';
    ok $tn{md},    'md has a name';
    like $tn{html}, qr/HTML/i, 'html name mentions HTML';
}

# Constants
is(Text::Txt2tags::Constants::DFT_TEXT_WIDTH(),  72, 'DFT_TEXT_WIDTH is 72');
is(Text::Txt2tags::Constants::DFT_SLIDE_WIDTH(), 80, 'DFT_SLIDE_WIDTH is 80');

# Special chars
is $Text::Txt2tags::Constants::ESCCHAR,   "\x00", 'ESCCHAR is NUL';
is $Text::Txt2tags::Constants::SEPARATOR, "\x01", 'SEPARATOR is SOH';

# LISTNAMES
{
    my %ln = %Text::Txt2tags::Constants::LISTNAMES;
    is $ln{'-'}, 'list',    'dash → list';
    is $ln{'+'}, 'numlist', 'plus → numlist';
    is $ln{':'}, 'deflist', 'colon → deflist';
}

done_testing;
