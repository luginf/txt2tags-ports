package Text::Txt2tags::Processing;

# txt2tags - MaskMaster, TitleMaster, TableMaster, BlockMaster, MacroMaster
# Port of txt2tags3_mod/processing.py to Perl 5

use strict;
use warnings;
use Exporter 'import';
use POSIX qw(strftime);

our $VERSION = '3.9.0';

use Text::Txt2tags::Constants qw(
    $ESCCHAR %MACROS $MY_NAME $MY_VERSION $MY_URL
);
use Text::Txt2tags::State qw(
    %CONF %TAGS %rules %regex $AUTOTOC $TARGET $DEBUG
);
use Text::Txt2tags::Utils  qw(Error Debug);
use Text::Txt2tags::Output qw(
    doEscape doFinalEscape doProtect enclose_me
    get_tagged_link fix_relative_path get_image_align
    maskEscapeChar unmaskEscapeChar compile_filters
    parse_deflist_term
);

# Package-level aliases so sub-packages can access these without qualification
our (%CONF, %TAGS, %rules, %regex, $AUTOTOC, $TARGET, %MACROS, $ESCCHAR);
BEGIN {
    *CONF    = \%Text::Txt2tags::State::CONF;
    *TAGS    = \%Text::Txt2tags::State::TAGS;
    *rules   = \%Text::Txt2tags::State::rules;
    *regex   = \%Text::Txt2tags::State::regex;
    *AUTOTOC = \$Text::Txt2tags::State::AUTOTOC;
    *TARGET  = \$Text::Txt2tags::State::TARGET;
    *MACROS  = \%Text::Txt2tags::Constants::MACROS;
    *ESCCHAR = \$Text::Txt2tags::Constants::ESCCHAR;
}

# ===========================================================================
# MacroMaster – expand %%macroname
# ===========================================================================

package Text::Txt2tags::MacroMaster;
our (%CONF, %MACROS);
BEGIN {
    *CONF   = \%Text::Txt2tags::State::CONF;
    *MACROS = \%Text::Txt2tags::Constants::MACROS;
}

sub new {
    my ($class, %args) = @_;
    return bless { config => $args{config} // \%CONF }, $class;
}

sub expand {
    my ($self, $line) = @_;
    $line //= '';
    my $config = $self->{config};

    # %%macroname[(format)]
    $line =~ s{%%(?<name>[a-zA-Z]+)\b(?:\((?<fmt>[^)]*)\))?}{
        my $name = lc $+{name};
        my $fmt  = $+{fmt} // '';
        $self->_expand_macro($name, $fmt, $config);
    }ge;

    return $line;
}

