# txt2tags - constants and configuration
# Extracted from the monolithic txt2tags3 script.

# User config (1=ON, 0=OFF)

USE_I18N = 1  # use gettext for i18ned messages?        (default is 1)
COLOR_DEBUG = 1  # show debug messages in colors?          (default is 1)
BG_LIGHT = 0  # your terminal background color is light (default is 0)
HTML_LOWER = 0  # use lowercased HTML tags instead upper? (default is 0)

import re
import os
import sys
import locale
import time
import getopt
import textwrap
import csv
import struct
import unicodedata
import base64
import shlex
import importlib
import binascii

try:
    import targets
except ImportError:
    targets = None
    TARGETS_LIST = []

# Program information
my_url = "http://txt2tags.org"
my_name = "txt2tags"
my_email = "verde@aurelio.net"
my_revision = "$Revision$"  # automatic, from SVN
my_version = "2.6"

my_version = "%s.%s" % (my_version, re.sub(r"\D", "", my_revision))

# i18n
if USE_I18N:
    try:
        import gettext
        cat = gettext.Catalog("txt2tags", localedir="/usr/share/locale/")
        _ = cat.gettext
    except:
        def _(x):
            return x
else:
    def _(x):
        return x

#
FLAGS = {
    "headers": 1,
    "enum-title": 0,
    "mask-email": 0,
    "toc-only": 0,
    "toc": 0,
    "qa": 0,
    "rc": 1,
    "css-sugar": 0,
    "css-inside": 0,
    "quiet": 0,
    "slides": 0,
    "spread": 0,
    "web": 0,
    "print": 0,
    "fix-path": 0,
    "embed-images": 0,
}
OPTIONS = {
    "target": "",
    "toc-level": 3,
    "toc-title": "",
    "style": "",
    "infile": "",
    "outfile": "",
    "encoding": "",
    "config-file": "",
    "split": 0,
    "lang": "",
    "width": 0,
    "height": 0,
    "chars": "",
    "show-config-value": "",
    "template": "",
    "dirname": "",  # internal use only
}
ACTIONS = {
    "help": 0,
    "version": 0,
    "gui": 0,
    "verbose": 0,
    "debug": 0,
    "dump-config": 0,
    "dump-source": 0,
    "targets": 0,
}
MACROS = {
    # date
    "date": "%Y-%m-%d",
    "mtime": "%Y%m%d",
    # files
    "infile": "%f",
    "currentfile": "%f",
    "outfile": "%f",
    # app
    "appurl": "",
    "appname": "",
    "appversion": "",
    # conversion
    "target": "",
    "cmdline": "",
    "encoding": "",
    # header
    "header1": "",
    "header2": "",
    "header3": "",
    # Creative Commons license
    "cc": "",
}
SETTINGS = {}  # for future use
NO_TARGET = [
    "help",
    "version",
    "gui",
    "toc-only",
    "dump-config",
    "dump-source",
    "targets",
]
NO_MULTI_INPUT = ["gui", "dump-config", "dump-source"]
CONFIG_KEYWORDS = [
    "cc",
    "target",
    "encoding",
    "style",
    "stylepath",  # internal use only
    "options",
    "preproc",
    "postproc",
    "postvoodoo",
    "guicolors",
]


TARGET_NAMES = {
    "txt2t": _("Txt2tags document"),
    "html": _("HTML page"),
    "html5": _("HTML5 page"),
    "xhtml": _("XHTML page"),
    "xhtmls": _("XHTML Strict page"),
    "htmls": _("HTML Spreadsheet"),
    "sgml": _("SGML document"),
    "dbk": _("DocBook document"),
    "tex": _("LaTeX document"),
    "texs": _("LaTeX Spreadsheet"),
    "lout": _("Lout document"),
    "man": _("UNIX Manual page"),
    "utmac": _("Utmac (utroff) document"),
    "mgp": _("MagicPoint presentation"),
    "wiki": _("Wikipedia page"),
    "gwiki": _("Google Wiki page"),
    "doku": _("DokuWiki page"),
    "pmw": _("PmWiki page"),
    "moin": _("MoinMoin page"),
    "pm6": _("PageMaker document"),
    "txt": _("Plain Text"),
    "aat": _("ASCII Art Text"),
    "aap": _("ASCII Art Presentation"),
    "aas": _("ASCII Art Spreadsheet"),
    "aatw": _("ASCII Art Text Web"),
    "aapw": _("ASCII Art Presentation Web"),
    "aasw": _("ASCII Art Spreadsheet Web"),
    "aapp": _("ASCII Art Presentation Print"),
    "db": _("SQLite database"),
    "adoc": _("AsciiDoc document"),
    "rst": _("ReStructuredText document"),
    "csv": _("CSV table"),
    "csvs": _("CSV Spreadsheet"),
    "ods": _("Open Document Spreadsheet"),
    "creole": _("Creole 1.0 document"),
    "md": _("Markdown document"),
    "gmi": _("Gemtext document"),
    "bbcode": _("BBCode document"),
    "red": _("Redmine Wiki page"),
    "spip": _("SPIP article"),
    "rtf": _("RTF document"),
    "wp": _("WordPress post"),
    "tml": _("Foswiki or TWiki page"),
    "mom": _("MOM groff macro"),
    "vimwiki": _("Vimwiki document"),
}


