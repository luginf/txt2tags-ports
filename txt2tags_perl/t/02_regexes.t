#!/usr/bin/perl
use strict;
use warnings;
use Test::More;

use_ok 'Text::Txt2tags::Regexes', 'getRegexes';

my $rx = getRegexes();
ok ref $rx eq 'HASH', 'getRegexes returns a hashref';

# Block delimiters
ok '```'    =~ $rx->{blockVerbOpen},    'blockVerbOpen matches ```';
ok '"""'    =~ $rx->{blockRawOpen},     'blockRawOpen matches """';
ok "'''"    =~ $rx->{blockTaggedOpen},  'blockTaggedOpen matches \'\'\'';
ok '%%%'    =~ $rx->{blockCommentOpen}, 'blockCommentOpen matches %%%';

# Inline verbatim
ok '``` some code' =~ $rx->{'1lineVerb'}, '1lineVerb matches ``` text';

# Font marks
ok '**bold**'       =~ $rx->{fontBold},      'fontBold matches **bold**';
ok '//italic//'     =~ $rx->{fontItalic},     'fontItalic matches //italic//';
ok '__underline__'  =~ $rx->{fontUnderline},  'fontUnderline matches __underline__';
ok '--strike--'     =~ $rx->{fontStrike},     'fontStrike matches --strike--';
ok '``mono``'       =~ $rx->{fontMono},       'fontMono matches ``mono``';

# Lists
ok '- item'    =~ $rx->{list},    'list matches - item';
ok '+ item'    =~ $rx->{numlist}, 'numlist matches + item';
ok ': term def'=~ $rx->{deflist}, 'deflist matches : term';

# Bar
ok '--------------------' =~ $rx->{bar}, 'bar matches ----...';
ok '====================' =~ $rx->{bar}, 'bar matches ====...';

# Table
ok '| cell' =~ $rx->{table}, 'table matches | cell';

# Blank line
ok ''        =~ $rx->{blankline}, 'blankline matches empty string';
ok '   '     =~ $rx->{blankline}, 'blankline matches spaces';
ok '% comment' =~ $rx->{comment}, 'comment matches % comment';

# Title
ok '= Title ='     =~ $rx->{title},    'title matches = Title =';
ok '== Title =='   =~ $rx->{title},    'title matches == Title ==';
ok '+ Title +'     =~ $rx->{numtitle}, 'numtitle matches + Title +';

# Quote (leading tab)
ok "\tquoted" =~ $rx->{quote}, 'quote matches tab-indented';

# Special config line
ok '%! target: html' =~ $rx->{special}, 'special matches %! line';

# Email
ok 'foo@example.com' =~ $rx->{email}, 'email matches foo@example.com';

# Link
ok 'http://example.com' =~ $rx->{link}, 'link matches http URL';
ok 'www.example.com'    =~ $rx->{link}, 'link matches www. URL';

# Image
ok '[image.png]' =~ $rx->{img}, 'img matches [image.png]';
ok '[photo.jpg]' =~ $rx->{img}, 'img matches [photo.jpg]';

# Named link
ok '[label http://example.com]' =~ $rx->{linkmark}, 'linkmark matches named link';

# Macros
ok '%%date'   =~ $rx->{macros}, 'macros matches %%date';
ok '%%target' =~ $rx->{macros}, 'macros matches %%target';

# TOC
ok '%%toc'   =~ $rx->{toc}, 'toc matches %%toc';
ok ' %%toc ' =~ $rx->{toc}, 'toc matches indented %%toc';

done_testing;
