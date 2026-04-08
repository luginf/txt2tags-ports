package Text::Txt2tags::Config;

# txt2tags - source document parsing and configuration management
# Port of txt2tags3_mod/config.py to Perl 5

use strict;
use warnings;
use Exporter 'import';

our $VERSION = '3.9.0';

use Text::Txt2tags::Constants qw(
    $MY_NAME %FLAGS %OPTIONS %ACTIONS %MACROS %SETTINGS
    @NO_TARGET @NO_MULTI_INPUT @CONFIG_KEYWORDS @TARGETS
    $STDIN $STDOUT $MODULEIN $MODULEOUT
    DFT_TEXT_WIDTH DFT_SLIDE_WIDTH DFT_SLIDE_HEIGHT
    DFT_SLIDE_WEB_WIDTH DFT_SLIDE_WEB_HEIGHT
    DFT_SLIDE_PRINT_WIDTH DFT_SLIDE_PRINT_HEIGHT
);
use File::Basename ();
use File::Spec     ();
use Text::Txt2tags::Utils   qw(Error Debug Message Readfile dotted_spaces);
use Text::Txt2tags::Regexes qw(getRegexes);
use Text::Txt2tags::State   qw($VERBOSE $QUIET $DEBUG @RC_RAW @CMDLINE_RAW);

# Aliases for use in sub-packages below (they can't inherit imports)
our (%FLAGS, %OPTIONS, %ACTIONS, %SETTINGS, @CONFIG_KEYWORDS, @TARGETS, @NO_TARGET);
our ($MY_NAME, $STDIN, $STDOUT, $MODULEIN, $MODULEOUT);
BEGIN {
    *FLAGS             = \%Text::Txt2tags::Constants::FLAGS;
    *OPTIONS           = \%Text::Txt2tags::Constants::OPTIONS;
    *ACTIONS           = \%Text::Txt2tags::Constants::ACTIONS;
    *SETTINGS          = \%Text::Txt2tags::Constants::SETTINGS;
    *CONFIG_KEYWORDS   = \@Text::Txt2tags::Constants::CONFIG_KEYWORDS;
    *TARGETS           = \@Text::Txt2tags::Constants::TARGETS;
    *NO_TARGET         = \@Text::Txt2tags::Constants::NO_TARGET;
    *MY_NAME           = \$Text::Txt2tags::Constants::MY_NAME;
    *STDIN             = \$Text::Txt2tags::Constants::STDIN;
    *STDOUT            = \$Text::Txt2tags::Constants::STDOUT;
    *MODULEIN          = \$Text::Txt2tags::Constants::MODULEIN;
    *MODULEOUT         = \$Text::Txt2tags::Constants::MODULEOUT;
}

# ---------------------------------------------------------------------------
# SourceDocument
# ---------------------------------------------------------------------------

package Text::Txt2tags::SourceDocument;
# Utility function aliases for this sub-package
sub Error     { Text::Txt2tags::Utils::Error(@_)     }
sub Debug     { Text::Txt2tags::Utils::Debug(@_)     }
sub Message   { Text::Txt2tags::Utils::Message(@_)   }
sub Readfile  { Text::Txt2tags::Utils::Readfile(@_)  }
sub getRegexes{ Text::Txt2tags::Regexes::getRegexes(@_) }

sub new {
    my ($class, %args) = @_;
    my $self = bless {
        areas      => [qw(head conf body)],
        arearef    => [],
        areas_fancy=> '',
        filename   => $args{filename} // '',
        buffer     => [],
    }, $class;

    if ($args{filename}) {
        $self->scan_file($args{filename});
    }
    elsif ($args{contents}) {
        $self->scan($args{contents});
    }
    return $self;
}

sub split_doc {
    my ($self) = @_;
    return ($self->get('head'), $self->get('conf'), $self->get('body'));
}