TARGET_TYPES = {
    "html": (
        _("HTML"),
        ["html", "html5", "xhtml", "xhtmls", "htmls", "aatw", "aapw", "aasw", "wp"],
    ),
    "wiki": (
        _("WIKI"),
        [
            "txt2t",
            "wiki",
            "gwiki",
            "doku",
            "pmw",
            "moin",
            "adoc",
            "rst",
            "creole",
            "gmi",
            "md",
            "bbcode",
            "red",
            "spip",
            "tml",
            "vimwiki",
        ],
    ),
    "office": (
        _("OFFICE"),
        [
            "sgml",
            "dbk",
            "tex",
            "texs",
            "lout",
            "mgp",
            "pm6",
            "csv",
            "csvs",
            "ods",
            "rtf",
            "db",
            "mom",
            "utmac",
        ],
    ),
    "text": (_("TEXT"), ["man", "txt", "aat", "aap", "aas", "aapp"]),
}

if targets:
    TARGETS_LIST = targets.TARGETS_LIST

OTHER_TARGETS = []

NOT_LOADED = []
LOADED = []
for target in TARGETS_LIST:
    if target not in TARGET_NAMES:
        LOADED.append(target)
        TARGET_NAMES[target] = getattr(
            getattr(targets, target), "NAME", target.capitalize() + " target"
        )
        try:
            TARGET_TYPES[getattr(targets, target).TYPE][1].append(target)
        except:
            OTHER_TARGETS.append(target)
    else:
        NOT_LOADED.append(target)
TARGETS_LIST = LOADED

TARGETS = list(TARGET_NAMES.keys())
TARGETS.sort()

DEBUG = 0  # do not edit here, please use --debug
VERBOSE = 0  # do not edit here, please use -v, -vv or -vvv
QUIET = 0  # do not edit here, please use --quiet
GUI = 0  # do not edit here, please use --gui
AUTOTOC = 1  # do not edit here, please use --no-toc or %%toc

DFT_TEXT_WIDTH = 72  # do not edit here, please use --width
DFT_SLIDE_WIDTH = 80  # do not edit here, please use --width
DFT_SLIDE_HEIGHT = 24  # do not edit here, please use --height
DFT_SLIDE_WEB_WIDTH = 73  # do not edit here, please use --width
DFT_SLIDE_WEB_HEIGHT = 27  # do not edit here, please use --height
DFT_SLIDE_PRINT_WIDTH = 112  # do not edit here, please use --width
DFT_SLIDE_PRINT_HEIGHT = 46  # do not edit here, please use --height

# ASCII Art config
AA_KEYS = "tlcorner trcorner blcorner brcorner tcross bcross lcross rcross lhhead hheadcross rhhead headerscross tvhead vheadcross bvhead cross border side bar1 bar2 level2 level3 level4 level5 bullet hhead vhead quote".split()
AA_SIMPLE = '+-|-==-^"-=$8'  # do not edit here, please use --chars
AA_ADVANCED = "+++++++++++++++" + AA_SIMPLE  # do not edit here, please use --chars
AA = dict(list(zip(AA_KEYS, AA_ADVANCED)))
AA_COUNT = 0
AA_PW_TOC = {}
AA_IMG = 0
AA_TITLE = ""
AA_MARKS = []

AA_QA = r"""\
       ________
   /#**TXT2TAGS**#\\
 /#####/      \####CC\\
/###/            \#BY#|
^-^               |NC#|
                  /SA#|
               /#####/
            /#####/
          /####/
         /###/
        |###|
        |###|
         \o/

         ___
        F2.7G
         (C)\
""".split("\n")

# ReStructuredText config
# http://docs.python.org/release/2.7/documenting/rest.html#sections
RST_KEYS = "title level1 level2 level3 level4 level5 bar1 bullet".split()
RST_VALUES = '#*=-^"--'  # do not edit here, please use --chars
RST = dict(list(zip(RST_KEYS, RST_VALUES)))

CSV_KEYS = "separator quotechar".split()
CSV_VALUES = ","  # do not edit here, please use --chars
CSV = dict(list(zip(CSV_KEYS, CSV_VALUES)))

RC_RAW = []
CMDLINE_RAW = []
CONF = {}
BLOCK = None
TITLE = None
regex = {}
TAGS = {}
rules = {}
MAILING = ""

# Gui globals
Tkinter = tkFileDialog = tkMessageBox = None

lang = "english"
TARGET = ""

file_dict = {}
STDIN = STDOUT = "-"
MODULEIN = MODULEOUT = "-module-"
ESCCHAR = "\x00"
SEPARATOR = "\x01"
LISTNAMES = {"-": "list", "+": "numlist", ":": "deflist"}
LINEBREAK = {"default": "\n", "win": "\r\n", "mac": "\r"}

ESCAPES = {
    "pm6": [(ESCCHAR + "<", "vvvvPm6Bracketvvvv", r"<\#92><")],
    "man": [("-", "vvvvManDashvvvv", r"\-")],
    "sgml": [("[", "vvvvSgmlBracketvvvv", "&lsqb;")],
    "lout": [("/", "vvvvLoutSlashvvvv", '"/"')],
    "tex": [
        ("_", "vvvvTexUndervvvv", r"\_"),
        ("\\", "vvvvTexBackslashvvvv", r"$\backslash$"),
    ],
    "rtf": [("\t", "vvvvRtfTabvvvv", ESCCHAR + "tab")],
}

for target in TARGETS_LIST:
    ESCAPES[target] = getattr(getattr(targets, target), "ESCAPES", [])

# Platform specific settings
LB = LINEBREAK.get(sys.platform[:3]) or LINEBREAK["default"]

VERSIONSTR = _("%s version %s <%s>") % (my_name, my_version, my_url)


