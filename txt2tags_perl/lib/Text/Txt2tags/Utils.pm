package Text::Txt2tags::Utils;

# txt2tags - utility functions: error, file I/O, debug, logging
# Port of txt2tags3_mod/utils.py to Perl 5

use strict;
use warnings;
use Exporter 'import';
use Carp qw(croak);

our $VERSION = '3.9.0';

use Text::Txt2tags::Constants qw(
    $MY_NAME $MY_EMAIL COLOR_DEBUG BG_LIGHT
    $STDIN
);
use Text::Txt2tags::State qw($VERBOSE $QUIET $DEBUG);

# ---------------------------------------------------------------------------
# Exception class
# ---------------------------------------------------------------------------
package Text::Txt2tags::Error;
use overload '""' => \&as_string;
sub new       { bless { message => $_[1] }, $_[0] }
sub as_string { $_[0]->{message} }
sub throw     { die $_[0]->new($_[1]) }

package Text::Txt2tags::Utils;

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

sub echo {
    my ($msg) = @_;
    print "\033[32;1m$msg\033[m\n";
}

sub Quit {
    my ($msg) = @_;
    print "$msg\n" if defined $msg && length $msg;
    exit 0;
}

sub Error {
    my ($msg) = @_;
    $msg = sprintf('%s: Error: %s', $MY_NAME, $msg);
    Text::Txt2tags::Error->throw($msg);
}

sub Message {
    my ($msg, $level) = @_;
    return if $level > $VERBOSE || $QUIET;
    my $prefix = '-' x 5;
    print(($prefix x $level) . " $msg\n");
}

sub Debug {
    my ($msg, $id, $linenr) = @_;
    $id //= 0;
    return if $QUIET || !$DEBUG;
    $id = 0 if $id < 0 || $id > 7;
    my @ids         = qw(INI CFG SRC BLK HLD GUI OUT DET);
    my @dark_colors = qw(7;1 1;1 3;1 6;1 4;1 5;1 2;1 7;1);
    my @lite_colors = qw(0   1   3   6   4   5   2   0  );
    $msg = sprintf('LINE %04d: %s', $linenr, $msg) if defined $linenr;
    if (COLOR_DEBUG) {
        my $color = BG_LIGHT ? $lite_colors[$id] : $dark_colors[$id];
        $msg = "\033[3${color}m$msg\033[m";
    }
    print "++ $ids[$id]: $msg\n";
}

sub Readfile {
    my ($path, $remove_linebreaks, $ignore_error) = @_;
    $remove_linebreaks //= 0;
    $ignore_error      //= 0;

    my @data;

    if ($path eq '-') {
        # STDIN
        eval { @data = <STDIN> };
        if ($@) {
            Error('You must feed me with data on STDIN!') unless $ignore_error;
        }
    }
    elsif ($path =~ m{^https?://|^ftp://|^news://}) {
        # URL – try LWP::Simple if available, else skip
        eval {
            require LWP::Simple;
            my $content = LWP::Simple::get($path)
                or die "not found";
            @data = split /\n/, $content;
            $_ .= "\n" for @data;
        };
        if ($@) {
            Error("Cannot read URL: $path") unless $ignore_error;
        }
    }
    else {
        # Local file
        if (!open(my $fh, '<:encoding(UTF-8)', $path)) {
            Error("Cannot read file: $path") unless $ignore_error;
        }
        else {
            @data = <$fh>;
            close $fh;
        }
    }

    if ($remove_linebreaks) {
        s/[\r\n]+$// for @data;
    }

    Message(sprintf('File read (%d lines): %s', scalar @data, $path), 2);
    return \@data;
}

sub Savefile {
    my ($path, $contents) = @_;
    open(my $fh, '>:encoding(UTF-8)', $path)
        or Error("Cannot open file for writing: $path");
    if (ref $contents eq 'ARRAY') {
        print $fh $_ for @$contents;
    }
    else {
        print $fh $contents;
    }
    close $fh;
}

sub showdic {
    my ($dic) = @_;
    for my $k (sort keys %$dic) {
        printf('%15s : %s\n', $k, $dic->{$k} // '');
    }
}

sub dotted_spaces {
    my ($txt) = @_;
    $txt //= '';
    $txt =~ s/ /./g;
    return $txt;
}

sub get_rc_path {
    # Try environment variable first
    my $user_defined = $ENV{T2TCONFIG};
    return $user_defined if $user_defined;

    # Platform-specific filename
    my $rc_file = ($^O =~ /^MSWin/i) ? '_t2trc' : '.txt2tagsrc';

    # Find home directory
    my $rc_dir = $ENV{HOME} || $ENV{HOMEPATH} || '';
    return '' unless $rc_dir;

    # On Windows, prefix with drive letter
    if ($^O =~ /^MSWin/i && $ENV{HOMEDRIVE}) {
        $rc_dir = $ENV{HOMEDRIVE} . $rc_dir;
    }

    return File::Spec->catfile($rc_dir, $rc_file);
}

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
our @EXPORT_OK = qw(
    echo Quit Error Message Debug Readfile Savefile showdic dotted_spaces get_rc_path
);

our %EXPORT_TAGS = ( all => \@EXPORT_OK );

1;
__END__

=head1 NAME

Text::Txt2tags::Utils - Utility functions for Text::Txt2tags

=head1 DESCRIPTION

Port of C<txt2tags3_mod/utils.py> to Perl 5.
Provides error handling (C<Error>, C<Quit>), file I/O (C<Readfile>, C<Savefile>),
debug/verbose messaging (C<Debug>, C<Message>), and helpers.

=cut
