# txt2tags - source document parsing and configuration management

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
from .utils import Error, Debug, Message, Readfile, dotted_spaces
from .regexes import getRegexes


class SourceDocument:
    """
    SourceDocument class - scan document structure, extract data

    It knows about full files. It reads a file and identify all
    the areas beginning (Head,Conf,Body). With this info it can
    extract each area contents.
    Note: the original line break is removed.

    DATA:
      self.arearef - Save Head, Conf, Body init line number
      self.areas   - Store the area names which are not empty
      self.buffer  - The full file contents (with NO \\r, \\n)

    METHODS:
      get()   - Access the contents of an Area. Example:
                config = SourceDocument(file).get('conf')

      split() - Get all the document Areas at once. Example:
                head, conf, body = SourceDocument(file).split()

    RULES:
        * The document parts are sequential: Head, Conf and Body.
        * One ends when the next begins.
        * The Conf Area is optional, so a document can have just
          Head and Body Areas.

        These are the Areas limits:
          - Head Area: the first three lines
          - Body Area: from the first valid text line to the end
          - Conf Area: the comments between Head and Body Areas

        Exception: If the first line is blank, this means no
        header info, so the Head Area is just the first line.
    """

    def __init__(self, filename="", contents=[]):
        self.areas = ["head", "conf", "body"]
        self.arearef = []
        self.areas_fancy = ""
        self.filename = filename
        self.buffer = []
        if filename:
            self.scan_file(filename)
        elif contents:
            self.scan(contents)

    def split(self):
        "Returns all document parts, splitted into lists."
        return self.get("head"), self.get("conf"), self.get("body")

    def get(self, areaname):
        "Returns head|conf|body contents from self.buffer"
        # Sanity
        if areaname not in self.areas:
            return []
        if not self.buffer:
            return []
        # Go get it
        bufini = 1
        bufend = len(self.buffer)
        if areaname == "head":
            ini = bufini
            end = self.arearef[1] or self.arearef[2] or bufend
        elif areaname == "conf":
            ini = self.arearef[1]
            end = self.arearef[2] or bufend
        elif areaname == "body":
            ini = self.arearef[2]
            end = bufend
        else:
            Error("Unknown Area name '%s'" % areaname)
        lines = self.buffer[ini:end]
        # Make sure head will always have 3 lines
        while areaname == "head" and len(lines) < 3:
            lines.append("")
        return lines

    def scan_file(self, filename):
        Debug("source file: %s" % filename)
        Message(_("Loading source document"), 1)
        buf = Readfile(filename, remove_linebreaks=1)
        self.scan(buf)

    def scan(self, lines):
        "Run through source file and identify head/conf/body areas"
        buf = lines
        if len(buf) == 0:
            Error(_("The input file is empty: %s") % self.filename)
        cfg_parser = ConfigLines().parse_line
        buf.insert(0, "")  # text start at pos 1
        ref = [1, 4, 0]
        if not buf[1].strip():  # no header
            ref[0] = 0
            ref[1] = 2
        rgx = getRegexes()
        on_comment_block = 0
        for i in range(ref[1], len(buf)):  # find body init:
            # Handle comment blocks inside config area
            if not on_comment_block and rgx["blockCommentOpen"].search(buf[i]):
                on_comment_block = 1
                continue
            if on_comment_block and rgx["blockCommentOpen"].search(buf[i]):
                on_comment_block = 0
                continue
            if on_comment_block:
                continue

            if buf[i].strip() and (  # ... not blank and
                buf[i][0] != "%"  # ... not comment or
                or rgx["macros"].match(buf[i])  # ... %%macro
                or rgx["toc"].match(buf[i])  # ... %%toc
                or cfg_parser(buf[i], "include")[1]  # ... %!include
                or cfg_parser(buf[i], "csv")[1]  # ... %!csv
                or cfg_parser(buf[i], "db")[1]  # ... %!db
                or cfg_parser(buf[i], "fen")[1]  # ... %!fen
            ):
                ref[2] = i
                break
        if ref[1] == ref[2]:
            ref[1] = 0  # no conf area
        for i in 0, 1, 2:  # del !existent
            if ref[i] >= len(buf):
                ref[i] = 0  # title-only
            if not ref[i]:
                self.areas[i] = ""
        Debug("Head,Conf,Body start line: %s" % ref)
        self.arearef = ref  # save results
        self.buffer = buf
        # Fancyness sample: head conf body (1 4 8)
        self.areas_fancy = "%s (%s)" % (
            " ".join(self.areas),
            " ".join(map(str, [x or "" for x in ref])),
        )
        Message(_("Areas found: %s") % self.areas_fancy, 2)

    def get_raw_config(self):
        "Handy method to get the state.CONF area RAW config (if any)"
        if not self.areas.count("conf"):
            return []
        Message(_("Scanning source document state.CONF area"), 1)
        raw = ConfigLines(
            file_=self.filename, lines=self.get("conf"), first_line=self.arearef[1]
        ).get_raw_config()
        Debug("document raw config: %s" % raw, 1)
        return raw


