#!/usr/bin/perl
use strict;
use warnings;
use Test::More;

use_ok 'Text::Txt2tags::Output', qw(
    doEscape doFinalEscape doProtect
    maskEscapeChar unmaskEscapeChar
    addLineBreaks expandLineBreaks
    compile_filters get_encoding_string
);

use Text::Txt2tags::Constants qw($ESCCHAR %ESCAPES);

# maskEscapeChar / unmaskEscapeChar
{
    my $original = 'foo\\bar\\baz';
    my $masked   = maskEscapeChar($original);
    unlike $masked,   qr/\\/, 'masked: no backslash';
    my $unmasked = unmaskEscapeChar($masked);
    is $unmasked, $original, 'round-trip mask/unmask';
}

# maskEscapeChar on arrayref
{
    my $arr    = ['a\\b', 'c\\d'];
    my $masked = maskEscapeChar($arr);
    is ref $masked, 'ARRAY', 'maskEscapeChar arrayref → arrayref';
    ok $masked->[0] !~ /\\/, 'first element masked';
    my $back = unmaskEscapeChar($masked);
    is $back->[0], 'a\\b', 'unmask restores first element';
}

# addLineBreaks / expandLineBreaks
{
    my $lines  = ['foo', 'bar'];
    my $with_lb = addLineBreaks($lines);
    is $with_lb->[0], "foo\n", 'addLineBreaks adds \\n';
    is $with_lb->[1], "bar\n", 'addLineBreaks adds \\n (2)';

    my $embedded = ['foo\nbar'];
    my $expanded = expandLineBreaks($embedded);
    # expandLineBreaks splits on literal \n in strings, not escape sequences
    is scalar @$expanded, 1, 'expandLineBreaks with no real newlines → 1 element';
}

# doEscape – XML special chars
{
    # Temporarily activate the escapexmlchars rule
    local $Text::Txt2tags::State::rules{escapexmlchars} = 1;
    my $txt = doEscape('html', '<b>foo & "bar"</b>');
    like $txt, qr/&amp;/,  'doEscape: & → &amp;';
    like $txt, qr/&lt;/,   'doEscape: < → &lt;';
    like $txt, qr/&gt;/,   'doEscape: > → &gt;';
}

# doEscape – no XML escaping when rule is off
{
    local $Text::Txt2tags::State::rules{escapexmlchars} = 0;
    my $txt = doEscape('txt', '<foo>');
    is $txt, '<foo>', 'doEscape: no escaping for txt target';
}

# compile_filters
{
    my $filters  = [['foo', 'bar']];
    my $compiled = compile_filters($filters, 'Test filter');
    is ref $compiled, 'ARRAY', 'compile_filters returns arrayref';
    is ref $compiled->[0][0], 'Regexp', 'first element is a Regexp';

    my $line = 'foo baz foo';
    $line =~ s/$compiled->[0][0]/$compiled->[0][1]/g;
    is $line, 'bar baz bar', 'compiled filter replaces correctly';
}

# compile_filters – bad regex dies
{
    eval { compile_filters([['(?invalid', 'x']], 'bad regex') };
    ok $@, 'compile_filters with bad regex dies';
}

# get_encoding_string
{
    my $s = get_encoding_string('UTF-8', 'html');
    like $s, qr/UTF-8/i, 'html encoding string mentions UTF-8';
    like $s, qr/charset/i, 'html encoding string mentions charset';

    my $t = get_encoding_string('utf-8', 'tex');
    like $t, qr/inputenc|utf8/i, 'tex encoding string mentions inputenc or utf8';

    my $u = get_encoding_string('', 'html');
    is $u, '', 'empty encoding → empty string';
}

done_testing;
