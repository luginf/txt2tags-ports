package Text::Txt2tags::Constants;

# txt2tags - constants and immutable configuration
# Port of txt2tags3_mod/constants.py to Perl 5

use strict;
use warnings;
use Exporter 'import';

our $VERSION = '3.9.0';

# ---------------------------------------------------------------------------
# User config
# ---------------------------------------------------------------------------
use constant USE_I18N    => 1;  # use locale for i18ned messages?
use constant COLOR_DEBUG => 1;  # show debug messages in colors?
use constant BG_LIGHT    => 0;  # terminal background is light?
use constant HTML_LOWER  => 0;  # use lowercased HTML tags?

# ---------------------------------------------------------------------------
# Program information
# ---------------------------------------------------------------------------
our $MY_URL      = 'http://txt2tags.org';
our $MY_NAME     = 'txt2tags';
our $MY_EMAIL    = 'verde@aurelio.net';
our $MY_REVISION = '$Revision$';
our $MY_VERSION  = '2.6';

# Strip non-digits from revision
(my $rev_num = $MY_REVISION) =~ s/\D//g;
$MY_VERSION = "$MY_VERSION.$rev_num" if $rev_num;

# ---------------------------------------------------------------------------
# i18n stub (no gettext dependency required)
# ---------------------------------------------------------------------------
sub _ { return $_[0] }

# ---------------------------------------------------------------------------
# Default FLAGS, OPTIONS, ACTIONS
# ---------------------------------------------------------------------------
our %FLAGS = (
    'headers'      => 1,
    'enum-title'   => 0,
    'mask-email'   => 0,
    'toc-only'     => 0,
    'toc'          => 0,
    'qa'           => 0,
    'rc'           => 1,
    'css-sugar'    => 0,
    'css-inside'   => 0,
    'quiet'        => 0,
    'slides'       => 0,
    'spread'       => 0,
    'web'          => 0,
    'print'        => 0,
    'fix-path'     => 0,
    'embed-images' => 0,
);

our %OPTIONS = (
    'target'             => '',
    'toc-level'          => 3,
    'toc-title'          => '',
    'style'              => '',
    'infile'             => '',
    'outfile'            => '',
    'encoding'           => '',
    'config-file'        => '',
    'split'              => 0,
    'lang'               => '',
    'width'              => 0,
    'height'             => 0,
    'chars'              => '',
    'show-config-value'  => '',
    'template'           => '',
    'dirname'            => '',
);

our %ACTIONS = (
    'help'          => 0,
    'version'       => 0,
    'gui'           => 0,
    'verbose'       => 0,
    'debug'         => 0,
    'dump-config'   => 0,
    'dump-source'   => 0,
    'targets'       => 0,
);

our %MACROS = (
    'date'        => '%Y-%m-%d',
    'mtime'       => '%Y%m%d',
    'infile'      => '%f',
    'currentfile' => '%f',
    'outfile'     => '%f',
    'appurl'      => '',
    'appname'     => '',
    'appversion'  => '',
    'target'      => '',
    'cmdline'     => '',
    'encoding'    => '',
    'header1'     => '',
    'header2'     => '',
    'header3'     => '',
    'cc'          => '',
);

our %SETTINGS = ();

our @NO_TARGET = qw(
    help version gui toc-only dump-config dump-source targets
);

our @NO_MULTI_INPUT = qw(gui dump-config dump-source);

our @CONFIG_KEYWORDS = qw(
    cc target encoding style stylepath options
    preproc postproc postvoodoo guicolors
);

