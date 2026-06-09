# txt2tags - command line interface and path handling

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
from .utils import Error, Debug, Message, dotted_spaces


class PathMaster:
    """Handle paths. See issues: 27, 62, 63, 71, 85."""

    def __init__(self):
        pass

    def is_url(self, text):
        return text.startswith("http://") or text.startswith("https://")

    def join(self, dirname, filename):
        """Join paths, unless filename is STDOUT, absolute or URL."""

        if (
            not dirname
            or not filename
            or filename in (STDOUT, MODULEOUT)
            or os.path.isabs(filename)
            or self.is_url(filename)
        ):
            return filename
        else:
            return os.path.join(dirname, filename)

    def relpath(self, path, start):
        """Unlike os.path.relpath(), never touch URLs"""
        if not path or self.is_url(path):
            return path
        else:
            return os.path.relpath(path, start)


class CommandLine:
    """
    Command Line class - Masters command line

    This class checks and extract data from the provided command line.
    The --long options and flags are taken from the global OPTIONS,
    FLAGS and ACTIONS dictionaries. The short options are registered
    here, and also their equivalence to the long ones.

    _compose_short_opts() -> str
    _compose_long_opts() -> list
        Compose the valid short and long options list, on the
        'getopt' format.

    parse() -> (opts, args)
        Call getopt to check and parse the command line.
        It expects to receive the command line as a list, and
        without the program name (sys.argv[1:]).

    get_raw_config() -> [RAW config]
        Scans command line and convert the data to the RAW config
        format. See ConfigMaster class to the RAW format description.
        Optional 'ignore' and 'filter_' arguments are used to filter
        in or out specified keys.

    compose_cmdline(dict) -> [Command line]
        Compose a command line list from an already parsed config
        dictionary, generated from RAW by ConfigMaster(). Use
        this to compose an optimal command line for a group of
        options.

    The get_raw_config() calls parse(), so the typical use of this
    class is:

        raw = CommandLine().get_raw_config(sys.argv[1:])
    """

    def __init__(self):
        self.all_options = list(OPTIONS.keys())
        self.all_flags = list(FLAGS.keys())
        self.all_actions = list(ACTIONS.keys())

        # short:long options equivalence
        self.short_long = {
            "C": "config-file",
            "h": "help",
            "H": "no-headers",
            "i": "infile",
            "n": "enum-title",
            "o": "outfile",
            "q": "quiet",
            "t": "target",
            "T": "template",
            "v": "verbose",
            "V": "version",
        }

        # Compose valid short and long options data for getopt
        self.short_opts = self._compose_short_opts()
        self.long_opts = self._compose_long_opts()

    def _compose_short_opts(self):
        "Returns a string like 'hVt:o' with all short options/flags"
        ret = []
        for opt in list(self.short_long.keys()):
            long_ = self.short_long[opt]
            if long_ in self.all_options:  # is flag or option?
                opt = opt + ":"  # option: have param
            ret.append(opt)
        # Debug('Valid SHORT options: %s' % ret)
        return "".join(ret)

    def _compose_long_opts(self, extra=True):
        "Returns a list with all the valid long options/flags"
        ret = [x + "=" for x in self.all_options]  # add =
        ret.extend(self.all_flags)  # flag ON
        ret.extend(self.all_actions)  # actions
        ret.extend(["no-" + x for x in self.all_flags])  # add no-*
        if extra:
            ret.extend(["no-style", "no-encoding"])  # turn OFF
            ret.extend(["no-outfile", "no-infile"])  # turn OFF
            ret.extend(["no-dump-config", "no-dump-source"])  # turn OFF
            ret.extend(["no-targets"])  # turn OFF
        # Debug('Valid LONG options: %s' % ret)
        return ret

    def tokenize(self, cmdline=""):
        "Convert a command line string to a list"
        return shlex.split(cmdline)

    def parse(self, cmdline=[]):
        "Check/Parse a command line list     TIP: no program name!"
        # Get the valid options
        short, long_ = self.short_opts, self.long_opts
        # Parse it!
        try:
            opts, args = getopt.getopt(cmdline, short, long_)
        except getopt.error as errmsg:
            Error(_("%s (try --help)") % errmsg)
        return (opts, args)

    def get_raw_config(self, cmdline=[], ignore=[], filter_=[], relative=0):
        "Returns the options/arguments found as RAW config"

        if not cmdline:
            return []
        ret = []

        # We need lists, not strings (such as from %!options)
        if type(cmdline) in (type(""),):
            if not isinstance(cmdline, str):
                cmdline = str(cmdline)

            cmdline = self.tokenize(cmdline)

        # Extract name/value pair of all configs, check for invalid names
        options, arguments = self.parse(cmdline[:])

        # Needed when expanding %!options inside remote %!includeconf
        dirname = ""

        # Some cleanup on the raw config
        for name, value in options:
            # Remove leading - and --
            name = re.sub("^--?", "", name)

            # Fix old misspelled --suGGar, --no-suGGar
            name = name.replace("suggar", "sugar")

            # Translate short option to long
            if len(name) == 1:
                name = self.short_long[name]

            if name == "dirname":
                dirname = value
                continue

            # Outfile exception: path relative to PWD
            if name == "outfile" and value not in [STDOUT, MODULEOUT]:
                if relative:
                    value = os.path.abspath(value)
                else:
                    value = PathMaster().join(dirname, value)

            # -C, --config-file inclusion, path relative to PWD
            if name == "config-file":
                value = PathMaster().join(dirname, value)
                from .config import ConfigLines
                ret.extend(ConfigLines().include_config_file(value))
                continue

            # --style: path relative to PWD
            # Already OK, when comming from the command line
            # Needs fix when coming from %!options: --style foo.css
            if name == "style":
                ret.append(["all", "stylepath", PathMaster().join(dirname, value)])

            # Save this config
            ret.append(["all", name, value])

        # All configuration was read and saved

        # Get infile, if any
        while arguments:
            infile = arguments.pop(0)
            ret.append(["all", "infile", infile])

        # Apply 'ignore' and 'filter_' state.rules (filter_ is stronger)
        if ignore or filter_:
            filtered = []
            for target, name, value in ret:
                if (filter_ and name in filter_) or (ignore and name not in ignore):
                    filtered.append([target, name, value])
                else:
                    fancykey = dotted_spaces("%12s" % name)
                    Message(_("Ignored config") + (" %s : %s" % (fancykey, value)), 3)
            ret = filtered[:]

        # Add the original command line string as 'realcmdline'
        ret.append(["all", "realcmdline", cmdline])

        return ret

    def compose_cmdline(self, conf={}, no_check=0):
        "compose a full (and diet) command line from state.CONF dict"
        if not conf:
            return []
        args = []
        dft_options = OPTIONS.copy()
        cfg = conf.copy()
        valid_opts = self.all_options + self.all_flags
        use_short = {"no-headers": "H", "enum-title": "n"}
        # Remove useless options
        if not no_check and cfg.get("toc-only"):
            if "no-headers" in cfg:
                del cfg["no-headers"]
            if "outfile" in cfg:
                del cfg["outfile"]  # defaults to STDOUT
            if cfg.get("target") == "txt":
                del cfg["target"]  # already default
            args.append("--toc-only")  # must be the first
            del cfg["toc-only"]
        # Add target type
        if "target" in cfg:
            args.append("-t " + cfg["target"])
            del cfg["target"]
        # Add other options
        for key in list(cfg.keys()):
            if key not in valid_opts:
                continue  # may be a %!setting
            if key == "outfile" or key == "infile":
                continue  # later
            val = cfg[key]
            if not val:
                continue
            # Default values are useless on cmdline
            if val == dft_options.get(key):
                continue
            # -short format
            if key in use_short:
                args.append("-" + use_short[key])
                continue
            # --long format
            if key in self.all_flags:  # add --option
                args.append("--" + key)
            else:  # add --option=value
                args.append("--%s=%s" % (key, val))
        # The outfile using -o
        if "outfile" in cfg and cfg["outfile"] != dft_options.get("outfile"):
            args.append("-o " + cfg["outfile"])
        # Place input file(s) always at the end
        if "infile" in cfg:
            args.append(" ".join(cfg["infile"]))
        # Return as a nice list
        Debug("Diet command line: %s" % " ".join(args), 1)
        return args


