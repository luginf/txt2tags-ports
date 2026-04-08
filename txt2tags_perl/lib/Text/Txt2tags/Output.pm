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
        $txt =~ s/"/"\Q$ESCCHAR\E""/g;
        $txt =~ s/([|&{}\@#^~])/"$1"/g;
        $txt =~ s/$tmpmask/"\Q$ESCCHAR$ESCCHAR\E"/g;
    }
    elsif ($target =~ /^tex/) {
        $txt =~ s/\Q$ESCCHAR\E/$tmpmask/g;
        $txt =~ s/([#\$&%{}])/\Q$ESCCHAR\E$1/g;
        $txt =~ s/([~^])/\Q$ESCCHAR\E$1\{\}/g;
        $txt =~ s/([<|>])/\$$1\$/g;
        $txt =~ s/$tmpmask/maskEscapeChar('$\\backslash$')/ge;
    }
    elsif ($target eq 'rtf') {
        $txt =~ s/\Q$ESCCHAR\E/$ESCCHAR$ESCCHAR/g;
        $txt =~ s/([{}])/\Q$ESCCHAR\E$1/g;
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
    # Normalise Python-style \1 → $1
    (my $tmpl = $template) =~ s/\\([1-9])/\$$1/g;
    return sub {
        # Snapshot the outer-match capture groups before any inner regex clobbers them
        my @c = ($1,$2,$3,$4,$5,$6,$7,$8,$9);
        (my $r = $tmpl) =~ s/\$([1-9])/defined $c[$1-1] ? $c[$1-1] : ''/ge;
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

    # HTML-escape & in URLs (for HTML targets)
    (my $url_esc = $url) =~ s/&/&amp;/g;

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
            (my $l = $label) =~ s/&/&amp;/g;
            $display = $l;
        }
    } else {
        (my $o = $orig_url) =~ s/&/&amp;/g;
        $display = $o;
    }

    # The tag template has \a placeholders: first \a → URL, second \a → display text
    my $result = $open_tag;
    my $first  = 1;
    $result =~ s/\\a/$first ? do { $first = 0; $url_esc } : $display/ge;

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
<?xml version="1.0" encoding="%(ENCODING)s"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta name="generator" content="http://txt2tags.org"/>
<meta http-equiv="Content-Type" content="text/html; charset=%(ENCODING)s"/>
<link rel="stylesheet" type="text/css" href="%(STYLE)s"/>
<title>%(HEADER1)s</title>
</head>
<body>

<div class="header" id="header">
<h1>%(HEADER1)s</h1>
<h2>%(HEADER2)s</h2>
<h3>%(HEADER3)s</h3>
</div>
END_XHTML
    html5 => <<'END_HTML5',
<!DOCTYPE html>
<html>
<head>
<meta charset="%(ENCODING)s"/>
<meta name="generator" content="http://txt2tags.org"/>
<link rel="stylesheet" href="%(STYLE)s"/>
<title>%(HEADER1)s</title>
</head>
<body>
<header>
<hgroup>
<h1>%(HEADER1)s</h1>
<h2>%(HEADER2)s</h2>
</hgroup>
</header>
<article>
END_HTML5
    txt => '%(HEADER1)s
%(HEADER2)s
%(HEADER3)s',
    tex => <<'END_TEX',
\documentclass{article}
%(ENCODING)s
\usepackage{graphicx}
\begin{document}
\title{%(HEADER1)s}
\author{%(HEADER2)s}
\date{%(HEADER3)s}
\maketitle
\clearpage
END_TEX
    man => '.TH "%(HEADER1)s" 1 "%(HEADER3)s" "%(HEADER2)s"',
    rst => '',
    md  => '',
    adoc=> '',
);

# Alias templates
$HEADER_TEMPLATE{xhtmls} = $HEADER_TEMPLATE{xhtml};
$HEADER_TEMPLATE{htmls}  = $HEADER_TEMPLATE{html};
$HEADER_TEMPLATE{wp}     = '';

sub _doHeader_html {
    my ($headers, $config) = @_;

    my ($h1, $h2, $h3) = map { $_ // '' } @{$headers}[0, 1, 2];
    my $enc   = get_encoding_string($config->{encoding} // '', 'html') // '';
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
    # v2 format: </HEAD><BODY on same line, BGCOLOR/TEXT attributes
    push @head, '</HEAD><BODY BGCOLOR="white" TEXT="black">';
    push @head, '<CENTER>';
    push @head, "<H1>$h1</H1>" if $h1;
    push @head, "<H2>$h2</H2>" if $h2;
    push @head, "<H3>$h3</H3>" if $h3;
    push @head, '</CENTER>';
    push @head, '';   # trailing blank matching Python v2 template

    return @head;
}

sub doHeader {
    my ($headers, $config) = @_;
    return $config->{fullBody} unless $config->{headers};

    $headers //= [];
    $headers = ['', '', ''] unless @$headers;

    my $target = $config->{target};
    my $tmpl_str = $HEADER_TEMPLATE{$target} // '';

    # HTML (and aliases) use the v2-compatible generator
    if ($tmpl_str eq 'DYNAMIC_HTML') {
        my @head  = _doHeader_html($headers, $config);
        my @body  = @{ $config->{fullBody} // [] };
        my @eod;
        if ($TAGS{EOD}) { push @eod, $TAGS{EOD} }

        return [@head, @body, @eod];
    }

    # Build substitution data for template-based targets
    my %head_data = (
        ENCODING => get_encoding_string($config->{encoding} // '', $target) // '',
        STYLE    => '',
        HEADER1  => $headers->[0] // '',
        HEADER2  => $headers->[1] // '',
        HEADER3  => $headers->[2] // '',
        BODY     => join("\n", @{ $config->{fullBody} // [] }),
    );

    # Style
    if ($config->{style} && @{ $config->{style} }) {
        $head_data{STYLE} = $config->{style}[0];
    }

    # For rst/md/adoc: no template, just return body
    if (!$tmpl_str) {
        return $config->{fullBody};
    }

    # Append body + EOD
    $tmpl_str .= "%(BODY)s\n";
    if ($TAGS{EOD}) {
        (my $eod = $TAGS{EOD}) =~ s/%/%%/g;
        $tmpl_str .= "$eod\n";
    }

    # Remove lines whose key is empty
    my @tmpl_lines = split /\n/, $tmpl_str, -1;
    my @out_lines;
    for my $line (@tmpl_lines) {
        if ($line =~ /%\(([A-Z0-9]+)\)s/) {
            my $key = $1;
            if (!$head_data{$key}) {
                # skip line if it has no other substitution key
                next unless $line =~ /%\([A-Z0-9]+\)s.*%\([A-Z0-9]+\)s/;
            }
        }
        # Perform substitution
        $line =~ s/%\((\w+)\)s/$head_data{$1} \/\/ ''/ge;
        push @out_lines, $line;
    }

    return \@out_lines;
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
