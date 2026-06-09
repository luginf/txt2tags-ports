package Text::Txt2tags::Output;

# txt2tags - output helpers: escaping, tags, TOC, headers/footers
# Port of txt2tags3_mod/output.py to Perl 5

use strict;
use warnings;
use Exporter 'import';
use POSIX qw();

our $VERSION = '3.9.0';

use Text::Txt2tags::Constants qw(
    $MY_NAME $MY_VERSION $MY_URL %ESCAPES %TARGET_TYPES %TARGET_NAMES
    $ESCCHAR $SEPARATOR %AA DFT_TEXT_WIDTH $STDOUT $MODULEOUT
);
use Text::Txt2tags::State qw(
    $AUTOTOC %CONF %TAGS %rules %regex $QUIET $DEBUG $VERBOSE
);
use Text::Txt2tags::Utils qw(Error Message Debug Readfile Savefile dotted_spaces);

# ---------------------------------------------------------------------------
# Escaping helpers
# ---------------------------------------------------------------------------

sub get_escapes {
    my ($target) = @_;
    $target = 'tex' if $target eq 'texs';
    return $ESCAPES{$target} // [];
}

sub doProtect {
    my ($target, $txt) = @_;
    for my $triple (@{ get_escapes($target) }) {
        my ($before, $protected, $after) = @$triple;
        $txt =~ s/\Q$before\E/$protected/g;
    }
    return $txt;
}

