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
from .utils import error, Quit, Error, getUnknownErrorMessage, Message, Debug, get_rc_path
from .cli import CommandLine
from .config import ConfigMaster, ConfigLines
from .converter import process_source_file, get_infiles_config, convert_this_files
from .usage import Usage
from .output import listTargets
from .gui import Gui, load_GUI_resources

def exec_command_line(user_cmdline=[]):
    global Error  # state vars: state.CMDLINE_RAW, state.RC_RAW, state.DEBUG, state.VERBOSE, state.QUIET, state.GUI

    # Extract command line data
    cmdline_data = user_cmdline or sys.argv[1:]
    state.CMDLINE_RAW = CommandLine().get_raw_config(cmdline_data, relative=1)
    cmdline_parsed = ConfigMaster(state.CMDLINE_RAW).parse()
    state.DEBUG = cmdline_parsed.get("debug") or 0
    state.VERBOSE = cmdline_parsed.get("verbose") or 0
    state.QUIET = cmdline_parsed.get("quiet") or 0
    state.GUI = cmdline_parsed.get("gui") or 0
    infiles = cmdline_parsed.get("infile") or []

    Message(_("Txt2tags %s processing begins") % my_version, 1)

    # The easy ones
    if cmdline_parsed.get("help"):
        Quit(Usage())
    if cmdline_parsed.get("version"):
        Quit(VERSIONSTR)
    if cmdline_parsed.get("targets"):
        listTargets()
        Quit()

    # Multifile haters
    if len(infiles) > 1:
        errmsg = _("Option --%s can't be used with multiple input files")
        for option in NO_MULTI_INPUT:
            if cmdline_parsed.get(option):
                Error(errmsg % option)

    Debug("system platform: %s" % sys.platform)
    Debug("python version: %s" % (sys.version.split("(")[0]))
    Debug("line break char: %s" % repr(LB))
    Debug("command line: %s" % sys.argv)
    Debug("command line raw config: %s" % state.CMDLINE_RAW, 1)

    # Extract RC file config
    if cmdline_parsed.get("rc") == 0:
        Message(_("Ignoring user configuration file"), 1)
    else:
        rc_file = get_rc_path()
        if os.path.isfile(rc_file):
            Message(_("Loading user configuration file"), 1)
            state.RC_RAW = ConfigLines(file_=rc_file).get_raw_config()

        Debug("rc file: %s" % rc_file)
        Debug("rc file raw config: %s" % state.RC_RAW, 1)

    # Get all infiles config (if any)
    infiles_config = get_infiles_config(infiles)

    # Is state.GUI available?
    # Try to load and start state.GUI interface for --gui
    if state.GUI:
        try:
            load_GUI_resources()
            Debug("state.GUI resources OK (Tk module is installed)")
        except:
            Error(
                _("state.Tkinter module not found, so state.GUI is not available, use CLI instead.")
            )
        try:
            winbox = Gui()
            Debug("state.GUI display OK")
            state.GUI = 1
        except:
            Debug("state.GUI Error: no DISPLAY")
            state.GUI = 0

    # User forced --gui, but it's not available
    if cmdline_parsed.get("gui") and not state.GUI:
        print(getTraceback())
        print()
        Error(
            "Sorry, I can't run my Graphical Interface - state.GUI\n"
            "- Check if Python Tcl/Tk module is installed (state.Tkinter)\n"
            "- Make sure you are in a graphical environment (like X)"
        )

    # Okay, we will use state.GUI
    if state.GUI:
        Message(_("We are on state.GUI interface"), 1)

        # Redefine Error function to raise exception instead sys.exit()
        def Error(msg):
            tkinter.messagebox.showerror(_("txt2tags ERROR!"), msg)
            raise error

        # If no input file, get RC+cmdline config, else full config
        if not infiles:
            gui_conf = ConfigMaster(state.RC_RAW + state.CMDLINE_RAW).parse()
        else:
            try:
                gui_conf = infiles_config[0][0]
            except:
                gui_conf = {}

        # Sanity is needed to set outfile and other things
        gui_conf = ConfigMaster().sanity(gui_conf, gui=1)
        Debug("state.GUI config: %s" % gui_conf, 5)

        # Insert config and populate the nice window!
        winbox.load_config(gui_conf)
        winbox.mainwindow()

    # Console mode rocks forever!
    else:
        Message(_("We are on Command Line interface"), 1)

        # Called with no arguments, show error
        # TODO#1: this checking should be only in ConfigMaster.sanity()
        if not infiles:
            Error(
                _("Missing input file (try --help)")
                + "\n\n"
                + _("Please inform an input file (.t2t) at the end of the command.")
                + "\n"
                + _("Example:")
                + " %s -t html %s" % (my_name, _("file.t2t"))
            )

        convert_this_files(infiles_config)

    Message(_("Txt2tags finished successfully"), 1)


if __name__ == "__main__":
    try:
        exec_command_line()
    except error as msg:
        sys.stderr.write("%s\n" % msg)
        sys.stderr.flush()
        sys.exit(1)
    except SystemExit:
        pass
    except:
        sys.stderr.write(getUnknownErrorMessage())
        sys.stderr.flush()
        sys.exit(1)
    Quit()

# The End.
