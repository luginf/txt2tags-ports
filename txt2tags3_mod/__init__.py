# txt2tags package
# Splits the original monolithic txt2tags3 script into modules:
#
#   constants.py  - immutable configuration, program info, i18n
#   state.py      - mutable runtime globals (CONF, TAGS, regex, ...)
#   tags.py       - getTags(config)
#   rules.py      - getRules(config)
#   regexes.py    - getRegexes()
#   aa.py         - ASCII Art rendering functions
#   utils.py      - error handling, file I/O, debug, logging
#   cli.py        - PathMaster, CommandLine, option classes
#   config.py     - SourceDocument, ConfigMaster, ConfigLines
#   processing.py - MaskMaster, TitleMaster, TableMaster,
#                   BlockMaster, MacroMaster
#   output.py     - TOC, headers, footers, escaping helpers
#   converter.py  - process_source_file(), convert(), etc.
#   gui.py        - Tkinter GUI (Gui class)
#   usage.py      - Usage() help text and embedded templates
#   __main__.py   - exec_command_line() entry point

from .constants import *
from .state import *
from .usage import Usage
from .tags import getTags
from .rules import getRules
from .regexes import getRegexes
from .utils import (
    error, echo, Quit, Error, getTraceback, getUnknownErrorMessage,
    Message, Debug, Readfile, Savefile, showdic, dotted_spaces, get_rc_path,
)
from .cli import PathMaster, CommandLine, BaseOptions, CsvOptions, DbOptions, FenOptions
from .config import SourceDocument, ConfigMaster, ConfigLines
from .processing import MaskMaster, TitleMaster, TableMaster, BlockMaster, MacroMaster
from .output import (
    cc_formatter, listTargets, dumpConfig, get_file_body, post_voodoo,
    finish_him, toc_inside_body, toc_tagger, toc_formatter,
    doHeader, doCommentLine, doFooter,
    convertUnicodeRTF, get_escapes, doProtect, doEscape, doFinalEscape,
    EscapeCharHandler, maskEscapeChar, unmaskEscapeChar,
    addLineBreaks, expandLineBreaks, compile_filters,
    enclose_me, fix_relative_path, fix_css_out_path,
    beautify_me, get_tagged_link, parse_deflist_term,
    get_image_align, get_encoding_string,
)
from .converter import (
    process_source_file, get_infiles_config, convert_this_files,
    getImageInfo, embedImage, parse_images, add_inline_tags,
    get_include_contents, set_global_config, convert,
)
from .gui import load_GUI_resources, Gui
