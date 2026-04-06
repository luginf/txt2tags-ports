# txt2tags - regex patterns for t2t markup detection
# getRegexes() -> dict of compiled regex patterns

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


def getRegexes():
    "Returns all the regexes used to find the t2t marks"

    bank = {
        "blockVerbOpen": re.compile(r"^```\s*$"),
        "blockVerbClose": re.compile(r"^```\s*$"),
        "blockRawOpen": re.compile(r'^"""\s*$'),
        "blockRawClose": re.compile(r'^"""\s*$'),
        "blockTaggedOpen": re.compile(r"^'''\s*$"),
        "blockTaggedClose": re.compile(r"^'''\s*$"),
        "blockCommentOpen": re.compile(r"^%%%\s*$"),
        "blockCommentClose": re.compile(r"^%%%\s*$"),
        "quote": re.compile(r"^\t+"),
        "1lineVerb": re.compile(r"^``` (?=.)"),
        "1lineRaw": re.compile(r'^""" (?=.)'),
        "1lineTagged": re.compile(r"^''' (?=.)"),
        # mono, raw, bold, italic, underline:
        # - marks must be glued with the contents, no boundary spaces
        # - they are greedy, so in ****bold****, turns to <b>**bold**</b>
        "fontMono": re.compile(r"``([^\s](|.*?[^\s])`*)``"),
        "raw": re.compile(r'""([^\s](|.*?[^\s])"*)""'),
        "tagged": re.compile(r"''([^\s](|.*?[^\s])'*)''"),
        "math": re.compile(r"\$\$([^\s](|.*?[^\s])\$*)\$\$"),
        "fontBold": re.compile(r"\*\*([^\s](|.*?[^\s])\**)\*\*"),
        "fontItalic": re.compile(r"//([^\s](|.*?[^\s])/*)//"),
        "fontUnderline": re.compile(r"__([^\s](|.*?[^\s])_*)__"),
        "fontStrike": re.compile(r"--([^\s](|.*?[^\s])-*)--"),
        "list": re.compile(r"^( *)(-) (?=[^ ])"),
        "numlist": re.compile(r"^( *)(\+) (?=[^ ])"),
        "deflist": re.compile(r"^( *)(:) (.*)$"),
        "listclose": re.compile(r"^( *)([-+:])\s*$"),
        "bar": re.compile(r"^(\s*)([_=-]{20,})\s*$"),
        "table": re.compile(r"^ *\|([|_/])? "),
        "blankline": re.compile(r"^\s*$"),
        "comment": re.compile(r"^%"),
        # Auxiliary tag regexes
        "_imgAlign": re.compile(r"~A~", re.I),
        "_tableAlign": re.compile(r"~A~", re.I),
        "_anchor": re.compile(r"~A~", re.I),
        "_tableBorder": re.compile(r"~B~", re.I),
        "_tableColAlign": re.compile(r"~C~", re.I),
        "_tableCellColSpan": re.compile(r"~S~", re.I),
        "_tableCellAlign": re.compile(r"~A~", re.I),
        "_tableAttrDelimiter": re.compile(r"~Z~", re.I),
        "_blockDepth": re.compile(r"~D~", re.I),
        "_listLevel": re.compile(r"~L~", re.I),
    }

    # Special char to place data on TAGs contents  (\a == bell)
    bank["x"] = re.compile("\a")

    # %%macroname [ (formatting) ]
    bank["macros"] = re.compile(
        r"%%%%(?P<name>%s)\b(\((?P<fmt>.*?)\))?" % ("|".join(list(MACROS.keys()))), re.I
    )

    # %%TOC special macro for TOC positioning
    bank["toc"] = re.compile(r"^ *%%toc\s*$", re.I)

    # Almost complicated title regexes ;)
    titskel = r"^ *(?P<id>%s)(?P<txt>%s)\1(\[(?P<label>[\w-]*)\])?\s*$"
    bank["title"] = re.compile(titskel % ("[=]{1,5}", "[^=](|.*[^=])"))
    bank["numtitle"] = re.compile(titskel % ("[+]{1,5}", "[^+](|.*[^+])"))

    ### Complicated regexes begin here ;)
    #
    # Textual descriptions on --help's style: [...] is optional, | is OR

    ### First, some auxiliary variables
    #

    # [image.EXT]
    patt_img = r"\[([\w_,.+%$#@!?+~/-]+\.(png|jpe?g|gif|eps|bmp|svg))\]"

    # Link things
    # http://www.gbiv.com/protocols/uri/rfc/rfc3986.html
    # pchar: A-Za-z._~- / %FF / !$&'()*+,;= / :@
    # Recomended order: scheme://user:pass@domain/path?query=foo#anchor
    # Also works      : scheme://user:pass@domain/path#anchor?query=foo
    # TODO form: !'():
    urlskel = {
        "proto": r"(https?|ftp|news|telnet|gopher|wais)://",
        "guess": r"(www[23]?|ftp)\.",  # w/out proto, try to guess
        "login": r"A-Za-z0-9_.-",  # for ftp://login@domain.com
        "pass": r"[^ @]*",  # for ftp://login:pass@dom.com
        "chars": r"A-Za-z0-9%._/~:,=$@&+-",  # %20(space), :80(port), D&D
        "anchor": r"A-Za-z0-9%._-",  # %nn(encoded)
        "form": r"A-Za-z0-9/%&=+:;.,$@*_-",  # .,@*_-(as is)
        "punct": r".,;:!?",
    }

    # username [ :password ] @
    patt_url_login = r"([%s]+(:%s)?@)?" % (urlskel["login"], urlskel["pass"])

    # [ http:// ] [ username:password@ ] domain.com [ / ]
    #     [ #anchor | ?form=data ]
    retxt_url = r"\b(%s%s|%s)[%s]+\b/*(\?[%s]+)?(#[%s]*)?" % (
        urlskel["proto"],
        patt_url_login,
        urlskel["guess"],
        urlskel["chars"],
        urlskel["form"],
        urlskel["anchor"],
    )

    # filename | [ filename ] #anchor
    retxt_url_local = r"[%s]+|[%s]*(#[%s]*)" % (
        urlskel["chars"],
        urlskel["chars"],
        urlskel["anchor"],
    )

    # user@domain [ ?form=data ]
    patt_email = r"\b[%s]+@([A-Za-z0-9_-]+\.)+[A-Za-z]{2,4}\b(\?[%s]+)?" % (
        urlskel["login"],
        urlskel["form"],
    )

    # Saving for future use
    bank["_urlskel"] = urlskel

    ### And now the real regexes
    #

    bank["email"] = re.compile(patt_email, re.I)

    # email | url
    bank["link"] = re.compile(r"%s|%s" % (retxt_url, patt_email), re.I)

    # \[ label | imagetag    url | email | filename \]
    bank["linkmark"] = re.compile(
        r"\[(?P<label>%s|[^]]+) (?P<link>%s|%s|%s)\]"
        % (patt_img, retxt_url, patt_email, retxt_url_local),
        re.I,
    )

    # Image
    bank["img"] = re.compile(patt_img, re.I)

    # Special things
    bank["special"] = re.compile(r"^%!\s*")

    return bank


### END OF state.regex nightmares

# The ASCII Art library