class BaseOptions(CommandLine):
    def __init__(self, cmdline=None, dft_options={}, dft_flags={}, short_long={}):
        # Available options
        self.dft_options = dft_options
        self.dft_flags = dft_flags
        self.short_long = short_long

        # Default values for all options
        self.defaults = {}
        self.defaults.update(self.dft_options)
        self.defaults.update(self.dft_flags)

        # Needed by self._compose_*_opts()
        self.all_flags = list(self.dft_flags.keys())
        self.all_options = list(self.dft_options.keys())
        self.all_actions = []

        # Compose valid short and long options data for getopt
        self.short_opts = self._compose_short_opts()
        self.long_opts = self._compose_long_opts(extra=False)

        # Got data? Parse it!
        if cmdline:
            self.raw = self.get_raw_config(cmdline)
            self.parsed = self.parse_raw()
        else:
            self.raw = []
            self.parsed = {}

    def get(self, key):
        return self.parsed.get(key, self.defaults[key])

    def parse(self, cmdline):
        try:
            opts, args = getopt.getopt(cmdline, self.short_opts, self.long_opts)
        except getopt.error as errmsg:
            Error(
                _("%s in %%!%s command")
                % (errmsg, self.__class__.__name__[:-7].upper())
            )
        return (opts, args)

    def parse_raw(self, raw=None):
        if not raw:
            raw = self.raw
        # Reset attributes to our modest needs
        from .config import ConfigMaster
        cm = ConfigMaster(raw)
        cm.dft_options = self.dft_options.copy()
        cm.dft_flags = self.dft_flags.copy()
        cm.dft_actions = {}
        cm.dft_settings = {}
        cm.incremental = []
        cm.numeric = []
        cm.multi = []  # maybe in the future: ['infile']
        cm.defaults = self.defaults.copy()
        cm.off = cm._get_off()
        return cm.parse()


