package Text::Txt2tags::Converter;

# txt2tags - main conversion engine
# Port of txt2tags3_mod/converter.py to Perl 5

use strict;
use warnings;
use Exporter 'import';

our $VERSION = '3.9.0';

use Text::Txt2tags::Constants qw(
    $MY_NAME $MY_VERSION $MY_URL %MACROS
    $STDIN $STDOUT $MODULEIN $MODULEOUT
    $ESCCHAR %LISTNAMES
    DFT_TEXT_WIDTH
);
use Text::Txt2tags::State qw(
    $DEBUG $VERBOSE $QUIET $AUTOTOC
    %CONF %TAGS %rules %regex
    $BLOCK $TITLE $TARGET
    @RC_RAW @CMDLINE_RAW
    %file_dict
);
use Text::Txt2tags::Utils    qw(Error Debug Message Readfile Savefile dotted_spaces);
use Text::Txt2tags::Regexes  qw(getRegexes);
use Text::Txt2tags::Tags     qw(getTags);
use Text::Txt2tags::Rules    qw(getRules);
use Text::Txt2tags::Config   ();
use Text::Txt2tags::Output   qw(
    maskEscapeChar unmaskEscapeChar EscapeCharHandler
    doEscape doFinalEscape doProtect doCommentLine
    compile_filters enclose_me get_tagged_link
    get_image_align fix_relative_path parse_deflist_term
    addLineBreaks expandLineBreaks
    toc_inside_body toc_tagger toc_formatter
    doHeader doFooter finish_him
    get_encoding_string beautify_me
);
use Text::Txt2tags::Processing ();

# ---------------------------------------------------------------------------
# set_global_config – initialise all global state for a conversion run
# ---------------------------------------------------------------------------

sub set_global_config {
    my ($config) = @_;
    %CONF  = %$config;
    %rules = %{ getRules($config) };
    %TAGS  = %{ getTags($config) };
    %regex = %{ getRegexes() };
    $TARGET= $config->{target} // '';
}

# ---------------------------------------------------------------------------
# add_inline_tags – apply bold/italic/underline/strike to a text line
# ---------------------------------------------------------------------------

sub add_inline_tags {
    my ($line) = @_;

    for my $font (qw(fontBold fontItalic fontUnderline fontStrike)) {
        if ($line =~ $regex{$font}) {
            my $open  = $TAGS{"${font}Open"}  // '';
            my $close = $TAGS{"${font}Close"} // '';
            $line =~ s/$regex{$font}/$open$1$close/g;
        }
    }

    # Image tags
    $line = parse_images($line);

    return $line;
}

# ---------------------------------------------------------------------------
# parse_images – replace [image.ext] with the target image tag
# ---------------------------------------------------------------------------

