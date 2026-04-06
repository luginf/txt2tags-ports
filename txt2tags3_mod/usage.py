# txt2tags - Usage/help text and embedded templates

from .constants import (
    _, re, os, sys, time, textwrap, csv, struct, unicodedata,
    base64, shlex, getopt, importlib, binascii,
    my_name, my_email, my_url, my_version, my_revision,
    USE_I18N, COLOR_DEBUG, BG_LIGHT, HTML_LOWER,
    FLAGS, OPTIONS, ACTIONS, MACROS, SETTINGS,
    NO_TARGET, NO_MULTI_INPUT, CONFIG_KEYWORDS,
    TARGET_NAMES, TARGET_TYPES, TARGETS, TARGETS_LIST, OTHER_TARGETS,
    NOT_LOADED, LOADED,
    AUTOTOC, DFT_TEXT_WIDTH, DFT_SLIDE_WIDTH, DFT_SLIDE_HEIGHT,
    DFT_SLIDE_WEB_WIDTH, DFT_SLIDE_WEB_HEIGHT,
    DFT_SLIDE_PRINT_WIDTH, DFT_SLIDE_PRINT_HEIGHT,
    AA_KEYS, AA_SIMPLE, AA_ADVANCED, AA, AA_QA,
    RST_KEYS, RST_VALUES, RST,
    CSV_KEYS, CSV_VALUES, CSV,
    STDIN, STDOUT, MODULEIN, MODULEOUT,
    ESCCHAR, SEPARATOR, LISTNAMES, LINEBREAK, ESCAPES, LB,
    VERSIONSTR, targets,
)
from . import state

def Usage():
    fmt1 = "%4s  %-15s %s"
    fmt2 = "%4s, %-15s %s"
    return "\n".join(
        [
            "",
            _("Usage: %s [OPTIONS] [infile.t2t ...]") % my_name,
            "",
            fmt1
            % (
                "",
                "--targets",
                _("print a list of all the available targets and exit"),
            ),
            fmt2
            % (
                "-t",
                "--target=TYPE",
                _("set target document type. currently supported:"),
            ),
            fmt1 % ("", "", ", ".join(TARGETS[:8]) + ","),
            fmt1 % ("", "", ", ".join(TARGETS[8:16]) + ","),
            fmt1 % ("", "", ", ".join(TARGETS[16:25]) + ","),
            fmt1 % ("", "", ", ".join(TARGETS[25:34]) + ","),
            fmt1 % ("", "", ", ".join(TARGETS[34:])),
            fmt2
            % (
                "-i",
                "--infile=FILE",
                _("set FILE as the input file name ('-' for STDIN)"),
            ),
            fmt2
            % (
                "-o",
                "--outfile=FILE",
                _("set FILE as the output file name ('-' for STDOUT)"),
            ),
            fmt1
            % (
                "",
                "--encoding=ENC",
                _("inform source file encoding (UTF-8, iso-8859-1, etc)"),
            ),
            fmt1 % ("", "--toc", _("add an automatic Table of Contents to the output")),
            fmt1 % ("", "--toc-title=S", _("set custom TOC title to S")),
            fmt1 % ("", "--toc-level=N", _("set maximum TOC level (depth) to N")),
            fmt1 % ("", "--toc-only", _("print the Table of Contents and exit")),
            fmt2
            % ("-n", "--enum-title", _("enumerate all titles as 1, 1.1, 1.1.1, etc")),
            fmt1
            % ("", "--style=FILE", _("use FILE as the document style (like HTML CSS)")),
            fmt1 % ("", "--css-sugar", _("insert CSS-friendly tags for HTML/XHTML")),
            fmt1
            % (
                "",
                "--css-inside",
                _("insert CSS file contents inside HTML/XHTML headers"),
            ),
            fmt1
            % (
                "",
                "--embed-images",
                _(
                    "embed image data inside HTML, html5, xhtml, RTF, aat and aap documents"
                ),
            ),
            fmt2
            % ("-H", "--no-headers", _("suppress header and footer from the output")),
            fmt2
            % (
                "-T",
                "--template=FILE",
                _("use FILE as the template for the output document"),
            ),
            fmt1
            % (
                "",
                "--mask-email",
                _("hide email from spam robots. x@y.z turns <x (a) y z>"),
            ),
            fmt1
            % (
                "",
                "--width=N",
                _(
                    "set the output's width to N columns (used by aat, aap and aatw targets)"
                ),
            ),
            fmt1
            % (
                "",
                "--height=N",
                _("set the output's height to N rows (used by aap target)"),
            ),
            fmt1
            % (
                "",
                "--chars=S",
                _("set the output's chars to S (used by all aa targets and rst)"),
            ),
            fmt1
            % ("", "", _("aa default " + AA_SIMPLE + " rst default " + RST_VALUES)),
            fmt2 % ("-C", "--config-file=F", _("read configuration from file F")),
            fmt1
            % (
                "",
                "--fix-path",
                _("fix resources path (image, links, CSS) when needed"),
            ),
            fmt1 % ("", "--gui", _("invoke Graphical Tk Interface")),
            fmt2
            % ("-q", "--quiet", _("quiet mode, suppress all output (except errors)")),
            fmt2
            % ("-v", "--verbose", _("print informative messages during conversion")),
            fmt2 % ("-h", "--help", _("print this help information and exit")),
            fmt2 % ("-V", "--version", _("print program version and exit")),
            fmt1
            % ("", "--dump-config", _("print all the configuration found and exit")),
            fmt1
            % (
                "",
                "--dump-source",
                _("print the document source, with includes expanded"),
            ),
            "",
            _("Example:"),
            "     %s -t html --toc %s" % (my_name, _("file.t2t")),
            "",
            _("The 'no-' prefix disables the option:"),
            "     --no-toc, --no-style, --no-enum-title, ...",
            "",
            _("By default, converted output is saved to 'infile.<target>'."),
            _("Use --outfile to force an output file name."),
            _("If  input file is '-', reads from STDIN."),
            _("If output file is '-', dumps output to STDOUT."),
            "",
            my_url,
            "",
        ]
    )


