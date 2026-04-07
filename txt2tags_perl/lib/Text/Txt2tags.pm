package Text::Txt2tags;

# txt2tags - convert plain text to 40+ markup formats
# Perl 5 port of txt2tags3_mod (Python)

use strict;
use warnings;
use Exporter 'import';

our $VERSION = '3.9.0';

# Re-export the full public API from sub-modules
use Text::Txt2tags::Constants ();
use Text::Txt2tags::State     ();
use Text::Txt2tags::Utils     qw(Error Quit Message Debug Readfile Savefile
                                  dotted_spaces get_rc_path);
use Text::Txt2tags::Regexes   qw(getRegexes);
use Text::Txt2tags::Tags      qw(getTags);
use Text::Txt2tags::Rules     qw(getRules);
use Text::Txt2tags::Config    ();
use Text::Txt2tags::Processing();
use Text::Txt2tags::Output    qw(
    doEscape doFinalEscape doProtect maskEscapeChar unmaskEscapeChar
    addLineBreaks expandLineBreaks compile_filters
    enclose_me get_tagged_link doCommentLine
    doHeader doFooter finish_him listTargets dumpConfig
    toc_inside_body toc_tagger toc_formatter
    fix_relative_path get_encoding_string
);
use Text::Txt2tags::Converter qw(
    convert convert_this_files get_infiles_config
    process_source_file set_global_config
);

our @EXPORT_OK = qw(
    Error Quit Message Debug Readfile Savefile dotted_spaces get_rc_path
    getRegexes getTags getRules
    doEscape doFinalEscape doProtect maskEscapeChar unmaskEscapeChar
    addLineBreaks expandLineBreaks compile_filters
    enclose_me get_tagged_link doCommentLine
    doHeader doFooter finish_him listTargets dumpConfig
    toc_inside_body toc_tagger toc_formatter
    fix_relative_path get_encoding_string
    convert convert_this_files get_infiles_config
    process_source_file set_global_config
);

our %EXPORT_TAGS = ( all => \@EXPORT_OK );

1;
__END__

=head1 NAME

Text::Txt2tags - Convert plain text (txt2tags markup) to 40+ formats

=head1 VERSION

3.9.0

=head1 SYNOPSIS

  use Text::Txt2tags qw(convert process_source_file);

  # Convert a body arrayref with a config hashref
  my ($lines, $toc) = convert(\@body_lines, {
      target  => 'html',
      headers => 1,
      toc     => 0,
  });
  print join("\n", @$lines), "\n";

  # High-level: read a .t2t file and write the result
  use Text::Txt2tags::Converter qw(convert_this_files get_infiles_config);
  my $configs = get_infiles_config(['myfile.t2t']);
  convert_this_files($configs);

=head1 DESCRIPTION

Perl 5 port of the C<txt2tags3_mod> Python module.

txt2tags is a document-conversion tool that reads plain text files with
a lightweight markup and produces output in more than 40 formats including
HTML, LaTeX, Markdown, reStructuredText, AsciiDoc, Man pages, and many more.

This module mirrors the Python module structure:

  Text::Txt2tags::Constants   – immutable program-wide constants
  Text::Txt2tags::State       – mutable per-run globals
  Text::Txt2tags::Regexes     – compiled markup-detection regexes
  Text::Txt2tags::Tags        – per-target tag strings
  Text::Txt2tags::Rules       – per-target boolean behaviour flags
  Text::Txt2tags::Utils       – error handling, file I/O, debug
  Text::Txt2tags::Config      – .t2t document parsing & config merging
  Text::Txt2tags::Processing  – MaskMaster, TitleMaster, BlockMaster, …
  Text::Txt2tags::Output      – escaping, TOC, header/footer, output
  Text::Txt2tags::Converter   – main conversion engine

=head1 SUPPORTED TARGETS

  HTML family : html html5 xhtml xhtmls htmls wp
  Wiki / light: txt2t wiki gwiki doku pmw moin adoc rst creole md
                gmi bbcode red spip tml vimwiki
  Office      : sgml dbk tex lout man utmac mgp pm6 rtf mom
                csv csvs ods db
  Plain text  : txt aat aap aas aatw aapw aasw aapp

=head1 AUTHOR

Port by luginf.  Original txt2tags by Aurelio Marinho Jargas <verde@aurelio.net>.

=head1 LICENSE

BSD

=cut