sub parse_images {
    my ($line) = @_;

    while ($line =~ $regex{img}) {
        my $txt = $1;
        my $tag = $TAGS{img} // '';
        last unless $tag;

        $txt = fix_relative_path($txt);

        if ($rules{imgalignable}) {
            my $align      = get_image_align($line);
            my $align_name = ucfirst $align;
            my $align_tag  = $TAGS{"_imgAlign$align_name"} // '';
            $tag =~ s/~A~/$align_tag/;

            # Centre solo image in HTML
            if ($align eq 'center' && $TARGET =~ /^x?html$/) {
                (my $rest = $line) =~ s/$regex{img}//;
                if ($rest =~ /^\s*$/) {
                    $tag = "<center>$tag</center>";
                }
            }
        }
        else {
            $tag =~ s/~A~//g;
        }

        # Expand \a placeholders in the tag
        my $first = 1;
        $tag =~ s/\\a/$first ? do { $first=0; $txt } : $txt/ge;

        # Ugly hack to avoid infinite loop when img tag contains []
        $tag =~ s/\[/vvvvEscSquarevvvv/g;
        $line =~ s/$regex{img}/$tag/;
        $line =~ s/vvvvEscSquarevvvv/[/g;
    }

    return $line;
}

# ---------------------------------------------------------------------------
# beautify_me – apply an inline font tag to a line
# ---------------------------------------------------------------------------

sub _beautify_me {
    my ($font, $line) = @_;
    my $open  = $TAGS{"${font}Open"}  // '';
    my $close = $TAGS{"${font}Close"} // '';
    $line =~ s/$regex{$font}/$open$1$close/g;
    return $line;
}

# ---------------------------------------------------------------------------
# process_source_file
# ---------------------------------------------------------------------------

sub process_source_file {
    my ($file, $noconf, $contents) = @_;
    $noconf   //= 0;
    $contents //= [];

    my $source;
    if (@$contents) {
        $source = Text::Txt2tags::SourceDocument->new(contents => $contents);
    }
    else {
        $source = Text::Txt2tags::SourceDocument->new(filename => $file);
    }

    my ($head, $conf, $body) = $source->split_doc;
    Message('Source document contents stored', 2);

    my $full_parsed = {};
    if (!$noconf) {
        my $source_raw = $source->get_raw_config;
        my @full_raw   = (@RC_RAW, @$source_raw, @CMDLINE_RAW);
        Message(sprintf('Parsing and saving all config found (%03d items)',
                        scalar @full_raw), 1);
        $full_parsed = Text::Txt2tags::ConfigMaster->new(\@full_raw)->parse;

        if (@$contents) {
            $full_parsed->{sourcefile}        = $MODULEIN;
            $full_parsed->{currentsourcefile} = $MODULEIN;
            $full_parsed->{infile}            = $MODULEIN;
            $full_parsed->{outfile}           = $MODULEOUT;
        }
        else {
            $full_parsed->{sourcefile}        = $file;
            $full_parsed->{currentsourcefile} = $file;
            $full_parsed->{infile}            = $file;
        }

        if ($full_parsed->{'dump-config'}) {
            require Text::Txt2tags::Output;
            Text::Txt2tags::Output::dumpConfig($source_raw, $full_parsed);
            Text::Txt2tags::Utils::Quit();
        }

        Debug("FULL config: " . join(', ', map { "$_=$full_parsed->{$_}" } sort keys %$full_parsed), 1);
    }

    return ($full_parsed, [$head, $conf, $body]);
}

# ---------------------------------------------------------------------------
# convert – line-by-line markup → target conversion
# ---------------------------------------------------------------------------

sub convert {
    my ($bodylines, $config, $firstlinenr) = @_;
    $firstlinenr //= 1;

    set_global_config($config);

    my $target = $config->{target};
    $BLOCK     = Text::Txt2tags::BlockMaster->new;
    my $MASK   = Text::Txt2tags::MaskMaster->new;
    $TITLE     = Text::Txt2tags::TitleMaster->new;

    my @ret;
    my $f_lastwasblank = 0;

    # Compile PreProc filters
    my $pre_filter = compile_filters($CONF{preproc} // [], 'Invalid PreProc filter regex');

    my $linenr  = $firstlinenr - 1;
    my $lineref = 0;

    while ($lineref < scalar @$bodylines) {
        my $untouched = $bodylines->[$lineref];
        $untouched //= '';
        $untouched =~ s/[\r\n]+$//;

        my $line = $untouched;

        # Apply PreProc filters
        if ($pre_filter && @$pre_filter) {
            for my $pair (@$pre_filter) {
                my ($rgx, $repl) = @$pair;
                eval { $line =~ s/$rgx/$repl/g };
                Error("Invalid PreProc filter replacement: '$repl'") if $@;
            }
        }

        $line = maskEscapeChar($line);   # protect backslash
        $linenr++;
        $lineref++;

        Debug(qq{"$line"}, 2, $linenr);

        # ---- Comment block -----------------------------------------------
        if ($BLOCK->block eq 'comment') {
            if ($line =~ $regex{blockCommentClose}) {
                push @ret, @{ $BLOCK->blockout };
            }
            next;
        }
        if ($line =~ $regex{blockCommentOpen}
            && !grep { $BLOCK->block eq $_ } @{ $BLOCK->{exclusive} }) {
            push @ret, @{ $BLOCK->blockin('comment') };
            next;
        }

        # ---- Tagged block ------------------------------------------------
        if ($BLOCK->block eq 'tagged') {
            if ($line =~ $regex{blockTaggedClose}) {
                push @ret, @{ $BLOCK->blockout };
            }
            else { $BLOCK->holdadd($line) }
            next;
        }
        if ($line =~ $regex{blockTaggedOpen}
            && !grep { $BLOCK->block eq $_ } @{ $BLOCK->{exclusive} }) {
            push @ret, @{ $BLOCK->blockin('tagged') };
            next;
        }
        if ($line =~ $regex{'1lineTagged'}
            && !grep { $BLOCK->block eq $_ } @{ $BLOCK->{exclusive} }) {
            push @ret, @{ $BLOCK->blockin('tagged') };
            $line =~ s/$regex{'1lineTagged'}//;
            $BLOCK->holdadd($line);
            push @ret, @{ $BLOCK->blockout };
            next;
        }

        # ---- Raw block ---------------------------------------------------
        if ($BLOCK->block eq 'raw') {
            if ($line =~ $regex{blockRawClose}) {
                push @ret, @{ $BLOCK->blockout };
            }
            else { $BLOCK->holdadd(doEscape($target, $line)) }
            next;
        }
        if ($line =~ $regex{blockRawOpen}
            && !grep { $BLOCK->block eq $_ } @{ $BLOCK->{exclusive} }) {
            push @ret, @{ $BLOCK->blockin('raw') };
            next;
        }
        if ($line =~ $regex{'1lineRaw'}
            && !grep { $BLOCK->block eq $_ } @{ $BLOCK->{exclusive} }) {
            push @ret, @{ $BLOCK->blockin('raw') };
            $line =~ s/$regex{'1lineRaw'}//;
            $BLOCK->holdadd(doEscape($target, $line));
            push @ret, @{ $BLOCK->blockout };
            next;
        }

        # ---- Verbatim block ----------------------------------------------
        if ($BLOCK->block eq 'verb') {
            if ($line =~ $regex{blockVerbClose}) {
                push @ret, @{ $BLOCK->blockout };
                next;
            }
            unless ($rules{verbblocknotescaped}) {
                $line = doEscape($target, $line);
            }
            $BLOCK->holdadd($line);
            next;
        }
        if ($line =~ $regex{blockVerbOpen}
            && !grep { $BLOCK->block eq $_ } @{ $BLOCK->{exclusive} }) {
            push @ret, @{ $BLOCK->blockin('verb') };
            next;
        }
        if ($line =~ $regex{'1lineVerb'}
            && !grep { $BLOCK->block eq $_ } @{ $BLOCK->{exclusive} }) {
            push @ret, @{ $BLOCK->blockin('verb') };
            $line =~ s/$regex{'1lineVerb'}//;
            unless ($rules{verbblocknotescaped}) {
                $line = doEscape($target, $line);
            }
            $BLOCK->holdadd($line);
            push @ret, @{ $BLOCK->blockout };
            next;
        }

        # ---- Blank line --------------------------------------------------
        if ($line =~ $regex{blankline}) {
            if ($BLOCK->block =~ /^(list|numlist|deflist|quote|para)$/) {
                # Blank line closes current block
                push @ret, @{ $BLOCK->blockout };
                $f_lastwasblank = 1;
            }
            elsif ($BLOCK->block eq '') {
                push @ret, '' if !$f_lastwasblank;
                $f_lastwasblank = 1;
            }
            next;
        }
        $f_lastwasblank = 0;

        # ---- Comment line ------------------------------------------------
        if ($line =~ $regex{comment} && $line !~ $regex{macros}
                                     && $line !~ $regex{toc}) {
            next;
        }

        # ---- Special %! config line (in body = ignored) -----------------
        if ($line =~ $regex{special}) {
            next;
        }

        # ---- Mask inline structures --------------------------------------
        $line = $MASK->mask($line);

        # ---- Title -------------------------------------------------------
        my $is_title = 0;
        for my $kind (qw(title numtitle)) {
            if ($line =~ $regex{$kind}) {
                my $id    = $+{id};
                my $txt   = $+{txt};
                $txt =~ s/^\s+|\s+$//g;
                my $label = $+{label} // '';
                my $level = length $id;

                # Close any open block
                if ($BLOCK->block) {
                    push @ret, @{ $BLOCK->blockout };
                }

                # Escape title text
                $txt = doEscape($target, $txt);
                $txt = $MASK->undo($txt);

                my $lbl = $TITLE->add($level, $kind, $txt, $label);

                # Build the title tag
                my $tag = $TAGS{"${kind}$level"} // $TAGS{"title$level"} // "\a";
                my $anchor_tag = '';
                if ($TAGS{anchor}) {
                    ($anchor_tag = $TAGS{anchor}) =~ s/\\a/$lbl/;
                }
                $tag =~ s/~A~/$anchor_tag/g;
                $tag =~ s/\\a/$txt/;

                push @ret, '' if $rules{blanksaroundtitle};
                push @ret, $tag;
                push @ret, '' if $rules{blanksaroundtitle};
                $is_title = 1;
                last;
            }
        }
        next if $is_title;

        # ---- Horizontal bar ----------------------------------------------
        if ($line =~ $regex{bar}) {
            my $bartype = ($2 eq ('=' x length($2))) ? 'bar2' : 'bar1';
            push @ret, @{ $BLOCK->blockout } if $BLOCK->block;
            my $bar_tag = $TAGS{$bartype} // '';
            $bar_tag =~ s/\\a/$line/g;
            push @ret, '' if $rules{blanksaroundbar};
            push @ret, $bar_tag;
            push @ret, '' if $rules{blanksaroundbar};
            next;
        }

        # ---- Table -------------------------------------------------------
        if ($line =~ $regex{table} && $rules{tableable}) {
            # Detect border/alignment from first cell marker
            my $is_title_row = ($line =~ /^ *\|\|/);
            if ($BLOCK->block ne 'table') {
                push @ret, @{ $BLOCK->blockout } if $BLOCK->block;
                push @ret, '' if $rules{blanksaroundtable};
                my $border_tag = ($line =~ /^ *\|_/) ? ($TAGS{_tableBorder} // '') : '';
                my $open_tag   = $TAGS{tableOpen} // '';
                $open_tag =~ s/~B~/$border_tag/;
                $open_tag =~ s/~A~//g;
                push @ret, $open_tag if $open_tag;
                $BLOCK->blockin('table');
            }
            # Parse and emit the row
            my $tm = Text::Txt2tags::TableMaster->new;
            my $row_lines = $tm->parse_row($line);
            push @ret, @$row_lines;
            next;
        }
        elsif ($BLOCK->block eq 'table') {
            push @ret, $TAGS{tableClose} // '';
            push @ret, '' if $rules{blanksaroundtable};
            $BLOCK->blockout;   # discard (we already closed it)
        }

        # ---- Quote -------------------------------------------------------
        if ($line =~ $regex{quote}) {
            my $depth = length( ($line =~ /^(\t+)/)[0] );
            if ($BLOCK->block ne 'quote') {
                push @ret, @{ $BLOCK->blockout } if $BLOCK->block;
                push @ret, '' if $rules{blanksaroundquote};
                push @ret, @{ $BLOCK->blockin('quote') };
            }
            $line =~ s/^\t+//;
            $line = doEscape($target, $line);
            $line = $MASK->undo($line);
            $line = add_inline_tags($line);
            my $prefix = $TAGS{blockQuoteLine} // '';
            push @ret, ($prefix x $depth) . $line;
            next;
        }
        elsif ($BLOCK->block eq 'quote') {
            push @ret, @{ $BLOCK->blockout };
            push @ret, '' if $rules{blanksaroundquote};
        }

        # ---- Lists -------------------------------------------------------
        if ($line =~ $regex{list} || $line =~ $regex{numlist}
                                  || $line =~ $regex{deflist}) {
            my ($list_type, $indent, $item_txt);
            if    ($line =~ $regex{deflist})  { $list_type = 'deflist';  $indent = $1; $item_txt = $3 }
            elsif ($line =~ $regex{numlist})  { $list_type = 'numlist';  $indent = $1; ($item_txt = $line) =~ s/^ *\+ // }
            else                              { $list_type = 'list';     $indent = $1; ($item_txt = $line) =~ s/^ *- //  }

            if ($BLOCK->block ne $list_type) {
                push @ret, @{ $BLOCK->blockout } if $BLOCK->block;
                push @ret, '' if $rules{"blanksaround$list_type"};
                push @ret, @{ $BLOCK->blockin($list_type) };
            }

            $item_txt = doEscape($target, $item_txt);
            $item_txt = $MASK->undo($item_txt);
            $item_txt = add_inline_tags($item_txt);

            my $open  = $TAGS{"${list_type}ItemOpen"}  // '';
            my $close = $TAGS{"${list_type}ItemClose"} // '';
            push @ret, "$open$item_txt$close";
            next;
        }
        elsif ($BLOCK->block =~ /list$/) {
            push @ret, @{ $BLOCK->blockout };
            push @ret, '' if $rules{"blanksaround${\$BLOCK->block}"};
        }

        # ---- Paragraph (plain text) ------------------------------------
        $line = doEscape($target, $line);
        $line = $MASK->undo($line);
        $line = add_inline_tags($line);

        if ($BLOCK->block ne 'para') {
            push @ret, @{ $BLOCK->blockout } if $BLOCK->block;
            push @ret, '' if $rules{blanksaroundpara};
            my $po = $TAGS{paragraphOpen} // '';
            push @ret, $po if $po;
            $BLOCK->blockin('para') unless $BLOCK->block;
        }
        push @ret, $line;
    }

    # Close any remaining open block
    if ($BLOCK->block) {
        push @ret, @{ $BLOCK->blockout };
    }

    # Apply final escapes
    if ($rules{verbblockfinalescape}) {
        @ret = map { doFinalEscape($target, $_) } @ret;
    }

    my $toc = $TITLE->{toc};
    return (\@ret, $toc);
}

# ---------------------------------------------------------------------------
# convert_this_files – high-level driver (single or multi file)
# ---------------------------------------------------------------------------

sub convert_this_files {
    my ($configs) = @_;

    for my $pair (@$configs) {
        my ($myconf, $doc) = @$pair;
        my ($source_head, $source_conf, $source_body) = @$doc;

        my $cm = Text::Txt2tags::ConfigMaster->new;
        $myconf = $cm->sanity($myconf);

        # Save header info for macros
        $myconf->{header1} = $source_head->[0] // '';
        $myconf->{header2} = $source_head->[1] // '';
        $myconf->{header3} = $source_head->[2] // '';

        my $first_body_line = (scalar @$source_head || 1)
                            + scalar @$source_conf + 1;

        Message('Composing target Body', 1);
        my ($target_body, $marked_toc) = convert(
            $source_body, $myconf, $first_body_line
        );

        # Dump-source mode
        if ($myconf->{'dump-source'}) {
            print join("\n", @$source_head, @$source_conf, @$target_body), "\n";
            return;
        }

        # Footer
        Message('Composing target Footer', 1);
        my $target_foot = doFooter($myconf);

        # TOC
        Message('Composing target TOC', 1);
        my $tagged_toc = toc_tagger($marked_toc, $myconf);
        my $target_toc = toc_formatter($tagged_toc, $myconf);
        $target_body   = toc_inside_body($target_body, $target_toc, $myconf);
        $target_toc    = [] if $AUTOTOC && !$myconf->{'toc-only'};

        $myconf->{fullBody} = [@$target_toc, @$target_body, @$target_foot];

        # Header
        Message('Composing target Headers', 1);
        my $outlist = doHeader($source_head, $myconf);

        if ($myconf->{outfile} && $myconf->{outfile} eq $MODULEOUT) {
            return (finish_him($outlist, $myconf), $myconf);
        }
        else {
            Message('Saving results to the output file', 1);
            finish_him($outlist, $myconf);
        }
    }
}

# ---------------------------------------------------------------------------
# get_infiles_config
# ---------------------------------------------------------------------------

sub get_infiles_config {
    my ($infiles) = @_;
    return [ map { [ process_source_file($_) ] } @$infiles ];
}

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
our @EXPORT_OK = qw(
    convert convert_this_files get_infiles_config
    process_source_file set_global_config
    parse_images add_inline_tags
);

our %EXPORT_TAGS = ( all => \@EXPORT_OK );

use Text::Txt2tags::Config ();

1;
__END__

=head1 NAME

Text::Txt2tags::Converter - Main conversion engine for Text::Txt2tags

=head1 SYNOPSIS

  use Text::Txt2tags::Converter qw(convert convert_this_files);

  my ($lines, $toc) = convert(\@body_lines, \%config);

=head1 DESCRIPTION

Port of C<txt2tags3_mod/converter.py> to Perl 5.

Drives the full markup-to-output pipeline: config setup, line-by-line
parsing (blocks, titles, lists, tables, inline marks), TOC generation,
header/footer composition, and file output.

=cut
