package Text::Txt2tags::State;

# txt2tags - mutable runtime globals
# Port of txt2tags3_mod/state.py to Perl 5

use strict;
use warnings;
use Exporter 'import';

our $VERSION = '3.9.0';

# ---------------------------------------------------------------------------
# Mutable globals that change during a conversion run
# ---------------------------------------------------------------------------

our $DEBUG   = 0;  # set via --debug
our $VERBOSE = 0;  # set via -v / -vv / -vvv
our $QUIET   = 0;  # set via --quiet
our $GUI     = 0;  # set via --gui
our $AUTOTOC = 1;  # set via --no-toc or %%toc

our %CONF  = ();
our %TAGS  = ();
our %rules = ();
our %regex = ();

our $BLOCK = undef;
our $TITLE = undef;

our $TARGET = '';

our @RC_RAW      = ();
our @CMDLINE_RAW = ();
our %file_dict   = ();
our $MAILING     = '';

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
our @EXPORT_OK = qw(
    $DEBUG $VERBOSE $QUIET $GUI $AUTOTOC
    %CONF %TAGS %rules %regex
    $BLOCK $TITLE $TARGET
    @RC_RAW @CMDLINE_RAW
    %file_dict $MAILING
);

our %EXPORT_TAGS = ( all => \@EXPORT_OK );

1;
__END__

=head1 NAME

Text::Txt2tags::State - Mutable runtime globals for Text::Txt2tags

=head1 DESCRIPTION

Port of C<txt2tags3_mod/state.py> to Perl 5.
All variables here may be modified during a conversion run.

=cut