##############################################################################


class ConfigMaster:
    """
    ConfigMaster class - the configuration wizard

    This class is the configuration master. It knows how to handle
    the RAW and PARSED config format. It also performs the sanity
    checking for a given configuration.

    DATA:
      self.raw         - Stores the config on the RAW format
      self.parsed      - Stores the config on the PARSED format
      self.defaults    - Stores the default values for all keys
      self.off         - Stores the OFF values for all keys
      self.multi       - List of keys which can have multiple values
      self.numeric     - List of keys which value must be a number
      self.incremental - List of keys which are incremental

    RAW FORMAT:
      The RAW format is a list of lists, being each mother list item
      a full configuration entry. Any entry is a 3 item list, on
      the following format: [ state.TARGET, KEY, VALUE ]
      Being a list, the order is preserved, so it's easy to use
      different kinds of configs, as state.CONF area and command line,
      respecting the precedence.
      The special target 'all' is used when no specific target was
      defined on the original config.

    PARSED FORMAT:
      The PARSED format is a dictionary, with all the 'key : value'
      found by reading the RAW config. The self.target contents
      matters, so this dictionary only contains the target's
      config. The configs of other targets are ignored.

    The CommandLine and ConfigLines classes have the get_raw_config()
    method to convert the configuration found to the RAW format.
    Just feed it to parse() and get a brand-new ready-to-use config
    dictionary. Example:

        >>> raw = CommandLine().get_raw_config(['-n', '-H'])
        >>> print raw
        [['all', 'enum-title', ''], ['all', 'no-headers', '']]
        >>> parsed = ConfigMaster(raw).parse()
        >>> print parsed
        {'enum-title': 1, 'headers': 0}
    """

    def __init__(self, raw=[], target=""):
        self.raw = raw
        self.target = target
        self.parsed = {}
        self.dft_options = OPTIONS.copy()
        self.dft_flags = FLAGS.copy()
        self.dft_actions = ACTIONS.copy()
        self.dft_settings = SETTINGS.copy()
        self.defaults = self._get_defaults()
        self.off = self._get_off()
        self.incremental = ["verbose"]
        self.numeric = ["toc-level", "split", "width", "height"]
        self.multi = [
            "infile",
            "preproc",
            "postproc",
            "postvoodoo",
            "options",
            "style",
            "stylepath",
        ]

    def _get_defaults(self):
        "Get the default values for all config/options/flags"
        empty = {}
        for kw in CONFIG_KEYWORDS:
            empty[kw] = ""
        empty.update(self.dft_options)
        empty.update(self.dft_flags)
        empty.update(self.dft_actions)
        empty.update(self.dft_settings)
        empty["realcmdline"] = ""  # internal use only
        empty["sourcefile"] = ""  # internal use only
        empty["currentsourcefile"] = ""  # internal use only
        return empty

    def _get_off(self):
        "Turns OFF all the config/options/flags"
        off = {}
        for key in list(self.defaults.keys()):
            kind = type(self.defaults[key])
            if kind == type(9):
                off[key] = 0
            elif kind == type("") or kind == type(""):
                off[key] = ""
            elif kind == type([]):
                off[key] = []
            else:
                Error("ConfigMaster: %s: Unknown type" % key)
        return off

    def _check_target(self):
        "Checks if the target is already defined. If not, do it"
        if not self.target:
            self.target = self.find_value("target")

    def get_target_raw(self):
        "Returns the raw config for self.target or 'all'"
        ret = []
        self._check_target()
        for entry in self.raw:
            if entry[0] == self.target or entry[0] == "all":
                ret.append(entry)
        return ret

    def add(self, key, val):
        "Adds the key:value pair to the config dictionary (if needed)"
        # %!options
        if key == "options":
            # Actions are not valid inside %!options
            ignoreme = list(self.dft_actions.keys())
            # --target inside %!options is not allowed (use %!target)
            ignoreme.append("target")
            # But there are some exceptions that are allowed (XXX why?)
            ignoreme.remove("dump-config")
            ignoreme.remove("dump-source")
            ignoreme.remove("targets")
            from .cli import CommandLine
            raw_opts = CommandLine().get_raw_config(val, ignore=ignoreme)
            for target, key, val in raw_opts:
                self.add(key, val)
            return
        # The no- prefix turns OFF this key
        if key.startswith("no-"):
            key = key[3:]  # remove prefix
            val = self.off.get(key)  # turn key OFF
        # Is this key valid?
        if key not in self.defaults:
            Debug("Bogus Config %s:%s" % (key, val), 1)
            return
        # Is this value the default one?
        if val == self.defaults.get(key):
            # If default value, remove previous key:val
            if key in self.parsed:
                del self.parsed[key]
            # Nothing more to do
            return
        # Flags ON comes empty. we'll add the 1 value now
        if val == "" and (key in self.dft_flags or key in self.dft_actions):
            val = 1
        # Multi value or single?
        if key in self.multi:
            # First one? start new list
            if key not in self.parsed:
                self.parsed[key] = []
            self.parsed[key].append(val)
        # Incremental value? so let's add it
        elif key in self.incremental:
            self.parsed[key] = (self.parsed.get(key) or 0) + val
        else:
            self.parsed[key] = val
        fancykey = dotted_spaces("%12s" % key)
        Message(_("Added config") + (" %s : %s" % (fancykey, val)), 3)

    def get_outfile_name(self, config={}):
        "Dirname is the same for {in,out}file"

        infile, outfile = config["sourcefile"], config["outfile"]

        # Set output to STDOUT/MODULEOUT when no real inputfile
        if infile == STDIN and not outfile:
            outfile = STDOUT
        if infile == MODULEIN and not outfile:
            outfile = MODULEOUT

        # Automatic outfile name: infile.target
        if not outfile and (infile and config.get("target")):
            # .t2t and .txt are the only "official" source extensions
            basename = re.sub(r"\.(txt|t2t)$", "", infile)
            outfile = "%s.%s" % (basename, config["target"])
            if config["target"] == "aat" and config["slides"]:
                outfile = "%s.%s" % (basename, "aap")
            if config["target"] == "aat" and config["spread"]:
                outfile = "%s.%s" % (basename, "aas")
            if config["target"] == "aat" and config["web"]:
                outfile = "%s.%s" % (basename, "aatw")
            if config["target"] == "aat" and config["slides"] and config["web"]:
                outfile = "%s.%s" % (basename, "aapw")
            if config["target"] == "aat" and config["spread"] and config["web"]:
                outfile = "%s.%s" % (basename, "aasw")
            if config["target"] == "aat" and config["slides"] and config["print"]:
                outfile = "%s.%s" % (basename, "aapp")

        Debug(" infile: '%s'" % infile, 1)
        Debug("outfile: '%s'" % outfile, 1)
        return outfile

    def sanity(self, config, gui=0):
        "Basic config sanity checking"
        global AA
        global RST
        global CSV
        if not config:
            return {}
        target = config.get("target")
        # Some actions don't require target specification
        if not target:
            for action in NO_TARGET:
                if config.get(action):
                    target = "txt"
                    break
        # On state.GUI, some checking are skipped
        if not gui:
            # We *need* a target
            if not target:
                Error(
                    _("No target specified (try --help)")
                    + "\n\n"
                    + _(
                        "Please inform a target using the -t option or the %!target command."
                    )
                    + "\n"
                    + _("Example:")
                    + " %s -t html %s" % (my_name, _("file.t2t"))
                    + "\n\n"
                    + _("Run 'txt2tags --targets' to see all the available targets.")
                )
            # And of course, an infile also
            # TODO#1: It seems that this checking is never reached
            if not config.get("infile"):
                Error(_("Missing input file (try --help)"))
            # Is the target valid?
            if not TARGETS.count(target):
                Error(
                    _("Invalid target '%s'") % target
                    + "\n\n"
                    + _("Run 'txt2tags --targets' to see all the available targets.")
                )
        # Ensure all keys are present
        empty = self.defaults.copy()
        empty.update(config)
        config = empty.copy()
        # Check integers options
        for key in list(config.keys()):
            if key in self.numeric:
                try:
                    config[key] = int(config[key])
                except ValueError:
                    Error(_("--%s value must be a number") % key)
        # Check split level value
        if config["split"] not in (0, 1, 2):
            Error(_("Option --split must be 0, 1 or 2"))
        if target == "aap":
            target, config["slides"] = "aat", True
        if target == "aas":
            target, config["spread"] = "aat", True
        if target == "aatw":
            target, config["web"] = "aat", True
        if target == "aapw":
            target, config["slides"], config["web"] = "aat", True, True
        if target == "aasw":
            target, config["spread"], config["web"] = "aat", True, True
        if target == "aapp":
            target, config["slides"], config["print"] = "aat", True, True
        # Slides needs width and height
        if config["slides"] and target == "aat":
            if config["web"]:
                if not config["width"]:
                    config["width"] = DFT_SLIDE_WEB_WIDTH
                if not config["height"]:
                    config["height"] = DFT_SLIDE_WEB_HEIGHT
            if config["print"]:
                if not config["width"]:
                    config["width"] = DFT_SLIDE_PRINT_WIDTH
                if not config["height"]:
                    config["height"] = DFT_SLIDE_PRINT_HEIGHT
            if not config["width"] and not config["height"] and os.name == "posix":
                import fcntl
                import termios

                data = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, 4 * "00")
                term_height, term_width = struct.unpack("4H", data)[:2]
                config["height"], config["width"] = term_height - 1, term_width
            if not config["width"]:
                config["width"] = DFT_SLIDE_WIDTH
            if not config["height"]:
                config["height"] = DFT_SLIDE_HEIGHT
        # ASCII Art needs a width
        if target == "aat" and not config["width"]:
            config["width"] = DFT_TEXT_WIDTH
        if target == "aat" and config["width"] < 5:
            Error(_("--width: Expected width > 4, got %i") % config["width"])
        # Check/set user ASCII Art formatting characters
        config["unicode_art"] = False
        if config["chars"]:
            try:
                # Peace for ASCII 7-bits only
                config["chars"] = config["chars"].encode()
            except:
                if (
                    config["encoding"].lower() == "utf-8"
                    and locale.getpreferredencoding() != "UTF-8"
                ):
                    Error(
                        _(
                            "--chars: Expected chars from an UTF-8 terminal for your UTF-8 file"
                        )
                    )
                if (
                    config["encoding"].lower() != "utf-8"
                    and locale.getpreferredencoding() == "UTF-8"
                ):
                    if not config["encoding"]:
                        Error(
                            _(
                                "--chars: Expected an UTF-8 file for your chars from an UTF-8 terminal, you could set %!encoding: UTF-8"
                            )
                        )
                    else:
                        Error(
                            _(
                                "--chars: Expected an UTF-8 file for your chars from an UTF-8 terminal"
                            )
                        )
            if target == "aat":
                if config["chars"] == "unicode":
                    config["unicode_art"] = True
                    if config["encoding"].lower() != "utf-8":
                        if not config["encoding"]:
                            Error(
                                _(
                                    "--chars: Expected an UTF-8 file for the unicode chars set, you could set %!encoding: UTF-8"
                                )
                            )
                        else:
                            Error(
                                _(
                                    "--chars: Expected an UTF-8 file for the unicode chars set"
                                )
                            )
                    config["chars"] = (
                        chr(0x250C)
                        + chr(0x2510)
                        + chr(0x2514)
                        + chr(0x2518)
                        + chr(0x252C)
                        + chr(0x2534)
                        + chr(0x251C)
                        + chr(0x2524)
                        + chr(0x255E)
                        + chr(0x256A)
                        + chr(0x2561)
                        + chr(0x256C)
                        + chr(0x2565)
                        + chr(0x256B)
                        + chr(0x2568)
                        + chr(0x253C)
                        + chr(0x2500)
                        + chr(0x2502)
                        + chr(0x2500)
                        + chr(0x2550)
                        + chr(0x2550)
                        + chr(0x2500)
                        + '^"'
                        + chr(0x2043)
                        + chr(0x2550)
                        + chr(0x2551)
                        + "8"
                    )
                if len(config["chars"]) != len(AA_SIMPLE) and len(
                    config["chars"]
                ) != len(AA_ADVANCED):
                    Error(
                        _("--chars: Expected %i or %i chars, got %i")
                        % (len(AA_SIMPLE), len(AA_ADVANCED), len(config["chars"]))
                    )
                if isinstance(config["chars"], str):
                    for char in config["chars"]:
                        if unicodedata.east_asian_width(char) in ("F", "W"):
                            Error(
                                _(
                                    "--chars: Expected no CJK double width chars, but got %s"
                                )
                                % char.encode("utf-8")
                            )
                if len(config["chars"]) == len(AA_SIMPLE):
                    config["chars"] = 15 * config["chars"][0] + config["chars"]
                AA = dict(list(zip(AA_KEYS, config["chars"])))
            elif target == "rst":
                if len(config["chars"]) != len(RST_VALUES):
                    Error(
                        _("--chars: Expected %i chars, got %i")
                        % (len(RST_VALUES), len(config["chars"]))
                    )
                else:
                    # http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#sections
                    chars_section = r"!\"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"
                    for char in config["chars"][:7]:
                        if char not in chars_section:
                            if locale.getpreferredencoding() == "UTF-8":
                                char = char.encode("utf-8")
                            Error(
                                _("--chars: Expected chars in : %s but got %s")
                                % (chars_section, char)
                            )
                    # http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#bullet-lists
                    chars_bullet, char_8 = "*+-", config["chars"][7]
                    if char_8 not in chars_bullet:
                        if locale.getpreferredencoding() == "UTF-8":
                            char_8 = char_8.encode("utf-8")
                        Error(
                            _("--chars: Expected chars in : %s but got %s")
                            % (chars_bullet, char_8)
                        )
                    RST = dict(list(zip(RST_KEYS, config["chars"])))
            elif target in ("csv", "csvs"):
                if (
                    len(config["chars"]) != len(CSV_VALUES)
                    and len(config["chars"]) != len(CSV_VALUES) + 1
                ):
                    Error(
                        _("--chars: Expected %i or %i chars, got %i")
                        % (len(CSV_VALUES), len(CSV_VALUES) + 1, len(config["chars"]))
                    )
                else:
                    CSV = dict(list(zip(CSV_KEYS, config["chars"])))

        if target == "ods":
            if not config["encoding"]:
                config["encoding"] = "UTF-8"

        # --toc-only is stronger than others
        if config["toc-only"]:
            config["headers"] = 0
            config["toc"] = 0
            config["split"] = 0
            config["gui"] = 0
            config["outfile"] = config["outfile"] or STDOUT
        # Splitting is disable for now (future: HTML only, no STDOUT)
        config["split"] = 0
        # Restore target
        config["target"] = target
        # Set output file name
        config["outfile"] = self.get_outfile_name(config)
        # Checking suicide
        if (
            os.path.abspath(config["sourcefile"]) == os.path.abspath(config["outfile"])
            and config["outfile"] not in [STDOUT, MODULEOUT]
            and not gui
        ):
            Error(_("Input and Output files are the same: %s") % config["outfile"])
        if target == "db":
            try:
                import sqlite3
            except:
                Error("No sqlite3 module")
            global DB, DBC
            try:
                os.remove(config["outfile"])
            except:
                pass
            DB = sqlite3.connect(config["outfile"])
            DBC = DB.cursor()
        return config

    def parse(self):
        "Returns the parsed config for the current target"
        raw = self.get_target_raw()
        for target, key, value in raw:
            if key == "chars" and locale.getpreferredencoding() == "UTF-8":
                self.add(key, value.decode("utf-8"))
            else:
                self.add(key, value)
        Message(
            _("Added the following keys: %s") % ", ".join(list(self.parsed.keys())), 2
        )
        return self.parsed.copy()

    def find_value(self, key="", target=""):
        "Scans ALL raw config to find the desired key"
        ret = []
        # Scan and save all values found
        for targ, k, val in self.raw:
            if k == key and (targ == target or targ == "all"):
                ret.append(val)
        if not ret:
            return ""
        # If not multi value, return only the last found
        if key in self.multi:
            return ret
        else:
            return ret[-1]