##############################################################################


# Here is all the target's templates
# You may edit them to fit your needs
#  - the %(HEADERn)s strings represent the Header lines
#  - the %(STYLE)s string is changed by --style contents
#  - the %(ENCODING)s string is changed by --encoding contents
#  - if any of the above is empty, the full line is removed
#  - use %% to represent a literal %
#
HEADER_TEMPLATE = {
    "aat": """\
""",
    "csv": """\
""",
    "csvs": """\
""",
    "db": """\
""",
    "rst": """\
""",
    "ods": """\
<?xml version='1.0' encoding='%(ENCODING)s'?>
<office:document xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.1" office:mimetype="application/vnd.oasis.opendocument.spreadsheet"><office:meta><meta:generator>Txt2tags www.txt2tags.org</meta:generator></office:meta><office:automatic-styles><style:style style:name="T1" style:family="text"><style:text-properties fo:font-weight="bold"/></style:style><style:style style:name="ce1" style:family="table-cell"><style:paragraph-properties fo:text-align="center"/></style:style><style:style style:name="ce2" style:family="table-cell"><style:paragraph-properties fo:text-align="end"/></style:style><style:style style:name="ce3" style:family="table-cell"><style:table-cell-properties fo:border="0.06pt solid #000000"/></style:style><style:style style:name="ce4" style:family="table-cell"><style:paragraph-properties fo:text-align="center"/><style:table-cell-properties fo:border="0.06pt solid #000000"/></style:style><style:style style:name="ce5" style:family="table-cell"><style:paragraph-properties fo:text-align="end"/><style:table-cell-properties fo:border="0.06pt solid #000000"/></style:style></office:automatic-styles><office:body><office:spreadsheet>
""",
    "txt": """\
%(HEADER1)s
%(HEADER2)s
%(HEADER3)s
""",
    "txt2t": """\
%(HEADER1)s
%(HEADER2)s
%(HEADER3)s
%%! style    : %(STYLE)s
%%! encoding : %(ENCODING)s
""",
    "sgml": """\
<!doctype linuxdoc system>
<article>
<title>%(HEADER1)s
<author>%(HEADER2)s
<date>%(HEADER3)s
""",
    "html": """\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<HTML>
<HEAD>
<META NAME="generator" CONTENT="http://txt2tags.org">
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=%(ENCODING)s">
<LINK REL="stylesheet" TYPE="text/css" HREF="%(STYLE)s">
<TITLE>%(HEADER1)s</TITLE>
</HEAD><BODY BGCOLOR="white" TEXT="black">
<CENTER>
<H1>%(HEADER1)s</H1>
<FONT SIZE="4"><I>%(HEADER2)s</I></FONT><BR>
<FONT SIZE="4">%(HEADER3)s</FONT>
</CENTER>
""",
    "htmlcss": """\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<HTML>
<HEAD>
<META NAME="generator" CONTENT="http://txt2tags.org">
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=%(ENCODING)s">
<LINK REL="stylesheet" TYPE="text/css" HREF="%(STYLE)s">
<TITLE>%(HEADER1)s</TITLE>
</HEAD>
<BODY>

<DIV CLASS="header" ID="header">
<H1>%(HEADER1)s</H1>
<H2>%(HEADER2)s</H2>
<H3>%(HEADER3)s</H3>
</DIV>
""",
    # HTML5 reference code:
    # https://github.com/h5bp/html5-boilerplate/blob/master/index.html
    # https://github.com/murtaugh/HTML5-Reset/blob/master/index.html
    "html5": """\
<!DOCTYPE html>
<html>
<head>
<meta charset="%(ENCODING)s">
<title>%(HEADER1)s</title>
<meta name="generator" content="http://txt2tags.org">
<link rel="stylesheet" href="%(STYLE)s">
<style>
body{background-color:#fff;color:#000;}
hr{background-color:#000;border:0;color:#000;}
hr.heavy{height:5px;}
hr.light{height:1px;}
img{border:0;display:block;}
img.right{margin:0 0 0 auto;}
img.center{border:0;margin:0 auto;}
table th,table td{padding:4px;}
.center,header{text-align:center;}
table.center {margin-left:auto; margin-right:auto;}
.right{text-align:right;}
.left{text-align:left;}
.tableborder,.tableborder td,.tableborder th{border:1px solid #000;}
.underline{text-decoration:underline;}
</style>
</head>
<body>
<header>
<hgroup>
<h1>%(HEADER1)s</h1>
<h2>%(HEADER2)s</h2>
<h3>%(HEADER3)s</h3>
</hgroup>
</header>
<article>
""",
    "html5css": """\
<!DOCTYPE html>
<html>
<head>
<meta charset="%(ENCODING)s">
<title>%(HEADER1)s</title>
<meta name="generator" content="http://txt2tags.org">
<link rel="stylesheet" href="%(STYLE)s">
</head>
<body>
<header>
<hgroup>
<h1>%(HEADER1)s</h1>
<h2>%(HEADER2)s</h2>
<h3>%(HEADER3)s</h3>
</hgroup>
</header>
<article>
""",
    "htmls": """\
<!DOCTYPE html>
<html>
<head>
<meta charset="%(ENCODING)s">
<title>%(HEADER1)s</title>
<meta name="generator" content="http://txt2tags.org">
<link rel="stylesheet" href="%(STYLE)s">
<style>
body{background-color:#fff;color:#000;}
hr{background-color:#000;border:0;color:#000;}
hr.heavy{height:5px;}
hr.light{height:1px;}
img{border:0;display:block;}
img.right{margin:0 0 0 auto;}
table,img.center{border:0;margin:0 auto;}
table th,table td{padding:4px;}
.center,header{text-align:center;}
.right{text-align:right;}
.tableborder,.tableborder td,.tableborder th{border:1px solid #000;}
.underline{text-decoration:underline;}
</style>
</head>
<body>
<article>
""",
    "xhtml": """\
<?xml version="1.0"
      encoding="%(ENCODING)s"
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>%(HEADER1)s</title>
<meta name="generator" content="http://txt2tags.org" />
<link rel="stylesheet" type="text/css" href="%(STYLE)s" />
</head>
<body bgcolor="white" text="black">
<div align="center">
<h1>%(HEADER1)s</h1>
<h2>%(HEADER2)s</h2>
<h3>%(HEADER3)s</h3>
</div>
""",
    "xhtmlcss": """\
<?xml version="1.0"
      encoding="%(ENCODING)s"
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>%(HEADER1)s</title>
<meta name="generator" content="http://txt2tags.org" />
<link rel="stylesheet" type="text/css" href="%(STYLE)s" />
</head>
<body>

<div class="header" id="header">
<h1>%(HEADER1)s</h1>
<h2>%(HEADER2)s</h2>
<h3>%(HEADER3)s</h3>
</div>
""",
    "xhtmls": """\
<?xml version="1.0"
      encoding="%(ENCODING)s"
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"\
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>%(HEADER1)s</title>
<meta name="generator" content="http://txt2tags.org" />
<link rel="stylesheet" type="text/css" href="%(STYLE)s" />
<style type="text/css">body {background-color:#FFFFFF ; color:#000000}</style>
</head>
<body>
<div style="text-align:center">
<h1>%(HEADER1)s</h1>
<h2>%(HEADER2)s</h2>
<h3>%(HEADER3)s</h3>
</div>
""",
    "xhtmlscss": """\
<?xml version="1.0"
      encoding="%(ENCODING)s"
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"\
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>%(HEADER1)s</title>
<meta name="generator" content="http://txt2tags.org" />
<link rel="stylesheet" type="text/css" href="%(STYLE)s" />
</head>
<body>

<div class="header" id="header">
<h1>%(HEADER1)s</h1>
<h2>%(HEADER2)s</h2>
<h3>%(HEADER3)s</h3>
</div>
""",
    "dbk": """\
<?xml version="1.0"
      encoding="%(ENCODING)s"
?>
<!DOCTYPE article PUBLIC "-//OASIS//DTD DocBook XML V4.5//EN"\
 "docbook/dtd/xml/4.5/docbookx.dtd">
<article lang="en">
  <articleinfo>
    <title>%(HEADER1)s</title>
    <authorgroup>
      <author><othername>%(HEADER2)s</othername></author>
    </authorgroup>
    <date>%(HEADER3)s</date>
  </articleinfo>
""",
    "man": """\
.TH "%(HEADER1)s" 1 "%(HEADER3)s" "%(HEADER2)s"
""",
    "utmac": r"""\
.DT "%(HEADER1)s"
.DA "%(HEADER2)s"
.DI "%(HEADER3)s"
.H1 "%(HEADER1)s"
.H* "%(HEADER2)s"
.
.\\" txt2tags shortcuts
.ds url \\W'\\\\$2'\\\\$1\\W
.ds mail \\W'mailto:\\\\$2'\\\\$1\\W
.ds underl \\Z'\\\\$*'\\v'.25m'\\l"\\w'\\\\$*'u"\\v'-.25m'
.ds strike \\Z'\\\\$*'\\v'-.25m'\\l"\w'\\\\$*'u"\\v'.25m'
.\\"ds underl \\X'SetColor blue'\\\\$1\\X'SetColor black'
.\\"ds strike \\X'SetColor red'\\\\$1\\X'SetColor black'
.\
""",
    # TODO style to <HR>
    "pm6": """\
<PMTags1.0 win><C-COLORTABLE ("Preto" 1 0 0 0)
><@Normal=
  <FONT "Times New Roman"><CCOLOR "Preto"><SIZE 11>
  <HORIZONTAL 100><LETTERSPACE 0><CTRACK 127><CSSIZE 70><C+SIZE 58.3>
  <C-POSITION 33.3><C+POSITION 33.3><P><CBASELINE 0><CNOBREAK 0><CLEADING -0.05>
  <GGRID 0><GLEFT 7.2><GRIGHT 0><GFIRST 0><G+BEFORE 7.2><G+AFTER 0>
  <GALIGNMENT "justify"><GMETHOD "proportional"><G& "ENGLISH">
  <GPAIRS 12><G%% 120><GKNEXT 0><GKWIDOW 0><GKORPHAN 0><GTABS $>
  <GHYPHENATION 2 34 0><GWORDSPACE 75 100 150><GSPACE -5 0 25>
><@Bullet=<@-PARENT "Normal"><FONT "Abadi MT Condensed Light">
  <GLEFT 14.4><G+BEFORE 2.15><G%% 110><GTABS(25.2 l "")>
><@PreFormat=<@-PARENT "Normal"><FONT "Lucida Console"><SIZE 8><CTRACK 0>
  <GLEFT 0><G+BEFORE 0><GALIGNMENT "left"><GWORDSPACE 100 100 100><GSPACE 0 0 0>
><@Title1=<@-PARENT "Normal"><FONT "Arial"><SIZE 14><B>
  <GCONTENTS><GLEFT 0><G+BEFORE 0><GALIGNMENT "left">
><@Title2=<@-PARENT "Title1"><SIZE 12><G+BEFORE 3.6>
><@Title3=<@-PARENT "Title1"><SIZE 10><GLEFT 7.2><G+BEFORE 7.2>
><@Title4=<@-PARENT "Title3">
><@Title5=<@-PARENT "Title3">
><@Quote=<@-PARENT "Normal"><SIZE 10><I>>

%(HEADER1)s
%(HEADER2)s
%(HEADER3)s
""",
    "vimwiki": """\
%%title %(HEADER1)s
## by %(HEADER2)s in %(HEADER3)s
%%toc %(HEADER1)s
""",
    "mgp": """\
#!/usr/X11R6/bin/mgp -t 90
%%deffont "normal"    xfont  "utopia-medium-r", charset "iso8859-1"
%%deffont "normal-i"  xfont  "utopia-medium-i", charset "iso8859-1"
%%deffont "normal-b"  xfont  "utopia-bold-r"  , charset "iso8859-1"
%%deffont "normal-bi" xfont  "utopia-bold-i"  , charset "iso8859-1"
%%deffont "mono"      xfont "courier-medium-r", charset "iso8859-1"
%%default 1 size 5
%%default 2 size 8, fore "yellow", font "normal-b", center
%%default 3 size 5, fore "white",  font "normal", left, prefix "  "
%%tab 1 size 4, vgap 30, prefix "     ", icon arc "red" 40, leftfill
%%tab 2 prefix "            ", icon arc "orange" 40, leftfill
%%tab 3 prefix "                   ", icon arc "brown" 40, leftfill
%%tab 4 prefix "                          ", icon arc "darkmagenta" 40, leftfill
%%tab 5 prefix "                                ", icon arc "magenta" 40, leftfill
%%%%------------------------- end of headers -----------------------------
%%page





%%size 10, center, fore "yellow"
%(HEADER1)s

%%font "normal-i", size 6, fore "white", center
%(HEADER2)s

%%font "mono", size 7, center
%(HEADER3)s
""",
    "moin": """\
'''%(HEADER1)s'''

''%(HEADER2)s''

%(HEADER3)s
""",
    "gwiki": """\
*%(HEADER1)s*

%(HEADER2)s

_%(HEADER3)s_
""",
    "adoc": """\
= %(HEADER1)s
%(HEADER2)s
%(HEADER3)s
""",
    "doku": """\
===== %(HEADER1)s =====

**//%(HEADER2)s//**

//%(HEADER3)s//
""",
    "pmw": """\
(:Title %(HEADER1)s:)

(:Description %(HEADER2)s:)

(:Summary %(HEADER3)s:)
""",
    "wiki": """\
'''%(HEADER1)s'''

%(HEADER2)s

''%(HEADER3)s''
""",
    "red": """\
h1. %(HEADER1)s

Author: %(HEADER2)s
Date: %(HEADER3)s
""",
    "tex": r"""\documentclass{article}
\usepackage{graphicx}
\usepackage{paralist} %% needed for compact lists
\usepackage[normalem]{ulem} %% needed by strike
\usepackage[urlcolor=blue,colorlinks=true]{hyperref}
\usepackage[%(ENCODING)s]{inputenc}  %% char encoding
\usepackage{%(STYLE)s}  %% user defined

\title{%(HEADER1)s}
\author{%(HEADER2)s}
\begin{document}
\date{%(HEADER3)s}
\maketitle
\clearpage
""",
    "texs": r"""\documentclass{article}
\usepackage{graphicx}
\usepackage[urlcolor=black,colorlinks=true]{hyperref}
\usepackage[%(ENCODING)s]{inputenc}  %% char encoding
\usepackage{%(STYLE)s}  %% user defined

\begin{document}
""",
    "lout": """\
@SysInclude { doc }
@SysInclude { tbl }
@Document
  @InitialFont { Times Base 12p }  # Times, Courier, Helvetica, ...
  @PageOrientation { Portrait }    # Portrait, Landscape
  @ColumnNumber { 1 }              # Number of columns (2, 3, ...)
  @PageHeaders { Simple }          # None, Simple, Titles, NoTitles
  @InitialLanguage { English }     # German, French, Portuguese, ...
  @OptimizePages { Yes }           # Yes/No smart page break feature
//
@Text @Begin
@Display @Heading { %(HEADER1)s }
@Display @I { %(HEADER2)s }
@Display { %(HEADER3)s }
#@NP                               # Break page after Headers
""",
    # @SysInclude { tbl }                   # Tables support
    # setup: @MakeContents { Yes }          # show TOC
    # setup: @SectionGap                    # break page at each section
    "creole": """\
%(HEADER1)s
%(HEADER2)s
%(HEADER3)s
""",
    "md": """\
%(HEADER1)s
%(HEADER2)s
%(HEADER3)s
""",
    "gmi": """\
# %(HEADER1)s
# %(HEADER2)s
# %(HEADER3)s
""",
    "bbcode": """\
%(HEADER1)s
%(HEADER2)s
%(HEADER3)s
""",
    "spip": """\
{{{%(HEADER1)s}}}

{{%(HEADER2)s}}

{%(HEADER3)s}

""",
    "rtf": r"""{\rtf1\ansi\ansicpg1252\deff0
{\fonttbl
{\f0\froman Times;}
{\f1\fswiss Arial;}
{\f2\fmodern Courier;}
}
{\colortbl;\red0\green0\blue255;}
{\stylesheet
{\s1\sbasedon222\snext1\f0\fs24\cf0 Normal;}
{\s2\sbasedon1\snext2{\*\txttags paragraph}\f0\fs24\qj\sb0\sa0\sl480\slmult1\li0\ri0\fi360 Body Text;}
{\s3\sbasedon2\snext3{\*\txttags verbatim}\f2\fs20\ql\sb0\sa240\sl240\slmult1\li720\ri720\fi0 Verbatim;}
{\s4\sbasedon2\snext4{\*\txttags quote}\f0\fs24\qj\sb0\sa0\sl480\slmult1\li720\ri720\fi0 Block Quote;}
{\s10\sbasedon1\snext10\keepn{\*\txttags maintitle}\f1\fs24\qc\sb0\sa0\sl480\slmult1\li0\ri0\fi0 Title;}
{\s11\sbasedon1\snext2\keepn{\*\txttags title1}\f1\fs24\qc\sb240\sa240\sl480\slmult1\li0\ri0\fi0\b Heading 1;}
{\s12\sbasedon11\snext2\keepn{\*\txttags title2}\f1\fs24\ql\sb240\sa240\sl480\slmult1\li0\ri0\fi0\b Heading 2;}
{\s13\sbasedon11\snext2\keepn{\*\txttags title3}\f1\fs24\ql\sb240\sa240\sl480\slmult1\li360\ri0\fi0\b Heading 3;}
{\s14\sbasedon11\snext2\keepn{\*\txttags title4}\f1\fs24\ql\sb240\sa240\sl480\slmult1\li360\ri0\fi0\b\i Heading 4;}
{\s15\sbasedon11\snext2\keepn{\*\txttags title5}\f1\fs24\ql\sb240\sa240\sl480\slmult1\li360\ri0\fi0\i Heading 5;}
{\s21\sbasedon2\snext21{\*\txttags list}\f0\fs24\qj\sb0\sa0\sl480\slmult1{\*\txttags list indent}\li720\ri0\fi-360 List;}
}
{\*\listtable
{\list\listtemplateid1
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li720\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li1080\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li1440\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li1800\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li2160\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li2520\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li2880\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li3240\ri0\fi-360}
{\listlevel\levelnfc23\leveljc0\levelstartat1\levelfollow0{\leveltext \'01\'95;}{\levelnumbers;}{\*\txttags list indent}\li3600\ri0\fi-360}
\listid1}
{\list\listtemplateid2
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'00.;}{\levelnumbers\'01;}{\*\txttags list indent}\li720\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'01.;}{\levelnumbers\'01;}{\*\txttags list indent}\li1080\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'02.;}{\levelnumbers\'01;}{\*\txttags list indent}\li1440\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'03.;}{\levelnumbers\'01;}{\*\txttags list indent}\li1800\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'04.;}{\levelnumbers\'01;}{\*\txttags list indent}\li2160\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'05.;}{\levelnumbers\'01;}{\*\txttags list indent}\li2520\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'06.;}{\levelnumbers\'01;}{\*\txttags list indent}\li2880\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'07.;}{\levelnumbers\'01;}{\*\txttags list indent}\li3240\ri0\fi-360}
{\listlevel\levelnfc0\leveljc0\levelstartat1\levelfollow0{\leveltext \'02\'08.;}{\levelnumbers\'01;}{\*\txttags list indent}\li3600\ri0\fi-360}
\listid2}
{\list\listtemplateid3
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'02\'00.;}{\levelnumbers\'01;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'04\'00.\'01.;}{\levelnumbers\'01\'03;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'06\'00.\'01.\'02.;}{\levelnumbers\'01\'03\'05;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'08\'00.\'01.\'02.\'03.;}{\levelnumbers\'01\'03\'05\'07;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'10\'00.\'01.\'02.\'03.\'04.;}{\levelnumbers\'01\'03\'05\'07\'09;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'02\'05.;}{\levelnumbers\'01;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'02\'06.;}{\levelnumbers\'01;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow1{\leveltext \'02\'07.;}{\levelnumbers\'01;}}
{\listlevel\levelnfc0\leveljc1\levelstartat1\levelfollow0{\leveltext \'02\'08.;}{\levelnumbers\'01;}}
\listid3}
}
{\listoverridetable
{\listoverride\listid1\listoverridecount0\ls1}
{\listoverride\listid2\listoverridecount0\ls2}
{\listoverride\listid3\listoverridecount0\ls3}
}
{\info
{\title %(HEADER1)s }
{\author %(HEADER2)s }
}
\deflang1033\widowctrl\hyphauto\uc1\fromtext
\paperw12240\paperh15840
\margl1440\margr1440\margt1440\margb1440
\sectd
{\header\pard\qr\plain\f0 Page \chpgn\par}
{\pard\plain\s10\keepn{\*\txttags maintitle}\f1\fs24\qc\sb2880\sa0\sl480\slmult1\li0\ri0\fi0 %(HEADER1)s\par}
{\pard\plain\s10\keepn{\*\txttags maintitle}\f1\fs24\qc\sb0\sa0\sl480\slmult1\li0\ri0\fi0 %(HEADER2)s\par}
{\pard\plain\s10\keepn{\*\txttags maintitle}\f1\fs24\qc\sb0\sa0\sl480\slmult1\li0\ri0\fi0 %(HEADER3)s\par}
""",
    "wp": """\
%(HEADER1)s
%(HEADER2)s
%(HEADER3)s
""",
    "wpcss": """\
%(HEADER1)s
%(HEADER2)s
%(HEADER3)s
""",
    "tml": """\
---+!! %(HEADER1)s
*%(HEADER2)s* %%BR%% __%(HEADER3)s__
""",
    ## MOM ##
    #
    # "mom" is a sort of "LaTeX" for groff and has a lot of macro
    # commands and variables to customize for specific needs.
    # These few lines of commands are sufficient anyway for a good
    # postscript typesetted document (and so also pdf): the author
    # of "mom" is a professional typographer so the typesetting
    # defaults are pleasant and sane.  See mom's author site:
    # http://www.schaffter.ca/mom/mom-01.html that's a good
    # example of documentation too!
    # NB: \# are commented lines in groff.
    # I put here a lot of options, commented or not, to let you
    # see the possibilities but there many more...
    # NB: use "-k" option for groff if input/output is UTF-8
    #
    # usage: groff -k -m mom sample.mom > sample.ps
    #
    "mom": r"""\
\# Cover and title
.TITLE "%(HEADER1)s"
.AUTHOR "%(HEADER2)s"
\#.DOCTITLE \" ONLY to collate different files (sections, chapters etc.)
.SUBTITLE "%(HEADER3)s"
\#
\# printstyle: typeset or typewrite it's MANDATORY!
.PRINTSTYLE TYPESET
\#.PRINTSTYLE TYPEWRITE
\#
\# doctype: default, chapter, user-defined, letter (commented is "default")
\#.DOCTYPE DEFAULT
\#
\# copystyle: draft or final
.COPYSTYLE FINAL
\#.COPYSTYLE DRAFT
\#
\# Default values for some strings
\# They're valid in every printstyle or copystyle
\# Here are MY defaults (italian)
\# For a more general use I think they should be groff commented
\#
\#.CHAPTER_STRING "Capitolo"
\#.ATTRIBUTE_STRING "di"
\#.TOC_HEADER_STRING "Indice"
\#.ENDNOTE_TITLE "Note"
\#
\# section break char "#" for 1 time (LINEBREAK)
\#.LINEBREAK_CHAR # 1
\# a null end string
.FINIS_STRING ""
\#
\# Typesetting values
\# These are all MY preferences! Comment out for default.
\#
.PAPER A4
\# Left margin (c=centimeters)
\#.L_MARGIN 2.8c
\# Length of line (it's for 62 chars a line for point size 12 in typewrite style)
\#.LL 15.75c
\# Palatino groff font, better than Times for reading. IMHO
.FAMILY P
.PT_SIZE 12
\# line spacing
.LS 18
\# left aligned (mom macro defaults to "both aligned")
.QUAD L
\# No hyphenation
.HY OFF
\# Header and footer sizes
.HEADER_SIZE -1
.FOOTER_SIZE -1
.PAGENUM_SIZE -2
\#
\# Other options
\#
\# Indent space for "quote" and "blockquote" (defaults are good too!)
\#.QUOTE_INDENT 2
\#.BLOCKQUOTE_INDENT 2
\#
\# Footnotes
\#
\# Next gives you superscript numbers (use STAR for symbols, it's default)
\# use additional argument NO_SUPERSCRIPT for typewrite printstyle
\#.FOOTNOTE_MARKER_STYLE NUMBER
\# Cover title at about 1/3 from top
\#.DOCHEADER_ADVANCE 7.5c
\#
\# Double quotes italian style! aka << and >> It works only for "typeset" printstyle
\#.SMARTQUOTES IT
\# Next cmd is MANDATORY.
.START
""",
}