class CsvOptions(BaseOptions):
    """Tokenize and parse the %!CSV command arguments.

    When you find this line in the user document:

        %!CSV: -s tab foo.csv

    Just feed everything after the first : to this class,
    as a single string. It will be tokenized, parsed and
    saved to self.raw and self.parsed.

    Use the self.get() method to get the value of a config.
    If missing, the default value will be returned.

    Example:
        >>> import txt2tags, pprint
        >>> csvopt = txt2tags.CsvOptions('-s tab foo.csv')
        >>> pprint.pprint(csvopt.raw)
        [['all', 'separator', 'tab'],
         ['all', 'infile', 'foo.csv'],
         ['all', 'realcmdline', ['-s', 'tab', 'foo.csv']]]
        >>> pprint.pprint(csvopt.parsed)
        {'infile': 'foo.csv',
         'realcmdline': ['-s', 'tab', 'foo.csv'],
         'separator': 'tab'}
        >>> csvopt.get('separator')
        'tab'
        >>>
    """

    def __init__(self, cmdline=None):
        # Available options for %!CSV
        self.dft_options = {
            "separator": ",",
            "quotechar": "",
            "infile": "",
        }
        self.dft_flags = {
            "headers": 0,
            "borders": 0,
            "center": 0,
            "utf8": 0,
            "mailing": 0,
        }
        self.short_long = {
            "b": "borders",
            "c": "center",
            "h": "headers",
            "s": "separator",
            "q": "quotechar",
            "u": "utf8",
            "m": "mailing",
        }

        BaseOptions.__init__(
            self, cmdline, self.dft_options, self.dft_flags, self.short_long
        )


class DbOptions(BaseOptions):
    """Tokenize and parse the %!DB command arguments.

    When you find this line in the user document:

        %!DB: -q "select * from table" foo.db

    Just feed everything after the first : to this class,
    as a single string. It will be tokenized, parsed and
    saved to self.raw and self.parsed.

    Use the self.get() method to get the value of a config.
    If missing, the default value will be returned.

    Example:
        >>> import txt2tags, pprint
        >>> dbopt = txt2tags.DbOptions('-q "select * from table" foo.db')
        >>> pprint.pprint(dbopt.raw)
        [['all', 'query', 'select * from table'],
         ['all', 'infile', 'foo.db'],
         ['all', 'realcmdline', ['-q', 'select * from table', 'foo.db']]]
        >>> pprint.pprint(dbopt.parsed)
        {'infile': 'foo.db',
         'query': 'select * from table'}
        >>> dbopt.get('query')
        'select * from table'
        >>>
    """

    def __init__(self, cmdline=None):
        # Available options for %!DB
        self.dft_options = {
            "query": "",
            "infile": "",
        }
        self.dft_flags = {
            "borders": 0,
            "center": 0,
            "headers": 0,
            "mailing": 0,
        }
        self.short_long = {
            "b": "borders",
            "c": "center",
            "h": "headers",
            "q": "query",
            "m": "mailing",
        }

        BaseOptions.__init__(
            self, cmdline, self.dft_options, self.dft_flags, self.short_long
        )


class FenOptions(BaseOptions):
    def __init__(self, cmdline=None):
        # Available options for %!FEN
        self.dft_options = {
            "infile": "",
        }
        self.dft_flags = {
            "unicode": 0,
        }
        self.short_long = {
            "u": "unicode",
        }

        BaseOptions.__init__(
            self, cmdline, self.dft_options, self.dft_flags, self.short_long
        )


##############################################################################


