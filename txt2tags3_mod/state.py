# txt2tags - mutable runtime state
# All module-level variables that change during program execution.

DEBUG = 0      # --debug
VERBOSE = 0    # -v/-vv/-vvv
QUIET = 0      # --quiet
GUI = 0        # --gui

AUTOTOC = 1    # 0 once a %%toc macro was found: the TOC then goes where the user put it

RC_RAW = []
CMDLINE_RAW = []
CONF = {}
BLOCK = None
TITLE = None
MASK = None
regex = {}
TAGS = {}
rules = {}
MAILING = ""

# GUI globals
Tkinter = None
tkFileDialog = None
tkMessageBox = None

lang = "english"
TARGET = ""

file_dict = {}

# ASCII Art dynamic state
AA_COUNT = 0
AA_PW_TOC = {}
AA_IMG = 0
AA_TITLE = ""
AA_MARKS = []