sub _expand_macro {
    my ($self, $name, $fmt, $config) = @_;
    $config //= \%CONF;

    if ($name eq 'date') {
        my $f = $fmt || $MACROS{date} || '%Y-%m-%d';
        return strftime($f, localtime);
    }
    elsif ($name eq 'mtime') {
        my $f = $fmt || $MACROS{mtime} || '%Y%m%d';
        return strftime($f, localtime);
    }
    elsif ($name =~ /^(infile|currentfile|outfile)$/) {
        return $config->{$name} // '';
    }
    elsif ($name =~ /^header([123])$/) {
        return $config->{"header$1"} // '';
    }
    elsif ($name eq 'target') {
        return $config->{target} // '';
    }
    elsif ($name eq 'encoding') {
        return $config->{encoding} // '';
    }
    elsif ($name eq 'cmdline') {
        return join(' ', @{ $config->{realcmdline} // [] });
    }
    elsif ($name =~ /^(appurl|appname|appversion)$/) {
        return $config->{$name} // '';
    }
    elsif ($name eq 'cc') {
        return $config->{cc} // '';
    }
    else {
        return "%%$name";
    }
}

# ===========================================================================
# MaskMaster – protect inline structures during markup parsing
# ===========================================================================

package Text::Txt2tags::MaskMaster;
our (%regex, %TAGS, $TARGET, $AUTOTOC, $ESCCHAR);
BEGIN {
    *regex   = \%Text::Txt2tags::State::regex;
    *TAGS    = \%Text::Txt2tags::State::TAGS;
    *TARGET  = \$Text::Txt2tags::State::TARGET;
    *AUTOTOC = \$Text::Txt2tags::State::AUTOTOC;
    *ESCCHAR = \$Text::Txt2tags::Constants::ESCCHAR;
}
sub doEscape      { Text::Txt2tags::Output::doEscape(@_)      }
sub doFinalEscape { Text::Txt2tags::Output::doFinalEscape(@_) }
sub doProtect     { Text::Txt2tags::Output::doProtect(@_)     }
sub enclose_me    { Text::Txt2tags::Output::enclose_me(@_)    }
sub get_tagged_link    { Text::Txt2tags::Output::get_tagged_link(@_) }
sub fix_relative_path  { Text::Txt2tags::Output::fix_relative_path(@_) }
sub maskEscapeChar  { Text::Txt2tags::Output::maskEscapeChar(@_)  }
sub unmaskEscapeChar{ Text::Txt2tags::Output::unmaskEscapeChar(@_) }

sub new {
    my ($class) = @_;
    my $self = bless {
        linkmask    => 'vvvLINKNNNvvv',
        monomask    => 'vvvMONONNNvvv',
        macromask   => 'vvvMACRONNNvvv',
        rawmask     => 'vvvRAWNNNvvv',
        taggedmask  => 'vvvTAGGEDNNNvvv',
        mathmask    => 'vvvMATHNNNvvv',
        tocmask     => 'vvvTOCvvv',
        linkmaskre  => qr/vvvLINK(\d+)vvv/,
        monomaskre  => qr/vvvMONO(\d+)vvv/,
        macromaskre => qr/vvvMACRO(\d+)vvv/,
        rawmaskre   => qr/vvvRAW(\d+)vvv/,
        taggedmaskre=> qr/vvvTAGGED(\d+)vvv/,
        mathmaskre  => qr/vvvMATH(\d+)vvv/,
        macroman    => Text::Txt2tags::MacroMaster->new,
    }, $class;
    $self->reset;
    return $self;
}

sub reset {
    my ($self) = @_;
    $self->{linkbank}      = [];
    $self->{monobank}      = [];
    $self->{monobank_orig} = [];
    $self->{macrobank}     = [];
    $self->{rawbank}       = [];
    $self->{rawbank_orig}  = [];
    $self->{taggedbank}    = [];
    $self->{taggedbank_orig} = [];
    $self->{mathbank}      = [];
    $self->{math_masks}    = [];
}

sub mask {
    my ($self, $line) = @_;
    $line //= '';

    # Protect verbatim/raw/tagged/math – whichever appears first wins
    PROTECT: while (1) {
        my ($t, $r, $v, $m) = (length($line)+1) x 4;
        $t = $-[0] if $line =~ $regex{tagged};
        $r = $-[0] if $line =~ $regex{raw};
        $v = $-[0] if $line =~ $regex{fontMono};
        $m = $-[0] if $line =~ $regex{math};

        if ($t <= $r && $t <= $v && $t <= $m && $t < length($line)+1) {
            $line =~ $regex{tagged};
            my $orig = $&;
            my $txt = $1;
            $txt = doProtect($TARGET, $txt);
            my $i = scalar @{ $self->{taggedbank} };
            push @{ $self->{taggedbank} }, $txt;
            push @{ $self->{taggedbank_orig} }, $orig;
            (my $mask = $self->{taggedmask}) =~ s/NNN/$i/;
            $line =~ s/$regex{tagged}/$mask/;
        }
        elsif ($r <= $t && $r <= $v && $r <= $m && $r < length($line)+1) {
            $line =~ $regex{raw};
            my $orig = $&;
            my $txt = doEscape($TARGET, $1);
            my $i = scalar @{ $self->{rawbank} };
            push @{ $self->{rawbank} }, $txt;
            push @{ $self->{rawbank_orig} }, $orig;
            (my $mask = $self->{rawmask}) =~ s/NNN/$i/;
            $line =~ s/$regex{raw}/$mask/;
        }
        elsif ($v <= $t && $v <= $r && $v <= $m && $v < length($line)+1) {
            $line =~ $regex{fontMono};
            my $orig = $&;
            my $txt = doEscape($TARGET, $1);
            my $i = scalar @{ $self->{monobank} };
            push @{ $self->{monobank} }, $txt;
            push @{ $self->{monobank_orig} }, $orig;
            (my $mask = $self->{monomask}) =~ s/NNN/$i/;
            $line =~ s/$regex{fontMono}/$mask/;
        }
        elsif ($m <= $t && $m <= $r && $m <= $v && $m < length($line)+1) {
            $line =~ $regex{math};
            my $txt = doEscape($TARGET, $1);
            my $i = scalar @{ $self->{mathbank} };
            push @{ $self->{mathbank} }, $txt;
            (my $mask = $self->{mathmask}) =~ s/NNN/$i/;
            push @{ $self->{math_masks} }, $mask;
            $line =~ s/$regex{math}/$mask/;
        }
        else { last PROTECT }
    }

    # Protect macros
    while ($line =~ $regex{macros}) {
        my $txt = $&;
        my $i   = scalar @{ $self->{macrobank} };
        push @{ $self->{macrobank} }, $txt;
        (my $mask = $self->{macromask}) =~ s/NNN/$i/;
        $line =~ s/\Q$txt\E/$mask/;
    }

    # Protect %%toc
    if ($line =~ $regex{toc}) {
        $line =~ s/$regex{toc}/$self->{tocmask}/g;
        $AUTOTOC = 0;
    }

    # Protect URLs and emails
    while ($line =~ $regex{linkmark} || $line =~ $regex{link}) {
        my ($link, $label, $link_re);
        my $ml = $line =~ $regex{link}     ? pos() // $-[0] : undef;
        my $mn = $line =~ $regex{linkmark} ? pos() // $-[0] : undef;

        if (defined $ml && defined $mn) {
            if ($mn <= $ml) {
                $line =~ $regex{linkmark};
                $link    = fix_relative_path($+{link} // '');
                $label   = $+{label} // '';
                $label   =~ s/\s+$//;
                $link_re = $regex{linkmark};
            }
            else {
                $line =~ $regex{link};
                $link    = $&;
                $label   = '';
                $link_re = $regex{link};
            }
        }
        elsif (defined $mn) {
            $line =~ $regex{linkmark};
            $link    = fix_relative_path($+{link} // '');
            $label   = $+{label} // '';
            $label   =~ s/\s+$//;
            $link_re = $regex{linkmark};
        }
        else {
            $line =~ $regex{link};
            $link    = $&;
            $label   = '';
            $link_re = $regex{link};
        }

        my $i = scalar @{ $self->{linkbank} };
        push @{ $self->{linkbank} }, [$label, $link];
        (my $mask = $self->{linkmask}) =~ s/NNN/$i/;
        $line =~ s/$link_re/$mask/;
    }

    return $line;
}

sub undo {
    my ($self, $line) = @_;

    # Links
    while ($line =~ /$self->{linkmaskre}/) {
        my $i     = $1;
        my $start = $-[0];
        my $end   = $+[0];
        my ($label, $url) = @{ $self->{linkbank}[$i] };
        my $tagged = get_tagged_link($label, $url);
        $line = substr($line, 0, $start) . $tagged . substr($line, $end);
    }

    # Macros
    while ($line =~ /$self->{macromaskre}/) {
        my $i     = $1;
        my $start = $-[0];
        my $end   = $+[0];
        my $macro = $self->{macroman}->expand($self->{macrobank}[$i]);
        $line = substr($line, 0, $start) . $macro . substr($line, $end);
    }

    # Verbatim (mono)
    while ($line =~ /$self->{monomaskre}/) {
        my $i     = $1;
        my $start = $-[0];
        my $end   = $+[0];
        my $txt   = ($TAGS{fontMonoOpen} // '') . $self->{monobank}[$i]
                  . ($TAGS{fontMonoClose} // '');
        $line = substr($line, 0, $start) . $txt . substr($line, $end);
    }

    # Raw
    while ($line =~ /$self->{rawmaskre}/) {
        my $i     = $1;
        my $start = $-[0];
        my $end   = $+[0];
        $line = substr($line, 0, $start) . $self->{rawbank}[$i] . substr($line, $end);
    }

    # Tagged
    while ($line =~ /$self->{taggedmaskre}/) {
        my $i     = $1;
        my $start = $-[0];
        my $end   = $+[0];
        $line = substr($line, 0, $start) . $self->{taggedbank}[$i] . substr($line, $end);
    }

    # Math (just restore as-is for non-special targets)
    while ($line =~ /$self->{mathmaskre}/) {
        my $i     = $1;
        my $start = $-[0];
        my $end   = $+[0];
        $line = substr($line, 0, $start) . $self->{mathbank}[$i] . substr($line, $end);
    }

    return $line;
}

# undo_title: restore masks to ORIGINAL markup (for use in title text)
# Raw/tagged/mono marks are kept as literal markup, not converted to HTML.
sub undo_title {
    my ($self, $line) = @_;

    # Restore raw masks as literal ""content"" with HTML-escaped content
    while ($line =~ /$self->{rawmaskre}/) {
        my $i     = $1;
        my $start = $-[0];
        my $end   = $+[0];
        my $literal = '""' . $self->{rawbank}[$i] . '""';
        $line = substr($line, 0, $start) . $literal . substr($line, $end);
    }

    # Restore tagged masks as literal ''content''
    while ($line =~ /$self->{taggedmaskre}/) {
        my $i     = $1;
        my $start = $-[0];
        my $end   = $+[0];
        my $literal = "''" . $self->{taggedbank}[$i] . "''";
        $line = substr($line, 0, $start) . $literal . substr($line, $end);
    }

    # Restore mono masks as literal ``content``
    while ($line =~ /$self->{monomaskre}/) {
        my $i     = $1;
        my $start = $-[0];
        my $end   = $+[0];
        my $literal = '``' . $self->{monobank}[$i] . '``';
        $line = substr($line, 0, $start) . $literal . substr($line, $end);
    }

    # Links and macros are still expanded normally
    while ($line =~ /$self->{linkmaskre}/) {
        my $i     = $1;
        my $start = $-[0];
        my $end   = $+[0];
        my ($label, $url) = @{ $self->{linkbank}[$i] };
        my $tagged = get_tagged_link($label, $url);
        $line = substr($line, 0, $start) . $tagged . substr($line, $end);
    }

    while ($line =~ /$self->{macromaskre}/) {
        my $i     = $1;
        my $start = $-[0];
        my $end   = $+[0];
        my $macro = $self->{macroman}->expand($self->{macrobank}[$i]);
        $line = substr($line, 0, $start) . $macro . substr($line, $end);
    }

    return $line;
}

# ===========================================================================
# TitleMaster – heading numbering & TOC
# ===========================================================================

package Text::Txt2tags::TitleMaster;
# (no globals needed)

sub new {
    my ($class) = @_;
    return bless {
        count        => ['', 0, 0, 0, 0, 0],
        toc          => [],
        level        => 0,
        kind         => '',
        txt          => '',
        label        => '',
        tag          => '',
        tag_hold     => [],
        last_level   => 0,
        count_id     => '',
        anchor_count => 0,
        anchor_prefix=> 'toc',
    }, $class;
}

sub _get_label {
    my ($self) = @_;
    if ($self->{label}) {
        return $self->{label};
    }
    $self->{anchor_count}++;
    return sprintf('%s%03d', $self->{anchor_prefix}, $self->{anchor_count});
}

sub add {
    my ($self, $level, $kind, $txt, $label) = @_;
    $self->{level} = $level;
    $self->{kind}  = $kind;    # 'title' or 'numtitle'
    $self->{txt}   = $txt;
    $self->{label} = $label // '';

    # Increment counter for numbered titles
    if ($kind eq 'numtitle') {
        $self->{count}[$level]++;
        $self->{count}[$_] = 0 for ($level+1 .. 5);
        $self->{count_id}  = join('.', @{ $self->{count} }[1..$level]);
    }
    else {
        $self->{count_id} = '';
    }

    my $lbl = $self->_get_label;
    $self->{last_count_id} = ($kind eq 'numtitle') ? $self->{count_id} : '';

    # Build TOC entry
    my $indent = '  ' x ($level - 1);
    my $entry;
    if ($kind eq 'numtitle') {
        $entry = sprintf('%s- %s %s', $indent, $self->{count_id}, $txt);
    }
    else {
        $entry = sprintf('%s- %s', $indent, $txt);
    }
    push @{ $self->{toc} }, $entry;

    return $lbl;
}

sub last_count_id { return $_[0]->{last_count_id} // '' }

sub close {
    my ($self) = @_;
    $self->{tag_hold} = [];
}

# ===========================================================================
# BlockMaster – manage open/close block state (verb, quote, list…)
# ===========================================================================

package Text::Txt2tags::BlockMaster;
our (%TAGS);
BEGIN { *TAGS = \%Text::Txt2tags::State::TAGS; }

sub new {
    my ($class) = @_;
    return bless {
        block_stack  => [],
        hold         => [],
        exclusive    => [qw(verb raw tagged comment)],
        last         => '',
        _last_raw    => 0,
    }, $class;
}

sub block {
    my ($self) = @_;
    return $self->{block_stack}[-1] // '';
}

sub depth {
    my ($self) = @_;
    return scalar @{ $self->{block_stack} };
}

sub prop {
    my ($self, $name) = @_;
    return $self->{"_prop_$name"};
}

sub set_prop {
    my ($self, $name, $val) = @_;
    $self->{"_prop_$name"} = $val;
}

# Map internal block names → TAGS key prefix
# e.g. 'verb' → 'blockVerb', 'quote' → 'blockQuote', 'para' → 'paragraph', ...
my %BLOCK_TAG_PREFIX = (
    verb    => 'blockVerb',
    raw     => 'blockRaw',
    tagged  => 'blockTagged',
    comment => 'blockComment',
    quote   => 'blockQuote',
    para    => 'paragraph',
    list    => 'list',
    numlist => 'numlist',
    deflist => 'deflist',
    table   => 'table',
);

sub _tag_prefix { $BLOCK_TAG_PREFIX{$_[1]} // $_[1] }

sub blockin {
    my ($self, $blockname) = @_;
    push @{ $self->{block_stack} }, $blockname;
    $self->{hold} = [];
    my @out;

    my $pfx      = $self->_tag_prefix($blockname);
    my $tag_open = $TAGS{$pfx . 'Open'} // '';
    push @out, $tag_open if $tag_open;

    return \@out;
}

sub blockout {
    my ($self, $flag_isempty) = @_;
    $flag_isempty //= 0;
    my $blockname = pop @{ $self->{block_stack} } // '';
    my @out;

    return \@out if $flag_isempty;

    my $pfx = $self->_tag_prefix($blockname);

    # Flush held lines
    for my $line (@{ $self->{hold} }) {
        my $tag = $TAGS{$pfx . 'Line'} // '';
        if ($tag) {
            $line = $tag . $line;
        }
        # indentverbblock: add 2-space prefix to verbatim lines
        if ($blockname eq 'verb' && $rules{indentverbblock}) {
            $line = '  ' . $line;
        }
        push @out, $line;
    }
    $self->{hold} = [];

    my $tag_close = $TAGS{$pfx . 'Close'} // '';
    push @out, $tag_close if $tag_close;

    # Only update last if this block produced output (matching Python v2 behavior)
    $self->{last} = $blockname if @out;
    return \@out;
}

sub last {
    my ($self, $val) = @_;
    $self->{last} = $val if defined $val;
    return $self->{last};
}

sub holdadd {
    my ($self, $line) = @_;
    push @{ $self->{hold} }, $line;
}

sub holdaddfinal {
    my ($self, @lines) = @_;
    push @{ $self->{hold} }, @lines;
}

sub holdget {
    my ($self) = @_;
    return $self->{hold};
}

sub holdflush {
    my ($self) = @_;
    my @data = @{ $self->{hold} };
    $self->{hold} = [];
    return \@data;
}

# ===========================================================================
# TableMaster – build tagged table rows/cells
# ===========================================================================

package Text::Txt2tags::TableMaster;
our (%TAGS, %rules);
BEGIN {
    *TAGS  = \%Text::Txt2tags::State::TAGS;
    *rules = \%Text::Txt2tags::State::rules;
}

sub new {
    my ($class) = @_;
    return bless {
        rows        => [],
        border      => 0,
        align       => '',
        n_table     => 0,
    }, $class;
}

sub _parse_cell {
    my ($self, $cell, $is_title, $cell_proc, $colspan) = @_;
    $colspan //= 1;

    # Detect alignment BEFORE stripping (based on leading/trailing spaces)
    # 2+ leading AND 2+ trailing → Center
    # 2+ leading only → Right
    # Otherwise → no special alignment (default left)
    my $align = '';
    if ($cell =~ /^  / && $cell =~ /  $/) { $align = 'Center' }
    elsif ($cell =~ /^  /)                 { $align = 'Right'  }

    $cell =~ s/^\s+|\s+$//g if $rules{tablecellstrip};

    my $open_tag  = $is_title ? ($TAGS{tableTitleCellOpen}  // '') : ($TAGS{tableCellOpen}  // '');
    my $close_tag = $is_title ? ($TAGS{tableTitleCellClose} // '') : ($TAGS{tableCellClose} // '');

    if ($align && $rules{tablecellaligntype} eq 'cell' && $cell =~ /\S/) {
        my $align_tag = $TAGS{"_tableCellAlign$align"} // '';
        $open_tag =~ s/~A~/$align_tag/;
    }
    if ($colspan > 1 && $TAGS{_tableCellColSpan}) {
        my $span_tag = $TAGS{_tableCellColSpan};
        $span_tag =~ s/\\a/$colspan/g;
        $open_tag =~ s/~S~/$span_tag/;
    }
    $open_tag =~ s/~[AS]~//g;  # remove unused placeholders

    # Apply text processing (escape, inline tags, unmask)
    $cell = $cell_proc->($cell) if $cell_proc;

    return ($open_tag, $cell, $close_tag);
}

sub parse_row {
    my ($self, $line, $cell_proc) = @_;
    # Remove leading | and determine if border/align
    my $is_title  = 0;
    my $is_border = 0;
    my $is_center = 0;

    $line =~ s/^ *//;
    if ($line =~ s/^\|\|//) { $is_title = 1 }
    else { $line =~ s/^\|// }

    my @raw_cells = split /\|/, $line, -1;
    # Remove trailing empty cell from trailing |
    pop @raw_cells if @raw_cells && ($raw_cells[-1] =~ /^\s*$/);

    # Merge consecutive TRULY empty cells (from ||) into colspan for preceding cell
    # Whitespace-only cells (from | |) are NOT merged.
    my @cells;     # [ [$content, $colspan], ... ]
    for my $cell (@raw_cells) {
        if ($cell eq '' && @cells) {
            $cells[-1][1]++;   # increment colspan of preceding cell
        } else {
            push @cells, [$cell, 1];
        }
    }

    my $row_open  = $TAGS{tableRowOpen}  // '';
    my $row_close = $TAGS{tableRowClose} // '';
    my @out;
    push @out, $row_open if $row_open;

    for my $cell_info (@cells) {
        my ($cell, $colspan) = @$cell_info;
        $cell //= '';
        my ($co, $ctxt, $cc) = $self->_parse_cell($cell, $is_title, $cell_proc, $colspan);
        push @out, "$co$ctxt$cc";
    }

    push @out, $row_close if $row_close;
    return \@out;
}

# ===========================================================================
# Exports
# ===========================================================================
package Text::Txt2tags::Processing;

our @EXPORT_OK = qw();   # classes are used by full name

1;
__END__

=head1 NAME

Text::Txt2tags::Processing - Core markup processing classes

=head1 DESCRIPTION

Port of C<txt2tags3_mod/processing.py> to Perl 5.

Provides:

=over 4

=item C<Text::Txt2tags::MacroMaster> – expand C<%%macroname> macros.

=item C<Text::Txt2tags::MaskMaster> – protect inline structures during parsing.

=item C<Text::Txt2tags::TitleMaster> – heading numbering and TOC accumulation.

=item C<Text::Txt2tags::BlockMaster> – block state machine (verb/quote/list/…).

=item C<Text::Txt2tags::TableMaster> – table row/cell tagging.

=back

=cut