########################################################################


class ConfigLines:
    """
    ConfigLines class - the config file data extractor

    This class reads and parse the config lines on the %!key:val
    format, converting it to RAW config. It deals with user
    config file (RC file), source document state.CONF area and
    %!includeconf directives.

    Call it passing a file name or feed the desired config lines.
    Then just call the get_raw_config() method and wait to
    receive the full config data on the RAW format. This method
    also follows the possible %!includeconf directives found on
    the config lines. Example:

        raw = ConfigLines(file=".txt2tagsrc").get_raw_config()

    The parse_line() method is also useful to be used alone,
    to identify and tokenize a single config line. For example,
    to get the %!include command components, on the source
    document BODY:

        target, key, value = ConfigLines().parse_line(body_line)
    """

    # parse_line regexes, moved here to avoid recompilation
    _parse_cfg = re.compile(
        r"""
        ^%!\s*                # leading id with opt spaces
        (?P<name>\w+)\s*       # config name
        (\((?P<target>\w*)\))? # optional target spec inside ()
        \s*:\s*               # key:value delimiter with opt spaces
        (?P<value>\S.+?)      # config value
        \s*$                  # rstrip() spaces and hit EOL
        """,
        re.I + re.VERBOSE,
    )
    _parse_prepost = re.compile(
        r"""
                                      # ---[ PATTERN ]---
        ^( "([^"]*)"          # "double quoted" or
        | '([^']*)'           # 'single quoted' or
        | ([^\s]+)            # single_word
        )
        \s+                   # separated by spaces
                                  # ---[ REPLACE ]---
        ( "([^"]*)"           # "double quoted" or
        | '([^']*)'           # 'single quoted' or
        | (.*)                # anything
        )
        \s*$
        """,
        re.VERBOSE,
    )
    _parse_guicolors = re.compile(r"^([^\s]+\s+){3}[^\s]+")  # 4 tokens

    def __init__(self, file_="", lines=[], first_line=1):
        self.file = file_ or "NOFILE"
        self.lines = lines
        self.first_line = first_line
        if file_:
            self.folder = os.path.dirname(self.file)
        else:
            self.folder = ""

    def load_lines(self):
        "Make sure we've loaded the file contents into buffer"
        if not self.lines and not self.file:
            Error("ConfigLines: No file or lines provided")
        if not self.lines:
            self.lines = self.read_config_file(self.file)

    def read_config_file(self, filename=""):
        "Read a Config File contents, aborting on invalid line"
        if not filename:
            return []
        errormsg = _("Invalid CONFIG line on %s") + "\n%03d:%s"
        lines = Readfile(filename, remove_linebreaks=1)
        # Sanity: try to find invalid config lines
        for i in range(len(lines)):
            line = lines[i].rstrip()
            if not line:  # empty
                continue
            if line[0] != "%":
                Error(errormsg % (filename, i + 1, line))
        return lines

    def include_config_file(self, file_=""):
        "Perform the %!includeconf action, returning RAW config"
        if not file_:
            return []

        # Fix config file path
        file_ = self.fix_config_relative_path(file_)

        # Read and parse included config file contents
        return ConfigLines(file_=file_).get_raw_config()

    def fix_config_relative_path(self, path_):
        """
        The path for external files must be relative to the config file path.
        External files appear in: %!includeconf, %!style, %!template.
        See issue 71.
        """
        from .cli import PathMaster
        return PathMaster().join(self.folder, path_)

    def get_raw_config(self):
        "Scan buffer and extract all config as RAW (including includes)"
        ret = []
        self.load_lines()
        first = self.first_line

        def add(target, key, val):
            "Save the RAW config"
            ret.append([target, key, val])
            Message(_("Added %s") % key, 3)

        for i in range(len(self.lines)):
            line = self.lines[i]
            Message(_("Processing line %03d: %s") % (first + i, line), 2)
            target, key, val = self.parse_line(line)

            if not key:  # no config on this line
                continue

            # %!style
            # We need to fix the CSS files path. See issue 71.
            #
            # This stylepath config holds the fixed path for each CSS file.
            # This path is used when composing headers, inside doHeader().
            #
            if key == "style":
                stylepath = self.fix_config_relative_path(val)
                add(target, "stylepath", stylepath)
                # Note: the normal 'style' config will be added later

            # %!options
            if key == "options":
                # Prepend --dirname option to track config file original folder
                if self.folder:
                    val = "--dirname %s %s" % (self.folder, val)

            # %!includeconf
            if key == "includeconf":
                # Sanity
                err = _("A file cannot include itself (loop!)")
                if val == self.file:
                    Error("%s: %%!includeconf: %s" % (err, self.file))

                more_raw = self.include_config_file(val)
                ret.extend(more_raw)

                Message(_("Finished Config file inclusion: %s") % val, 2)

            # Normal config, except %!includeconf
            else:
                add(target, key, val)
        return ret

    def parse_line(self, line="", keyname="", target=""):
        "Detects %!key:val config lines and extract data from it"
        empty = ["", "", ""]
        if not line:
            return empty
        no_target = ["target", "includeconf"]
        # XXX TODO <value>\S.+?  requires TWO chars, breaks %!include:a
        cfgregex = ConfigLines._parse_cfg
        prepostregex = ConfigLines._parse_prepost
        guicolors = ConfigLines._parse_guicolors

        # Give me a match or get out
        match = cfgregex.match(line)
        if not match:
            return empty

        if keyname and keyname != match.group("name"):
            return empty
        if target and match.group("target") not in (None, "", target):
            return empty

        # Save information about this config
        name = (match.group("name") or "").lower()
        target = (match.group("target") or "all").lower()
        value = match.group("value")

        # %!keyword(target) not allowed for these
        if name in no_target and match.group("target"):
            Error(_("You can't use (target) with %s") % ("%!" + name) + "\n%s" % line)

        # Force no_target keywords to be valid for all targets
        if name in no_target:
            target = "all"

        # Special config for state.GUI colors
        if name == "guicolors":
            valmatch = guicolors.search(value)
            if not valmatch:
                return empty
            value = re.split(r"\s+", value)

        # Special config with two quoted values (%!preproc: "foo" 'bar')
        if name in ["preproc", "postproc", "postvoodoo"]:
            valmatch = prepostregex.search(value)
            if not valmatch:
                return empty
            getval = valmatch.group
            patt = getval(2) or getval(3) or getval(4) or ""
            repl = getval(6) or getval(7) or getval(8) or ""
            value = (patt, repl)
        return [target, name, value]


##############################################################################


