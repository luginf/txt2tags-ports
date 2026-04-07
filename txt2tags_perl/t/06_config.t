#!/usr/bin/perl
use strict;
use warnings;
use Test::More;

use_ok 'Text::Txt2tags::Config';

# ConfigLines::parse_line
{
    my $cl = Text::Txt2tags::ConfigLines->new;

    # Basic %!key: value
    my ($tgt, $val, $key) = $cl->parse_line('%! target: html');
    is $key, 'target', 'parse_line: key=target';
    is $val, 'html',   'parse_line: val=html';
    is $tgt, 'all',    'parse_line: no target → all';

    # With explicit target
    ($tgt, $val, $key) = $cl->parse_line('%! encoding(html): UTF-8');
    is $key, 'encoding', 'parse_line: key=encoding';
    is $val, 'UTF-8',    'parse_line: val=UTF-8';
    is $tgt, 'html',     'parse_line: target=html';

    # Not a config line
    ($tgt, $val, $key) = $cl->parse_line('% just a comment');
    is $key, '', 'non-config line → empty key';
}

# ConfigLines::get_raw_config
{
    my $lines = [
        '%! target: html',
        '%! encoding: UTF-8',
        '% ignored comment',
        '%! toc: ',
    ];
    my $cl  = Text::Txt2tags::ConfigLines->new(lines => $lines, first_line => 1);
    my $raw = $cl->get_raw_config;
    is ref $raw, 'ARRAY', 'get_raw_config returns arrayref';
    is scalar @$raw, 3, 'found 3 config entries';
    is $raw->[0][1], 'target',   'first entry key=target';
    is $raw->[0][2], 'html',     'first entry val=html';
    is $raw->[1][1], 'encoding', 'second entry key=encoding';
}

# ConfigMaster::parse
{
    my $raw = [
        ['all', 'target',   'html'],
        ['all', 'encoding', 'UTF-8'],
        ['all', 'toc',      ''],
    ];
    my $cm     = Text::Txt2tags::ConfigMaster->new($raw, 'html');
    my $parsed = $cm->parse;
    is ref $parsed, 'HASH',  'parse returns hashref';
    is $parsed->{target},   'html',  'parsed target=html';
    is $parsed->{encoding}, 'UTF-8', 'parsed encoding=UTF-8';
    is $parsed->{toc},      1,       'empty flag value → 1';
}

# ConfigMaster::add – no- prefix turns OFF
{
    my $cm = Text::Txt2tags::ConfigMaster->new;
    $cm->add('no-headers', '');
    is $cm->{parsed}{headers}, 0, 'no-headers sets headers=0';
}

# ConfigMaster::add – multi value
{
    my $cm = Text::Txt2tags::ConfigMaster->new;
    $cm->add('style', 'main.css');
    $cm->add('style', 'extra.css');
    is ref $cm->{parsed}{style}, 'ARRAY', 'style is an array';
    is scalar @{ $cm->{parsed}{style} }, 2, '2 style entries';
}

# SourceDocument – minimal scan
{
    my $lines = [
        'My Title',
        'My Author',
        '2026-01-01',
        '',
        'Body line one.',
        'Body line two.',
    ];
    my $sd = Text::Txt2tags::SourceDocument->new(contents => $lines);
    my ($head, $conf, $body) = $sd->split_doc;

    is ref $head, 'ARRAY', 'head is arrayref';
    is $head->[0], 'My Title',  'head[0] = title';
    is $head->[1], 'My Author', 'head[1] = author';
    is $head->[2], '2026-01-01','head[2] = date';

    ok scalar @$body >= 2, 'body has at least 2 lines';
    ok grep { /Body line one/ } @$body, 'body contains first body line';
}

# SourceDocument – no header (first line blank)
{
    my $lines = ['', 'Body without header.'];
    my $sd    = Text::Txt2tags::SourceDocument->new(contents => $lines);
    my ($head, undef, $body) = $sd->split_doc;
    is $head->[0], '', 'blank first line → empty header';
}

done_testing;