sub doEscape {
    my ($target, $txt) = @_;
    my $tmpmask = 'vvvvThisEscapingSuxvvvv';

    if ($rules{escapexmlchars}) {
        $txt =~ s/&/&amp;/g;
        $txt =~ s/</&lt;/g;
        $txt =~ s/>/&gt;/g;
    }

    if ($target eq 'sgml') {
        $txt =~ s/\xff/&yuml;/g;
    }
    elsif ($target eq 'pm6') {
        $txt =~ s/</\<\\#60\>/g;
    }
    elsif ($target eq 'mgp') {
        $txt =~ s/^%/ %/mg;
    }
    elsif ($target eq 'man') {
        $txt =~ s/^([.'])/\\&$1/mg;
        $txt =~ s/\Q$ESCCHAR\E/${ESCCHAR}e/g;
    }
    elsif ($target eq 'lout') {
        $txt =~ s/\Q$ESCCHAR\E/$tmpmask/g;
        $txt =~ s/"/"${ESCCHAR}""/g;
        $txt =~ s/([|&{}\@#^~])/"$1"/g;
        $txt =~ s/$tmpmask/"${ESCCHAR}${ESCCHAR}"/g;
    }
    elsif ($target =~ /^tex/) {
        $txt =~ s/\Q$ESCCHAR\E/$tmpmask/g;
        $txt =~ s/([#\$&%{}])/${ESCCHAR}$1/g;
        $txt =~ s/([~^])/${ESCCHAR}$1\{\}/g;
        $txt =~ s/([<|>])/\$$1\$/g;
        $txt =~ s/$tmpmask/maskEscapeChar('$\\backslash$')/ge;
    }
    elsif ($target eq 'rtf') {
        $txt =~ s/\Q$ESCCHAR\E/$ESCCHAR$ESCCHAR/g;
        $txt =~ s/([{}])/${ESCCHAR}$1/g;
    }
    return $txt;
}

sub doFinalEscape {
    my ($target, $txt) = @_;
    for my $triple (@{ get_escapes($target) }) {
        my ($before, $protected, $after) = @$triple;
        $txt =~ s/\Q$before\E/$after/g;
        $txt =~ s/\Q$protected\E/$before/g;
    }
    return $txt;
}

sub EscapeCharHandler {
    my ($action, $data) = @_;
    return $data unless $data =~ /\S/;
    if ($action eq 'mask') {
        $data =~ s/\\/$ESCCHAR/g;
    }
    elsif ($action eq 'unmask') {
        $data =~ s/\Q$ESCCHAR\E/\\/g;
    }
    else {
        Error("EscapeCharHandler: Invalid action '$action'");
    }
    return $data;
}

sub maskEscapeChar {
    my ($data) = @_;
    if (ref $data eq 'ARRAY') {
        return [ map { EscapeCharHandler('mask', $_) } @$data ];
    }
    return EscapeCharHandler('mask', $data);
}

sub unmaskEscapeChar {
    my ($data) = @_;
    if (ref $data eq 'ARRAY') {
        return [ map { EscapeCharHandler('unmask', $_) } @$data ];
    }
    return EscapeCharHandler('unmask', $data);
}

# ---------------------------------------------------------------------------
# Line-break helpers
# ---------------------------------------------------------------------------

sub addLineBreaks {
    my ($list) = @_;
    my @ret;
    for my $line (@$list) {
        $line =~ s/\n/\n/g;   # embedded \n stays as-is
        push @ret, "$line\n";
    }
    return \@ret;
}

sub expandLineBreaks {
    my ($list) = @_;
    my @ret;
    for my $line (@$list) {
        if (!defined $line || $line eq '') {
            push @ret, '';   # preserve blank lines (split discards them)
        } else {
            push @ret, split /\n/, $line, -1;
        }
    }
    return \@ret;
}

# ---------------------------------------------------------------------------
# Filter compilation
# ---------------------------------------------------------------------------

# Build a replacement closure from a template that may contain \1..\9 or $1..$9
# backreferences.  The closure is called within s/$rgx/$fn->()/ge so that
# $1,$2,... from the outer match are still alive when the closure runs.
sub _make_repl_closure {
    my ($template) = @_;
    return sub {
        # Snapshot outer-match captures before inner regex ops clobber them
        my @c = ($1,$2,$3,$4,$5,$6,$7,$8,$9);
        # Process Python re.sub replacement escapes:
        #   \\ → \    \n → newline    \r → CR    \t → tab    \1-\9 → group
        (my $r = $template) =~ s{\\(\\|n|r|t|[1-9])}{
            $1 eq '\\' ? '\\' :
            $1 eq 'n'  ? "\n" :
            $1 eq 'r'  ? "\r" :
            $1 eq 't'  ? "\t" :
            (defined $c[$1-1] ? $c[$1-1] : '')
        }ge;
        $r
    };
}

sub compile_filters {
    my ($filters, $errmsg) = @_;
    $errmsg //= 'Filter';
    return [] unless $filters && @$filters;
    my @compiled;
    for my $pair (@$filters) {
        my ($patt, $repl) = @$pair;
        # Perl 5.26+ warns on bare { not forming a valid quantifier ({n},{n,m}).
        # Python's re allows bare { and uses \{ for literal braces.
        # Translate to Perl-safe [{] / [}] in three steps to avoid
        # double-processing: first stash \{ away, handle bare {, then restore.
        my $PH = "\x00LB\x00";
        $patt =~ s/\\[{]/$PH/g;                          # \{ → placeholder
        $patt =~ s/[{](?!\d+,?\d*[}])/[{]/g;            # bare { (non-quantifier) → [{]
        $patt =~ s/\Q$PH\E/[{]/g;                        # placeholder → [{]
        $patt =~ s/\\[}]/[}]/g;                          # \} → [}]
        my $rgx = eval { qr/$patt/m };
        Error("$errmsg: '$patt': $@") if $@;
        push @compiled, [$rgx, _make_repl_closure($repl)];
    }
    return \@compiled;
}

# ---------------------------------------------------------------------------
# Tag helpers
# ---------------------------------------------------------------------------

sub enclose_me {
    my ($tagname, $txt) = @_;
    return ($TAGS{$tagname . 'Open'} // '')
         . $txt
         . ($TAGS{$tagname . 'Close'} // '');
}

sub get_tagged_link {
    my ($label, $url) = @_;

    my $target = $CONF{target} // '';

    my $is_email = ($url =~ /^[\w.+-]+\@[\w.-]+\.[A-Za-z]{2,4}/);
    my $is_img   = ($url =~ /\.(png|jpe?g|gif|eps|bmp|svg)$/i);

    my ($open_tag, $close_tag);

    if ($label) {
        if ($is_email) {
            $open_tag  = $TAGS{emailMark} // '';
            $close_tag = '';
        }
        else {
            $open_tag  = $TAGS{urlMark} // '';
            $close_tag = '';
        }
    }
    else {
        if ($is_email) {
            $open_tag  = $TAGS{email} // '';
            $close_tag = '';
        }
        else {
            $open_tag  = $TAGS{url} // '';
            $close_tag = '';
        }
    }

    # Add protocol to bare www.*/ftp.* URLs (guessed URLs)
    my $orig_url = $url;
    if (!$is_email && $url =~ /^(?:www[23]?|ftp)\./i) {
        my $proto = ($url =~ /^ftp\./i) ? 'ftp://' : 'http://';
        $url = $proto . $url;
    }

    # Escape specials in URL (Python: if not linkable or escapeurl)
    # doEscape handles & → &amp; for escapexmlchars targets (HTML etc.)
    if (!$rules{linkable} || $rules{escapeurl}) {
        $url = doEscape($target, $url);
    }

    # Escape specials in label text (Python always does this)
    $label = doEscape($target, $label) if $label;

    # Use the (already-escaped) url directly for href
    my $url_esc = $url;

    # Display: label if given, else original URL text (no added proto)
    my $display;
    if ($label) {
        # Check if label is an image [img.ext] → expand to <IMG> tag
        if ($label =~ /^\[([A-Za-z0-9_,.+%\$#\@!?+~\/-]+\.(?:png|jpe?g|gif|eps|bmp|svg))\]$/i) {
            my $img_src = $1;
            my $img_tag = $TAGS{img} // '';
            if ($img_tag) {
                my $align_tag = $rules{imgalignable} ? ($TAGS{_imgAlignCenter} // '') : '';
                $img_tag =~ s/~A~/$align_tag/g;
                my $first2 = 1;
                $img_tag =~ s/\\a/$first2 ? do { $first2=0; $img_src } : $img_src/ge;
                $display = $img_tag;
            } else {
                $display = $label;
            }
        } else {
            $display = $label;  # already escaped by doEscape above
        }
    } else {
        # No label: display the original URL (without added protocol)
        # Escape it the same way as the URL
        my $disp_url = $orig_url;
        if (!$rules{linkable} || $rules{escapeurl}) {
            $disp_url = doEscape($target, $disp_url);
        }
        $display = $disp_url;
    }

    # Substitution order: labelbeforelink OR non-linkable target → label first, URL second
    my ($first_val, $second_val);
    if ($label && ($rules{labelbeforelink} || !$rules{linkable})) {
        $first_val  = $display;
        $second_val = $url_esc;
    } else {
        $first_val  = $url_esc;
        $second_val = $display;
    }
    my $result = $open_tag;
    my $first  = 1;
    $result =~ s/\\a/$first ? do { $first = 0; $first_val } : $second_val/ge;

    return $result;
}

sub parse_deflist_term {
    my ($line) = @_;
    if ($line =~ /^( *): (.*)$/) {
        return ($1, $2);
    }
    return ('', $line);
}

sub get_image_align {
    my ($img_tag) = @_;
    # Look for leading/trailing spaces around [image]
    if ($img_tag =~ /^\s+\[/) { return 'right'  }
    if ($img_tag =~ /\]\s+$/) { return 'left'   }
    return 'center';
}

sub get_encoding_string {
    my ($encoding, $target) = @_;
    return '' unless $encoding;
    my $enc_lc = lc $encoding;
    if ($target =~ /^x?html/) {
        return qq{<meta http-equiv="Content-Type" content="text/html; charset=$encoding">};
    }
    elsif ($target eq 'tex' || $target eq 'texs') {
        my %tex_enc = (
            'utf-8'       => 'utf8',
            'iso-8859-1'  => 'latin1',
            'iso-8859-2'  => 'latin2',
        );
        my $tex = $tex_enc{$enc_lc} or return '';
        return "\\usepackage[$tex]{inputenc}";
    }
    elsif ($target eq 'sgml') {
        return qq{<!doctype html public "-//W3C//DTD HTML 4.0 Transitional//EN"\n"http://www.w3.org/TR/REC-html40/loose.dtd">};
    }
    return '';
}

# ---------------------------------------------------------------------------
# Comment line
# ---------------------------------------------------------------------------

sub doCommentLine {
    my ($txt) = @_;
    $txt = maskEscapeChar($txt);
    my $ctag = $TAGS{comment} // '';
    if ($ctag =~ /--/ && $txt =~ /--/) {
        $txt =~ s/-(?=-)/-\\/g;
    }
    return '' unless $ctag;
    $txt =~ s/\a/$txt/;    # \a placeholder
    (my $out = $ctag) =~ s/\\a/$txt/;
    return $out;
}

# ---------------------------------------------------------------------------
# post_voodoo
# ---------------------------------------------------------------------------

sub post_voodoo {
    my ($lines, $config) = @_;
    my $loser1 = 'No, no. Your PostVoodoo regex is wrong.';
    my $loser2 = 'Dear PostVoodoo apprentice: regex right but replacement wrong';
    my $subject = join "\n", @$lines;
    my $spells  = compile_filters($config->{postvoodoo}, $loser1);
    for my $pair (@$spells) {
        my ($rgx, $repl_fn) = @$pair;
        eval { $subject =~ s/$rgx/$repl_fn->()/ge };
        Error($loser2) if $@;
    }
    return [ split /\n/, $subject, -1 ];
}

# ---------------------------------------------------------------------------
# finish_him – write output
# ---------------------------------------------------------------------------

sub finish_him {
    my ($outlist, $config) = @_;
    my $outfile = $config->{outfile};
    if ($DEBUG) {
        my $lim2 = $#$outlist < 15 ? $#$outlist : 15;
        print STDERR "DEBUG finish_him ENTRY: outlist has ", scalar(@$outlist), " lines\n";
        for my $i (0..$lim2) {
            print STDERR "  entry[$i]: <<$outlist->[$i]>>\n";
        }
    }
    $outlist = unmaskEscapeChar($outlist);
    $outlist = expandLineBreaks($outlist);

    # Apply postproc filters
    if ($config->{postproc} && @{ $config->{postproc} }) {
        my $filters = compile_filters($config->{postproc}, 'Invalid PostProc filter regex');
        my @post;
        for my $line (@$outlist) {
            for my $pair (@$filters) {
                my ($rgx, $repl_fn) = @$pair;
                eval { $line =~ s/$rgx/$repl_fn->()/ge };
                Error('Invalid PostProc filter replacement') if $@;
            }
            push @post, $line;
        }
        $outlist = \@post;
    }

    if ($config->{postvoodoo} && @{ $config->{postvoodoo} }) {
        $outlist = post_voodoo($outlist, $config);
    }

    # Save to file_dict (global via State)
    if ($DEBUG) {
        my $lim = $#$outlist < 15 ? $#$outlist : 15;
        print STDERR "DEBUG finish_him: outlist has ", scalar(@$outlist), " lines\n";
        for my $i (0..$lim) {
            print STDERR "  [$i]: <<$outlist->[$i]>>\n";
        }
    }
    $Text::Txt2tags::State::file_dict{$outfile} = $outlist
        unless $config->{target} =~ /^csv/;

    if ($outfile eq $MODULEOUT) {
        my @all;
        push @all, $Text::Txt2tags::State::file_dict{$_}
            for keys %Text::Txt2tags::State::file_dict;
        return \@all;
    }
    elsif ($outfile eq $STDOUT) {
        my @all;
        push @all, @{ $Text::Txt2tags::State::file_dict{$_} // [] }
            for keys %Text::Txt2tags::State::file_dict;
        print "$_\n" for @all;
    }
    else {
        for my $wf (keys %Text::Txt2tags::State::file_dict) {
            Savefile($wf, addLineBreaks($Text::Txt2tags::State::file_dict{$wf}));
        }
        unless ($QUIET) {
            print "$MY_NAME wrote $_\n"
                for keys %Text::Txt2tags::State::file_dict;
        }
    }
    return;
}

# ---------------------------------------------------------------------------
# fix_relative_path
# ---------------------------------------------------------------------------

sub fix_relative_path {
    my ($path) = @_;
    return $path unless $CONF{'fix-path'};
    return $path if $path =~ /^https?:|^ftp:|^#/;
    return $path if $path =~ m{^/};
    return $path if $CONF{infile} =~ /^-/;
    return $path if ($CONF{outfile} // '') =~ /^-/;

    my $src_dir = $CONF{sourcefile} // '';
    if ($src_dir) {
        require File::Basename;
        $src_dir = File::Basename::dirname($src_dir);
    }
    require File::Spec;
    return File::Spec->rel2abs($path, $src_dir);
}

# ---------------------------------------------------------------------------
# fix_css_out_path
# ---------------------------------------------------------------------------

sub fix_css_out_path {
    my ($config) = @_;
    return [] unless $config->{style} && @{ $config->{style} };
    return $config->{style};
}

# ---------------------------------------------------------------------------
# beautify_me – indent/format output
# ---------------------------------------------------------------------------

sub beautify_me {
    my ($what, $tag, $config) = @_;
    my @ret;
    if ($rules{indentverbblock} && $what eq 'verb') {
        push @ret, '    ' . $_ for @$tag;
    }
    else {
        push @ret, @$tag;
    }
    return \@ret;
}

# ---------------------------------------------------------------------------
# TOC functions
# ---------------------------------------------------------------------------

sub toc_inside_body {
    my ($body, $toc, $config) = @_;
    return $body if $AUTOTOC;

    my $toc_mark = 'vvvTOCvvv';
    my @ret;
    for my $line (@$body) {
        if (index($line, $toc_mark) >= 0) {
            push @ret, @$toc if $config->{toc};
        }
        else {
            push @ret, $line;
        }
    }
    return \@ret;
}

sub toc_tagger {
    my ($toc, $config) = @_;
    my @ret;
    if ($config->{'toc-only'} || ($config->{toc} && !$TAGS{TOC})) {
        # convert the TOC list (t2t markup) to target format
        my %fakeconf = %$config;
        $fakeconf{headers}    = 0;
        $fakeconf{'toc-only'} = 0;
        $fakeconf{'mask-email'} = 0;
        $fakeconf{preproc}    = [];
        $fakeconf{postproc}   = [];
        $fakeconf{postvoodoo} = [];
        $fakeconf{'css-sugar'}= 0;
        $fakeconf{'fix-path'} = 0;
        require Text::Txt2tags::Converter;
        my ($body, undef) = Text::Txt2tags::Converter::convert($toc, \%fakeconf);
        @ret = @$body;
    }
    elsif ($config->{toc} && $TAGS{TOC}) {
        @ret = ($TAGS{TOC});
    }
    return \@ret;
}

sub toc_formatter {
    my ($toc, $config) = @_;
    return $toc if $config->{'toc-only'};
    return []   unless $config->{toc};

    my @ret = @$toc;
    unshift @ret, $TAGS{tocOpen}  if $TAGS{tocOpen};
    push    @ret, $TAGS{tocClose} if $TAGS{tocClose};

    if ($AUTOTOC) {
        if ($rules{autotocwithbars}) {
            my $para = ($TAGS{paragraphOpen} // '') . ($TAGS{paragraphClose} // '');
            my $bar  = $TAGS{bar1} // ('-' x DFT_TEXT_WIDTH);
            $bar =~ s/\a/'-' x DFT_TEXT_WIDTH/e if $bar =~ /\a/;
            my @tocbar = ($para, $bar, $para);
            @ret = (@tocbar, @ret, @tocbar);
        }
        push @ret, '' if $rules{blankendautotoc};
        unshift @ret, $TAGS{pageBreak} if $rules{autotocnewpagebefore};
        push    @ret, $TAGS{pageBreak} if $rules{autotocnewpageafter};
    }
    return \@ret;
}

# ---------------------------------------------------------------------------
# Header template + doHeader
# ---------------------------------------------------------------------------

# Minimal built-in header templates (subset of original)
my %HEADER_TEMPLATE = (
    html => 'DYNAMIC_HTML',
    xhtml => <<'END_XHTML',
<?xml version="1.0"
      encoding="%(ENCODING)s"
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>%(HEADER1)s</title>
<meta name="generator" content="http://txt2tags.org" />
<link rel="stylesheet" type="text/css" href="%(STYLE)s" />
</head>
<body bgcolor="white" text="black">
<div align="center">
<h1>%(HEADER1)s</h1>
<h2>%(HEADER2)s</h2>
<h3>%(HEADER3)s</h3>
</div>
END_XHTML
    xhtmls => <<'END_XHTMLS',
<?xml version="1.0"
      encoding="%(ENCODING)s"
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>%(HEADER1)s</title>
<meta name="generator" content="http://txt2tags.org" />
<link rel="stylesheet" type="text/css" href="%(STYLE)s" />
<style type="text/css">body {background-color:#FFFFFF ; color:#000000}</style>
</head>
<body>
<div style="text-align:center">
<h1>%(HEADER1)s</h1>
<h2>%(HEADER2)s</h2>
<h3>%(HEADER3)s</h3>
</div>
END_XHTMLS
    html5 => <<'END_HTML5',
<!DOCTYPE html>
<html>
<head>
<meta charset="%(ENCODING)s">
<title>%(HEADER1)s</title>
<meta name="generator" content="http://txt2tags.org">
<link rel="stylesheet" href="%(STYLE)s">
<style>
body{background-color:#fff;color:#000;}
hr{background-color:#000;border:0;color:#000;}
hr.heavy{height:5px;}
hr.light{height:1px;}
img{border:0;display:block;}
img.right{margin:0 0 0 auto;}
img.center{border:0;margin:0 auto;}
table th,table td{padding:4px;}
.center,header{text-align:center;}
table.center {margin-left:auto; margin-right:auto;}
.right{text-align:right;}
.left{text-align:left;}
.tableborder,.tableborder td,.tableborder th{border:1px solid #000;}
.underline{text-decoration:underline;}
</style>
</head>
<body>
<header>
<hgroup>
<h1>%(HEADER1)s</h1>
<h2>%(HEADER2)s</h2>
<h3>%(HEADER3)s</h3>
</hgroup>
</header>
<article>
END_HTML5
    htmls => <<'END_HTMLS',
<!DOCTYPE html>
<html>
<head>
<meta charset="%(ENCODING)s">
<title>%(HEADER1)s</title>
<meta name="generator" content="http://txt2tags.org">
<link rel="stylesheet" href="%(STYLE)s">
<style>
body{background-color:#fff;color:#000;}
hr{background-color:#000;border:0;color:#000;}
hr.heavy{height:5px;}
hr.light{height:1px;}
img{border:0;display:block;}
img.right{margin:0 0 0 auto;}
table,img.center{border:0;margin:0 auto;}
table th,table td{padding:4px;}
.center,header{text-align:center;}
.right{text-align:right;}
.tableborder,.tableborder td,.tableborder th{border:1px solid #000;}
.underline{text-decoration:underline;}
</style>
</head>
<body>
<article>
END_HTMLS
    txt => '%(HEADER1)s
%(HEADER2)s
%(HEADER3)s
',
    tex => <<'END_TEX',
\documentclass{article}
\usepackage{graphicx}
\usepackage{paralist} %% needed for compact lists
\usepackage[normalem]{ulem} %% needed by strike
\usepackage[urlcolor=blue,colorlinks=true]{hyperref}
\usepackage[%(ENCODING)s]{inputenc}  %% char encoding
\usepackage{%(STYLE)s}  %% user defined

\title{%(HEADER1)s}
\author{%(HEADER2)s}
\begin{document}
\date{%(HEADER3)s}
\maketitle
\clearpage
END_TEX
    man => ".TH \"%(HEADER1)s\" 1 \"%(HEADER3)s\" \"%(HEADER2)s\"\n",
    rst => '',
    md  => "%(HEADER1)s\n%(HEADER2)s\n%(HEADER3)s\n",
    adoc=> "= %(HEADER1)s\n%(HEADER2)s\n%(HEADER3)s\n",
    sgml => <<'END_SGML',
<!doctype linuxdoc system>
<article>
<title>%(HEADER1)s
<author>%(HEADER2)s
<date>%(HEADER3)s
END_SGML
    dbk => <<'END_DBK',
<?xml version="1.0"
      encoding="%(ENCODING)s"
?>
<!DOCTYPE article PUBLIC "-//OASIS//DTD DocBook XML V4.5//EN" "docbook/dtd/xml/4.5/docbookx.dtd">
<article lang="en">
  <articleinfo>
    <title>%(HEADER1)s</title>
    <authorgroup>
      <author><othername>%(HEADER2)s</othername></author>
    </authorgroup>
    <date>%(HEADER3)s</date>
  </articleinfo>
END_DBK
    lout => <<'END_LOUT',
@SysInclude { doc }
@SysInclude { tbl }
@Document
  @InitialFont { Times Base 12p }  # Times, Courier, Helvetica, ...
  @PageOrientation { Portrait }    # Portrait, Landscape
  @ColumnNumber { 1 }              # Number of columns (2, 3, ...)
  @PageHeaders { Simple }          # None, Simple, Titles, NoTitles
  @InitialLanguage { English }     # German, French, Portuguese, ...
  @OptimizePages { Yes }           # Yes/No smart page break feature
//
@Text @Begin
@Display @Heading { %(HEADER1)s }
@Display @I { %(HEADER2)s }
@Display { %(HEADER3)s }
#@NP                               # Break page after Headers
END_LOUT
    moin => "'''%(HEADER1)s'''\n\n''%(HEADER2)s''\n\n%(HEADER3)s\n",
    gwiki => "*%(HEADER1)s*\n\n%(HEADER2)s\n\n_%(HEADER3)s_\n",
    doku => "===== %(HEADER1)s =====\n\n**//%(HEADER2)s//**\n\n//%(HEADER3)s//\n",
    pmw => "(:Title %(HEADER1)s:)\n\n(:Description %(HEADER2)s:)\n\n(:Summary %(HEADER3)s:)\n",
    wiki => "'''%(HEADER1)s'''\n\n%(HEADER2)s\n\n''%(HEADER3)s''\n",
    red => "h1. %(HEADER1)s\n\nAuthor: %(HEADER2)s\nDate: %(HEADER3)s\n",
    vimwiki => "%%title %(HEADER1)s\n## by %(HEADER2)s in %(HEADER3)s\n%%toc %(HEADER1)s\n",
    mgp => <<'END_MGP',
#!/usr/X11R6/bin/mgp -t 90
%%deffont "normal"    xfont  "utopia-medium-r", charset "iso8859-1"
%%deffont "normal-i"  xfont  "utopia-medium-i", charset "iso8859-1"
%%deffont "normal-b"  xfont  "utopia-bold-r"  , charset "iso8859-1"
%%deffont "normal-bi" xfont  "utopia-bold-i"  , charset "iso8859-1"
%%deffont "mono"      xfont "courier-medium-r", charset "iso8859-1"
%%default 1 size 5
%%default 2 size 8, fore "yellow", font "normal-b", center
%%default 3 size 5, fore "white",  font "normal", left, prefix "  "
%%tab 1 size 4, vgap 30, prefix "     ", icon arc "red" 40, leftfill
%%tab 2 prefix "            ", icon arc "orange" 40, leftfill
%%tab 3 prefix "                   ", icon arc "brown" 40, leftfill
%%tab 4 prefix "                          ", icon arc "darkmagenta" 40, leftfill
%%tab 5 prefix "                                ", icon arc "magenta" 40, leftfill
%%%%------------------------- end of headers -----------------------------
%%page




%%size 10, center, fore "yellow"
%(HEADER1)s

%%font "normal-i", size 6, fore "white", center
%(HEADER2)s

%%font "mono", size 7, center
%(HEADER3)s
END_MGP
    utmac => <<'END_UTMAC',
\
.DT "%(HEADER1)s"
.DA "%(HEADER2)s"
.DI "%(HEADER3)s"
.H1 "%(HEADER1)s"
.H* "%(HEADER2)s"
.
.\\" txt2tags shortcuts
.ds url \\W'\\\\$2'\\\\$1\\W
.ds mail \\W'mailto:\\\\$2'\\\\$1\\W
.ds underl \\Z'\\\\$*'\\v'.25m'\\l"\\w'\\\\$*'u"\\v'-.25m'
.ds strike \\Z'\\\\$*'\\v'-.25m'\\l"\w'\\\\$*'u"\\v'.25m'
.\\"ds underl \\X'SetColor blue'\\\\$1\\X'SetColor black'
.\\"ds strike \\X'SetColor red'\\\\$1\\X'SetColor black'
.\
END_UTMAC
    pm6 => <<'END_PM6',
<PMTags1.0 win><C-COLORTABLE ("Preto" 1 0 0 0)
><@Normal=
  <FONT "Times New Roman"><CCOLOR "Preto"><SIZE 11>
  <HORIZONTAL 100><LETTERSPACE 0><CTRACK 127><CSSIZE 70><C+SIZE 58.3>
  <C-POSITION 33.3><C+POSITION 33.3><P><CBASELINE 0><CNOBREAK 0><CLEADING -0.05>
  <GGRID 0><GLEFT 7.2><GRIGHT 0><GFIRST 0><G+BEFORE 7.2><G+AFTER 0>
  <GALIGNMENT "justify"><GMETHOD "proportional"><G& "ENGLISH">
  <GPAIRS 12><G%% 120><GKNEXT 0><GKWIDOW 0><GKORPHAN 0><GTABS $>
  <GHYPHENATION 2 34 0><GWORDSPACE 75 100 150><GSPACE -5 0 25>
><@Bullet=<@-PARENT "Normal"><FONT "Abadi MT Condensed Light">
  <GLEFT 14.4><G+BEFORE 2.15><G%% 110><GTABS(25.2 l "")>
><@PreFormat=<@-PARENT "Normal"><FONT "Lucida Console"><SIZE 8><CTRACK 0>
  <GLEFT 0><G+BEFORE 0><GALIGNMENT "left"><GWORDSPACE 100 100 100><GSPACE 0 0 0>
><@Title1=<@-PARENT "Normal"><FONT "Arial"><SIZE 14><B>
  <GCONTENTS><GLEFT 0><G+BEFORE 0><GALIGNMENT "left">
><@Title2=<@-PARENT "Title1"><SIZE 12><G+BEFORE 3.6>
><@Title3=<@-PARENT "Title1"><SIZE 10><GLEFT 7.2><G+BEFORE 7.2>
><@Title4=<@-PARENT "Title3">
><@Title5=<@-PARENT "Title3">
><@Quote=<@-PARENT "Normal"><SIZE 10><I>>

%(HEADER1)s
%(HEADER2)s
%(HEADER3)s
END_PM6
    creole => "%(HEADER1)s\n%(HEADER2)s\n%(HEADER3)s\n",
    gmi => "# %(HEADER1)s\n# %(HEADER2)s\n# %(HEADER3)s\n",
    bbcode => "%(HEADER1)s\n%(HEADER2)s\n%(HEADER3)s\n",
    spip => "{{{%(HEADER1)s}}}\n\n{{%(HEADER2)s}}\n\n{%(HEADER3)s}\n\n",
    tml => "---+!! %(HEADER1)s\n*%(HEADER2)s* %%BR%% __%(HEADER3)s__\n",
);

# RTF template — stored separately due to backslash complexity
$HEADER_TEMPLATE{rtf} = <<'END_RTF';
{\rtf1\ansi\ansicpg1252\deff0
{\fonttbl
{\f0\froman Times;}
{\f1\fswiss Arial;}
{\f2\fmodern Courier;}
}
{\colortbl;\red0\green0\blue255;}
{\stylesheet
{\s1\sbasedon222\snext1\f0\fs24\cf0 Normal;}
{\s2\sbasedon1\snext2{\*\txttags paragraph}\f0\fs24\qj\sb0\sa0\sl480\slmult1\li0\ri0\fi360 Body Text;}
{\s3\sbasedon2\snext3{\*\txttags verbatim}\f2\fs20\ql\sb0\sa240\sl240\slmult1\li720\ri720\fi0 Verbatim;}
{\s4\sbasedon2\snext4{\*\txttags quote}\f0\fs24\qj\sb0\sa0\sl480\slmult1\li720\ri720\fi0 Block Quote;}
{\s10\sbasedon1\snext10\keepn{\*\txttags maintitle}\f1\fs24\qc\sb0\sa0\sl480\slmult1\li0\ri0\fi0 Title;}
{\s11\sbasedon1\snext2\keepn{\*\txttags title1}\f1\fs24\qc\sb240\sa240\sl480\slmult1\li0\ri0\fi0\b Heading 1;}
{\s12\sbasedon11\snext2\keepn{\*\txttags title2}\f1\fs24\ql\sb240\sa240\sl480\slmult1\li0\ri0\fi0\b Heading 2;}
{\s13\sbasedon11\snext2\keepn{\*\txttags title3}\f1\fs24\ql\sb240\sa240\sl480\slmult1\li360\ri0\fi0\b Heading 3;}
{\s14\sbasedon11\snext2\keepn{\*\txttags title4}\f1\fs24\ql\sb240\sa240\sl480\slmult1\li360\ri0\fi0\b\i Heading 4;}
{\s15\sbasedon11\snext2\keepn{\*\txttags title5}\f1\fs24\ql\sb240\sa240\sl480\slmult1\li360\ri0\fi0\i Heading 5;}
{\s21\sbasedon2\snext21{\*\txttags list}\f0\fs24\qj\sb0\sa0\sl480\slmult1{\*\txttags list indent}\li720\ri0\fi-360 List;}
}
{\*\listtable
{\list\listtemplateid1
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li720\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li1080\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li1440\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li1800\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li2160\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li2520\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li2880\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li3240\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li3600\ri0\fi-360}
\listid1}
{\list\listtemplateid2
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'00.;}{\levelnumbers\'01;}{\*\txttags list indent}\li720\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'01.;}{\levelnumbers\'01;}{\*\txttags list indent}\li1080\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'02.;}{\levelnumbers\'01;}{\*\txttags list indent}\li1440\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'03.;}{\levelnumbers\'01;}{\*\txttags list indent}\li1800\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'04.;}{\levelnumbers\'01;}{\*\txttags list indent}\li2160\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'05.;}{\levelnumbers\'01;}{\*\txttags list indent}\li2520\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'06.;}{\levelnumbers\'01;}{\*\txttags list indent}\li2880\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'07.;}{\levelnumbers\'01;}{\*\txttags list indent}\li3240\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'08.;}{\levelnumbers\'01;}{\*\txttags list indent}\li3600\ri0\fi-360}
\listid2}
{\list\listtemplateid3
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'02\'00.;}{\levelnumbers\'01;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'04\'00.\'01.;}{\levelnumbers\'01\'03;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'06\'00.\'01.\'02.;}{\levelnumbers\'01\'03\'05;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'08\'00.\'01.\'02.\'03.;}{\levelnumbers\'01\'03\'05\'07;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'10\'00.\'01.\'02.\'03.\'04.;}{\levelnumbers\'01\'03\'05\'07\'09;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'02\'05.;}{\levelnumbers\'01;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'02\'06.;}{\levelnumbers\'01;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'02\'07.;}{\levelnumbers\'01;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow0{\leveltext \'02\'08.;}{\levelnumbers\'01;}}
\listid3}
}
{\listoverridetable
{\listoverride\listid1\listoverridecount0\ls1}
{\listoverride\listid2\listoverridecount0\ls2}
{\listoverride\listid3\listoverridecount0\ls3}
}
{\info
{\title %(HEADER1)s }
{\author %(HEADER2)s }
}
\deflang1033\widowctrl\hyphauto\uc1\fromtext
END_RTF

# mom template
$HEADER_TEMPLATE{mom} = <<'END_MOM';
\
\# Cover and title
.TITLE "%(HEADER1)s"
.AUTHOR "%(HEADER2)s"
\#.DOCTITLE \" ONLY to collate different files (sections, chapters etc.)
.SUBTITLE "%(HEADER3)s"
\#
\# printstyle: typeset or typewrite it's MANDATORY!
.PRINTSTYLE TYPESET
\#.PRINTSTYLE TYPEWRITE
\#
\# doctype: default, chapter, user-defined, letter (commented is "default")
\#.DOCTYPE DEFAULT
\#
\# copystyle: draft or final
.COPYSTYLE FINAL
\#.COPYSTYLE DRAFT
\#
\# Default values for some strings
\# They're valid in every printstyle or copystyle
\# Here are MY defaults (italian)
\# For a more general use I think they should be groff commented
\#
\#.CHAPTER_STRING "Capitolo"
\#.ATTRIBUTE_STRING "di"
\#.TOC_HEADER_STRING "Indice"
\#.ENDNOTE_TITLE "Note"
\#
\# section break char "#" for 1 time (LINEBREAK)
\#.LINEBREAK_CHAR # 1
\# a null end string
.FINIS_STRING ""
\#
\# Typesetting values
\# These are all MY preferences! Comment out for default.
\#
.PAPER A4
\# Left margin (c=centimeters)
\#.L_MARGIN 2.8c
\# Length of line (it's for 62 chars a line for point size 12 in typewrite style)
\#.LL 15.75c
\# Palatino groff font, better than Times for reading. IMHO
.FAMILY P
.PT_SIZE 12
\# line spacing
.LS 18
\# left aligned (mom macro defaults to "both aligned")
.QUAD L
\# No hyphenation
.HY OFF
\# Header and footer sizes
.HEADER_SIZE -1
.FOOTER_SIZE -1
.PAGENUM_SIZE -2
\#
\# Other options
\#
\# Indent space for "quote" and "blockquote" (defaults are good too!)
\#.QUOTE_INDENT 2
\#.BLOCKQUOTE_INDENT 2
\#
\# Footnotes
\#
\# Next gives you superscript numbers (use STAR for symbols, it's default)
\# use additional argument NO_SUPERSCRIPT for typewrite printstyle
\#.FOOTNOTE_MARKER_STYLE NUMBER
\# Cover title at about 1/3 from top
\#.DOCHEADER_ADVANCE 7.5c
\#
\# Double quotes italian style! aka << and >> It works only for "typeset" printstyle
\#.SMARTQUOTES IT
\# Next cmd is MANDATORY.
.START
END_MOM

# Additional aliases/defaults
$HEADER_TEMPLATE{wp} = "%(HEADER1)s\n%(HEADER2)s\n%(HEADER3)s\n";

sub _doHeader_html {
    my ($headers, $config) = @_;

    my ($h1, $h2, $h3) = map { $_ // '' } @{$headers}[0, 1, 2];
    my $enc   = $config->{encoding} // '';
    my $style = ($config->{style} && @{ $config->{style} })
                    ? $config->{style}[0] : '';

    my @head;
    push @head, '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">';
    push @head, '<HTML>';
    push @head, '<HEAD>';
    push @head, '<META NAME="generator" CONTENT="http://txt2tags.org">';
    push @head, "<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; charset=$enc\">"
        if $enc;
    push @head, "<LINK REL=\"stylesheet\" TYPE=\"text/css\" HREF=\"$style\">"
        if $style;
    push @head, "<TITLE>$h1</TITLE>" if $h1;
    push @head, '</HEAD><BODY BGCOLOR="white" TEXT="black">';
    push @head, '<CENTER>';
    push @head, "<H1>$h1</H1>" if $h1;
    push @head, "<FONT SIZE=\"4\"><I>$h2</I></FONT><BR>" if $h2;
    push @head, "<FONT SIZE=\"4\">$h3</FONT>" if $h3;
    push @head, '</CENTER>';
    push @head, '';

    return @head;
}

sub _build_head_data {
    my ($headers, $config) = @_;
    my $target = $config->{target};
    my $enc = $config->{encoding} // '';
    # Normalize encoding name for targets that need it (Python get_encoding_string)
    if ($enc && $target =~ /^tex/) {
        my %tex_enc = (
            'utf-8'       => 'utf8',
            'us-ascii'    => 'ascii',
            'windows-1250'=> 'cp1250',
            'windows-1252'=> 'cp1252',
            'ibm850'      => 'cp850',
            'ibm852'      => 'cp852',
            'iso-8859-1'  => 'latin1',
            'iso-8859-2'  => 'latin2',
            'iso-8859-3'  => 'latin3',
            'iso-8859-4'  => 'latin4',
            'iso-8859-5'  => 'latin5',
            'iso-8859-9'  => 'latin9',
            'koi8-r'      => 'koi8-r',
        );
        $enc = $tex_enc{lc $enc} // $enc;
    }
    my %d = (
        ENCODING => $enc,
        STYLE    => '',
        HEADER1  => $headers->[0] // '',
        HEADER2  => $headers->[1] // '',
        HEADER3  => $headers->[2] // '',
        BODY     => join("\n", @{ $config->{fullBody} // [] }),
    );
    if ($config->{style} && @{ $config->{style} }) {
        my $sty = $config->{style}[0];
        # LaTeX requires \usepackage{name} without the .sty extension
        $sty =~ s/\.sty$//i if $target =~ /^tex/i;
        $d{STYLE} = $sty;
    }
    return %d;
}

sub _apply_tmpl {
    my ($tmpl_str, %head_data) = @_;
    my @tmpl_lines = split /\n/, $tmpl_str, -1;
    my @out;
    for my $line (@tmpl_lines) {
        if ($line =~ /%\(([A-Z0-9]+)\)s/) {
            my $key = $1;
            if (!$head_data{$key}) {
                next unless $line =~ /%\([A-Z0-9]+\)s.*%\([A-Z0-9]+\)s/;
            }
        }
        $line =~ s/%\((\w+)\)s/$head_data{$1} \/\/ ''/ge;
        $line =~ s/%%/%/g;   # Python %% → % literal (after %(KEY)s substitution)
        push @out, $line;
    }
    return \@out;
}

sub doHeader {
    my ($headers, $config) = @_;
    return $config->{fullBody} unless $config->{headers};

    $headers //= [];
    $headers = ['', '', ''] unless @$headers;

    my $target = $config->{target};

    # User-provided template file (-T / --template)
    if ($config->{template}) {
        my $tbase = $config->{template};
        my $found;
        for my $name ("$tbase.$target", $tbase) {
            if (-f $name) { $found = $name; last }
        }
        Error("Cannot find template file: $tbase") unless $found;
        my $lines = Readfile($found, 1);
        my $tmpl_str = join("\n", @$lines);
        my %head_data = _build_head_data($headers, $config);
        return _apply_tmpl($tmpl_str, %head_data);
    }

    my $tmpl_str = $HEADER_TEMPLATE{$target} // '';

    # HTML (and aliases) use the v2-compatible generator
    if ($tmpl_str eq 'DYNAMIC_HTML') {
        my @head  = _doHeader_html($headers, $config);
        my @body  = @{ $config->{fullBody} // [] };
        my @eod;
        if ($TAGS{EOD}) { push @eod, $TAGS{EOD} }

        return [@head, @body, @eod];
    }

    # For rst/md/adoc: no template, just return body
    if (!$tmpl_str) {
        return $config->{fullBody};
    }

    # Apply template (header section only), then directly concatenate body + EOD
    my %head_data = _build_head_data($headers, $config);
    my $header_lines = _apply_tmpl($tmpl_str, %head_data);
    my @result = @$header_lines;
    push @result, @{ $config->{fullBody} // [] };
    push @result, $TAGS{EOD} if $TAGS{EOD};
    return \@result;
}

# ---------------------------------------------------------------------------
# doFooter
# ---------------------------------------------------------------------------

sub doFooter {
    my ($config) = @_;
    return [] unless $config->{headers};

    my @ret;

    # Blank line before footer if needed
    if ($Text::Txt2tags::State::BLOCK) {
        my $last = $Text::Txt2tags::State::BLOCK->{last} // '';
        push @ret, '' unless $rules{"blanksaround$last"};
    }

    # Generator comment
    if ($TAGS{comment}) {
        my $tgt = $config->{target} // '';
        $tgt = 'LaTeX2e'  if $tgt eq 'tex';
        $tgt = 'ASCII Art' if $tgt eq 'aat';
        my $t2t = "$tgt code generated by $MY_NAME $MY_VERSION ($MY_URL)";
        my $rcl = $config->{realcmdline};
        my $cmd = 'cmdline: ' . $MY_NAME . ' '
                . join(' ', ref $rcl eq 'ARRAY' ? @$rcl : ());
        push @ret, doCommentLine($t2t);
        push @ret, doCommentLine($cmd);
    }
    return \@ret;
}

# ---------------------------------------------------------------------------
# listTargets, dumpConfig
# ---------------------------------------------------------------------------

sub listTargets {
    for my $typ (sort keys %TARGET_TYPES) {
        my @tgts = sort @{ $TARGET_TYPES{$typ}[1] };
        print "\n";
        print $TARGET_TYPES{$typ}[0] . ":\n";
        printf "\t%-10s %s\n", $_, $TARGET_NAMES{$_} // '' for @tgts;
    }
    print "\n";
}

sub dumpConfig {
    my ($source_raw, $parsed_config) = @_;
    my %onoff = (1 => 'ON', 0 => 'OFF');
    print "Full PARSED config\n";
    for my $key (sort keys %$parsed_config) {
        next if $key =~ /^(pre|post)proc$|^postvoodoo$/;
        my $val = $parsed_config->{$key} // '';
        $val = ref $val eq 'ARRAY' ? join(', ', @$val) : $val;
        printf "%25s: %s\n", dotted_spaces(sprintf('%-14s', $key)), $val;
    }
    print "\n";
}

# ---------------------------------------------------------------------------
# get_file_body
# ---------------------------------------------------------------------------

sub get_file_body {
    my ($file) = @_;
    require Text::Txt2tags::Converter;
    my (undef, $doc) = Text::Txt2tags::Converter::process_source_file($file, 1);
    return $doc->[2];
}

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
our @EXPORT_OK = qw(
    get_escapes doProtect doEscape doFinalEscape
    EscapeCharHandler maskEscapeChar unmaskEscapeChar
    addLineBreaks expandLineBreaks compile_filters
    enclose_me get_tagged_link parse_deflist_term
    get_image_align get_encoding_string
    doCommentLine doHeader doFooter finish_him
    post_voodoo toc_inside_body toc_tagger toc_formatter
    listTargets dumpConfig get_file_body
    fix_relative_path fix_css_out_path beautify_me
);

our %EXPORT_TAGS = ( all => \@EXPORT_OK );

1;
__END__

=head1 NAME

Text::Txt2tags::Output - Output helpers for Text::Txt2tags

=head1 DESCRIPTION

Port of C<txt2tags3_mod/output.py> to Perl 5.
Provides escaping, tagging, TOC generation, header/footer composition,
and final output routines.

=cut