sub get {
    my ($self, $areaname) = @_;
    my @areas = @{ $self->{areas} };
    # Head area always returns 3 lines (title/author/date), even if empty
    if ($areaname eq 'head') {
        return ['', '', ''] unless @{ $self->{buffer} };
    }
    else {
        return [] unless grep { $_ eq $areaname } @areas;
        return [] unless @{ $self->{buffer} };
    }

    my $buf    = $self->{buffer};
    my $bufini = 1;
    my $bufend = $#$buf;

    my ($ini, $end);
    my ($ref0, $ref1, $ref2) = @{ $self->{arearef} };

    if ($areaname eq 'head') {
        $ini = $bufini;
        $end = ($ref1 || $ref2 || $bufend + 1) - 1;
    }
    elsif ($areaname eq 'conf') {
        $ini = $ref1;
        $end = ($ref2 || $bufend + 1) - 1;
    }
    elsif ($areaname eq 'body') {
        $ini = $ref2;
        $end = $bufend;
    }
    else {
        Text::Txt2tags::Utils::Error("Unknown area name '$areaname'");
    }

    my @lines = @{$buf}[$ini .. $end];

    # Head always has exactly 3 lines
    if ($areaname eq 'head') {
        push @lines, '' while @lines < 3;
    }
    return \@lines;
}

sub scan_file {
    my ($self, $filename) = @_;
    Debug("source file: $filename");
    Message('Loading source document', 1);
    my $buf = Readfile($filename, 1);   # remove_linebreaks=1
    $self->scan($buf);
}

