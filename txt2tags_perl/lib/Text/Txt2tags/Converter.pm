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
use File::Basename qw(dirname);
use File::Spec;
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
    get_file_body
);
use Text::Txt2tags::Processing ();

# ---------------------------------------------------------------------------
# set_global_config – initialise all global state for a conversion run
# ---------------------------------------------------------------------------

sub set_global_config {
    my ($config) = @_;
    %CONF  = %$config;
    %rules = %{ getRules($config) };
    %TAGS  = %{ getTags($config, \%rules) };
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
        my $txt    = $1;
        my $before = substr($line, 0, $-[0]);
        my $after  = substr($line, $+[0]);
        my $tag    = $TAGS{img} // '';
        last unless $tag;

        $txt = fix_relative_path($txt);

        if ($rules{imgalignable}) {
            # Match Python get_image_align logic:
            # before empty, after non-empty → left
            # before non-empty, after empty → right
            # else (standalone, both, or neither) → center
            my $align;
            my $has_before = length($before) > 0;
            my $has_after  = length($after)  > 0;
            if (!$has_before && $has_after) { $align = 'left'   }
            elsif ($has_before && !$has_after) { $align = 'right'  }
            else                               { $align = 'center' }

            my $align_key = ucfirst($align);   # Left / Right / Center

            # Python: if imgAlignX tag exists, use it as the whole tag;
            # otherwise substitute _imgAlignX into img's ~A~ placeholder.
            if ($TAGS{"imgAlign$align_key"}) {
                $tag = $TAGS{"imgAlign$align_key"};
            } else {
                my $align_tag = $TAGS{"_imgAlign$align_key"} // '';
                $tag =~ s/~A~/$align_tag/;
            }

            # Python "dirty fix": add center wrapper only when the rest of the
            # line (after removing the image) is whitespace-only (not empty).
            if ($align eq 'center' && $TARGET =~ /^x?html$/) {
                my $rest = $before . $after;
                if ($rest =~ /^\s+$/) {
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

        # Escape [ to prevent re-matching on the next while iteration.
        # The placeholder is unescaped after the loop ends (matching Python behavior).
        $tag =~ s/\[/vvvvEscSquarevvvv/g;
        $line =~ s/$regex{img}/$tag/;
    }

    $line =~ s/vvvvEscSquarevvvv/[/g;
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
    $BLOCK       = Text::Txt2tags::BlockMaster->new;
    my $MASK     = Text::Txt2tags::MaskMaster->new;
    $TITLE       = Text::Txt2tags::TitleMaster->new;
    my $quote_depth = 0;   # current nesting depth of BLOCKQUOTE
    my $quote_oneline_buf;  # undef or string buffer for onelinequote content

    # List nesting state (bypass BlockMaster for lists)
    my @list_stack        = ();  # each: {indent=>str, type=>str, open_item=>0}
    my $list_pending_blank = 0;  # deferred <P></P> within a list
    my @section_stack     = ();  # open section levels (for titleblocks targets)
    my @ret;                     # output lines (declared before closures so they can capture it)
    my $f_lastwasblank = 0;
    my $para_content_start = -1;  # index in @ret where current para content begins (for onelinepara)

    # Table state (set when table block opens, used for all rows in the table)
    my $table_is_border  = 0;
    my $table_colalign   = [];
    my $table_row_open_override = undef;  # undef = use TAGS; '' = suppress; defined = use value

    # Return the item-level close tag for a given list type
    my $_item_close_tag = sub {
        my ($type) = @_;
        return $type eq 'deflist'
            ? ($TAGS{deflistItem2Close} // '')
            : ($TAGS{$type . 'ItemClose'} // '');
    };

    # Emit an item close tag (appending to last line if notbreaklistitemclose)
    my $_emit_item_close = sub {
        my ($indent, $ic) = @_;
        return unless $ic;
        if ($rules{notbreaklistitemclose}) {
            $ret[-1] .= $ic if @ret;
        } else {
            push @ret, $indent . $ic;
        }
    };

    # Effective indent for list tags (empty when keeplistindent=0)
    my $_list_ind = sub {
        my ($ind) = @_;
        return $rules{keeplistindent} ? $ind : '';
    };

    # Compact-aware list open/close tag helpers (Python compactlist rule)
    my $_list_open_tag = sub {
        my ($type) = @_;
        return ($rules{compactlist} && $TAGS{$type . 'OpenCompact'})
            ? $TAGS{$type . 'OpenCompact'}
            : ($TAGS{$type . 'Open'} // '');
    };
    my $_list_close_tag = sub {
        my ($type) = @_;
        return ($rules{compactlist} && $TAGS{$type . 'CloseCompact'})
            ? $TAGS{$type . 'CloseCompact'}
            : ($TAGS{$type . 'Close'} // '');
    };

    # Close list levels down to target indent length; return old top indent
    my $_close_list_levels = sub {
        my ($target_len) = @_;
        my $old_top = @list_stack ? $list_stack[-1]{indent} : '';
        while (@list_stack && length($list_stack[-1]{indent}) > $target_len) {
            my $cl = pop @list_stack;
            if ($cl->{open_item}) {
                my $ic = $_item_close_tag->($cl->{type});
                $_emit_item_close->($_list_ind->($cl->{indent}), $ic);
            }
            my $lc_tag = $cl->{wide} ? ($TAGS{$cl->{type} . 'Close'} // '') : $_list_close_tag->($cl->{type});
            push @ret, $_list_ind->($cl->{indent}) . $lc_tag if $lc_tag;
            if (!@list_stack) {
                # Outermost list just closed
                $BLOCK->last($cl->{type});
                push @ret, '' if $rules{ 'blanksaround' . $cl->{type} };
            }
        }
        return $old_top;
    };

    # Close ALL list levels (double-blank, title, bar, etc.)
    my $_close_all_lists = sub {
        $list_pending_blank = 0;
        while (@list_stack) {
            my $cl = pop @list_stack;
            if ($cl->{open_item}) {
                my $ic = $_item_close_tag->($cl->{type});
                $_emit_item_close->($_list_ind->($cl->{indent}), $ic);
            }
            my $lc_tag = $cl->{wide} ? ($TAGS{$cl->{type} . 'Close'} // '') : $_list_close_tag->($cl->{type});
            push @ret, $_list_ind->($cl->{indent}) . $lc_tag if $lc_tag;
            if (!@list_stack) {
                $BLOCK->last($cl->{type});
                push @ret, '' if $rules{ 'blanksaround' . $cl->{type} };
            }
        }
    };

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
                my ($rgx, $repl_fn) = @$pair;
                eval { $line =~ s/$rgx/$repl_fn->()/ge };
                Error("Invalid PreProc filter replacement") if $@;
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
        # Close a verb block that was mapped from a table when line is no longer a table
        if ($BLOCK->block eq 'verb' && ($BLOCK->prop('mapped') // '') eq 'table'
            && $line !~ $regex{table}) {
            my $result = $BLOCK->blockout;
            push @ret, @$result;
            push @ret, '' if $rules{blanksaroundverb};
            # fall through to process the current line normally
        }

        if ($BLOCK->block eq 'verb') {
            if ($line =~ $regex{blockVerbClose}) {
                my $result = $BLOCK->blockout;
                push @ret, @$result;
                push @ret, '' if $rules{blanksaroundverb};
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
            push @ret, @{ $BLOCK->blockout } if $BLOCK->block;
            push @ret, '' if $rules{blanksaroundverb} && !$rules{"blanksaround" . $BLOCK->last};
            push @ret, @{ $BLOCK->blockin('verb') };
            next;
        }
        if ($line =~ $regex{'1lineVerb'}
            && !grep { $BLOCK->block eq $_ } @{ $BLOCK->{exclusive} }) {
            push @ret, @{ $BLOCK->blockout } if $BLOCK->block;
            push @ret, '' if $rules{blanksaroundverb} && !$rules{"blanksaround" . $BLOCK->last};
            push @ret, @{ $BLOCK->blockin('verb') };
            $line =~ s/$regex{'1lineVerb'}//;
            unless ($rules{verbblocknotescaped}) {
                $line = doEscape($target, $line);
            }
            $BLOCK->holdadd($line);
            my $result = $BLOCK->blockout;
            push @ret, @$result;
            push @ret, '' if $rules{blanksaroundverb};
            next;
        }

        # ---- Blank line --------------------------------------------------
        # Blank lines close open blocks but produce no output themselves
        # (blanks in output come only from blanksaroundXXX rules)
        if ($line =~ $regex{blankline}) {
            if (@list_stack) {
                if ($list_pending_blank) {
                    # Second blank → close all lists
                    $_close_all_lists->();
                    $f_lastwasblank = 1;
                }
                else {
                    $list_pending_blank = 1;
                    # Note: the blank is deferred; it will be pushed in the
                    # continuation or item handler when !parainsidelist,
                    # but discarded if the next blank closes the list.
                }
            }
            elsif ($quote_depth > 0) {
                # Blank line closes all open BLOCKQUOTE levels
                my $ti = ($rules{tagnotindentable} ? '' : "\t");
                if ($rules{onelinequote} && defined $quote_oneline_buf) {
                    push @ret, $quote_oneline_buf;
                    $quote_oneline_buf = undef;
                }
                for my $lv (reverse 1 .. $quote_depth) {
                    my $qtag = $TAGS{blockQuoteClose} // '';
                    push @ret, ($ti x $lv) . $qtag if $qtag;
                }
                # Python emits one blank per depth level (each nested quote adds its own after-blank)
                my $closing_depth = $quote_depth;
                $quote_depth = 0;
                $BLOCK->last('quote');
                push @ret, (('') x $closing_depth) if $rules{blanksaroundquote};
                $f_lastwasblank = 1;
            }
            elsif ($BLOCK->block =~ /^(para|table)$/) {
                # Blank line closes current block
                my $closed_block = $BLOCK->block;
                my $block_out = $BLOCK->blockout;
                # tex gotcha: for border tables, prepend tableRowOpen to tableClose
                if ($closed_block eq 'table' && $target =~ /^tex/ && $table_is_border) {
                    my $row_open = $TAGS{tableRowOpen} // '';
                    if ($row_open && @$block_out) {
                        $block_out->[-1] = $row_open . $block_out->[-1];
                    }
                }
                push @ret, @$block_out;
                if ($rules{onelinepara} && $closed_block eq 'para' && $para_content_start >= 0) {
                    my @para_lines = splice(@ret, $para_content_start);
                    push @ret, join(' ', @para_lines) if @para_lines;
                    $para_content_start = -1;
                }
                push @ret, '' if $rules{"blanksaround$closed_block"};
                $f_lastwasblank = 1;
            }
            elsif ($BLOCK->block eq '') {
                if ($f_lastwasblank) {
                    # 2nd consecutive blank: no-op (Python v2 ignores these)
                } else {
                    $f_lastwasblank = 1;
                }
            }
            next;
        }
        $f_lastwasblank = 0;

        # ---- Special %! config line in body (must come before comment check) -
        if ($line =~ $regex{special}) {
            my ($targ, $val, $key) = Text::Txt2tags::ConfigLines->new->parse_line($line);

            # %!currentfile: path — restore currentsourcefile after an include
            if ($key eq 'currentfile') {
                $CONF{currentsourcefile} = $val if $val;
                next;
            }

            # %!include: filename — expand file contents inline
            if ($key eq 'include') {
                my %inc_ids = ('`' => 'verb', '"' => 'raw', "'" => 'tagged');
                my $incfile = $val;
                my $inctype = 't2t';

                # Detect type delimiters: ``file`` or ""file"" or ''file''
                if (length($incfile) >= 4) {
                    my $mark = substr($incfile, 0, 1);
                    if (exists $inc_ids{$mark}
                        && substr($incfile, 0, 2) eq $mark x 2
                        && substr($incfile, -2)   eq $mark x 2) {
                        $inctype = $inc_ids{$mark};
                        $incfile = substr($incfile, 2, length($incfile) - 4);
                    }
                }

                # Resolve path relative to current source file's directory
                my $curfile  = $CONF{currentsourcefile} // '';
                my $incdir   = $curfile ? File::Basename::dirname($curfile) : '.';
                my $fullpath = File::Spec->rel2abs(
                    File::Spec->catfile($incdir, $incfile)
                );

                # Infinite-loop guard
                if ($curfile && File::Spec->rel2abs($curfile) eq $fullpath) {
                    Error("A file cannot include itself: $fullpath");
                }

                if ($inctype eq 't2t') {
                    my $inclines = get_file_body($fullpath);
                    # Insert: currentfile marker, included body lines, restore marker
                    splice(@$bodylines, $lineref, 0,
                        "%!currentfile: $fullpath",
                        @$inclines,
                        "%!currentfile: $curfile",
                    );
                }
                else {
                    # Verb / raw / tagged inclusion: read file and hold as block
                    my $rawlines = Readfile($fullpath, 1);
                    push @ret, @{ $BLOCK->blockin($inctype) };
                    $BLOCK->holdaddfinal(@$rawlines);
                    push @ret, @{ $BLOCK->blockout() };
                }
                next;
            }

            # All other %! directives in the body are ignored
            next;
        }

        # ---- Comment line ------------------------------------------------
        if ($line =~ $regex{comment} && $line !~ $regex{toc}) {
            next;
        }

        # ---- Mask inline structures --------------------------------------
        $line = $MASK->mask($line);

        # Helper: should we add a blank line BEFORE starting block $name?
        # Yes if blanksaroundX is set AND the previous block did NOT already add a blank after itself.
        # (Mirrors Python v2's BlockMaster._should_add_blank_line logic.)
        my $blank_before = sub {
            my ($name) = @_;
            return $rules{"blanksaround$name"}
                && !$rules{"blanksaround" . $BLOCK->last};
        };

        # ---- Horizontal bar (checked before title; same syntax can overlap) ---
        if ($line =~ $regex{bar}) {
            my $bar_chars = $2;
            my $bartype = (substr($bar_chars, 0, 1) eq '=') ? 'bar2' : 'bar1';
            $_close_all_lists->();
            push @ret, @{ $BLOCK->blockout } if $BLOCK->block;
            my $bar_tag = $TAGS{$bartype} // '';
            $bar_tag =~ s/\\a/$bar_chars/g;
            push @ret, '' if $blank_before->('bar');
            push @ret, $bar_tag;
            push @ret, '' if $rules{blanksaroundbar};
            $BLOCK->last('bar');
            next;
        }

        # ---- Title -------------------------------------------------------
        my $is_title = 0;
        for my $kind (qw(title numtitle)) {
            if (!@list_stack && $line =~ $regex{$kind}) {
                my $id    = $+{id};
                my $txt   = $+{txt};
                my $label = $+{label} // '';  # must capture before any regex ops reset $+
                $txt =~ s/^\s+|\s+$//g;
                my $level = length $id;

                # Close any open lists and blocks
                $_close_all_lists->();
                if ($BLOCK->block) {
                    my $was_blk = $BLOCK->block;
                    push @ret, @{ $BLOCK->blockout };
                    if ($rules{onelinepara} && $was_blk eq 'para' && $para_content_start >= 0) {
                        my @para_lines = splice(@ret, $para_content_start);
                        push @ret, join(' ', @para_lines) if @para_lines;
                        $para_content_start = -1;
                    }
                }

                # Escape title text (raw/tagged/mono marks stay as literal markup in titles)
                $txt = doEscape($target, $txt);
                $txt = $MASK->undo_title($txt);

                my $lbl = $TITLE->add($level, $kind, $txt, $label);

                # For numbered titles, prepend the count (e.g. "1. " or "1.2. ")
                my $count_id = $TITLE->last_count_id;
                my $display_txt = $count_id ? "$count_id. $txt" : $txt;

                # Build the title tag
                my $anchor_tag = '';
                # Only add anchor when: title has explicit label OR TOC is on
                if ($TAGS{anchor} && ($label || $CONF{toc})) {
                    ($anchor_tag = $TAGS{anchor}) =~ s/\\a/$lbl/;
                }

                my $tag;
                if ($rules{titleblocks}) {
                    $tag = $TAGS{"${kind}${level}Open"} || $TAGS{"title${level}Open"} || "\a";
                } else {
                    $tag = $TAGS{"${kind}$level"} || $TAGS{"title$level"} || "\a";
                }
                $tag =~ s/~A~/$anchor_tag/g;
                my $tag_tmpl = $tag;   # save template (before \a substitution) for underline
                $tag =~ s/\\a/$display_txt/g;

                # txt target: always add blank before title when there's been a prior block
                # (mirrors Python's `if state.BLOCK.count > 1: ret.append("")`)
                if ($TARGET eq 'txt' && $BLOCK->last ne '') {
                    push @ret, '';
                }

                # blank before: only if previous block didn't already add one
                push @ret, '' if $blank_before->($kind);

                # For titleblocks targets: close open sections AFTER the blank
                if ($rules{titleblocks}) {
                    while (@section_stack && $section_stack[-1] >= $level) {
                        my $lv = pop @section_stack;
                        push @ret, $TAGS{"title${lv}Close"} // '</section>';
                    }
                }

                # Emit the title (may span multiple lines for titleblocks targets)
                push @ret, split /\n/, $tag, -1;

                # txt target: add underline (=×len) using same tag template
                if ($TARGET eq 'txt') {
                    my $underline = '=' x length($display_txt);
                    (my $under_tag = $tag_tmpl) =~ s/\\a/$underline/g;
                    push @ret, $under_tag;
                }

                # blank after: always (if rule set)
                push @ret, '' if $rules{"blanksaround$kind"};
                $BLOCK->last($kind);   # update last-block tracker

                if ($rules{titleblocks}) {
                    push @section_stack, $level;
                }
                $is_title = 1;
                last;
            }
        }
        next if $is_title;

        # Tables mapped to verb for non-tableable targets
        if (!$rules{tableable} && $line =~ $regex{table}) {
            if ($BLOCK->block ne 'verb') {
                push @ret, @{ $BLOCK->blockout } if $BLOCK->block;
                push @ret, '' if $blank_before->('verb') && !$rules{"blanksaround" . $BLOCK->last};
                push @ret, @{ $BLOCK->blockin('verb') };
                $BLOCK->set_prop('mapped', 'table');
            }
            $BLOCK->holdadd($line);
            next;
        }

        # ---- Table -------------------------------------------------------
        if ($line =~ $regex{table} && $rules{tableable}) {
            if ($BLOCK->block ne 'table') {
                $_close_all_lists->();
                push @ret, @{ $BLOCK->blockout } if $BLOCK->block;
                push @ret, '' if $blank_before->('table');
                $table_is_border  = ($line =~ /\|\s*$/) ? 1 : 0;
                my $border_tag = $table_is_border ? ($TAGS{_tableBorder} // '') : '';
                my $align_tag  = ($line =~ /^ /) ? ($TAGS{_tableAlignCenter} // '') : '';
                my $open_tag   = $TAGS{tableOpen} // '';
                $open_tag =~ s/~A~/$align_tag/g;
                $open_tag =~ s/~B~/$border_tag/g;
                # Get column info from first row (Python _get_full_tag / TableMaster.__init__)
                my $tm_tmp = Text::Txt2tags::TableMaster->new;
                my $props  = $tm_tmp->parse_row_props($line);
                $table_colalign = $props->{colalign};
                my $n_cols = 0;
                for my $span (@{$props->{cellspan}}) { $n_cols += $span }
                # Substitute ~C~ with column alignment string (Python _get_full_tag logic)
                if ($open_tag =~ /~C~/) {
                    my $calignsep = $TAGS{tableColAlignSep} // '';
                    my $colalign_str = '';
                    if ($rules{tablecellaligntype} && $rules{tablecellaligntype} eq 'column') {
                        my @calign = map { $TAGS{"_tableColAlign$_"} // 'l' } @$table_colalign;
                        $colalign_str = $calignsep ? join($calignsep, @calign) : join('', @calign);
                    }
                    $open_tag =~ s/~C~/$colalign_str/g;
                    # Python: for non-border, remove ALL calignsep from entire open_tag
                    if ($calignsep && !$table_is_border) {
                        $open_tag =~ s/\Q$calignsep\E//g;
                    }
                }
                # Substitute n_cols (tablecolumnsnumber rule, e.g. dbk)
                if ($rules{tablecolumnsnumber} && $open_tag =~ /n_cols/) {
                    $open_tag =~ s/n_cols/$n_cols/g;
                }
                # tex gotcha: for non-border suppress row open; for border prepend to close
                if ($target =~ /^tex/) {
                    $table_row_open_override = $table_is_border
                        ? ($TAGS{tableRowOpen} // '')
                        : '';
                } else {
                    $table_row_open_override = undef;
                }
                push @ret, $open_tag if $open_tag;
                $BLOCK->blockin('table');
            }
            # Parse and emit the row
            my $tm = Text::Txt2tags::TableMaster->new;
            my $cell_proc = sub {
                my ($txt) = @_;
                $txt = doEscape($target, $txt);
                $txt = add_inline_tags($txt);
                $txt = $MASK->undo($txt);
                return $txt;
            };
            my $row_context = {
                colalign          => $table_colalign,
                is_border         => $table_is_border,
                row_open_override => $table_row_open_override,
            };
            my $row_lines = $tm->parse_row($line, $cell_proc, $row_context);
            push @ret, @$row_lines;
            next;
        }
        elsif ($BLOCK->block eq 'table') {
            # tex gotcha: for border tables, prepend tableRowOpen to tableClose
            my $close = $TAGS{tableClose} // '';
            if ($target =~ /^tex/ && $table_is_border) {
                my $row_open = $TAGS{tableRowOpen} // '';
                $close = $row_open . $close if $row_open;
            }
            push @ret, $close;
            push @ret, '' if $rules{blanksaroundtable};
            $BLOCK->blockout;   # discard hold (rows were output inline)
            $BLOCK->last('table');  # update tracker since blockout discarded output
        }

        # ---- Quote -------------------------------------------------------
        if ($line =~ $regex{quote}) {
            my $new_depth = length( ($line =~ /^(\t+)/)[0] );

            # Clamp depth to quotemaxdepth if set
            my $qmax = $rules{quotemaxdepth} // 0;
            $new_depth = $qmax if $qmax && $new_depth > $qmax;

            if ($quote_depth == 0) {
                # Entering quote from non-quote context
                push @ret, @{ $BLOCK->blockout } if $BLOCK->block;
                push @ret, '' if $blank_before->('quote');
                $quote_oneline_buf = '' if $rules{onelinequote};
            }

            # Tag prefix per depth level
            my $ti = ($rules{tagnotindentable} ? '' : "\t");
            # Content prefix per depth level
            my $ci = ($rules{keepquoteindent} ? "\t" : '');
            my $cq = $TAGS{blockQuoteLine} // '';

            # Open new BLOCKQUOTE levels (depth increased)
            if ($new_depth > $quote_depth) {
                if ($rules{onelinequote} && defined $quote_oneline_buf && length($quote_oneline_buf)) {
                    push @ret, $quote_oneline_buf;
                    $quote_oneline_buf = '';
                }
                # Python adds blank before nested quote content (inner._should_add_blank_line("before","quote") depth>1)
                if ($new_depth > 1 && $rules{blanksaroundquote}) {
                    push @ret, '';
                }
                for my $lv ($quote_depth + 1 .. $new_depth) {
                    my $qtag = $TAGS{blockQuoteOpen} // '';
                    push @ret, ($ti x $lv) . $qtag if $qtag;
                }
            }
            # Close excess BLOCKQUOTE levels (depth decreased)
            elsif ($new_depth < $quote_depth) {
                if ($rules{onelinequote} && defined $quote_oneline_buf && length($quote_oneline_buf)) {
                    push @ret, $quote_oneline_buf;
                    $quote_oneline_buf = '';
                }
                for my $lv (reverse $new_depth + 1 .. $quote_depth) {
                    my $qtag = $TAGS{blockQuoteClose} // '';
                    push @ret, ($ti x $lv) . $qtag if $qtag;
                }
            }
            $quote_depth = $new_depth;

            # Process and emit the content line
            $line =~ s/^\t+//;
            $line = doEscape($target, $line);
            $line = add_inline_tags($line);
            $line = $MASK->undo($line);
            if ($rules{onelinequote}) {
                $quote_oneline_buf .= ($quote_oneline_buf ? ' ' : '') . $line;
            } else {
                push @ret, ($ci x $new_depth) . ($cq x $new_depth) . $line;
            }
            next;
        }
        elsif ($quote_depth > 0) {
            # Non-quote line encountered while in quote: close all levels
            my $ti = ($rules{tagnotindentable} ? '' : "\t");
            if ($rules{onelinequote} && defined $quote_oneline_buf) {
                push @ret, $quote_oneline_buf;
                $quote_oneline_buf = undef;
            }
            for my $lv (reverse 1 .. $quote_depth) {
                my $qtag = $TAGS{blockQuoteClose} // '';
                push @ret, ($ti x $lv) . $qtag if $qtag;
            }
            my $closing_depth = $quote_depth;
            $quote_depth = 0;
            $BLOCK->last('quote');
            push @ret, (('') x $closing_depth) if $rules{blanksaroundquote};
            # Fall through to process current line as non-quote
        }

        # ---- Empty list item (listclose) → closes current sublist level ----
        if ($line =~ $regex{listclose}) {
            my ($ind, $marker) = ($1, $2);
            if (@list_stack) {
                $list_pending_blank = 0;
                $_close_list_levels->(length($ind) - 1);
            }
            next;
        }

        # ---- List item --------------------------------------------------
        if ($line =~ $regex{list} || $line =~ $regex{numlist}
                                  || $line =~ $regex{deflist}) {
            my ($list_type, $ind, $item_txt);
            if    ($line =~ $regex{deflist})  { $list_type = 'deflist'; $ind = $1; $item_txt = $3 }
            elsif ($line =~ $regex{numlist})  { $list_type = 'numlist'; $ind = $1; ($item_txt = $line) =~ s/^ *\+ // }
            else                              { $list_type = 'list';    $ind = $1; ($item_txt = $line) =~ s/^ *- //  }

            # Emit deferred blank before depth/type changes
            if ($list_pending_blank) {
                if ($rules{parainsidelist}) {
                    # Mark current list as wide and retroactively switch to non-compact open tag
                    if ($rules{compactlist} && @list_stack && !$list_stack[-1]{wide}) {
                        my $entry = $list_stack[-1];
                        $entry->{wide} = 1;
                        if (defined $entry->{open_tag_idx}) {
                            my $nco = $TAGS{$entry->{type} . 'Open'} // '';
                            $ret[$entry->{open_tag_idx}] = $_list_ind->($entry->{indent}) . $nco;
                        }
                    }
                    my $po = $TAGS{paragraphOpen}  // '';
                    my $pc = $TAGS{paragraphClose} // '';
                    if ($po || $pc) {
                        my $top_ind = @list_stack ? $list_stack[-1]{indent} : '';
                        push @ret, $top_ind . $po . $pc;
                    } else {
                        push @ret, '';
                    }
                } else {
                    push @ret, '';
                }
            }
            $list_pending_blank = 0;

            my $was_empty = (@list_stack == 0);
            my $old_top   = $_close_list_levels->(length($ind));

            if (@list_stack == 0) {
                # Entering list from non-list context, or stack emptied by reverse nesting
                push @ret, '' if $was_empty && $blank_before->($list_type);
                my $lo_tag = $_list_open_tag->($list_type);
                my $open_idx = @ret;
                push @ret, $_list_ind->($ind) . $lo_tag if $lo_tag;
                push @list_stack, { indent => $ind, type => $list_type, open_item => 0, open_tag_idx => $lo_tag ? $open_idx : undef, wide => 0 };
            }
            elsif (length($ind) > length($old_top)) {
                # New item is deeper than the old top → open sublist
                my $lo_tag = $_list_open_tag->($list_type);
                my $open_idx = @ret;
                push @ret, $_list_ind->($ind) . $lo_tag if $lo_tag;
                push @list_stack, { indent => $ind, type => $list_type, open_item => 0, open_tag_idx => $lo_tag ? $open_idx : undef, wide => 0 };
            }
            elsif ($list_stack[-1]{type} ne $list_type) {
                # Same indent, different list type → close old item then list, open new
                my $cl = pop @list_stack;
                if ($cl->{open_item}) {
                    my $ic = $_item_close_tag->($cl->{type});
                    $_emit_item_close->($_list_ind->($cl->{indent}), $ic);
                }
                my $lc_tag = $cl->{wide} ? ($TAGS{$cl->{type} . 'Close'} // '') : $_list_close_tag->($cl->{type});
                push @ret, $_list_ind->($cl->{indent}) . $lc_tag if $lc_tag;
                if (!@list_stack) {
                    $BLOCK->last($cl->{type});
                    push @ret, '' if $rules{'blanksaround' . $cl->{type}};
                }
                my $lo_tag = $_list_open_tag->($list_type);
                my $open_idx = @ret;
                push @ret, $_list_ind->($ind) . $lo_tag if $lo_tag;
                push @list_stack, { indent => $ind, type => $list_type, open_item => 0, open_tag_idx => $lo_tag ? $open_idx : undef, wide => 0 };
            }
            else {
                # Same level, same type → close previous open item before new item
                if ($list_stack[-1]{open_item}) {
                    my $ic = $_item_close_tag->($list_type);
                    $_emit_item_close->($_list_ind->($list_stack[-1]{indent}), $ic);
                    $list_stack[-1]{open_item} = 0;
                }
            }

            $item_txt = doEscape($target, $item_txt);
            $item_txt = add_inline_tags($item_txt);
            $item_txt = $MASK->undo($item_txt);

            my $eff_ind = $_list_ind->($list_stack[-1]{indent});
            my $depth   = scalar @list_stack;
            my $item_line;
            if ($list_type eq 'deflist') {
                my $dt_open  = $TAGS{deflistItem1Open}  // '';
                my $dt_close = $TAGS{deflistItem1Close} // '';
                my $dd_open  = $TAGS{deflistItem2Open}  // '';
                $item_line = $eff_ind . $dt_open . $item_txt . $dt_close . $dd_open;
            } else {
                my $open    = $TAGS{$list_type . 'ItemOpen'} // '';
                my $linepfx = $TAGS{$list_type . 'ItemLine'} // '';
                if ($linepfx) {
                    if ($rules{listlineafteropen}) {
                        $open = $open . $linepfx x $depth;
                    } else {
                        $open = $linepfx x $depth . $open;
                    }
                }
                if (($list_type eq 'list' && $rules{spacedlistitemopen}) ||
                    ($list_type eq 'numlist' && $rules{spacednumlistitemopen})) {
                    $open .= ' ';
                }
                # For numbered list without autonumber, substitute \a with count
                if ($list_type eq 'numlist' && !$rules{autonumberlist}) {
                    $list_stack[-1]{item_count} //= 0;
                    $list_stack[-1]{item_count}++;
                    my $n = $list_stack[-1]{item_count};
                    $open =~ s/\\a/$n/g;
                }
                $item_line = $eff_ind . $open . $item_txt;
            }
            push @ret, $item_line;
            $list_stack[-1]{open_item} = 1;
            next;
        }

        # ---- Continuation line inside a list ----------------------------
        if (@list_stack) {
            if ($list_pending_blank) {
                if ($rules{parainsidelist}) {
                    my $po = $TAGS{paragraphOpen}  // '';
                    my $pc = $TAGS{paragraphClose} // '';
                    if ($po || $pc) {
                        my $top_ind = $_list_ind->($list_stack[-1]{indent});
                        push @ret, $top_ind . $po . $pc;
                    } else {
                        push @ret, '';
                    }
                } else {
                    push @ret, '';  # blank is content for non-parainsidelist targets
                }
            }
            $list_pending_blank = 0;
            $line = doEscape($target, $line);
            $line = add_inline_tags($line);
            $line = $MASK->undo($line);
            # Strip leading whitespace when keeplistindent=0 or deflist+deflisttextstrip
            my $top_type = $list_stack[-1]{type} // '';
            if (!$rules{keeplistindent} || ($top_type eq 'deflist' && $rules{deflisttextstrip})) {
                $line =~ s/^\s+//;
            }
            # Apply deflistItem2LinePrefix for definition body lines
            if ($top_type eq 'deflist' && $TAGS{deflistItem2LinePrefix}) {
                $line = $TAGS{deflistItem2LinePrefix} . $line;
            }
            push @ret, $line;
            next;
        }

        # ---- Paragraph (plain text) ------------------------------------
        $line = doEscape($target, $line);
        $line = add_inline_tags($line);
        $line = $MASK->undo($line);

        if ($BLOCK->block ne 'para') {
            push @ret, @{ $BLOCK->blockout } if $BLOCK->block;
            push @ret, '' if $blank_before->('para');
            my $po = $TAGS{paragraphOpen} // '';
            push @ret, $po if $po;
            $BLOCK->blockin('para') unless $BLOCK->block;
            $para_content_start = scalar @ret if $rules{onelinepara};
        }
        push @ret, $line;
    }

    # Close any remaining open lists
    $_close_all_lists->();

    # Close any remaining open quote levels
    if ($quote_depth > 0) {
        my $ti = ($rules{tagnotindentable} ? '' : "\t");
        if ($rules{onelinequote} && defined $quote_oneline_buf) {
            push @ret, $quote_oneline_buf;
            $quote_oneline_buf = undef;
        }
        for my $lv (reverse 1 .. $quote_depth) {
            my $qtag = $TAGS{blockQuoteClose} // '';
            push @ret, ($ti x $lv) . $qtag if $qtag;
        }
        $quote_depth = 0;
        $BLOCK->last('quote');
        push @ret, '' if $rules{blanksaroundquote};
    }

    # Close any remaining open block (para/verb/table) BEFORE sections
    if ($BLOCK->block) {
        my $closing_blk = $BLOCK->block;
        my $result = $BLOCK->blockout;
        push @ret, @$result;
        if ($rules{onelinepara} && $closing_blk eq 'para' && $para_content_start >= 0) {
            my @para_lines = splice(@ret, $para_content_start);
            push @ret, join(' ', @para_lines) if @para_lines;
            $para_content_start = -1;
        }
        # Add trailing blank for block types that use blanksaroundXXX
        push @ret, '' if $rules{"blanksaround$closing_blk"};
    }

    # Close any remaining open sections (titleblocks targets like html5/htmls)
    if ($rules{titleblocks} && @section_stack) {
        while (@section_stack) {
            my $lv = pop @section_stack;
            push @ret, $TAGS{"title${lv}Close"} // '</section>';
        }
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
        $target_toc    = [] if !$AUTOTOC && !$myconf->{'toc-only'};

        $myconf->{fullBody} = [@$target_toc, @$target_body, @$target_foot];

        # Header – expand macros in header lines (%%date, %%mtime, etc.)
        Message('Composing target Headers', 1);
        my $macro = Text::Txt2tags::MacroMaster->new(config => $myconf);
        my @expanded_head = map { $macro->expand($_ // '') } @{$source_head}[0..2];
        my $outlist = doHeader(\@expanded_head, $myconf);

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
