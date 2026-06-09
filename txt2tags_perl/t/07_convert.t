#!/usr/bin/perl
use strict;
use warnings;
use Test::More;

use Text::Txt2tags::Converter qw(convert set_global_config);
use Text::Txt2tags::State;

sub make_config {
    my (%extra) = @_;
    return {
        target       => 'html',
        headers      => 1,
        toc          => 0,
        'toc-level'  => 3,
        'mask-email' => 0,
        'css-sugar'  => 0,
        'css-inside' => 0,
        'fix-path'   => 0,
        'embed-images'=> 0,
        encoding     => '',
        style        => [],
        preproc      => [],
        postproc     => [],
        postvoodoo   => [],
        realcmdline  => [],
        infile       => '-',
        outfile      => '-',
        sourcefile   => '-',
        currentsourcefile => '-',
        %extra,
    };
}

# --- Bold -----------------------------------------------------------------
{
    my ($lines, $toc) = convert(['**bold text**'], make_config());
    my $out = join ' ', @$lines;
    like $out, qr/<B>bold text<\/B>/i, 'html: bold markup';
}

# --- Italic ---------------------------------------------------------------
{
    my ($lines) = convert(['//italic text//'], make_config());
    my $out = join ' ', @$lines;
    like $out, qr/<I>italic text<\/I>/i, 'html: italic markup';
}

# --- Underline ------------------------------------------------------------
{
    my ($lines) = convert(['__underline text__'], make_config());
    my $out = join ' ', @$lines;
    like $out, qr/<U>underline text<\/U>/i, 'html: underline markup';
}

# --- Strike ---------------------------------------------------------------
{
    my ($lines) = convert(['--strike text--'], make_config());
    my $out = join ' ', @$lines;
    like $out, qr/<S>strike text<\/S>/i, 'html: strikethrough markup';
}

# --- Verbatim block -------------------------------------------------------
{
    my @body = ('```', 'code here', '```');
    my ($lines) = convert(\@body, make_config());
    my $out = join "\n", @$lines;
    like $out, qr/<PRE>/i,  'html: verb block open';
    like $out, qr/code here/, 'html: verb block content';
    like $out, qr/<\/PRE>/i,'html: verb block close';
}

# --- Comment block (ignored) ----------------------------------------------
{
    my @body = ('%%%', 'this is a comment', '%%%', 'visible text');
    my ($lines) = convert(\@body, make_config());
    my $out = join "\n", @$lines;
    unlike $out, qr/this is a comment/, 'comment block is suppressed';
    like   $out, qr/visible text/,      'text after comment block is kept';
}

# --- Title ----------------------------------------------------------------
{
    my ($lines) = convert(['= Hello ='], make_config());
    my $out = join ' ', @$lines;
    like $out, qr/<H1[^>]*>Hello<\/H1>/i, 'html: h1 title';
}

{
    my ($lines) = convert(['== World =='], make_config());
    my $out = join ' ', @$lines;
    like $out, qr/<H2[^>]*>World<\/H2>/i, 'html: h2 title';
}

# --- Horizontal bar -------------------------------------------------------
{
    my ($lines) = convert(['--------------------'], make_config());
    my $out = join ' ', @$lines;
    like $out, qr/<HR/i, 'html: bar1 becomes HR';
}

# --- Unordered list -------------------------------------------------------
{
    my @body = ('- apple', '- banana', '- cherry');
    my ($lines) = convert(\@body, make_config());
    my $out = join "\n", @$lines;
    like $out, qr/<UL>/i,  'html: list open';
    like $out, qr/<LI>/i,  'html: list item';
    like $out, qr/apple/,  'html: first list item';
    like $out, qr/banana/, 'html: second list item';
    like $out, qr/<\/UL>/i,'html: list close';
}

# --- Numbered list --------------------------------------------------------
{
    my @body = ('+ one', '+ two');
    my ($lines) = convert(\@body, make_config());
    my $out = join "\n", @$lines;
    like $out, qr/<OL>/i,  'html: numlist open';
    like $out, qr/one/,    'html: numlist first item';
    like $out, qr/<\/OL>/i,'html: numlist close';
}

# --- Quote ----------------------------------------------------------------
{
    my @body = ("\tquoted text");
    my ($lines) = convert(\@body, make_config());
    my $out = join "\n", @$lines;
    like $out, qr/BLOCKQUOTE|quoted text/i, 'html: blockquote';
}

# --- Plain text target ----------------------------------------------------
{
    my ($lines) = convert(['**bold**'], make_config(target => 'txt'));
    # txt target has no bold tags, text passes through
    my $out = join ' ', @$lines;
    like $out, qr/bold/, 'txt: bold text passes through';
}

# --- Markdown target ------------------------------------------------------
{
    my ($lines) = convert(['**bold**'], make_config(target => 'md'));
    my $out = join ' ', @$lines;
    like $out, qr/\*\*bold\*\*/, 'md: bold uses ** markers';
}

# --- Comment lines are skipped -------------------------------------------
{
    my ($lines) = convert(['% this is a comment', 'real text'], make_config());
    my $out = join "\n", @$lines;
    unlike $out, qr/this is a comment/, 'comment line suppressed';
    like   $out, qr/real text/,         'real text kept';
}

# --- TOC accumulation ----------------------------------------------------
{
    my @body = ('= Section A =', '== Sub B ==');
    my ($lines, $toc) = convert(\@body, make_config());
    is ref $toc, 'ARRAY', 'TOC is arrayref';
    ok scalar @$toc >= 2, 'TOC has at least 2 entries';
    ok grep { /Section A/ } @$toc, 'TOC contains Section A';
    ok grep { /Sub B/     } @$toc, 'TOC contains Sub B';
}

done_testing;