sub scan {
    my ($self, $lines) = @_;
    my @buf = @$lines;

    Text::Txt2tags::Utils::Error("The input file is empty: $self->{filename}")
        if !@buf;

    my $cfg_parser = Text::Txt2tags::ConfigLines->new;
    unshift @buf, '';   # text starts at pos 1

    my @ref = (1, 4, 0);
    # No header if: first line is blank OR starts with '%' (config/comment directive)
    if (!$buf[1] || $buf[1] !~ /\S/ || $buf[1] =~ /^%/) {
        $ref[0] = 0;
        $ref[1] = ($buf[1] && $buf[1] =~ /^%/) ? 1 : 2;  # conf at line 1 for %-lines
    }

    my $rgx = getRegexes();
    my $on_comment_block = 0;

    for my $i ($ref[1] .. $#buf) {
        my $line = $buf[$i] // '';
        # Handle comment blocks
        if (!$on_comment_block && $line =~ $rgx->{blockCommentOpen}) {
            $on_comment_block = 1;
            next;
        }
        if ($on_comment_block && $line =~ $rgx->{blockCommentOpen}) {
            $on_comment_block = 0;
            next;
        }
        next if $on_comment_block;

        if ($line =~ /\S/) {
            my $is_comment = substr($line, 0, 1) eq '%';
            my $is_macro   = $line =~ $rgx->{macros};
            my $is_toc     = $line =~ $rgx->{toc};
            my $is_include = ($cfg_parser->parse_line($line, 'include'))[1];
            my $is_csv     = ($cfg_parser->parse_line($line, 'csv'))[1];

            unless ($is_comment && !$is_macro && !$is_toc
                                && !$is_include && !$is_csv) {
                $ref[2] = $i;
                last;
            }
        }
    }

    $ref[1] = 0 if $ref[1] == $ref[2];   # no conf area

    for my $i (0, 1, 2) {
        if ($ref[$i] >= scalar @buf) { $ref[$i] = 0 }
        if (!$ref[$i]) { $self->{areas}[$i] = '' }
    }

    Debug(sprintf('Head,Conf,Body start line: %s %s %s', @ref));
    $self->{arearef} = \@ref;
    $self->{buffer}  = \@buf;
    $self->{areas_fancy} = join(' ', grep { $_ } @{ $self->{areas} })
        . ' (' . join(' ', map { $_ // '' } @ref) . ')';
    Message("Areas found: $self->{areas_fancy}", 2);
}

sub get_raw_config {
    my ($self) = @_;
    return [] unless grep { $_ eq 'conf' } @{ $self->{areas} };
    Message('Scanning source document CONF area', 1);
    my $raw = Text::Txt2tags::ConfigLines->new(
        file_     => $self->{filename},
        lines     => $self->get('conf'),
        first_line=> $self->{arearef}[1],
    )->get_raw_config;
    Debug("document raw config: " . join(', ', map { "[@$_]" } @$raw), 1);
    return $raw;
}

# ---------------------------------------------------------------------------
# ConfigLines – parse %! config lines
# ---------------------------------------------------------------------------

package Text::Txt2tags::ConfigLines;
sub Debug   { Text::Txt2tags::Utils::Debug(@_)   }
sub Error   { Text::Txt2tags::Utils::Error(@_)   }
sub Message { Text::Txt2tags::Utils::Message(@_) }

sub new {
    my ($class, %args) = @_;
    return bless {
        file_      => $args{file_}      // '',
        lines      => $args{lines}      // [],
        first_line => $args{first_line} // 1,
    }, $class;
}

# Returns (target, value) or ('', '') if not a config line for $keyword
sub parse_line {
    my ($self, $line, $keyword) = @_;
    $keyword //= '';

    # %!keyword[target]: value
    if ($line =~ /^%!\s*(\w[\w-]*)\s*(?:\(([^)]*)\))?\s*:\s*(.*)$/i) {
        my ($key, $target, $val) = ($1, $2 // 'all', $3);
        $key    = lc $key;
        $target = lc($target || 'all');
        $val    =~ s/\s+$//;
        if (!$keyword || $key eq lc($keyword)) {
            return ($target, $val, $key);
        }
    }
    return ('', '', '');
}

sub get_raw_config {
    my ($self, $depth) = @_;
    $depth //= 0;
    my @raw;
    my $n = $self->{first_line};
    for my $line (@{ $self->{lines} }) {
        $line //= '';
        chomp $line;
        if ($line =~ /^%!/) {
            my ($target, $val, $key) = $self->parse_line($line);
            if ($key eq 'includeconf' && $depth < 5) {
                # Resolve path relative to the current file
                my $dir = '';
                if ($self->{file_}) {
                    $dir = File::Basename::dirname($self->{file_});
                }
                my $inc = ($dir && $dir ne '.')
                    ? File::Spec->catfile($dir, $val)
                    : $val;
                if (-r $inc) {
                    open my $fh, '<', $inc or next;
                    my @inc_lines = <$fh>;
                    close $fh;
                    chomp @inc_lines;
                    my $sub = Text::Txt2tags::ConfigLines->new(
                        file_      => $inc,
                        lines      => \@inc_lines,
                        first_line => 1,
                    );
                    push @raw, @{ $sub->get_raw_config($depth + 1) };
                }
                else {
                    Debug("includeconf: cannot read '$inc'", 1);
                }
            }
            elsif ($key) {
                push @raw, [$target, $key, $val];
                Debug("config: target=$target key=$key val=$val", 1);
            }
        }
        $n++;
    }
    return \@raw;
}

# ---------------------------------------------------------------------------
# ConfigMaster – parse, validate and merge config
# ---------------------------------------------------------------------------

package Text::Txt2tags::ConfigMaster;
sub Debug   { Text::Txt2tags::Utils::Debug(@_)   }
sub Error   { Text::Txt2tags::Utils::Error(@_)   }
sub Message { Text::Txt2tags::Utils::Message(@_) }

sub new {
    my ($class, $raw, $target) = @_;
    $raw    //= [];
    $target //= '';
    my $self = bless {
        raw         => $raw,
        target      => $target,
        parsed      => {},
        dft_options => { %OPTIONS },
        dft_flags   => { %FLAGS   },
        dft_actions => { %ACTIONS },
        dft_settings=> { %SETTINGS},
        incremental => [qw(verbose)],
        numeric     => [qw(toc-level split width height)],
        multi       => [qw(infile preproc postproc postvoodoo options style stylepath)],
    }, $class;
    $self->{defaults} = $self->_get_defaults;
    $self->{off}      = $self->_get_off;
    return $self;
}

sub _get_defaults {
    my ($self) = @_;
    my %empty;
    $empty{$_} = '' for @CONFIG_KEYWORDS;
    %empty = (%empty, %{ $self->{dft_options} }, %{ $self->{dft_flags} },
              %{ $self->{dft_actions} }, %{ $self->{dft_settings} });
    $empty{realcmdline}       = '';
    $empty{sourcefile}        = '';
    $empty{currentsourcefile} = '';
    return \%empty;
}

sub _get_off {
    my ($self) = @_;
    my %off;
    for my $key (keys %{ $self->{defaults} }) {
        my $val = $self->{defaults}{$key};
        if (!defined $val) {
            $off{$key} = '';
        }
        elsif ($val =~ /^\d+$/) {
            $off{$key} = 0;
        }
        elsif (ref $val eq 'ARRAY') {
            $off{$key} = [];
        }
        else {
            $off{$key} = '';
        }
    }
    return \%off;
}

sub _check_target {
    my ($self) = @_;
    $self->{target} ||= $self->find_value('target');
}

sub find_value {
    my ($self, $key) = @_;
    for my $entry (reverse @{ $self->{raw} }) {
        return $entry->[2] if $entry->[1] eq $key;
    }
    return '';
}

sub get_target_raw {
    my ($self) = @_;
    $self->_check_target;
    my @ret;
    for my $entry (@{ $self->{raw} }) {
        push @ret, $entry
            if $entry->[0] eq $self->{target} || $entry->[0] eq 'all';
    }
    return \@ret;
}

# Parse a preproc/postproc value string "'pattern' 'replacement'" into
# an arrayref [$pattern, $replacement].  Tokens may be single-quoted or
# unquoted (splitting on whitespace).
sub _parse_prepost_value {
    my ($val) = @_;
    my @tokens;
    # Match up to 2 tokens: either 'quoted' or unquoted-word
    while (length $val && @tokens < 2) {
        $val =~ s/^\s+//;
        if ($val =~ s/^'([^']*)'?//) {
            push @tokens, $1;
        }
        elsif ($val =~ s/^(\S+)//) {
            push @tokens, $1;
        }
        else {
            last;
        }
    }
    return [ $tokens[0] // '', $tokens[1] // '' ];
}

sub add {
    my ($self, $key, $val) = @_;
    $val //= '';

    # no- prefix = turn OFF
    if ($key =~ s/^no-//) {
        $val = $self->{off}{$key} // 0;
    }

    return unless exists $self->{defaults}{$key};

    # If value == default, remove
    if (defined $self->{defaults}{$key} && $val eq $self->{defaults}{$key}) {
        delete $self->{parsed}{$key};
        return;
    }

    # Flags/actions come empty → set to 1
    if ($val eq '' && (exists $self->{dft_flags}{$key}
                    || exists $self->{dft_actions}{$key})) {
        $val = 1;
    }

    # Multi-value
    if (grep { $_ eq $key } @{ $self->{multi} }) {
        $self->{parsed}{$key} //= [];
        # preproc/postproc/postvoodoo: parse value into [pattern, replacement]
        if ($key eq 'preproc' || $key eq 'postproc' || $key eq 'postvoodoo') {
            push @{ $self->{parsed}{$key} }, _parse_prepost_value($val);
        }
        else {
            push @{ $self->{parsed}{$key} }, $val;
        }
    }
    # Incremental
    elsif (grep { $_ eq $key } @{ $self->{incremental} }) {
        $self->{parsed}{$key} = ($self->{parsed}{$key} // 0) + ($val || 1);
    }
    else {
        $self->{parsed}{$key} = $val;
    }

    my $fk = Text::Txt2tags::Utils::dotted_spaces(sprintf('%12s', $key));
    Message("Added config $fk : $val", 3);
}

sub parse {
    my ($self) = @_;
    $self->_check_target;
    for my $entry (@{ $self->get_target_raw }) {
        my (undef, $key, $val) = @$entry;
        $self->add($key, $val);
    }
    return $self->{parsed};
}

sub get_outfile_name {
    my ($self, $config) = @_;
    my $infile  = $config->{sourcefile} // '';
    my $outfile = $config->{outfile}    // '';

    $outfile = $STDOUT   if $infile eq $STDIN    && !$outfile;
    $outfile = $MODULEOUT if $infile eq $MODULEIN && !$outfile;

    if (!$outfile && $infile && $config->{target}) {
        (my $base = $infile) =~ s/\.(txt|t2t)$//;
        my $tgt = $config->{target};
        $outfile = "$base.$tgt";
    }
    Debug(" infile: '$infile'",  1);
    Debug("outfile: '$outfile'", 1);
    return $outfile;
}

sub sanity {
    my ($self, $config, $gui) = @_;
    $gui //= 0;
    return {} unless $config && %$config;

    my $target = $config->{target} // '';

    unless ($target) {
        for my $action (@NO_TARGET) {
            if ($config->{$action}) { $target = 'txt'; last }
        }
    }

    unless ($gui) {
        unless ($target) {
            Text::Txt2tags::Utils::Error(
                "No target specified (try --help)\n\n"
              . "Please inform a target using the -t option or the %!target command.\n"
              . "Example: $MY_NAME -t html file.t2t\n\n"
              . "Run 'txt2tags --targets' to see all available targets."
            );
        }
        unless ($config->{infile}) {
            Text::Txt2tags::Utils::Error("Missing input file (try --help)");
        }
        unless (grep { $_ eq $target } @TARGETS) {
            Text::Txt2tags::Utils::Error(
                "Invalid target '$target'\n\n"
              . "Run 'txt2tags --targets' to see all available targets."
            );
        }
    }

    # Fill in defaults
    my %full = (%{ $self->{defaults} }, %$config);
    $config = \%full;

    # Numeric options
    for my $key (@{ $self->{numeric} }) {
        next unless exists $config->{$key} && defined $config->{$key};
        unless ($config->{$key} =~ /^\d+$/) {
            Text::Txt2tags::Utils::Error("--$key value must be a number");
        }
        $config->{$key} = int($config->{$key});
    }

    # Alias targets
    my %alias_map = (
        aap  => [qw(aat slides)],
        aas  => [qw(aat spread)],
        aatw => [qw(aat web)],
        aapw => [qw(aat slides web)],
        aasw => [qw(aat spread web)],
        aapp => [qw(aat slides print)],
    );
    if (exists $alias_map{$target}) {
        my ($real_tgt, @flags) = @{ $alias_map{$target} };
        $target = $real_tgt;
        $config->{$_} = 1 for @flags;
    }
    $config->{target} = $target;

    # Default width for ASCII Art
    if ($target eq 'aat') {
        $config->{width} ||= Text::Txt2tags::Constants::DFT_TEXT_WIDTH();
    }

    # Determine output file name if not already set
    $config->{outfile} ||= $self->get_outfile_name($config);

    return $config;
}

# ---------------------------------------------------------------------------
# Package exports
# ---------------------------------------------------------------------------
package Text::Txt2tags::Config;

our @EXPORT_OK = qw(SourceDocument ConfigMaster ConfigLines);

1;
__END__

=head1 NAME

Text::Txt2tags::Config - Document parsing and configuration management

=head1 DESCRIPTION

Port of C<txt2tags3_mod/config.py> to Perl 5.

Provides three classes:

=over 4

=item C<Text::Txt2tags::SourceDocument> – splits a .t2t file into head/conf/body.

=item C<Text::Txt2tags::ConfigLines> – parses C<%!> directive lines.

=item C<Text::Txt2tags::ConfigMaster> – merges and validates all config sources.

=back

=cut
