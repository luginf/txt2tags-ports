# txt2tags - syntax rules per target
# getRules(config) -> dict of boolean rules for the given target

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


def getRules(config):
    "Returns all the target-specific syntax state.rules"

    ret = {}
    allrules = [
        # target state.rules (ON/OFF)
        "linkable",  # target supports external links
        "tableable",  # target supports tables
        "tableonly",  # target computes only the tables
        "spread",  # target uses the spread.py engine
        "spreadgrid",  # target adds the reference grid to the sheet
        "imglinkable",  # target supports images as links
        "imgalignable",  # target supports image alignment
        "imgasdefterm",  # target supports image as definition term
        "autonumberlist",  # target supports numbered lists natively
        "autonumbertitle",  # target supports numbered titles natively
        "stylable",  # target supports external style files
        "parainsidelist",  # lists items supports paragraph
        "compactlist",  # separate enclosing tags for compact lists
        "spacedlistitem",  # lists support blank lines between items
        "listnotnested",  # lists cannot be nested
        "listitemnotnested",  # list items must be closed before nesting lists
        "quotenotnested",  # quotes cannot be nested
        "verbblocknotescaped",  # don't escape specials in verb block
        "verbblockfinalescape",  # do final escapes in verb block
        "escapeurl",  # escape special in link URL
        "labelbeforelink",  # label comes before the link on the tag
        "onelinepara",  # dump paragraph as a single long line
        "onelinequote",  # dump quote as a single long line (EXPERIMENTAL)
        "notbreaklistitemclose",  # do not break line before the list item close tag (EXPERIMENTAL)
        "tabletitlerowinbold",  # manually bold any cell on table titles
        "tablecellstrip",  # strip extra spaces from each table cell
        "tablecellspannable",  # the table cells can have span attribute
        "tablecellcovered",  # covered cell follows the cell span
        "tablecellmulticol",  # separate open+close tags for multicol cells
        "tablecolumnsnumber",  # set the number of columns in place of n_cols in tableOpen
        "tablenumber",  # set the number of the table in place of n_table in tableOpen
        "barinsidequote",  # bars are allowed inside quote blocks
        "finalescapetitle",  # perform final escapes on title lines
        "autotocnewpagebefore",  # break page before automatic TOC
        "autotocnewpageafter",  # break page after automatic TOC
        "autotocwithbars",  # automatic TOC surrounded by bars
        "plaintexttoc",  # TOC will be plain text (no links)
        "mapbar2pagebreak",  # map the strong bar to a page break
        "titleblocks",  # titles must be on open/close section blocks
        "listlineafteropen",  # put listItemLine after listItemOpen
        "escapexmlchars",  # escape the XML special chars: < > &
        "listlevelzerobased",  # list levels start at 0 when encoding into tags
        "zerodepthparagraph",  # non-nested paras have block depth of 0 instead of 1
        "cellspancumulative",  # cell span value adds up for each cell of a row
        "keepblankheaderline",  # template lines are not removed if headers are blank
        "confdependenttags",  # tags are configuration dependent
        "confdependentrules",  # state.rules are configuration dependent
        # Target code beautify (ON/OFF)
        "indentverbblock",  # add leading spaces to verb block lines
        "breaktablecell",  # break lines after any table cell
        "breaktablelineopen",  # break line after opening table line
        "notbreaklistopen",  # don't break line after opening a new list
        "keepquoteindent",  # don't remove the leading TABs on quotes
        "keeplistindent",  # don't remove the leading spaces on lists
        "blankendautotoc",  # append a blank line at the auto TOC end
        "tagnotindentable",  # tags must be placed at the line beginning
        "spacedlistitemopen",  # append a space after the list item open tag
        "spacednumlistitemopen",  # append a space after the numlist item open tag
        "deflisttextstrip",  # strip the contents of the deflist text
        "blanksaroundpara",  # put a blank line before and after paragraphs
        "blanksaroundverb",  # put a blank line before and after verb blocks
        "blanksaroundquote",  # put a blank line before and after quotes
        "blanksaroundlist",  # put a blank line before and after lists
        "blanksaroundnumlist",  # put a blank line before and after numlists
        "blanksarounddeflist",  # put a blank line before and after deflists
        "blanksaroundnestedlist",  # put a blank line before and after all type of nested lists
        "blanksaroundtable",  # put a blank line before and after tables
        "blanksaroundbar",  # put a blank line before and after bars
        "blanksaroundtitle",  # put a blank line before and after titles
        "blanksaroundnumtitle",  # put a blank line before and after numtitles
        "iswrapped",  # wrap with the --width value
        # Value settings
        "listmaxdepth",  # maximum depth for lists
        "quotemaxdepth",  # maximum depth for quotes
        "tablecellaligntype",  # type of table cell align: cell, column
        "blockdepthmultiply",  # block depth multiple for encoding
        "depthmultiplyplus",  # add to block depth before multiplying
        "cellspanmultiplier",  # cell span is multiplied by this value
        "spreadmarkup",  # the markup spread engine option: 'txt', 'html' or 'tex'
    ]

    rules_bank = {
        "txt": {
            "indentverbblock": 1,
            "spacedlistitem": 1,
            "parainsidelist": 1,
            "keeplistindent": 1,
            "barinsidequote": 1,
            "autotocwithbars": 1,
            "plaintexttoc": 1,
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            "blanksaroundquote": 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
            "iswrapped": 1,
        },
        "txt2t": {
            "linkable": 1,
            "tableable": 1,
            "imglinkable": 1,
            # 'imgalignable',
            "imgasdefterm": 1,
            "autonumberlist": 1,
            "autonumbertitle": 1,
            "stylable": 1,
            "spacedlistitem": 1,
            "labelbeforelink": 1,
            "tablecellstrip": 1,
            "tablecellspannable": 1,
            "keepblankheaderline": 1,
            "barinsidequote": 1,
            "keeplistindent": 1,
            "blankendautotoc": 1,
            "blanksaroundpara": 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
            "tablecellaligntype": "cell",
        },
        "rst": {
            "indentverbblock": 1,
            "spacedlistitem": 1,
            "parainsidelist": 1,
            "keeplistindent": 1,
            "barinsidequote": 1,
            "imgalignable": 1,
            "imglinkable": 1,
            "tableable": 1,
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            "blanksaroundquote": 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
            "blanksaroundnestedlist": 1,
        },
        "aat": {
            # TIP art inherits all TXT state.rules
        },
        "csv": {
            "tableable": 1,
            "tableonly": 1,
            "tablecellstrip": 1,
        },
        "csvs": {
            # TIP csvs inherits all csv state.rules
            "spread": 1,
            "spreadmarkup": "txt",
        },
        "db": {
            "tableable": 1,
            "tableonly": 1,
        },
        "ods": {
            "escapexmlchars": 1,
            "tableable": 1,
            "tableonly": 1,
            "tablecellstrip": 1,
            "tablecellspannable": 1,
            "tablecellcovered": 1,
            "tablecellaligntype": "cell",
        },
        "html": {
            "escapexmlchars": 1,
            "indentverbblock": 1,
            "linkable": 1,
            "stylable": 1,
            "escapeurl": 1,
            "imglinkable": 1,
            "imgalignable": 1,
            "imgasdefterm": 1,
            "autonumberlist": 1,
            "spacedlistitem": 1,
            "parainsidelist": 1,
            "tableable": 1,
            "tablecellstrip": 1,
            "breaktablecell": 1,
            "breaktablelineopen": 1,
            "keeplistindent": 1,
            "keepquoteindent": 1,
            "barinsidequote": 1,
            "autotocwithbars": 1,
            "tablecellspannable": 1,
            "tablecellaligntype": "cell",
            # 'blanksaroundpara': 1,
            "blanksaroundverb": 1,
            # 'blanksaroundquote': 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "xhtml": {
            # TIP xhtml inherits all HTML state.rules
        },
        "wp": {
            # TIP wp inherits all HTML state.rules
            "onelinepara": 1,
            "onelinequote": 1,
            "tagnotindentable": 1,
            "blanksaroundpara": 1,
            "quotemaxdepth": 1,
            "keepquoteindent": 0,
            "keeplistindent": 0,
            "notbreaklistitemclose": 1,
        },
        "xhtmls": {
            # TIP xhtmls inherits all HTML state.rules
        },
        "html5": {
            # TIP html5 inherits all HTML state.rules
            "titleblocks": 1,
        },
        "htmls": {
            # TIP htmls inherits all HTML state.rules
            "tableonly": 1,
            "spread": 1,
            "spreadgrid": 1,
            "spreadmarkup": "html",
        },
        "sgml": {
            "escapexmlchars": 1,
            "linkable": 1,
            "escapeurl": 1,
            "autonumberlist": 1,
            "spacedlistitem": 1,
            "tableable": 1,
            "tablecellstrip": 1,
            "blankendautotoc": 1,
            "keeplistindent": 1,
            "keepquoteindent": 1,
            "barinsidequote": 1,
            "finalescapetitle": 1,
            "tablecellaligntype": "column",
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            "blanksaroundquote": 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
            "quotemaxdepth": 1,
        },
        "dbk": {
            "escapexmlchars": 1,
            "linkable": 1,
            "tableable": 1,
            "imglinkable": 1,
            "imgalignable": 1,
            "imgasdefterm": 1,
            "autonumberlist": 1,
            "autonumbertitle": 1,
            "parainsidelist": 1,
            "spacedlistitem": 1,
            "titleblocks": 1,
            "tablecolumnsnumber": 1,
        },
        "vimwiki": {
            "linkable": 1,
            "tableable": 1,
            #'spacedlistitem':1,
            #'tablecellstrip':1,
            #'autotocwithbars':1,
            #'spacedlistitemopen':1,
            #'spacednumlistitemopen':1,
            #'deflisttextstrip':1,
            "autonumberlist": 1,
            "autonumbertitle": 1,
            "imgalignable": 1,
            "keeplistindent": 1,
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            # 'blanksaroundquote':1,
            #'blanksaroundlist':1,
            #'blanksaroundnumlist':1,
            #'blanksarounddeflist':1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "mgp": {
            "tagnotindentable": 1,
            "spacedlistitem": 1,
            "imgalignable": 1,
            "autotocnewpagebefore": 1,
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            # 'blanksaroundquote': 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "tableable": 1,
            # 'blanksaroundtitle': 1,
            # 'blanksaroundnumtitle': 1,
        },
        "tex": {
            "stylable": 1,
            "escapeurl": 1,
            "linkable": 1,
            # 'labelbeforelink': 0,
            "autonumberlist": 1,
            "autonumbertitle": 1,
            "spacedlistitem": 1,
            "compactlist": 1,
            "parainsidelist": 1,
            "tableable": 1,
            "tablecellstrip": 1,
            "tabletitlerowinbold": 1,
            "verbblocknotescaped": 1,
            "keeplistindent": 1,
            "listmaxdepth": 4,  # deflist is 6
            "quotemaxdepth": 6,
            "barinsidequote": 1,
            "finalescapetitle": 1,
            "autotocnewpageafter": 1,
            "mapbar2pagebreak": 1,
            "tablecellaligntype": "column",
            "tablecellmulticol": 1,
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            # 'blanksaroundquote': 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "texs": {
            # TIP texs inherits all tex state.rules
            "tableonly": 1,
            "spread": 1,
            "spreadgrid": 1,
            "spreadmarkup": "tex",
        },
        "lout": {
            "tableable": 1,
            "tablecolumnsnumber": 1,
            "tablecellspannable": 1,
            "tablecellaligntype": "cell",
            "tablecellstrip": 1,
            "breaktablecell": 1,
            "keepquoteindent": 1,
            "deflisttextstrip": 1,
            "escapeurl": 1,
            "verbblocknotescaped": 1,
            "imgalignable": 1,
            #'mapbar2pagebreak': 1,
            "titleblocks": 1,
            "autonumberlist": 1,
            "parainsidelist": 1,
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            # 'blanksaroundquote': 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "moin": {
            "spacedlistitem": 1,
            "linkable": 1,
            "keeplistindent": 1,
            "tableable": 1,
            "barinsidequote": 1,
            "tabletitlerowinbold": 1,
            "tablecellstrip": 1,
            "autotocwithbars": 1,
            "tablecellspannable": 1,
            "tablecellaligntype": "cell",
            "deflisttextstrip": 1,
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            # 'blanksaroundquote': 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            # 'blanksaroundbar': 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "gwiki": {
            "spacedlistitem": 1,
            "linkable": 1,
            "keeplistindent": 1,
            "tableable": 1,
            "tabletitlerowinbold": 1,
            "tablecellstrip": 1,
            "autonumberlist": 1,
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            # 'blanksaroundquote': 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            # 'blanksaroundbar': 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "adoc": {
            "spacedlistitem": 1,
            "linkable": 1,
            "keeplistindent": 0,
            "autonumberlist": 1,
            "autonumbertitle": 1,
            "listnotnested": 1,
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "doku": {
            "indentverbblock": 1,  # DokuWiki uses '  ' to mark verb blocks
            "spacedlistitem": 1,
            "linkable": 1,
            "keeplistindent": 1,
            "tableable": 1,
            "barinsidequote": 1,
            "tablecellstrip": 1,
            "autotocwithbars": 1,
            "autonumberlist": 1,
            "imgalignable": 1,
            "tablecellaligntype": "cell",
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            # 'blanksaroundquote': 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "pmw": {
            "indentverbblock": 1,
            "spacedlistitem": 1,
            "linkable": 1,
            "labelbeforelink": 1,
            # 'keeplistindent': 1,
            "tableable": 1,
            "barinsidequote": 1,
            "tablecellstrip": 1,
            "autotocwithbars": 1,
            "autonumberlist": 1,
            "spacedlistitemopen": 1,
            "spacednumlistitemopen": 1,
            "imgalignable": 1,
            "tabletitlerowinbold": 1,
            "tablecellaligntype": "cell",
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            "blanksaroundquote": 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "wiki": {
            "escapexmlchars": 1,
            "linkable": 1,
            "tableable": 1,
            "tablecellstrip": 1,
            "autotocwithbars": 1,
            "spacedlistitemopen": 1,
            "spacednumlistitemopen": 1,
            "deflisttextstrip": 1,
            "autonumberlist": 1,
            "imgalignable": 1,
            "tablecellspannable": 1,
            "tablecellaligntype": "cell",
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            # 'blanksaroundquote': 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "red": {
            "linkable": 1,
            "tableable": 1,
            "tablecellstrip": 1,
            "tablecellspannable": 1,
            "tablecellaligntype": "cell",
            "autotocwithbars": 1,
            "spacedlistitemopen": 1,
            "spacednumlistitemopen": 1,
            "deflisttextstrip": 1,
            "autonumberlist": 1,
            "imgalignable": 1,
            "labelbeforelink": 1,
            "quotemaxdepth": 1,
            "autonumbertitle": 1,
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            # 'blanksaroundquote': 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "man": {
            "spacedlistitem": 1,
            "tagnotindentable": 1,
            "tableable": 1,
            "tablecellaligntype": "column",
            "tabletitlerowinbold": 1,
            "tablecellstrip": 1,
            "barinsidequote": 1,
            "parainsidelist": 0,
            "plaintexttoc": 1,
            "blanksaroundpara": 0,
            "blanksaroundverb": 1,
            # 'blanksaroundquote': 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            # 'blanksaroundbar': 1,
            "blanksaroundtitle": 0,
            "blanksaroundnumtitle": 1,
        },
        "utmac": {
            "tagnotindentable": 1,
            "autonumbertitle": 1,
            "quotenotnested": 1,
            "barinsidequote": 1,
            "parainsidelist": 0,
            "spacedlistitem": 0,
            "labelbeforelink": 0,  # is that work ?
            "imgalignable": 1,
            "plaintexttoc": 0,
            "tableable": 1,
            "tablecellaligntype": "column",
            "tabletitlerowinbold": 1,
            "tablecellstrip": 1,
            "blanksaroundpara": 0,
            "blanksaroundverb": 0,
            "blanksaroundquote": 0,
            "blanksaroundlist": 0,
            "blanksaroundnumlist": 0,
            "blanksarounddeflist": 0,
            "blanksaroundtable": 0,
            "blanksaroundbar": 0,
            "blanksaroundtitle": 0,
            "blanksaroundnumtitle": 0,
        },
        "pm6": {
            "keeplistindent": 1,
            "verbblockfinalescape": 1,
            # TODO add support for these
            # maybe set a JOINNEXT char and do it on addLineBreaks()
            "notbreaklistopen": 1,
            "barinsidequote": 1,
            "autotocwithbars": 1,
            "onelinepara": 1,
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            # 'blanksaroundquote': 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            # 'blanksaroundtable': 1,
            # 'blanksaroundbar': 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "creole": {
            "linkable": 1,
            "tableable": 1,
            "imglinkable": 1,
            "tablecellstrip": 1,
            "autotocwithbars": 1,
            "spacedlistitemopen": 1,
            "spacednumlistitemopen": 1,
            "deflisttextstrip": 1,
            "verbblocknotescaped": 1,
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            "blanksaroundquote": 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
        },
        "md": {
            #'keeplistindent': 1,
            "linkable": 1,
            "labelbeforelink": 1,
            "tableable": 1,
            "imglinkable": 1,
            "tablecellstrip": 1,
            "autonumberlist": 1,
            "spacedlistitemopen": 1,
            "spacednumlistitemopen": 1,
            "deflisttextstrip": 1,
            "blanksaroundpara": 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            #'blanksarounddeflist': 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
        },
        "gmi": {
            #'keeplistindent': 1,
            "linkable": 1,
            "labelbeforelink": 0,
            "tableable": 1,
            "imglinkable": 1,
            "tablecellstrip": 1,
            "autonumberlist": 1,
            "spacedlistitemopen": 1,
            "spacednumlistitemopen": 1,
            "deflisttextstrip": 1,
            "blanksaroundpara": 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            #'blanksarounddeflist': 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
        },
        "bbcode": {
            #'keeplistindent': 1,
            "keepquoteindent": 1,
            #'indentverbblock': 1,
            "linkable": 1,
            #'labelbeforelink': 1,
            #'tableable': 1,
            "imglinkable": 1,
            "tablecellstrip": 1,
            #'autotocwithbars': 1,
            "autonumberlist": 1,
            "spacedlistitemopen": 1,
            "spacednumlistitemopen": 1,
            "deflisttextstrip": 1,
            #'verbblocknotescaped': 1,
            "blanksaroundpara": 1,
            #'blanksaroundverb': 1,
            #'blanksaroundquote': 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            #'blanksarounddeflist': 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
        },
        "spip": {
            "spacedlistitem": 1,
            "spacedlistitemopen": 1,
            "linkable": 1,
            "blankendmotherlist": 1,
            "tableable": 1,
            "barinsidequote": 1,
            "keepquoteindent": 1,
            "blankendtable": 1,
            "tablecellstrip": 1,
            "imgalignable": 1,
            "tablecellaligntype": "cell",
            "listlineafteropen": 1,
            "labelbeforelink": 1,
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            "blanksaroundquote": 1,
            "blanksaroundlist": 1,
            "blanksaroundnumlist": 1,
            "blanksarounddeflist": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "rtf": {
            "linkable": 1,
            "tableable": 1,
            "autonumbertitle": 1,
            "parainsidelist": 1,
            "listnotnested": 1,
            "listitemnotnested": 1,
            "quotenotnested": 1,
            "onelinepara": 1,
            "tablecellstrip": 1,
            "tablecellspannable": 1,
            "tagnotindentable": 1,
            "deflisttextstrip": 1,
            "encodeblockdepth": 1,
            "zerodepthparagraph": 1,
            "cellspancumulative": 1,
            "blockdepthmultiply": 360,
            "depthmultiplyplus": 1,
            "cellspanmultiplier": 1080,
            "listmaxdepth": 9,
            "tablecellaligntype": "cell",
        },
        "tml": {
            "escapexmlchars": 1,
            "linkable": 1,
            "tableable": 1,
            "tablecellstrip": 1,
            "tablecellspannable": 1,
            "spacedlistitem": 1,
            "autonumberlist": 1,
            "notbreaklistopen": 1,
            "imgalignable": 1,
            "imglinkable": 1,
            "tablecellaligntype": "cell",
            "blanksaroundpara": 1,
            "blanksaroundverb": 1,
            "blanksaroundtable": 1,
            "blanksaroundbar": 1,
            "blanksaroundtitle": 1,
            "blanksaroundnumtitle": 1,
        },
        "mom": {
            "autonumberlist": 1,  # target supports numbered lists natively
            "autonumbertitle": 1,  # target supports numbered titles natively
            "imgalignable": 1,  # target supports image alignment
            #        'stylable': 1,               # target supports external style files
            "parainsidelist": 1,  # lists items supports paragraph
            "spacedlistitem": 1,  # lists support blank lines between items
            "labelbeforelink": 1,  # label comes before the link on the tag
            "barinsidequote": 1,  # bars are allowed inside quote blocks
            "quotenotnested": 1,  # quotes cannot be nested
            "autotocnewpagebefore": 1,  # break page before automatic TOC
            "autotocnewpageafter": 1,  # break page after automatic TOC
            "mapbar2pagebreak": 1,  # map the strong bar to a page break
            "tableable": 1,  # target supports tables
            "tablecellaligntype": "column",
            "tabletitlerowinbold": 1,
            "tablecellstrip": 1,
            "blanksaroundlist": 1,  # put a blank line before and after lists
            #        'blanksaroundnumlist': 1,    # put a blank line before and after numlists
            #        'blanksarounddeflist': 1,    # put a blank line before and after deflists
            #        'blanksaroundnestedlist': 1, # put a blank line before and after all type of nested lists
            #        'blanksaroundquote',      # put a blank line before and after quotes
            "blanksaroundtable": 1,  # put a blank line before and after tables
            "blankendautotoc": 1,  # append a blank line at the auto TOC end
            "tagnotindentable": 1,  # tags must be placed at the line beginning
        },
    }
    for target in TARGETS_LIST:
        if getattr(getattr(targets, target), "RULES", {}).get("confdependentrules"):
            importlib.reload(getattr(targets, target))
        rules_bank[target] = getattr(getattr(targets, target), "RULES", {})

    # Exceptions for --css-sugar
    if (
        config["css-sugar"] and config["target"] in ("html", "xhtml", "xhtmls", "html5")
    ) or config["target"] == "wp":
        rules_bank["html"]["indentverbblock"] = 0
        rules_bank["html"]["autotocwithbars"] = 0
    # Get the target specific state.rules
    if config["target"] in ("xhtml", "xhtmls", "html5", "htmls", "wp"):
        myrules = rules_bank["html"].copy()  # inheritance
        myrules.update(rules_bank[config["target"]])  # get specific
    elif config["target"] == "aat":
        myrules = rules_bank["txt"].copy()  # inheritance
        myrules["tableable"] = 1
        if config["slides"]:
            myrules["blanksaroundtitle"] = 0
            myrules["blanksaroundnumtitle"] = 0
            myrules["blanksaroundlist"] = 0
            myrules["blanksaroundnumlist"] = 0
            myrules["blanksarounddeflist"] = 0
        if config["web"]:
            myrules["linkable"] = 1
            myrules["imglinkable"] = 1
            myrules["escapexmlchars"] = 1
        if config["spread"]:
            myrules["tableonly"] = 1
            myrules["spread"] = 1
            myrules["spreadgrid"] = (1,)
            myrules["spreadmarkup"] = "txt"
            if config["web"]:
                myrules["spreadmarkup"] = "html"
    elif config["target"] == "texs":
        myrules = rules_bank["tex"].copy()  # inheritance
        myrules.update(rules_bank[config["target"]])  # get specific
    elif config["target"] == "csvs":
        myrules = rules_bank["csv"].copy()  # inheritance
        myrules.update(rules_bank[config["target"]])  # get specific
    else:
        myrules = rules_bank[config["target"]].copy()

    # Populate return dictionary
    for key in allrules:
        ret[key] = 0  # reset all
    ret.update(myrules)  # get state.rules

    if ret["iswrapped"] and not config["width"]:
        config["width"] = DFT_TEXT_WIDTH

    return ret


##############################################################################