for target in TARGETS_LIST:
    HEADER_TEMPLATE[target] = getattr(getattr(targets, target), "HEADER", "")
    HEADER_TEMPLATE[target + "css"] = getattr(getattr(targets, target), "HEADERCSS", "")

# Generated files are easier to edit with the DZSlides engine at the end, but breaks W3C validator.
AAPW_FOOT = r"""\
</html>
<style>
  html { background-color: black; }
  body { background-color: white; }
  /* A section is a slide. It's size is 800x600, and this will never change */
  section {
      font-family: monospace;
      font-size: 18px;
  }

/*  footer {
    position: absolute;
    bottom: 10px;
    right: 20px;
  } */

  /* Transition effect */
  /* Feel free to change the transition effect for original
     animations. See here:
     https://developer.mozilla.org/en/CSS/CSS_transitions
     How to use CSS3 Transitions: */
  section {
      -moz-transition: top 400ms linear 0s;
      -webkit-transition: top 400ms linear 0s;
      -ms-transition: top 400ms linear 0s;
      transition: top 400ms linear 0s;
  }

  /* Before */
  section { left: -150%; }
  /* Now */
  section[aria-selected] { left: 0; }
  /* After */
  section[aria-selected] ~ section { left: +150%; }

  /* Incremental elements */

  /* By default, visible */
  .incremental > * { opacity: 1; }

  /* The current item */
  .incremental > *[aria-selected] { color: red; opacity: 1; }

  /* The items to-be-selected */
  .incremental > *[aria-selected] ~ * { opacity: 0.2; }

</style>

 <!-- {{{{ dzslides core
#
#
#     __  __  __       .  __   ___  __
#    |  \  / /__` |    | |  \ |__  /__`
#    |__/ /_ .__/ |___ | |__/ |___ .__/ core :(
#
#
# The following block of code is not supposed to be edited.
# But if you want to change the behavior of these slides,
# feel free to hack it!
#
-->

<!-- Default Style -->
<style>
  * { margin: 0; padding: 0; }
  details { display: none; }
  body {
    width: 800px; height: 600px;
    margin-left: -400px; margin-top: -300px;
    position: absolute; top: 50%; left: 50%;
    overflow: hidden;
  }
  section {
    position: absolute;
    pointer-events: none;
    width: 100%; height: 100%;
  }
  section[aria-selected] { pointer-events: auto; }
  html { overflow: hidden; }
  body { display: none; }
  body.loaded { display: block; }
  .incremental {visibility: hidden; }
  .incremental[active] {visibility: visible; }
</style>

<script>
  var Dz = {
    remoteWindows: [],
    idx: -1,
    step: 0,
    slides: null,
    params: {
      autoplay: "1"
    }
  };

  Dz.init = function() {
    document.body.className = "loaded";
    this.slides = $$("body > section");
    this.setupParams();
    this.onhashchange();
    this.setupTouchEvents();
    this.onresize();
  }
  
  Dz.setupParams = function() {
    var p = window.location.search.substr(1).split('&');
    p.forEach(function(e, i, a) {
      var keyVal = e.split('=');
      Dz.params[keyVal[0]] = decodeURIComponent(keyVal[1]);
    });
  }

  Dz.onkeydown = function(aEvent) {
    // Don't intercept keyboard shortcuts
    if (aEvent.altKey
      || aEvent.ctrlKey
      || aEvent.metaKey
      || aEvent.shiftKey) {
      return;
    }
    if ( aEvent.keyCode == 37 // left arrow
      || aEvent.keyCode == 38 // up arrow
      || aEvent.keyCode == 33 // page up
    ) {
      aEvent.preventDefault();
      this.back();
    }
    if ( aEvent.keyCode == 39 // right arrow
      || aEvent.keyCode == 40 // down arrow
      || aEvent.keyCode == 34 // page down
    ) {
      aEvent.preventDefault();
      this.forward();
    }
    if (aEvent.keyCode == 35) { // end
      aEvent.preventDefault();
      this.goEnd();
    }
    if (aEvent.keyCode == 36) { // home
      aEvent.preventDefault();
      this.goStart();
    }
    if (aEvent.keyCode == 32) { // space
      aEvent.preventDefault();
      this.toggleContent();
    }
  }

  /* Touch Events */

  Dz.setupTouchEvents = function() {
    var orgX, newX;
    var tracking = false;

    var db = document.body;
    db.addEventListener("touchstart", start.bind(this), false);
    db.addEventListener("touchmove", move.bind(this), false);

    function start(aEvent) {
      aEvent.preventDefault();
      tracking = true;
      orgX = aEvent.changedTouches[0].pageX;
    }

    function move(aEvent) {
      if (!tracking) return;
      newX = aEvent.changedTouches[0].pageX;
      if (orgX - newX > 100) {
        tracking = false;
        this.forward();
      } else {
        if (orgX - newX < -100) {
          tracking = false;
          this.back();
        }
      }
    }
  }

  /* Adapt the size of the slides to the window */

  Dz.onresize = function() {
    var db = document.body;
    var sx = db.clientWidth / window.innerWidth;
    var sy = db.clientHeight / window.innerHeight;
    var transform = "scale(" + (1/Math.max(sx, sy)) + ")";

    db.style.MozTransform = transform;
    db.style.WebkitTransform = transform;
    db.style.OTransform = transform;
    db.style.msTransform = transform;
    db.style.transform = transform;
  }


  Dz.getDetails = function(aIdx) {
    var s = $("section:nth-of-type(" + aIdx + ")");
    var d = s.$("details");
    return d ? d.innerHTML : "";
  }

  Dz.onmessage = function(aEvent) {
    var argv = aEvent.data.split(" "), argc = argv.length;
    argv.forEach(function(e, i, a) { a[i] = decodeURIComponent(e) });
    var win = aEvent.source;
    if (argv[0] === "REGISTER" && argc === 1) {
      this.remoteWindows.push(win);
      this.postMsg(win, "REGISTERED", document.title, this.slides.length);
      this.postMsg(win, "CURSOR", this.idx + "." + this.step);
      return;
    }
    if (argv[0] === "BACK" && argc === 1)
      this.back();
    if (argv[0] === "FORWARD" && argc === 1)
      this.forward();
    if (argv[0] === "START" && argc === 1)
      this.goStart();
    if (argv[0] === "END" && argc === 1)
      this.goEnd();
    if (argv[0] === "TOGGLE_CONTENT" && argc === 1)
      this.toggleContent();
    if (argv[0] === "SET_CURSOR" && argc === 2)
      window.location.hash = "#" + argv[1];
    if (argv[0] === "GET_CURSOR" && argc === 1)
      this.postMsg(win, "CURSOR", this.idx + "." + this.step);
    if (argv[0] === "GET_NOTES" && argc === 1)
      this.postMsg(win, "NOTES", this.getDetails(this.idx));
  }

  Dz.toggleContent = function() {
    // If a Video is present in this new slide, play it.
    // If a Video is present in the previous slide, stop it.
    var s = $("section[aria-selected]");
    if (s) {
      var video = s.$("video");
      if (video) {
        if (video.ended || video.paused) {
          video.play();
        } else {
          video.pause();
        }
      }
    }
  }

  Dz.setCursor = function(aIdx, aStep) {
    // If the user change the slide number in the URL bar, jump
    // to this slide.
    aStep = (aStep != 0 && typeof aStep !== "undefined") ? "." + aStep : ".0";
    window.location.hash = "#" + aIdx + aStep;
  }

  Dz.onhashchange = function() {
    var cursor = window.location.hash.split("#"),
        newidx = 1,
        newstep = 0;
    if (cursor.length == 2) {
      newidx = ~~cursor[1].split(".")[0];
      newstep = ~~cursor[1].split(".")[1];
      if (newstep > Dz.slides[newidx - 1].$$('.incremental > *').length) {
        newstep = 0;
        newidx++;
      }
    }
    if (newidx != this.idx) {
      this.setSlide(newidx);
    }
    if (newstep != this.step) {
      this.setIncremental(newstep);
    }
    for (var i = 0; i < this.remoteWindows.length; i++) {
      this.postMsg(this.remoteWindows[i], "CURSOR", this.idx + "." + this.step);
    }
  }

  Dz.back = function() {
    if (this.idx == 1 && this.step == 0) {
      return;
    }
    if (this.step == 0) {
      this.setCursor(this.idx - 1,
                     this.slides[this.idx - 2].$$('.incremental > *').length);
    } else {
      this.setCursor(this.idx, this.step - 1);
    }
  }

  Dz.forward = function() {
    if (this.idx >= this.slides.length &&
        this.step >= this.slides[this.idx - 1].$$('.incremental > *').length) {
        return;
    }
    if (this.step >= this.slides[this.idx - 1].$$('.incremental > *').length) {
      this.setCursor(this.idx + 1, 0);
    } else {
      this.setCursor(this.idx, this.step + 1);
    }
  }

  Dz.goStart = function() {
    this.setCursor(1, 0);
  }

  Dz.goEnd = function() {
    var lastIdx = this.slides.length;
    var lastStep = this.slides[lastIdx - 1].$$('.incremental > *').length;
    this.setCursor(lastIdx, lastStep);
  }

  Dz.setSlide = function(aIdx) {
    this.idx = aIdx;
    var old = $("section[aria-selected]");
    var next = $("section:nth-of-type("+ this.idx +")");
    if (old) {
      old.removeAttribute("aria-selected");
      var video = old.$("video");
      if (video) {
        video.pause();
      }
    }
    if (next) {
      next.setAttribute("aria-selected", "true");
      var video = next.$("video");
      if (video && !!+this.params.autoplay) {
        video.play();
      }
    } else {
      // That should not happen
      this.idx = -1;
      // console.warn("Slide doesn't exist.");
    }
  }

  Dz.setIncremental = function(aStep) {
    this.step = aStep;
    var old = this.slides[this.idx - 1].$('.incremental > *[aria-selected]');
    if (old) {
      old.removeAttribute('aria-selected');
    }
    var incrementals = this.slides[this.idx - 1].$$('.incremental');
    if (this.step <= 0) {
      incrementals.forEach(function(aNode) {
        aNode.removeAttribute('active');
      });
      return;
    }
    var next = this.slides[this.idx - 1].$$('.incremental > *')[this.step - 1];
    if (next) {
      next.setAttribute('aria-selected', true);
      next.parentNode.setAttribute('active', true);
      var found = false;
      incrementals.forEach(function(aNode) {
        if (aNode != next.parentNode)
          if (found)
            aNode.removeAttribute('active');
          else
            aNode.setAttribute('active', true);
        else
          found = true;
      });
    } else {
      setCursor(this.idx, 0);
    }
    return next;
  }
  
  Dz.postMsg = function(aWin, aMsg) { // [arg0, [arg1...]]
    aMsg = [aMsg];
    for (var i = 2; i < arguments.length; i++)
      aMsg.push(encodeURIComponent(arguments[i]));
    aWin.postMessage(aMsg.join(" "), "*");
  }

  function init() {
    Dz.init();
    window.onkeydown = Dz.onkeydown.bind(Dz);
    window.onresize = Dz.onresize.bind(Dz);
    window.onhashchange = Dz.onhashchange.bind(Dz);
    window.onmessage = Dz.onmessage.bind(Dz);
  }

  window.onload = init;
</script>


<script> // Helpers
  if (!Function.prototype.bind) {
    Function.prototype.bind = function (oThis) {

      // closest thing possible to the ECMAScript 5 internal IsCallable
      // function
      if (typeof this !== "function")
      throw new TypeError(
        "Function.prototype.bind - what is trying to be fBound is not callable"
      );

      var aArgs = Array.prototype.slice.call(arguments, 1),
          fToBind = this,
          fNOP = function () {},
          fBound = function () {
            return fToBind.apply( this instanceof fNOP ? this : oThis || window,
                   aArgs.concat(Array.prototype.slice.call(arguments)));
          };

      fNOP.prototype = this.prototype;
      fBound.prototype = new fNOP();

      return fBound;
    };
  }

  var $ = (HTMLElement.prototype.$ = function(aQuery) {
    return this.querySelector(aQuery);
  }).bind(document);

  var $$ = (HTMLElement.prototype.$$ = function(aQuery) {
    return this.querySelectorAll(aQuery);
  }).bind(document);

  NodeList.prototype.forEach = function(fun) {
    if (typeof fun !== "function") throw new TypeError();
    for (var i = 0; i < this.length; i++) {
      fun.call(this, this[i]);
    }
  }

</script>
"""

##############################################################################