# ---------------------------------------------------------------------------
# Target names
# ---------------------------------------------------------------------------
our %TARGET_NAMES = (
    'txt2t'   => _('Txt2tags document'),
    'html'    => _('HTML page'),
    'html5'   => _('HTML5 page'),
    'xhtml'   => _('XHTML page'),
    'xhtmls'  => _('XHTML Strict page'),
    'htmls'   => _('HTML Spreadsheet'),
    'sgml'    => _('SGML document'),
    'dbk'     => _('DocBook document'),
    'tex'     => _('LaTeX document'),
    'texs'    => _('LaTeX Spreadsheet'),
    'lout'    => _('Lout document'),
    'man'     => _('UNIX Manual page'),
    'utmac'   => _('Utmac (utroff) document'),
    'mgp'     => _('MagicPoint presentation'),
    'wiki'    => _('Wikipedia page'),
    'gwiki'   => _('Google Wiki page'),
    'doku'    => _('DokuWiki page'),
    'pmw'     => _('PmWiki page'),
    'moin'    => _('MoinMoin page'),
    'pm6'     => _('PageMaker document'),
    'txt'     => _('Plain Text'),
    'aat'     => _('ASCII Art Text'),
    'aap'     => _('ASCII Art Presentation'),
    'aas'     => _('ASCII Art Spreadsheet'),
    'aatw'    => _('ASCII Art Text Web'),
    'aapw'    => _('ASCII Art Presentation Web'),
    'aasw'    => _('ASCII Art Spreadsheet Web'),
    'aapp'    => _('ASCII Art Presentation Print'),
    'db'      => _('SQLite database'),
    'adoc'    => _('AsciiDoc document'),
    'rst'     => _('ReStructuredText document'),
    'csv'     => _('CSV table'),
    'csvs'    => _('CSV Spreadsheet'),
    'ods'     => _('Open Document Spreadsheet'),
    'creole'  => _('Creole 1.0 document'),
    'md'      => _('Markdown document'),
    'gmi'     => _('Gemtext document'),
    'bbcode'  => _('BBCode document'),
    'red'     => _('Redmine Wiki page'),
    'spip'    => _('SPIP article'),
    'rtf'     => _('RTF document'),
    'wp'      => _('WordPress post'),
    'tml'     => _('Foswiki or TWiki page'),
    'mom'     => _('MOM groff macro'),
    'vimwiki' => _('Vimwiki document'),
);

our %TARGET_TYPES = (
    'html' => [ _('HTML'), [qw(html html5 xhtml xhtmls htmls aatw aapw aasw wp)] ],
    'wiki' => [ _('WIKI'), [qw(txt2t wiki gwiki doku pmw moin adoc rst creole gmi md bbcode red spip tml vimwiki)] ],
    'office' => [ _('OFFICE'), [qw(sgml dbk tex texs lout mgp pm6 csv csvs ods rtf db mom utmac)] ],
    'text'   => [ _('TEXT'), [qw(man txt aat aap aas aapp)] ],
);

our @TARGETS = sort keys %TARGET_NAMES;

# ---------------------------------------------------------------------------
# Dimensions and ASCII Art
# ---------------------------------------------------------------------------
use constant DFT_TEXT_WIDTH        => 72;
use constant DFT_SLIDE_WIDTH       => 80;
use constant DFT_SLIDE_HEIGHT      => 24;
use constant DFT_SLIDE_WEB_WIDTH   => 73;
use constant DFT_SLIDE_WEB_HEIGHT  => 27;
use constant DFT_SLIDE_PRINT_WIDTH => 112;
use constant DFT_SLIDE_PRINT_HEIGHT=> 46;

our @AA_KEYS = split ' ',
    'tlcorner trcorner blcorner brcorner tcross bcross lcross rcross '
  . 'lhhead hheadcross rhhead headerscross tvhead vheadcross bvhead '
  . 'cross border side bar1 bar2 level2 level3 level4 level5 '
  . 'bullet hhead vhead quote';

our $AA_SIMPLE   = '+-|-==-^"-=$8';   # --chars
our $AA_ADVANCED = '++++++++++++++++' . $AA_SIMPLE;  # --chars

our %AA;
{
    my @adv = split //, $AA_ADVANCED;
    @AA{@AA_KEYS} = @adv;
}

our $AA_COUNT = 0;
our %AA_PW_TOC = ();
our $AA_IMG = 0;
our $AA_TITLE = '';
our @AA_MARKS = ();

# ReStructuredText config
our @RST_KEYS   = split ' ', 'title level1 level2 level3 level4 level5 bar1 bullet';
our $RST_VALUES = '#*=-^"--';
our %RST;
{
    my @vals = split //, $RST_VALUES;
    @RST{@RST_KEYS} = @vals;
}

