package Text::Txt2tags::Regexes;

# txt2tags - compiled regex patterns for t2t markup detection
# Port of txt2tags3_mod/regexes.py to Perl 5

use strict;
use warnings;
use Exporter 'import';

our $VERSION = '3.9.0';

use Text::Txt2tags::Constants qw(%MACROS);

# ---------------------------------------------------------------------------
# getRegexes() → hashref of compiled qr// patterns
# ---------------------------------------------------------------------------

sub getRegexes {

    # ---- URL skeleton parts -----------------------------------------------
    my %url = (
        proto  => q{(?:https?|ftp|news|telnet|gopher|wais)://},
        guess  => q{(?:www[23]?|ftp)\.},
        login  => q{[A-Za-z0-9_.-]},
        pass   => q{[^ @]*},
        chars  => q{[A-Za-z0-9%._/~:,=$@&+\-]},
        anchor => q{[A-Za-z0-9%._\-]},
        form   => q{[A-Za-z0-9/%&=+:;.,$@*_\-]},
        punct  => q{[.,;:!?]},
    );

    my $login_chars = $url{login};
    my $pass_chars  = $url{pass};
    my $url_chars   = $url{chars};
    my $form_chars  = $url{form};
    my $anchor_chars= $url{anchor};
    my $proto       = $url{proto};
    my $guess       = $url{guess};

    # Build as qr// objects so that interpolation into /x regexes is safe
    # (qr// retains its own flags and is not re-parsed under the outer /x)
    my $patt_url_login = qr/(?:$login_chars+(?::$pass_chars)?@)?/;

    # Full URL pattern (with or without proto)
    my $retxt_url = qr/\b(?:(?:$proto$patt_url_login|$guess)$url_chars+\b\/*(?:[?]$form_chars+)?(?:[#]$anchor_chars*)?)/i;

    # Local filename or #anchor
    my $retxt_url_local = qr/$url_chars+|$url_chars*(?:[#]$anchor_chars*)/i;

    # email pattern
    my $patt_email = qr/\b$login_chars+\@(?:[A-Za-z0-9_-]+\.)+[A-Za-z]{2,4}\b(?:[?]$form_chars+)?/i;

    # Image pattern – use literal char class, avoid $ interpolation in character class
    my $patt_img = qr/\[([A-Za-z0-9_,.+%\$#\@!?+~\/-]+\.(?:png|jpe?g|gif|eps|bmp|svg))\]/i;

    # Macro names joined by |
    my $macro_names = join '|', keys %MACROS;

    my %bank = (
        # Block delimiters
        blockVerbOpen    => qr/^```\s*$/,
        blockVerbClose   => qr/^```\s*$/,
        blockRawOpen     => qr/^"""\s*$/,
        blockRawClose    => qr/^"""\s*$/,
        blockTaggedOpen  => qr/^'''\s*$/,
        blockTaggedClose => qr/^'''\s*$/,
        blockCommentOpen => qr/^%%%\s*$/,
        blockCommentClose=> qr/^%%%\s*$/,

        # Inline structural
        quote            => qr/^\t+/,
        '1lineVerb'      => qr/^``` (?=.)/,
        '1lineRaw'       => qr/^""" (?=.)/,
        '1lineTagged'    => qr/^''' (?=.)/,

        # Inline font marks – greedy, glued (no boundary spaces)
        fontMono         => qr/``([^\s](?:.*?[^\s])?`*)``/,
        raw              => qr/""([^\s](?:.*?[^\s])?")""/ ,
        tagged           => qr/''([^\s](?:.*?[^\s])?'*)''/ ,
        math             => qr/\$\$([^\s](?:.*?[^\s])?\$*)\$\$/,
        fontBold         => qr/\*\*([^\s](?:.*?[^\s])?\**)\*\*/,
        fontItalic       => qr|//([^\s](?:.*?[^\s])?/*)//'|,
        fontUnderline    => qr/__([^\s](?:.*?[^\s])?_*)__/,
        fontStrike       => qr/--([^\s](?:.*?[^\s])?-*)--/,

        # Lists
        list             => qr/^( *)(-) (?=[^ ])/,
        numlist          => qr/^( *)(\+) (?=[^ ])/,
        deflist          => qr/^( *)(:) (.*)$/,
        listclose        => qr/^( *)([-+:])\s*$/,

        # Structural
        bar              => qr/^(\s*)([_=-]{20,})\s*$/,
        table            => qr/^ *\|([|_\/])? /,
        blankline        => qr/^\s*$/,
        comment          => qr/^%/,

        # Auxiliary alignment/attribute placeholders
        _imgAlign        => qr/~A~/i,
        _tableAlign      => qr/~A~/i,
        _anchor          => qr/~A~/i,
        _tableBorder     => qr/~B~/i,
        _tableColAlign   => qr/~C~/i,
        _tableCellColSpan=> qr/~S~/i,
        _tableCellAlign  => qr/~A~/i,
        _tableAttrDelimiter => qr/~Z~/i,
        _blockDepth      => qr/~D~/i,
        _listLevel       => qr/~L~/i,

        # Bell char placeholder (used inside TAGs)
        x                => qr/\a/,

        # Special config line
        special          => qr/^%!\s*/,
    );

    # Italic regex: // needs special care to avoid URL confusion
    $bank{fontItalic} = qr{//([^\s](?:.*?[^\s])?/*)//};

    # Macro pattern  %%macroname[(fmt)]
    $bank{macros} = qr/%%(?<name>$macro_names)\b(?:\((?<fmt>.*?)\))?/i;

    # %%TOC
    $bank{toc} = qr/^ *%%toc\s*$/i;

    # Titles  = text =  or  + text +  with optional [label]
    # Use backreference \k to match the same number of = or +
    $bank{title}    = qr/^ *(?<id>[=]{1,5})(?<txt>[^=](?:.*[^=])?)(?:\k<id>)(?:\[(?<label>[\w-]*)\])?\s*$/;
    $bank{numtitle} = qr/^ *(?<id>[+]{1,5})(?<txt>[^+](?:.*[^+])?)(?:\k<id>)(?:\[(?<label>[\w-]*)\])?\s*$/;

    # Email
    $bank{email} = $patt_email;

    # Link (URL or email) — avoid /x so # in URL is not treated as comment
    $bank{link} = qr/(?:$retxt_url|$patt_email)/i;

    # Named link  [label url] — no /x flag to preserve # in URLs
    $bank{linkmark} = qr/\[(?<label>$patt_img|[^\]]+?)\x20(?<link>$retxt_url|$patt_email|$retxt_url_local)\]/i;

    # Image
    $bank{img} = $patt_img;

    # Save urlskel for later use
    $bank{_urlskel} = \%url;

    return \%bank;
}

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
our @EXPORT_OK = qw(getRegexes);

1;
__END__

=head1 NAME

Text::Txt2tags::Regexes - Compiled regex patterns for t2t markup

=head1 SYNOPSIS

  use Text::Txt2tags::Regexes qw(getRegexes);
  my $rx = getRegexes();
  if ($line =~ $rx->{fontBold}) { ... }

=head1 DESCRIPTION

Port of C<txt2tags3_mod/regexes.py> to Perl 5.
Returns a hashref of compiled C<qr//> patterns for every t2t markup element.

=cut
