# txt2tags - utility functions: error handling, file I/O, debug

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


class error(Exception):
    pass


def echo(msg):  # for quick debug
    print("\033[32;1m%s\033[m" % msg)


def Quit(msg=""):
    if msg:
        print(msg)
    sys.exit(0)


def Error(msg):
    msg = _("%s: Error: ") % my_name + msg
    raise error(msg)


def getTraceback():
    try:
        from traceback import format_exception

        etype, value, tb = sys.exc_info()
        return "".join(format_exception(etype, value, tb))
    except:
        pass


def getUnknownErrorMessage():
    msg = "%s\n%s (%s):\n\n%s" % (
        _("Sorry! Txt2tags aborted by an unknown error."),
        _("Please send the following Error Traceback to the author"),
        my_email,
        getTraceback(),
    )
    return msg


def Message(msg, level):
    if level <= state.VERBOSE and not state.QUIET:
        prefix = "-" * 5
        print("%s %s" % (prefix * level, msg))


def Debug(msg, id_=0, linenr=None):
    "Show debug messages, categorized (colored or not)"
    if state.QUIET or not state.DEBUG:
        return
    if int(id_) not in list(range(8)):
        id_ = 0
    # 0:black 1:red 2:green 3:yellow 4:blue 5:pink 6:cyan 7:white ;1:light
    ids = ["INI", "CFG", "SRC", "BLK", "HLD", "state.GUI", "OUT", "DET"]
    colors_bgdark = ["7;1", "1;1", "3;1", "6;1", "4;1", "5;1", "2;1", "7;1"]
    colors_bglight = ["0", "1", "3", "6", "4", "5", "2", "0"]
    if linenr is not None:
        msg = "LINE %04d: %s" % (linenr, msg)
    if COLOR_DEBUG:
        if BG_LIGHT:
            color = colors_bglight[id_]
        else:
            color = colors_bgdark[id_]
        msg = "\033[3%sm%s\033[m" % (color, msg)
    print("++ %s: %s" % (ids[id_], msg))


def _is_url(path):
    from .cli import PathMaster
    return PathMaster().is_url(path)


def Readfile(file_path, remove_linebreaks=0, ignore_error=0):
    data = []

    # STDIN
    if file_path == "-":
        try:
            data = sys.stdin.readlines()
        except:
            if not ignore_error:
                Error(_("You must feed me with data on STDIN!"))

    # URL
    elif _is_url(file_path):
        try:
            from urllib.request import urlopen

            f = urlopen(file_path)
            if f.getcode() == 404:  # URL not found
                raise

            # fixme: Maybe there's a better solution for this?
            data = [line.decode("utf-8") for line in f.readlines()]

            f.close()
        except:
            if not ignore_error:
                Error(_("Cannot read file:") + " " + file_path)

    # local file
    else:
        try:
            f = open(file_path)
            data = f.readlines()
            f.close()
        except:
            if not ignore_error:
                Error(_("Cannot read file:") + " " + file_path)

    if remove_linebreaks:
        data = [re.sub("[\n\r]+$", "", str(x)) for x in data]

    Message(_("File read (%d lines): %s") % (len(data), file_path), 2)
    return data


def Savefile(file_path, contents):
    try:
        f = open(file_path, "wb")
    except:
        Error(_("Cannot open file for writing:") + " " + file_path)

    if isinstance(contents, list):
        doit = f.writelines
    else:
        doit = f.write

    cont = [bytes(s.encode("utf-8")) for s in contents]

    doit(cont)
    f.close()


def showdic(dic):
    for k in list(dic.keys()):
        print("%15s : %s" % (k, dic[k]))


def dotted_spaces(txt=""):
    return txt.replace(" ", ".")


# TIP: win env vars http://www.winnetmag.com/Article/ArticleID/23873/23873.html
def get_rc_path():
    "Return the full path for the users' RC file"
    # Try to get the path from an env var. if yes, we're done
    user_defined = os.environ.get("T2TCONFIG")
    if user_defined:
        return user_defined
    # Env var not found, so perform automatic path composing
    # Set default filename according system platform
    rc_names = {"default": ".txt2tagsrc", "win": "_t2trc"}
    rc_file = rc_names.get(sys.platform[:3]) or rc_names["default"]
    # The file must be on the user directory, but where is this dir?
    rc_dir_search = ["HOME", "HOMEPATH"]
    for var in rc_dir_search:
        rc_dir = os.environ.get(var)
        if rc_dir:
            break
    # rc dir found, now we must join dir+file to compose the full path
    if rc_dir:
        # Compose path and return it if the file exists
        rc_path = os.path.join(rc_dir, rc_file)
        # On windows, prefix with the drive (%homedrive%: 2k/XP/NT)
        if sys.platform.startswith("win"):
            rc_drive = os.environ.get("HOMEDRIVE")
            rc_path = os.path.join(rc_drive, rc_path)
        return rc_path
    # Sorry, not found
    return ""


##############################################################################