# CSV config
our @CSV_KEYS   = qw(separator quotechar);
our $CSV_VALUES = ',';
our %CSV;
{
    my @vals = split //, $CSV_VALUES;
    @CSV{@CSV_KEYS} = @vals;
}

# ---------------------------------------------------------------------------
# Runtime globals (will be overridden by State.pm)
# ---------------------------------------------------------------------------
our @RC_RAW      = ();
our @CMDLINE_RAW = ();
our %CONF        = ();
our $BLOCK       = undef;
our $TITLE       = undef;
our %regex       = ();
our %TAGS        = ();
our %rules       = ();
our $MAILING     = '';

our $lang   = 'english';
our $TARGET = '';

our %file_dict = ();
our $STDIN     = '-';
our $STDOUT    = '-';
our $MODULEIN  = '-module-';
our $MODULEOUT = '-module-';
our $ESCCHAR   = "\x00";
our $SEPARATOR = "\x01";
our %LISTNAMES = ( '-' => 'list', '+' => 'numlist', ':' => 'deflist' );
our %LINEBREAK = ( 'default' => "\n", 'win' => "\r\n", 'mac' => "\r" );

our %ESCAPES = (
    'pm6'  => [ [ $ESCCHAR . '<', 'vvvvPm6Bracketvvvv', '<\#92><' ] ],
    'man'  => [ [ '-', 'vvvvManDashvvvv', '\-' ] ],
    'sgml' => [ [ '[', 'vvvvSgmlBracketvvvv', '&lsqb;' ] ],
    'lout' => [ [ '/', 'vvvvLoutSlashvvvv', '"/"' ] ],
    'tex'  => [
        [ '_',  'vvvvTexUndervvvv',     '\_' ],
        [ '\\', 'vvvvTexBackslashvvvv', '$\backslash$' ],
    ],
    'rtf'  => [ [ "\t", 'vvvvRtfTabvvvv', $ESCCHAR . 'tab' ] ],
);

# Platform-specific line break
our $LB = $LINEBREAK{$^O =~ /^win/i ? 'win' : $^O =~ /^mac/i ? 'mac' : 'default'};

our $VERSIONSTR = sprintf('%s version %s <%s>', $MY_NAME, $MY_VERSION, $MY_URL);

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
our @EXPORT_OK = qw(
    USE_I18N COLOR_DEBUG BG_LIGHT HTML_LOWER
    $MY_URL $MY_NAME $MY_EMAIL $MY_REVISION $MY_VERSION
    %FLAGS %OPTIONS %ACTIONS %MACROS %SETTINGS
    @NO_TARGET @NO_MULTI_INPUT @CONFIG_KEYWORDS
    %TARGET_NAMES %TARGET_TYPES @TARGETS
    DFT_TEXT_WIDTH DFT_SLIDE_WIDTH DFT_SLIDE_HEIGHT
    DFT_SLIDE_WEB_WIDTH DFT_SLIDE_WEB_HEIGHT
    DFT_SLIDE_PRINT_WIDTH DFT_SLIDE_PRINT_HEIGHT
    @AA_KEYS $AA_SIMPLE $AA_ADVANCED %AA $AA_COUNT %AA_PW_TOC $AA_IMG $AA_TITLE @AA_MARKS
    @RST_KEYS $RST_VALUES %RST
    @CSV_KEYS $CSV_VALUES %CSV
    @RC_RAW @CMDLINE_RAW %CONF $BLOCK $TITLE %regex %TAGS %rules $MAILING
    $lang $TARGET %file_dict
    $STDIN $STDOUT $MODULEIN $MODULEOUT
    $ESCCHAR $SEPARATOR %LISTNAMES %LINEBREAK %ESCAPES $LB
    $VERSIONSTR
    $_
);

our %EXPORT_TAGS = ( all => \@EXPORT_OK );

1;
__END__

=head1 NAME

Text::Txt2tags::Constants - Immutable constants for Text::Txt2tags

=head1 DESCRIPTION

Port of C<txt2tags3_mod/constants.py> to Perl 5.
Defines program metadata, default flags/options, target tables,
ASCII-art keys, and other compile-time constants.

=cut
