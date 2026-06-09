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
from .utils import Error, Debug
from .regexes import getRegexes
from .aa import (
    aa_line, aa_under, aa_quote, aa_box, aa_header, aa_slide, aa_table,
    aa_image, aa_wrap, aa_lencjk, aa_slicecjk, TextWrapperCJK, aa_center,
    SpreadSheet, spreadsheet, completes_table, convert_to_table,
    parse_convert_table, math_print,
)
from .output import (
    cc_formatter, doEscape, doFinalEscape, doProtect,
    enclose_me, fix_relative_path, get_tagged_link,
    beautify_me, compile_filters, maskEscapeChar, unmaskEscapeChar,
    EscapeCharHandler, get_escapes, addLineBreaks, expandLineBreaks,
    parse_deflist_term, get_image_align, get_encoding_string,
    doCommentLine,
)
from .cli import PathMaster



class MaskMaster:
    """(Un)Protect important structures from escaping and formatting.

    Some inline markup must be protected, because its contents may match
    other markup, or because we should not escape or format its contents
    in any way.

    When the source line is read, we call the mask() method to identify
    those inliners (link, mono, macro, raw, tagged) and change each one
    for an (ugly) internal identifier.

    For example, ''<b>this</b>'' will become vvvTAGGED0vvv. The number
    increases as other inliners of the same type are found.

    The method undo() is called at the end of the line processing,
    expanding all masks back to their original (untouched) content.
    """

    def __init__(self):
        self.linkmask = "vvvLINKNNNvvv"  # NNN will be replaced by the index
        self.monomask = "vvvMONONNNvvv"
        self.macromask = "vvvMACRONNNvvv"
        self.rawmask = "vvvRAWNNNvvv"
        self.taggedmask = "vvvTAGGEDNNNvvv"
        self.mathmask = "vvvMATHNNNvvv"
        self.tocmask = "vvvTOCvvv"
        self.linkmaskre = re.compile(r"vvvLINK(\d+)vvv")
        self.monomaskre = re.compile(r"vvvMONO(\d+)vvv")
        self.macromaskre = re.compile(r"vvvMACRO(\d+)vvv")
        self.rawmaskre = re.compile(r"vvvRAW(\d+)vvv")
        self.taggedmaskre = re.compile(r"vvvTAGGED(\d+)vvv")
        self.mathmaskre = re.compile(r"vvvMATH(\d+)vvv")
        self.macroman = MacroMaster()
        self.reset()

    def reset(self):
        self.linkbank = []
        self.monobank = []
        self.macrobank = []
        self.rawbank = []
        self.taggedbank = []
        self.mathbank = []
        self.math_masks = []

    def mask(self, line=""):
        global AUTOTOC

        # The verbatim, raw, tagged and math inline marks are mutually exclusive.
        # This means that one can't appear inside the other.
        # If found, the inner marks must be ignored.
        # Example: ``foo ""bar"" ''baz''``
        # In HTML: <code>foo ""bar"" ''baz''</code>
        #
        # The trick here is to protect the mark who appears first on the line.
        # The four regexes are tried and the one with the lowest index wins.
        # If none is found (else), we get out of the loop.
        #
        while True:
            # Try to match the line for the three marks
            t = r = v = m = len(line) + 1  # fixme: Py3 valid solution?

            try:
                t = state.regex["tagged"].search(line).start()
            except:
                pass
            try:
                r = state.regex["raw"].search(line).start()
            except:
                pass
            try:
                v = state.regex["fontMono"].search(line).start()
            except:
                pass
            try:
                m = state.regex["math"].search(line).start()
            except:
                pass

            # Protect tagged text
            if t >= 0 and t < r and t < v and t < m:
                txt = state.regex["tagged"].search(line).group(1)
                txt = doProtect(state.TARGET, txt)
                i = len(self.taggedbank)
                self.taggedbank.append(txt)
                mask = self.taggedmask.replace("NNN", str(i))
                line = state.regex["tagged"].sub(mask, line, 1)

            # Protect raw text
            elif r >= 0 and r < t and r < v and r < m:
                txt = state.regex["raw"].search(line).group(1)
                txt = doEscape(state.TARGET, txt)
                i = len(self.rawbank)
                self.rawbank.append(txt)
                mask = self.rawmask.replace("NNN", str(i))
                line = state.regex["raw"].sub(mask, line, 1)

            # Protect verbatim text
            elif v >= 0 and v < t and v < r and v < m:
                txt = state.regex["fontMono"].search(line).group(1)
                txt = doEscape(state.TARGET, txt)
                i = len(self.monobank)
                self.monobank.append(txt)
                mask = self.monomask.replace("NNN", str(i))
                line = state.regex["fontMono"].sub(mask, line, 1)

            # Protect math formula
            elif m >= 0 and m < t and m < v and m < r:
                txt = state.regex["math"].search(line).group(1)
                txt = doEscape(state.TARGET, txt)
                i = len(self.mathbank)
                self.mathbank.append(txt)
                mask = self.mathmask.replace("NNN", str(i))
                self.math_masks.append(mask)
                line = state.regex["math"].sub(mask, line, 1)
            else:
                break

        # Protect macros
        while state.regex["macros"].search(line):
            txt = state.regex["macros"].search(line).group()
            i = len(self.macrobank)
            self.macrobank.append(txt)
            mask = self.macromask.replace("NNN", str(i))
            line = state.regex["macros"].sub(mask, line, 1)

        # Protect TOC location
        while state.regex["toc"].search(line):
            line = state.regex["toc"].sub(self.tocmask, line)
            AUTOTOC = 0

        # Protect URLs and emails
        while state.regex["linkmark"].search(line) or state.regex["link"].search(line):
            # Try to match plain or named links
            match_link = state.regex["link"].search(line)
            match_named = state.regex["linkmark"].search(line)

            # Define the current match
            if match_link and match_named:
                # Both types found, which is the first?
                m = match_link
                if match_named.start() < match_link.start():
                    m = match_named
            else:
                # Just one type found, we're fine
                m = match_link or match_named

            # Extract link data and apply mask
            if m == match_link:  # plain link
                link = m.group()
                label = ""
                link_re = state.regex["link"]
            else:  # named link
                link = fix_relative_path(m.group("link"))
                label = m.group("label").rstrip()
                link_re = state.regex["linkmark"]

            # Save link data to the link bank
            i = len(self.linkbank)
            self.linkbank.append((label, link))

            # Mask the link mark in the original line
            mask = self.linkmask.replace("NNN", str(i))
            line = link_re.sub(mask, line, 1)

        return line

    def undo(self, line):
        # url & email
        matches = list(self.linkmaskre.finditer(line))
        while matches:
            m = matches.pop()
            i = int(m.group(1))
            label, url = self.linkbank[i]
            link = get_tagged_link(label, url)
            line = line[0 : m.start()] + link + line[m.end() :]

        # Expand macros
        matches = list(self.macromaskre.finditer(line))
        while matches:
            m = matches.pop()
            i = int(m.group(1))
            macro = self.macroman.expand(self.macrobank[i])
            line = line[0 : m.start()] + macro + line[m.end() :]

        # Expand verb
        matches = list(self.monomaskre.finditer(line))
        while matches:
            m = matches.pop()
            i = int(m.group(1))
            open_, close = state.TAGS["fontMonoOpen"], state.TAGS["fontMonoClose"]
            line = (
                line[0 : m.start()] + open_ + self.monobank[i] + close + line[m.end() :]
            )

        # Expand raw
        matches = list(self.rawmaskre.finditer(line))
        while matches:
            m = matches.pop()
            i = int(m.group(1))
            line = line[0 : m.start()] + self.rawbank[i] + line[m.end() :]

        # Expand tagged
        matches = list(self.taggedmaskre.finditer(line))
        while matches:
            m = matches.pop()
            i = int(m.group(1))
            line = line[0 : m.start()] + self.taggedbank[i] + line[m.end() :]

        # Expand math
        matches = list(self.mathmaskre.finditer(line))
        while matches:
            mask = self.math_masks.pop()
            m = matches.pop()
            i = int(m.group(1))
            if state.TARGET in ["aat", "tex", "html5"]:
                mathp = math_print(state.TARGET, self.mathbank[i]).split("\n")
            if not isinstance(line, list):
                line_start = line[0 : m.start()]
                line_end = line[m.end() :]
            else:
                midline_start = line[middle][0 : m.start()]
                midline_end = line[middle][m.end() :]
            if state.TARGET == "aat":
                if len(mathp) > 1:
                    middle = len(mathp) / 2
                    if not isinstance(line, list):
                        line = (
                            [" " * len(line_start) + l for l in mathp[:middle]]
                            + [line_start + mathp[middle] + line_end]
                            + [" " * len(line_start) + l for l in mathp[middle + 1 :]]
                        )
                    else:
                        diff_mask = len(mask) - len(mathp[middle])
                        diff_line = len(line) - len(mathp)
                        up_lines = [""] * (abs(diff_line) / 2)
                        down_lines = [""] * (abs(diff_line) - (abs(diff_line) / 2))
                        if diff_line < 0:
                            line = up_lines + line + down_lines
                        else:
                            mathp = up_lines + mathp + down_lines
                        middle = len(mathp) / 2
                        if diff_mask < 0:
                            line = (
                                [
                                    " " * len(midline_start)
                                    + m
                                    + " " * abs(diff_mask)
                                    + l[len(midline_start + m) :]
                                    for m, l in zip(mathp[:middle], line[:middle])
                                ]
                                + [midline_start + mathp[middle] + midline_end]
                                + [
                                    " " * len(midline_start)
                                    + m
                                    + " " * abs(diff_mask)
                                    + l[len(midline_start + m) :]
                                    for m, l in zip(
                                        mathp[middle + 1 :], line[middle + 1 :]
                                    )
                                ]
                            )
                        else:
                            line = (
                                [
                                    " " * len(midline_start)
                                    + m
                                    + l[len(midline_start + m) + diff_mask :]
                                    for m, l in zip(mathp[:middle], line[:middle])
                                ]
                                + [midline_start + mathp[middle] + midline_end]
                                + [
                                    " " * len(midline_start)
                                    + m
                                    + l[len(midline_start + m) + diff_mask :]
                                    for m, l in zip(
                                        mathp[middle + 1 :], line[middle + 1 :]
                                    )
                                ]
                            )

                else:
                    if not isinstance(line, list):
                        line = line_start + mathp[0] + line_end
                    else:
                        diff_mask = len(mask) - len(mathp[0])
                        if diff_mask < 0:
                            line = (
                                [" " * abs(diff_mask) + l for l in line[:middle]]
                                + [midline_start + mathp[0] + midline_end]
                                + [" " * abs(diff_mask) + l for l in line[middle + 1 :]]
                            )
                        else:
                            line = (
                                [l[diff_mask:] for l in line[:middle]]
                                + [midline_start + mathp[0] + midline_end]
                                + [l[diff_mask:] for l in line[middle + 1 :]]
                            )
            elif state.TARGET == "tex":
                line = line_start + "$" + mathp[0] + "$" + line_end
            elif state.TARGET == "html5":
                line = "\n".join([line_start, "<math>"] + mathp[2:-1] + [line_end])
            else:
                line = line_start + self.mathbank[i] + line_end

        return line


##############################################################################


class TitleMaster:
    "Title things"

    def __init__(self):
        self.count = ["", 0, 0, 0, 0, 0]
        self.toc = []
        self.level = 0
        self.kind = ""
        self.txt = ""
        self.label = ""
        self.tag = ""
        self.tag_hold = []
        self.last_level = 0
        self.count_id = ""
        self.anchor_count = 0
        self.anchor_prefix = "toc"

    def _open_close_blocks(self):
        "Open new title blocks, closing the previous (if any)"
        if not state.rules["titleblocks"]:
            return
        tag = ""
        last = self.last_level
        curr = self.level

        # Same level, just close the previous
        if curr == last:
            tag = state.TAGS.get("title%dClose" % last)
            if tag:
                self.tag_hold.append(tag)

        # Section -> subsection, more depth
        while curr > last:
            last += 1

            # Open the new block of subsections
            tag = state.TAGS.get("blockTitle%dOpen" % last)
            if tag:
                self.tag_hold.append(tag)

            # Jump from title1 to title3 or more
            # Fill the gap with an empty section
            if curr - last > 0:
                tag = state.TAGS.get("title%dOpen" % last)
                tag = state.regex["x"].sub("", tag)  # del \a
                if tag:
                    self.tag_hold.append(tag)

        # Section <- subsection, less depth
        while curr < last:
            # Close the current opened subsection
            tag = state.TAGS.get("title%dClose" % last)
            if tag:
                self.tag_hold.append(tag)

            # Close the current opened block of subsections
            tag = state.TAGS.get("blockTitle%dClose" % last)
            if tag:
                self.tag_hold.append(tag)

            last -= 1

            # Close the previous section of the same level
            # The subsections were under it
            if curr == last:
                tag = state.TAGS.get("title%dClose" % last)
                if tag:
                    self.tag_hold.append(tag)

    def add(self, line):
        "Parses a new title line."
        if not line:
            return
        self._set_prop(line)
        self._open_close_blocks()
        self._set_count_id()
        self._set_label()
        self._save_toc_info()

    def close_all(self):
        "Closes all opened title blocks"
        ret = []
        ret.extend(self.tag_hold)
        while self.level:
            tag = state.TAGS.get("title%dClose" % self.level)
            if tag:
                ret.append(tag)
            tag = state.TAGS.get("blockTitle%dClose" % self.level)
            if tag:
                ret.append(tag)
            self.level -= 1
        return ret

    def _save_toc_info(self):
        "Save TOC info, used by self.dump_marked_toc()"
        self.toc.append((self.level, self.count_id, self.txt, self.label))

    def _set_prop(self, line=""):
        "Extract info from original line and set data holders."
        # Detect title type (numbered or not)
        id_ = line.lstrip()[0]
        if id_ == "=":
            kind = "title"
        elif id_ == "+":
            kind = "numtitle"
        else:
            Error("Unknown Title ID '%s'" % id_)
        # Extract line info
        match = state.regex[kind].search(line)
        level = len(match.group("id"))
        txt = match.group("txt").strip()
        label = match.group("label")
        # Parse info & save
        if state.CONF["enum-title"]:
            kind = "numtitle"  # force
        if state.rules["titleblocks"]:
            self.tag = state.TAGS.get("%s%dOpen" % (kind, level)) or state.TAGS.get(
                "title%dOpen" % level
            )
        else:
            self.tag = state.TAGS.get(kind + str(level)) or state.TAGS.get("title" + str(level))
        self.last_level = self.level
        self.kind = kind
        self.level = level
        self.txt = txt
        self.label = label

    def _set_count_id(self):
        "Compose and save the title count identifier (if needed)."
        count_id = ""
        if self.kind == "numtitle" and not state.rules["autonumbertitle"]:
            # Manually increase title count
            self.count[self.level] += 1
            # Reset sublevels count (if any)
            max_levels = len(self.count)
            if self.level < max_levels - 1:
                for i in range(self.level + 1, max_levels):
                    self.count[i] = 0
            # Compose count id from hierarchy
            for i in range(self.level):
                count_id = "%s%d." % (count_id, self.count[i + 1])
        self.count_id = count_id

    def _set_label(self):
        "Compose and save title label, used by anchors."
        # Remove invalid chars from label set by user
        self.label = re.sub("[^A-Za-z0-9_-]", "", self.label or "")
        # Generate name as 15 first :alnum: chars
        # TODO how to translate safely accented chars to plain?
        # self.label = re.sub('[^A-Za-z0-9]', '', self.txt)[:15]
        # 'tocN' label - sequential count, ignoring 'toc-level'
        # self.label = self.anchor_prefix + str(len(self.toc) + 1)

    def _get_tagged_anchor(self):
        "Return anchor if user defined a label, or TOC is on."
        ret = ""
        label = self.label
        if state.CONF["toc"] and self.level <= state.CONF["toc-level"]:
            # This count is needed bcos self.toc stores all
            # titles, regardless of the 'toc-level' setting,
            # so we can't use self.toc length to number anchors
            self.anchor_count += 1
            # Autonumber label (if needed)
            label = label or "%s%s" % (self.anchor_prefix, self.anchor_count)
        if label and state.TAGS["anchor"]:
            ret = state.regex["x"].sub(label, state.TAGS["anchor"])
        return ret

    def _get_full_title_text(self):
        "Returns the full title contents, already escaped."
        ret = self.txt
        # Insert count_id (if any) before text
        if self.count_id:
            ret = "%s %s" % (self.count_id, ret)
        # Escape specials
        ret = doEscape(state.TARGET, ret)
        # Same targets needs final escapes on title lines
        # It's here because there is a 'continue' after title
        if state.rules["finalescapetitle"]:
            ret = doFinalEscape(state.TARGET, ret)
        return ret

    def get(self):
        "Returns the tagged title as a list."
        # global (use state.) AA_TITLE, AA_COUNT
        ret = []

        # Maybe some anchoring before?
        anchor = self._get_tagged_anchor()
        self.tag = state.regex["_anchor"].sub(anchor, self.tag)

        ### Compose & escape title text (TOC uses unescaped)
        full_title = self._get_full_title_text()

        # Close previous section area
        ret.extend(self.tag_hold)
        self.tag_hold = []

        tagged = state.regex["x"].sub(full_title, self.tag)

        if state.rules["tableonly"]:
            state.AA_TITLE = full_title.replace(" ", "_")
            state.AA_COUNT = 0

        # Adds "underline" on TXT target
        if state.TARGET == "txt":
            if state.BLOCK.count > 1:
                ret.append("")  # blank line before
            ret.append(tagged)
            i = aa_lencjk(full_title)
            ret.append(state.regex["x"].sub("=" * i, self.tag))
        elif state.TARGET == "aat" and self.level == 1:
            if state.CONF["slides"]:
                state.AA_TITLE = tagged
            else:
                if state.BLOCK.count > 1:
                    ret.append("")  # blank line before
                box = aa_box([tagged], AA, state.CONF["width"])
                if state.CONF["web"] and state.CONF["toc"]:
                    ret.extend([anchor] + box + ["</a>"])
                else:
                    ret.extend(box)
        elif state.TARGET == "aat":
            level = "level" + str(self.level)
            if state.BLOCK.count > 1:
                ret.append("")  # blank line before
            if state.CONF["slides"]:
                under = aa_under(tagged, AA[level], state.CONF["width"] - 2, False)
            else:
                under = aa_under(tagged, AA[level], state.CONF["width"], False)
            if (
                state.CONF["web"]
                and state.CONF["toc"]
                and self.level <= state.CONF["toc-level"]
                and not state.CONF["slides"]
            ):
                ret.extend([anchor] + under + ["</a>"])
            else:
                ret.extend(under)
        elif state.TARGET == "rst" and self.level == 1:
            if state.BLOCK.count > 1:
                ret.append("")  # blank line before
            ret.extend(aa_under(tagged, RST["level1"], 10000, True))
        elif state.TARGET == "rst":
            level = "level" + str(self.level)
            if state.BLOCK.count > 1:
                ret.append("")  # blank line before
            ret.extend(aa_under(tagged, RST[level], 10000, False))
        else:
            ret.append(tagged)
        return ret

    def dump_marked_toc(self, max_level=99):
        "Dumps all toc itens as a valid t2t-marked list"
        ret = []
        toc_count = 1
        head = 0
        if state.CONF["headers"] and state.CONF["header1"]:
            head = 1
        for level, count_id, txt, label in self.toc:
            if level > max_level:  # ignore
                continue
            indent = "  " * level
            id_txt = ("%s %s" % (count_id, txt)).lstrip()
            if state.CONF["target"] == "aat" and state.CONF["slides"]:
                indent = "  " * (level - 1)
                if state.CONF["web"] and not state.CONF["toc-only"]:
                    label = str(state.AA_PW_TOC[txt] / state.CONF["height"] + head + 2) + ".0"
            label = label or self.anchor_prefix + str(toc_count)
            toc_count += 1

            # TOC will have crosslinks to anchors
            if state.TAGS["anchor"]:
                if state.CONF["enum-title"] and level == 1:
                    # 1. [Foo #anchor] is more readable than [1. Foo #anchor] in level 1.
                    # This is a stoled idea from Windows .CHM help files.
                    tocitem = '%s+ [""%s"" #%s]' % (indent, txt, label)
                else:
                    tocitem = '%s- [""%s"" #%s]' % (indent, id_txt, label)

            # TOC will be plain text (no links)
            else:
                if state.rules["plaintexttoc"] and not state.CONF["slides"]:
                    # For these, the list is not necessary, just dump the text
                    tocitem = '%s""%s""' % (indent, id_txt)
                elif state.TARGET == "aat" and state.CONF["enum-title"] and level == 1:
                    tocitem = '%s+ ""%s""' % (indent, txt)
                else:
                    tocitem = '%s- ""%s""' % (indent, id_txt)
            ret.append(tocitem)
        return ret


##############################################################################

# Table syntax reference for targets:
# http://www.mediawiki.org/wiki/Help:Tables
# http://moinmo.in/HelpOnMoinWikiSyntax#Tables
# http://moinmo.in/HelpOnTables
# http://www.wikicreole.org/wiki/Creole1.0#section-Creole1.0-Tables
# http://www.wikicreole.org/wiki/Tables
# http://www.pmwiki.org/wiki/PmWiki/Tables
# http://www.dokuwiki.org/syntax#tables
# http://michelf.com/projects/php-markdown/extra/#table
# http://code.google.com/p/support/wiki/WikiSyntax#Tables
# http://www.biblioscape.com/rtf15_spec.htm
# http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#tables
#
# Good reading:
# http://www.wikicreole.org/wiki/ListOfTableMarkups
#
# See also:
# test/marks/table.t2t
# test/target/table.t2t


# TODO check all this table mess
# It uses parse_row properties for table lines
# state.BLOCK.table() replaces the cells by the parsed content
#
class TableMaster:
    def __init__(self, line=""):
        self.rows = []
        self.border = 0
        self.align = "Left"
        self.cellalign = []
        self.colalign = []
        self.cellspan = []
        if line:
            prop = self.parse_row(line)
            self.border = prop["border"]
            self.title = prop["title"]
            self.vert_head = prop["vert_head"]
            self.align = prop["align"]
            self.cellalign = prop["cellalign"]
            self.cellspan = prop["cellspan"]
            self.n_cols = sum(self.cellspan)
            self.colalign = self._get_col_align()

    def _get_col_align(self):
        colalign = []
        for cell in range(0, len(self.cellalign)):
            align = self.cellalign[cell]
            span = self.cellspan[cell]
            colalign.extend([align] * span)
        return colalign

    def _get_full_tag(self, topen):
        # topen     = state.TAGS['tableOpen']
        tborder = state.TAGS["_tableBorder"]
        talign = state.TAGS["_tableAlign" + self.align]
        calignsep = state.TAGS["tableColAlignSep"]
        calign = ""

        # The first line defines if table has border or not
        if not self.border:
            tborder = ""
        # Set the columns alignment
        if state.rules["tablecellaligntype"] == "column":
            calign = [state.TAGS["_tableColAlign%s" % x] for x in self.colalign]
            calign = calignsep.join(calign)
        # Align full table, set border and Column align (if any)
        topen = state.regex["_tableAlign"].sub(talign, topen)
        topen = state.regex["_tableBorder"].sub(tborder, topen)
        topen = state.regex["_tableColAlign"].sub(calign, topen)
        # Tex table spec, border or not: {|l|c|r|} , {lcr}
        if calignsep and not self.border:
            # Remove cell align separator
            topen = topen.replace(calignsep, "")
        return topen

    def _get_cell_align(self, cells):
        ret = []
        for cell in cells:
            align = "Left"
            if cell.strip():
                if cell[0] == " " and cell[-1] == " ":
                    align = "Center"
                elif cell[0] == " ":
                    align = "Right"
            ret.append(align)
        return ret

    def _get_cell_span(self, cells):
        ret = []
        for cell in cells:
            span = 1
            m = re.search(r"\a(\|+)$", cell)
            if m:
                span = len(m.group(1)) + 1
            ret.append(span)
        return ret

    def _tag_cells(self, rowdata):
        cells = rowdata["cells"]
        open_ = state.TAGS["tableCellOpen"]
        close = state.TAGS["tableCellClose"]
        sep = state.TAGS["tableCellSep"]
        head = state.TAGS["tableCellHead"]
        caligntag = [state.TAGS["tableCellAlign" + x] for x in rowdata["cellalign"]]
        if state.TARGET == "ods" and self.border:
            rowdata["cellalign"] = [align + "Border" for align in rowdata["cellalign"]]
        calign = [state.TAGS["_tableCellAlign" + x] for x in rowdata["cellalign"]]
        calignsep = state.TAGS["tableColAlignSep"]
        ncolumns = len(self.colalign)

        # Populate the span and multicol open tags
        cspan = []
        ccovered = []
        multicol = []
        colindex = 0

        thisspan = 0
        spanmultiplier = state.rules["cellspanmultiplier"] or 1

        cellhead = []
        cellbody = []

        for cellindex in range(0, len(rowdata["cellspan"])):
            span = rowdata["cellspan"][cellindex]
            align = rowdata["cellalign"][cellindex]

            # hack to get cell size/span into rtf, in twips
            if state.rules["cellspancumulative"]:
                thisspan += span
            else:
                thisspan = span
            span = thisspan * spanmultiplier

            if span > 1:
                if state.TAGS["_tableCellColSpanChar"]:
                    # spanchar * n
                    cspan.append(state.TAGS["_tableCellColSpanChar"] * (span - 1))
                    # Note: using -1 for moin, where spanchar == cell delimiter
                else:
                    # \a replaced by n
                    cspan.append(state.regex["x"].sub(str(span), state.TAGS["_tableCellColSpan"]))
                    ccovered.append(
                        state.regex["x"].sub(str(span - 1), state.TAGS["tableCellCovered"])
                    )

                mcopen = state.regex["x"].sub(str(span), state.TAGS["_tableCellMulticolOpen"])
                multicol.append(mcopen)
            else:
                cspan.append("")
                ccovered.append("")

                if colindex < ncolumns and align != self.colalign[colindex]:
                    mcopen = state.regex["x"].sub("1", state.TAGS["_tableCellMulticolOpen"])
                    multicol.append(mcopen)
                else:
                    multicol.append("")

            if not self.border:
                multicol[-1] = multicol[-1].replace(calignsep, "")

            colindex += span

        # Maybe is it a title row?
        if rowdata["title"]:
            # Defaults to normal cell tag if not found
            open_ = state.TAGS["tableTitleCellOpen"] or open_
            close = state.TAGS["tableTitleCellClose"] or close
            sep = state.TAGS["tableTitleCellSep"] or sep
            head = state.TAGS["tableTitleCellHead"] or head

        # Should we break the line on *each* table cell?
        if state.rules["breaktablecell"]:
            close = close + "\n"

        # Cells pre processing
        if state.rules["tablecellstrip"]:
            cells = [x.strip() for x in cells]
        if rowdata["title"] and state.rules["tabletitlerowinbold"]:
            cells = [enclose_me("fontBold", x) for x in cells]

        # Add cell BEGIN/END tags
        for i, cell in enumerate(cells):
            # Lout requires special routines, cells are labeled according alphabet
            if state.TARGET == "lout":
                alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                if len(rowdata["cellspan"]) < self.n_cols:
                    tblabel = alphabet[sum(rowdata["cellspan"][0:i])]
                else:
                    tblabel = alphabet[i]
                copen = re.sub("[\x07]", "", tblabel + open_)
            else:
                copen = open_
            cclose = close
            chead = head
            if self.vert_head and i == 0:
                if state.TARGET == "lout":
                    copen = copen + state.TAGS["tableTitleCellOpen"]
                    cclose = cclose + state.TAGS["tableTitleCellClose"]
                else:
                    copen = state.TAGS["tableTitleCellOpen"] or copen
                    cclose = state.TAGS["tableTitleCellClose"] or cclose

                if state.rules["breaktablecell"]:
                    cclose = cclose + "\n"

            # Make sure we will pop from some filled lists
            # Fixes empty line bug '| |'
            this_align = this_cell = this_span = this_mcopen = this_covered = ""
            if calign:
                this_align = calign.pop(0)
            if caligntag:
                this_cell = caligntag.pop(0)
            if cspan:
                this_span = cspan.pop(0)
            if ccovered:
                this_covered = ccovered.pop(0)
            if multicol:
                this_mcopen = multicol.pop(0)

            # Insert cell align into open tag (if cell is alignable)
            if state.rules["tablecellaligntype"] == "cell":
                copen = state.regex["_tableCellAlign"].sub(this_align, copen)
                cclose = state.regex["_tableCellAlign"].sub(this_align, cclose)
                chead = state.regex["_tableCellAlign"].sub(this_align, chead)

                # Insert cell data into cellAlign tags
                if this_cell:
                    cell = state.regex["x"].sub(cell, this_cell)

            # Insert cell span into open tag (if cell is spannable)
            if state.rules["tablecellspannable"]:
                copen = state.regex["_tableCellColSpan"].sub(this_span, copen)
                cclose = state.regex["_tableCellColSpan"].sub(this_span, cclose)
                chead = state.regex["_tableCellColSpan"].sub(this_span, chead)

            if state.rules["tablecellcovered"]:
                cclose = cclose + this_covered

            # Use multicol tags instead (if multicol supported, and if
            # cell has a span or is aligned differently to column)
            if state.rules["tablecellmulticol"]:
                if this_mcopen:
                    copen = state.regex["_tableColAlign"].sub(this_align, this_mcopen)
                    cclose = state.TAGS["_tableCellMulticolClose"]

            # RTF target requires the border in each cell
            border = ""
            if self.border:
                border = state.TAGS["_tableCellBorder"]
            copen = state.regex["_tableBorder"].sub(border, copen)
            cclose = state.regex["_tableBorder"].sub(border, cclose)
            chead = state.regex["_tableBorder"].sub(border, chead)

            # Attribute delimiter, added when align/span attributes were used
            # Example: Wikipedia table cell, without and with attributes:
            # | cell contents
            # | align="right" colspan="2" | cell contents
            #
            if state.regex["_tableAttrDelimiter"].search(copen):
                if this_align or this_span:
                    copen = state.regex["_tableAttrDelimiter"].sub(
                        state.TAGS["_tableAttrDelimiter"], copen
                    )
                else:
                    copen = state.regex["_tableAttrDelimiter"].sub("", copen)  # remove marker

            if chead:
                cellhead.append(chead)
            cellbody.append(copen + cell + cclose)

        # Maybe there are cell separators?
        return "".join(cellhead) + sep.join(cellbody)

    def add_row(self, cells):
        self.rows.append(cells)

    def parse_row(self, line):
        # Default table properties
        ret = {
            "border": 0,
            "title": 0,
            "vert_head": 0,
            "align": "Left",
            "cells": [],
            "cellalign": [],
            "cellspan": [],
        }
        # Detect table align (and remove spaces mark)
        if line[0] == " ":
            ret["align"] = "Center"
        line = line.lstrip()
        # Detect vertical header mark
        if line[1] == "_":
            ret["vert_head"] = 1
            line = line[0] + line[2:]
        # Detect horizontal and vertical headers mark
        if line[1] == "/":
            ret["vert_head"] = 1
            line = line[0] + "|" + line[2:]
        # Detect title mark
        if line[1] == "|":
            ret["title"] = 1
        # Detect border mark and normalize the EOL
        m = re.search(r" (\|+) *$", line)
        if m:
            line = line + " "
            ret["border"] = 1
        else:
            line = line + " | "
        # Delete table mark
        line = state.regex["table"].sub("", line)
        # Detect colspan  | foo | bar baz |||
        line = re.sub(r" (\|+)\| ", "\a\\1 | ", line)
        # Split cells (the last is fake)
        ret["cells"] = line.split(" | ")[:-1]
        # Find cells span
        ret["cellspan"] = self._get_cell_span(ret["cells"])
        # Remove span ID
        ret["cells"] = [re.sub(r"\a\|+$", "", x) for x in ret["cells"]]
        # Find cells align
        ret["cellalign"] = self._get_cell_align(ret["cells"])
        # Hooray!
        Debug("Table Prop: %s" % ret, 7)
        return ret

    def dump(self):
        open_ = self._get_full_tag(state.TAGS["tableOpen"])
        if state.TARGET in ["ods", "csv", "csvs"]:
            # global (use state.) AA_COUNT
            if state.AA_TITLE:
                if state.AA_COUNT:
                    if state.TARGET == "ods":
                        open_ = re.sub("table_name", state.AA_TITLE + "_", open_)
                        open_ = re.sub("n_table", str(state.AA_COUNT), open_)
                    else:
                        csv_file = state.AA_TITLE + "_" + str(state.AA_COUNT)
                    state.AA_COUNT += 1
                else:
                    if state.TARGET == "ods":
                        open_ = re.sub("table_name", state.AA_TITLE, open_)
                        open_ = re.sub("n_table", "", open_)
                    else:
                        csv_file = state.AA_TITLE
                    state.AA_COUNT = 2
            else:
                if state.TARGET == "ods":
                    open_ = re.sub("n_table", str(state.BLOCK.tablecount), open_)
                    open_ = re.sub("table_name", _("Sheet"), open_)
                else:
                    csv_file = _("Sheet") + str(state.BLOCK.tablecount)
        if state.rules["tablenumber"]:
            open_ = re.sub("n_table", str(state.BLOCK.tablecount), open_)
        if state.rules["tablecolumnsnumber"]:
            # Lout requires alphabetical index
            alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            open_ = re.sub("n_cols", str(self.n_cols), open_)
        rows = self.rows
        close = self._get_full_tag(state.TAGS["tableClose"])

        rowopen = self._get_full_tag(state.TAGS["tableRowOpen"])
        rowclose = self._get_full_tag(state.TAGS["tableRowClose"])
        rowsep = self._get_full_tag(state.TAGS["tableRowSep"])
        titrowopen = self._get_full_tag(state.TAGS["tableTitleRowOpen"]) or rowopen
        titrowclose = self._get_full_tag(state.TAGS["tableTitleRowClose"]) or rowclose

        if state.rules["breaktablelineopen"]:
            rowopen = rowopen + "\n"
            titrowopen = titrowopen + "\n"

        # Tex gotchas
        if state.TARGET in ["tex", "texs"]:
            if not self.border:
                rowopen = titrowopen = ""
            else:
                close = rowopen + close

        # Now we tag all the table cells on each row
        # tagged_cells = map(lambda x: self._tag_cells(x), rows)  #!py15
        tagged_cells = []
        for cell in rows:
            tagged_cells.append(self._tag_cells(cell))

        # Add row separator tags between lines
        tagged_rows = []
        if rowsep:
            #!py15
            # tagged_rows = map(lambda x: x + rowsep, tagged_cells)
            for cell in tagged_cells:
                tagged_rows.append(cell + rowsep)
            # Remove last rowsep, because the table is over
            tagged_rows[-1] = tagged_rows[-1].replace(rowsep, "")
        # Add row BEGIN/END tags for each line
        else:
            for rowdata in rows:
                if rowdata["title"]:
                    o, c = titrowopen, titrowclose
                else:
                    o, c = rowopen, rowclose
                row = tagged_cells.pop(0)
                if state.TARGET == "lout":
                    calign = [state.TAGS["_tableCellAlign" + x] for x in rowdata["cellalign"]]
                    element = rowdata["cellspan"]
                    spandef = ""
                    regdef = ""
                    # In Lout the format of a row can be defined once after table
                    # setup or for each row separately. For automatization the
                    # second approach is chosen.
                    formatdef = "format { "

                    for i in range(0, len(element)):
                        regdef += " @Cell " + calign[i] + alphabet[i] + " |"
                    regdef = formatdef + re.sub(r"\|$", "", regdef) + " }\n"

                    # Set up Lout definition for spanning cells
                    if 1 <= len(element) < self.n_cols:
                        spandef += formatdef
                        inccol = 0
                        for i in range(0, len(element)):
                            if (element[i] == 1 and i == 0) or (
                                element[i] == 1 and element[i - 1] == 1
                            ):
                                spandef += (
                                    " @Cell " + calign[i] + alphabet[i + inccol] + " |"
                                )
                            if element[i] == 1 and i > 0 and element[i - 1] > 1:
                                spandef += (
                                    " @Cell " + calign[i] + alphabet[i + inccol] + " |"
                                )
                            if element[i] > 1:
                                spandef += (
                                    " @StartHVSpan @Cell "
                                    + calign[i]
                                    + alphabet[i + inccol]
                                    + " |"
                                )
                                for j in range(1, element[i]):
                                    spandef += " @HSpan |"
                                    inccol += 1
                        spandef = re.sub(r"\|$", "", spandef)
                        spandef += "}\n"
                        regdef = spandef

                    if rowdata["title"]:
                        # Necessary to get a heading over every page on Multi-page
                        # tables AND over first row
                        tagged_rows.append(titrowopen + regdef + row + titrowclose)
                        tagged_rows.append(rowopen + regdef + row + rowclose)
                    else:
                        tagged_rows.append(o + regdef + row + c)

                else:
                    tagged_rows.append(o + row + c)

        # Join the pieces together
        fulltable = []
        if open_:
            fulltable.append(open_)
        fulltable.extend(tagged_rows)
        if close:
            fulltable.append(close)

        if state.TARGET in ["csv", "csvs"]:
            state.file_dict[csv_file + "." + state.TARGET] = fulltable

        return fulltable


##############################################################################


class BlockMaster:
    "TIP: use blockin/out to add/del holders"

    def __init__(self):
        self.BLK = []
        self.HLD = []
        self.PRP = []
        self.depth = 0
        self.count = 0
        self.last = ""
        self.tableparser = None
        self.tablecount = 0
        self.contains = {
            "para": ["comment", "raw", "tagged"],
            "verb": [],
            "table": ["comment"],
            "raw": [],
            "tagged": [],
            "comment": [],
            "quote": ["quote", "comment", "raw", "tagged"],
            "list": [
                "list",
                "numlist",
                "deflist",
                "para",
                "verb",
                "comment",
                "raw",
                "tagged",
            ],
            "numlist": [
                "list",
                "numlist",
                "deflist",
                "para",
                "verb",
                "comment",
                "raw",
                "tagged",
            ],
            "deflist": [
                "list",
                "numlist",
                "deflist",
                "para",
                "verb",
                "comment",
                "raw",
                "tagged",
            ],
            "bar": [],
            "title": [],
            "numtitle": [],
        }
        self.allblocks = list(self.contains.keys())

        # If one is found inside another, ignore the marks
        self.exclusive = ["comment", "verb", "raw", "tagged"]

        # May we include bars inside quotes?
        if state.rules["barinsidequote"]:
            self.contains["quote"].append("bar")

    def block(self):
        if not self.BLK:
            return ""
        return self.BLK[-1]

    def isblock(self, name=""):
        return self.block() == name

    def prop(self, key):
        if not self.PRP:
            return ""
        return self.PRP[-1].get(key) or ""

    def propset(self, key, val):
        self.PRP[-1][key] = val
        # Debug('state.BLOCK prop ++: %s->%s' % (key, repr(val)), 1)
        # Debug('state.BLOCK props: %s' % (repr(self.PRP)), 1)

    def hold(self):
        if not self.HLD:
            return []
        return self.HLD[-1]

    def holdadd(self, line):
        if self.block().endswith("list"):
            line = [line]
        self.HLD[-1].append(line)
        Debug("HOLD add: %s" % repr(line), 4)
        Debug("FULL HOLD: %s" % self.HLD, 4)

    def holdaddsub(self, line):
        self.HLD[-1][-1].append(line)
        Debug("HOLD addsub: %s" % repr(line), 4)
        Debug("FULL HOLD: %s" % self.HLD, 4)

    def holdextend(self, lines):
        if self.block().endswith("list"):
            lines = [lines]
        self.HLD[-1].extend(lines)
        Debug("HOLD extend: %s" % repr(lines), 4)
        Debug("FULL HOLD: %s" % self.HLD, 4)

    def blockin(self, block):
        ret = []
        if block not in self.allblocks:
            Error("Invalid block '%s'" % block)

        # First, let's close other possible open blocks
        while self.block() and block not in self.contains[self.block()]:
            ret.extend(self.blockout())

        # Now we can gladly add this new one
        self.BLK.append(block)
        self.HLD.append([])
        self.PRP.append({})
        self.count += 1
        if block == "table":
            self.tableparser = TableMaster()
        # Deeper and deeper
        self.depth = len(self.BLK)
        Debug("block ++ (%s): %s" % (block, self.BLK), 3)
        return ret

    def blockout(self):
        if not self.BLK:
            Error("No block to pop")
        blockname = self.BLK.pop()
        result = getattr(self, blockname)()
        parsed = self.HLD.pop()
        self.PRP.pop()
        self.depth = len(self.BLK)

        if state.rules["tableonly"] and blockname != "table":
            return []

        if blockname == "table":
            del self.tableparser

        # Inserting a nested block into mother
        if self.block():
            if blockname != "comment":  # ignore comment blocks
                if self.block().endswith("list"):
                    self.HLD[-1][-1].append(result)
                else:
                    self.HLD[-1].append(result)
            # Reset now. Mother block will have it all
            result = []

        Debug("block -- (%s): %s" % (blockname, self.BLK), 3)
        Debug("RELEASED (%s): %s" % (blockname, parsed), 3)

        # Save this top level block name (produced output)
        # The next block will use it
        if result:
            self.last = blockname
            if state.rules["iswrapped"]:
                final = []
                if state.TARGET != "aat":
                    for line in result:
                        if not line or blockname in ("verb", "tagged"):
                            final.append(line)
                        else:
                            final.extend(aa_wrap(line, state.CONF["width"], False))
                elif state.CONF["slides"] and blockname in ("list", "numlist", "deflist"):
                    final.extend(
                        aa_box(
                            result,
                            AA,
                            state.CONF["width"],
                            False,
                            web=state.CONF["web"],
                            slides=state.CONF["slides"],
                        )
                    )
                else:
                    for line in result:
                        if (
                            not line
                            or (
                                blockname in ("table", "tagged", "verb")
                                and not state.CONF["slides"]
                            )
                            or (blockname == "quote" and state.CONF["slides"])
                        ):
                            final.append(line)
                        else:
                            if state.CONF["slides"] and blockname in (
                                "table",
                                "tagged",
                                "verb",
                            ):
                                final.append(line[: state.CONF["width"]])
                            elif state.CONF["slides"]:
                                final.extend(
                                    " " + line
                                    for line in aa_wrap(
                                        line, state.CONF["width"] - 2, state.CONF["web"]
                                    )
                                )
                            else:
                                final.extend(aa_wrap(line, state.CONF["width"], state.CONF["web"]))
                result = final[:]

            Debug("state.BLOCK: %s" % result, 6)

        # ASCII Art processing
        # global (use state.) AA_TITLE, AA_COUNT, AA_PW_TOC, AA_IMG
        if (
            state.TARGET == "aat"
            and state.CONF["slides"]
            and not state.CONF["toc-only"]
            and not state.CONF.get("art-no-title")
        ):
            len_res = len(result)
            for el in result:
                if "<img" in el:
                    len_res = len_res + state.AA_IMG
            n = state.CONF["height"] - (state.AA_COUNT % state.CONF["height"] + 1)
            spaces = [""] * n
            if n < len_res and not (
                state.TITLE.level == 1 and blockname in ["title", "numtitle"]
            ):
                end_line = aa_line(AA["bar1"], state.CONF["width"])
                slide_head = aa_slide(state.AA_TITLE, AA["bar2"], state.CONF["width"], state.CONF["web"])
                if state.CONF["web"]:
                    if len_res > state.CONF["height"] - 6:
                        result[state.CONF["height"] - 7] = (
                            result[state.CONF["height"] - 7] + "</pre></section>"
                        )
                        for i, line in enumerate(result[state.CONF["height"] - 6 :]):
                            j = i % state.CONF["height"]
                            if j == 0:
                                result[i + state.CONF["height"] - 6] = "<section><pre>" + line
                            elif j == state.CONF["height"] - 1:
                                result[i + state.CONF["height"] - 6] = (
                                    line + "</pre></section>"
                                )
                    result = (
                        spaces
                        + [end_line + "</pre></section>"]
                        + slide_head
                        + [""]
                        + result
                    )
                elif state.CONF["print"]:
                    result = spaces + [end_line + ""] + slide_head + [""] + result
                else:
                    result = spaces + [end_line] + slide_head + [""] + result
            if (
                blockname in ["title", "numtitle"] and state.TITLE.level == 1
            ) or not state.AA_TITLE:
                if not state.AA_TITLE:
                    state.AA_TITLE = os.path.splitext(state.CONF["sourcefile"])[0].capitalize()
                end_line = aa_line(AA["bar2"], state.CONF["width"])
                aa_title = aa_slide(
                    state.AA_TITLE, AA["bar2"], state.CONF["width"], state.CONF["web"]
                ) + [""]
                if state.AA_COUNT:
                    if state.CONF["web"]:
                        aa_title = spaces + [end_line + "</pre></section>"] + aa_title
                    elif state.CONF["print"]:
                        aa_title = spaces + [end_line + ""] + aa_title
                    else:
                        aa_title = spaces + [end_line] + aa_title
                result = aa_title + result
            state.AA_COUNT += len(result) + state.AA_IMG
            state.AA_IMG = 0
            if blockname in ["title", "numtitle"]:
                state.AA_PW_TOC[state.TITLE.txt] = state.AA_COUNT

        return result

    def _last_escapes(self, line):
        return doFinalEscape(state.TARGET, line)

    def _get_escaped_hold(self):
        ret = []
        for line in self.hold():
            linetype = type(line)
            if linetype == type("") or linetype == type(""):
                ret.append(self._last_escapes(line))
            elif linetype == type([]):
                ret.extend(line)
            else:
                Error("BlockMaster: Unknown HOLD item type: %s" % linetype)
        return ret

    def _remove_twoblanks(self, lastitem):
        if len(lastitem) > 1 and lastitem[-2:] == ["", ""]:
            return lastitem[:-2]
        return lastitem

    def _should_add_blank_line(self, where, blockname):
        "Validates the blanksaround* state.rules"

        # Nestable blocks: only mother blocks (level 1) are spaced
        if blockname.endswith("list") and self.depth > 1:
            return False

        # The blank line after the block is always added
        if where == "after" and state.rules["blanksaround" + blockname]:
            return True

        # # No blank before if it's the first block of the body
        # elif where == 'before' \
        #   and state.BLOCK.count == 1:
        #   return False

        # # No blank before if it's the first block of this level (nested)
        # elif where == 'before' \
        #   and self.count == 1:
        #   return False

        # The blank line before the block is only added if
        # the previous block haven't added a blank line
        # (to avoid consecutive blanks)
        elif (
            where == "before"
            and state.rules["blanksaround" + blockname]
            and not state.rules.get("blanksaround" + self.last)
        ):
            return True

        # Nested quotes are handled here,
        # because the mother quote isn't closed yet
        elif (
            where == "before"
            and blockname == "quote"
            and state.rules["blanksaround" + blockname]
            and self.depth > 1
        ):
            return True

        return False

    # functions to help encode block depth into RTF formatting
    def _apply_depth(self, line, level):
        # convert block depth into an indent in twips
        depth = level
        multiply = state.rules["blockdepthmultiply"]
        if depth > 0 and state.rules["depthmultiplyplus"]:
            depth = depth + state.rules["depthmultiplyplus"]
        if multiply:
            depth = depth * multiply
        return state.regex["_blockDepth"].sub(str(depth), line)

    def _apply_list_level(self, line, level):
        mylevel = level
        if state.rules["listlevelzerobased"]:
            mylevel = mylevel - 1
        return state.regex["_listLevel"].sub(str(mylevel), line)

    def comment(self):
        return ""

    def raw(self):
        lines = self.hold()
        return [doEscape(state.TARGET, x) for x in lines]

    def tagged(self):
        return self.hold()

    def para(self):
        result = []
        open_ = state.TAGS["paragraphOpen"]
        close = state.TAGS["paragraphClose"]
        lines = self._get_escaped_hold()

        # Blank line before?
        if self._should_add_blank_line("before", "para"):
            result.append("")

        # RTF needs depth level encoded into nested paragraphs
        mydepth = self.depth
        if state.rules["zerodepthparagraph"]:
            mydepth = 0
        open_ = self._apply_depth(open_, mydepth)

        # Open tag
        if open_:
            result.append(open_)

        # Pagemaker likes a paragraph as a single long line
        if state.rules["onelinepara"]:
            result.append(" ".join(lines))
        # Others are normal :)
        else:
            result.extend(lines)

        # Close tag
        if close:
            result.append(close)

        # Blank line after?
        if self._should_add_blank_line("after", "para"):
            result.append("")

        # Very very very very very very very very very UGLY fix
        # Needed because <center> can't appear inside <p>
        try:
            if (
                len(lines) == 1
                and state.TARGET in ("html", "xhtml", "xhtmls", "wp")
                and re.match(r"^\s*<center>.*</center>\s*$", lines[0])
            ):
                result = [lines[0]]
        except:
            pass

        return result

    def verb(self):
        "Verbatim lines are not masked, so there's no need to unmask"
        result = []
        open_ = state.TAGS["blockVerbOpen"]
        close = state.TAGS["blockVerbClose"]
        sep = state.TAGS["blockVerbSep"]

        # Blank line before?
        if self._should_add_blank_line("before", "verb"):
            result.append("")

        # Open tag
        if open_:
            result.append(open_)

        # Get contents
        for line in self.hold():
            if self.prop("mapped") == "table":
                line = MacroMaster().expand(line)
            if not state.rules["verbblocknotescaped"]:
                line = doEscape(state.TARGET, line)
            if state.TAGS["blockVerbLine"]:
                line = state.TAGS["blockVerbLine"] + line
            if state.rules["indentverbblock"]:
                line = "  " + line
            if state.rules["verbblockfinalescape"]:
                line = doFinalEscape(state.TARGET, line)
            result.append(line)
            if sep:
                result.append(sep)

        if sep:
            result.pop()

        # Close tag
        if close:
            result.append(close)

        # Blank line after?
        if self._should_add_blank_line("after", "verb"):
            result.append("")

        return result

    def numtitle(self):
        return self.title("numtitle")

    def title(self, name="title"):
        result = []

        # Blank line before?
        if self._should_add_blank_line("before", name):
            result.append("")

        # Get contents
        result.extend(state.TITLE.get())

        # Blank line after?
        if self._should_add_blank_line("after", name):
            result.append("")

        return result

    def table(self):
        self.tablecount += 1
        result = []

        if state.TARGET == "aat" and self.tableparser.rows:
            if state.CONF["spread"]:
                data = spreadsheet(
                    completes_table(self.tableparser.rows),
                    state.rules["spreadmarkup"],
                    state.rules["spreadgrid"],
                )
                return aa_table(
                    data,
                    AA,
                    state.CONF["width"],
                    True,
                    True,
                    True,
                    "Center",
                    True,
                    state.CONF["web"],
                ) + [""]
            else:
                return aa_table(
                    completes_table(self.tableparser.rows),
                    AA,
                    state.CONF["width"],
                    self.tableparser.border,
                    self.tableparser.title,
                    self.tableparser.vert_head,
                    self.tableparser.align,
                    False,
                    False,
                ) + [""]

        if state.TARGET == "rst" and self.tableparser.rows:
            chars = AA.copy()
            if not self.tableparser.border:
                chars["border"] = "="
                chars["tlcorner"] = chars["trcorner"] = chars["cross"] = chars[
                    "blcorner"
                ] = chars["brcorner"] = chars["lcross"] = chars["side"] = chars[
                    "rcross"
                ] = chars["tcross"] = chars["bcross"] = chars["lhhead"] = chars[
                    "rhhead"
                ] = " "
            return aa_table(
                completes_table(self.tableparser.rows),
                chars,
                state.CONF["width"],
                self.tableparser.border,
                self.tableparser.title,
                False,
                "Left",
                False,
                False,
            ) + [""]

        if state.TARGET == "mgp" and self.tableparser.rows:
            aa_t = aa_table(
                completes_table(self.tableparser.rows),
                AA,
                state.CONF["width"],
                True,
                self.tableparser.title,
                False,
                "Left",
                False,
                False,
            )
            try:
                import aafigure

                t_name = "table_" + str(self.tablecount) + ".png"
                aafigure.render(
                    str("\n".join(aa_t)),
                    t_name,
                    {
                        "format": "png",
                        "background": "#000000",
                        "foreground": "#FFFFFF",
                        "textual": True,
                    },
                )
                return ["%center", '%newimage "' + t_name + '"']
            except:
                return ['%font "mono"'] + aa_t + [""]

        if state.TARGET == "db" and self.tableparser.rows:
            data = completes_table(self.tableparser.rows)
            n = max([len(line[0]) for line in data])
            table = "table_" + str(self.tablecount)
            if self.tableparser.title:
                cols = [s.strip().replace(" ", "_") for s in data[0][0]]
                del data[0]
            else:
                cols = []
                for i in range(n):
                    cols.append("col_" + str(i + 1))
            cols_insert = ", ".join(cols)
            cols_create = " text, ".join(cols) + " text"
            sql_create = (
                "create table "
                + table
                + " (id integer primary key, "
                + cols_create
                + ")"
            )
            DBC.execute(sql_create)
            sql_insert = (
                "insert into "
                + table
                + " ("
                + cols_insert
                + ") values"
                + " ("
                + ("?," * n)[:-1]
                + ")"
            )
            for line in data:
                DBC.execute(sql_insert, line[0])
            DB.commit()

        # Blank line before?
        if self._should_add_blank_line("before", "table"):
            result.append("")

        # Rewrite all table cells by the unmasked and escaped data
        lines = self._get_escaped_hold()
        for i in range(len(lines)):
            cells = lines[i].split(SEPARATOR)
            self.tableparser.rows[i]["cells"] = cells
        if state.rules["spread"]:
            data = spreadsheet(
                completes_table(self.tableparser.rows),
                state.rules["spreadmarkup"],
                state.rules["spreadgrid"],
            )
            self.tableparser.border, len_line = True, len(data[0][0])
            self.tableparser.cellalign = len_line
            self.tableparser.colalign = len_line * ["Left"]
            if state.rules["spreadgrid"]:
                self.tableparser.vert_head = True
                self.tableparser.rows = [
                    {
                        "cells": data[0][0],
                        "cellspan": data[0][1],
                        "cellalign": ["Left"] * len_line,
                        "title": 1,
                    }
                ] + self.tableparser.rows
                for i, row in enumerate(self.tableparser.rows[1:]):
                    row["cells"], row["cellspan"], row["cellalign"], row["title"] = (
                        data[i + 1][0],
                        data[i + 1][1],
                        ["Left"] * len_line,
                        0,
                    )
            else:
                for i, row in enumerate(self.tableparser.rows):
                    row["cells"], row["cellspan"], row["cellalign"], row["title"] = (
                        data[i][0],
                        data[i][1],
                        ["Left"] * len_line,
                        0,
                    )
        result.extend(self.tableparser.dump())

        # Blank line after?
        if self._should_add_blank_line("after", "table"):
            result.append("")

        return result

    def quote(self):
        result = []
        open_ = state.TAGS["blockQuoteOpen"]  # block based
        close = state.TAGS["blockQuoteClose"]
        qline = state.TAGS["blockQuoteLine"]  # line based
        indent = tagindent = "\t" * self.depth

        # Apply state.rules
        if state.rules["tagnotindentable"]:
            tagindent = ""
        if not state.rules["keepquoteindent"]:
            indent = ""

        # Blank line before?
        if self._should_add_blank_line("before", "quote"):
            result.append("")

        # RTF needs depth level encoded into almost everything
        open_ = self._apply_depth(open_, self.depth)

        # Open tag
        if open_:
            result.append(tagindent + open_)

        itemisclosed = False

        # Get contents
        if state.rules["onelinequote"]:
            # XXX Dirty hack, won't work for nested blocks inside quote (when TABS are used in your t2t source), even subquotes
            result.append(" ".join([state.regex["quote"].sub("", x) for x in self.hold()]))
        else:
            for item in self.hold():
                if type(item) == type([]):
                    if close and state.rules["quotenotnested"]:
                        result.append(tagindent + close)
                        itemisclosed = True
                    result.extend(item)  # subquotes
                else:
                    if open_ and itemisclosed:
                        result.append(tagindent + open_)
                    item = state.regex["quote"].sub("", item)  # del TABs
                    item = self._last_escapes(item)
                    if state.CONF["target"] == "aat" and not state.CONF["slides"]:
                        result.extend(
                            aa_quote(
                                item, qline, " ", state.CONF["width"], self.depth, state.CONF["web"]
                            )
                        )
                    elif state.CONF["target"] == "aat" and state.CONF["slides"]:
                        result.extend(
                            aa_box(
                                [item],
                                AA,
                                state.CONF["width"],
                                web=state.CONF["web"],
                                slides=state.CONF["slides"],
                            )
                        )
                    else:
                        item = qline * self.depth + item
                        result.append(indent + item)  # quote line

        # Close tag
        if close and not itemisclosed:
            result.append(tagindent + close)

        # Blank line after?
        if self._should_add_blank_line("after", "quote"):
            result.append("")

        return result

    def bar(self):
        result = []
        bar_tag = ""

        # Blank line before?
        if self._should_add_blank_line("before", "bar"):
            result.append("")

        # Get the original bar chars
        bar_chars = self.hold()[0].strip()

        # Set bar type
        if bar_chars.startswith("="):
            bar_tag = state.TAGS["bar2"]
        else:
            bar_tag = state.TAGS["bar1"]

        # To avoid comment tag confusion like <!-- ------ --> (sgml)
        if state.TAGS["comment"].count("--"):
            bar_chars = bar_chars.replace("--", "__")

        # Get the bar tag (may contain \a)
        result.append(state.regex["x"].sub(bar_chars, bar_tag))

        # Blank line after?
        if self._should_add_blank_line("after", "bar"):
            result.append("")

        return result

    def deflist(self):
        return self.list("deflist")

    def numlist(self):
        return self.list("numlist")

    def list(self, name="list"):
        result = []
        items = self.hold()
        indent = self.prop("indent")
        tagindent = indent
        listline = state.TAGS.get(name + "ItemLine")
        itemcount = 0

        if name == "deflist":
            itemopen = state.TAGS[name + "Item1Open"]
            itemclose = state.TAGS[name + "Item2Close"]
            itemsep = state.TAGS[name + "Item1Close"] + state.TAGS[name + "Item2Open"]
        else:
            itemopen = state.TAGS[name + "ItemOpen"]
            itemclose = state.TAGS[name + "ItemClose"]
            itemsep = ""

        # Apply state.rules
        if state.rules["tagnotindentable"]:
            tagindent = ""
        if not state.rules["keeplistindent"]:
            indent = tagindent = ""

        # RTF encoding depth
        itemopen = self._apply_depth(itemopen, self.depth)
        itemopen = self._apply_list_level(itemopen, self.depth)

        # ItemLine: number of leading chars identifies list depth
        if listline:
            if state.rules["listlineafteropen"]:
                itemopen = itemopen + listline * self.depth
            else:
                itemopen = listline * self.depth + itemopen

        # Adds trailing space on opening tags
        if (name == "list" and state.rules["spacedlistitemopen"]) or (
            name == "numlist" and state.rules["spacednumlistitemopen"]
        ):
            itemopen = itemopen + " "

        # Remove two-blanks from list ending mark, to avoid <p>
        items[-1] = self._remove_twoblanks(items[-1])

        # Blank line before?
        if self._should_add_blank_line("before", name):
            result.append("")

        if state.rules["blanksaroundnestedlist"]:
            result.append("")

        # Tag each list item (multiline items), store in listbody
        itemopenorig = itemopen
        listbody = []
        widelist = 0
        if state.CONF["slides"]:
            width = state.CONF["width"] - 6
        else:
            width = state.CONF["width"]
        for item in items:
            # Add "manual" item count for noautonum targets
            itemcount += 1
            if name == "numlist" and not state.rules["autonumberlist"]:
                n = str(itemcount)
                itemopen = state.regex["x"].sub(n, itemopenorig)
                del n

            # Tag it
            item[0] = self._last_escapes(item[0])
            if name == "deflist":
                z, term, rest = item[0].split(SEPARATOR, 2)
                item[0] = rest
                if not item[0]:
                    del item[0]  # to avoid <p>
                listbody.append(tagindent + itemopen + term + itemsep)
            else:
                fullitem = tagindent + itemopen
                if state.TARGET == "aat":
                    listbody.extend(
                        aa_quote(
                            item[0].replace(SEPARATOR, ""),
                            tagindent,
                            itemopen,
                            width,
                            1,
                            state.CONF["web"],
                            True,
                        )
                    )
                else:
                    listbody.append(item[0].replace(SEPARATOR, fullitem))
                del item[0]

            itemisclosed = False

            # Process next lines for this item (if any)
            for line in item:
                if type(line) == type([]):  # sublist inside
                    if state.rules["listitemnotnested"] and itemclose:
                        listbody.append(tagindent + itemclose)
                        itemisclosed = True
                    if state.TARGET == "rst" and name == "deflist":
                        del line[0]
                    listbody.extend(line)
                else:
                    line = self._last_escapes(line)

                    # Blank lines turns to <p>
                    if not line and state.rules["parainsidelist"]:
                        line = indent + state.TAGS["paragraphOpen"] + state.TAGS["paragraphClose"]
                        line = line.rstrip()
                        widelist = 1
                    elif not line and state.TARGET == "rtf":
                        listbody.append(state.TAGS["paragraphClose"])
                        line = state.TAGS["paragraphOpen"]
                        line = self._apply_depth(line, self.depth)

                    # Some targets don't like identation here (wiki)
                    if not state.rules["keeplistindent"] or (
                        name == "deflist" and state.rules["deflisttextstrip"]
                    ):
                        line = line.lstrip()

                    # Maybe we have a line prefix to add? (wiki)
                    if name == "deflist" and state.TAGS["deflistItem2LinePrefix"]:
                        line = state.TAGS["deflistItem2LinePrefix"] + line

                    if state.TARGET == "aat":
                        indent = " " * (len(line) - len(line.lstrip()))
                        listbody.extend(
                            aa_quote(line.lstrip(), indent, "", width, 1, state.CONF["web"])
                        )
                    else:
                        listbody.append(line)

            # Close item (if needed)
            if itemclose and not itemisclosed:
                if state.rules["notbreaklistitemclose"]:
                    listbody[-1] += itemclose
                else:
                    listbody.append(tagindent + itemclose)

        if not widelist and state.rules["compactlist"]:
            listopen = state.TAGS.get(name + "OpenCompact")
            listclose = state.TAGS.get(name + "CloseCompact")
        else:
            listopen = state.TAGS.get(name + "Open")
            listclose = state.TAGS.get(name + "Close")

        # Open list (not nestable lists are only opened at mother)
        if listopen and not (state.rules["listnotnested"] and state.BLOCK.depth != 1):
            result.append(tagindent + listopen)

        result.extend(listbody)

        # Close list (not nestable lists are only closed at mother)
        if listclose and not (state.rules["listnotnested"] and self.depth != 1):
            result.append(tagindent + listclose)

        # Blank line after?
        if self._should_add_blank_line("after", name):
            result.append("")

        if state.rules["blanksaroundnestedlist"]:
            if result[-1]:
                result.append("")

        return result


##############################################################################


class MacroMaster:
    def __init__(self, config={}):
        self.name = ""
        self.config = config or state.CONF
        self.infile = self.config["sourcefile"]
        self.outfile = self.config["outfile"]
        self.currentfile = self.config["currentsourcefile"]
        self.currdate = time.gmtime(
            int(os.environ.get("SOURCE_DATE_EPOCH", time.time()))
        )
        self.rgx = state.regex.get("macros") or getRegexes()["macros"]
        self.fileinfo = {"infile": None, "outfile": None}
        self.dft_fmt = MACROS

    def walk_file_format(self, fmt):
        "Walks the %%{in/out}file format string, expanding the % flags"
        i = 0
        ret = ""
        while i < len(fmt):  # char by char
            c = fmt[i]
            i += 1
            if c == "%":  # hot char!
                if i == len(fmt):  # % at the end
                    ret = ret + c
                    break
                c = fmt[i]  # read next
                i += 1
                ret = ret + self.expand_file_flag(c)
            else:
                ret = ret + c  # common char
        return ret

    def expand_file_flag(self, flag):
        "%f: filename          %F: filename (w/o extension)"
        "%d: dirname           %D: dirname (only parent dir)"
        "%p: file path         %e: extension"
        info = self.fileinfo[self.name]  # get dict
        if flag == "%":
            x = "%"  # %% -> %
        elif flag == "f":
            x = info["name"]
        elif flag == "F":
            x = os.path.splitext(info["name"])[0]
        elif flag == "d":
            x = info["dir"]
        elif flag == "D":
            x = os.path.split(info["dir"])[-1]
        elif flag == "p":
            x = info["path"]
        elif flag == "e":
            x = os.path.splitext(info["name"])[1].replace(".", "")
        else:
            x = "%" + flag  # false alarm
        return x

    def set_file_info(self, macroname):
        if macroname == "currentfile":
            self.currentfile = self.config["currentsourcefile"]
        else:
            if self.fileinfo.get(macroname):  # already done
                return
        file_ = getattr(self, self.name)  # self.infile
        if file_ == STDOUT or file_ == MODULEOUT:
            dir_ = ""
            path = name = file_
        else:
            path = os.path.abspath(file_)
            dir_ = os.path.dirname(path)
            name = os.path.basename(path)
        self.fileinfo[macroname] = {"path": path, "dir": dir_, "name": name}

    def expand(self, line=""):
        if (
            state.CONF.get("encoding")
            and state.CONF.get("encoding").lower() == "utf-8"
            and not isinstance(line, str)
        ):
            line = line.decode("utf-8")
        "Expand all macros found on the line"
        while self.rgx.search(line):
            m = self.rgx.search(line)
            name = self.name = m.group("name").lower()
            fmt = m.group("fmt") or self.dft_fmt.get(name)
            if name == "date":
                txt = time.strftime(fmt, self.currdate)
            elif name == "mtime":
                if self.infile in (STDIN, MODULEIN):
                    fdate = self.currdate
                elif PathMaster().is_url(self.infile):
                    try:
                        # Doing it the easy way: fetching the URL again.
                        # The right way would be doing it in Readfile().
                        # But I'm trying to avoid yet another global var
                        # or fake 'sourcefile_mtime' config.
                        #
                        # >>> f= urllib.urlopen('http://txt2tags.org/index.t2t')
                        # >>> f.info().get('last-modified')
                        # 'Thu, 18 Nov 2010 22:42:11 GMT'
                        # >>>
                        #
                        from urllib.request import urlopen
                        from email.Utils import parsedate

                        f = urlopen(self.infile)
                        mtime_rfc2822 = f.info().get("last-modified")
                        fdate = parsedate(mtime_rfc2822)
                    except:
                        # If mtime cannot be found, defaults to current date
                        fdate = self.currdate
                else:
                    mtime = os.path.getmtime(self.infile)
                    fdate = time.gmtime(mtime)
                txt = time.strftime(fmt, fdate)
            elif name in ("infile", "outfile", "currentfile"):
                self.set_file_info(name)
                txt = self.walk_file_format(fmt)
            elif name == "appurl":
                txt = my_url
            elif name == "appname":
                txt = my_name
            elif name == "appversion":
                txt = my_version
            elif name == "target":
                txt = state.TARGET
            elif name == "encoding":
                txt = self.config["encoding"]
            elif name == "cmdline":
                txt = "%s %s" % (my_name, " ".join(self.config["realcmdline"]))
            elif name in ("header1", "header2", "header3"):
                txt = self.config[name]
            elif name == "cc":
                txt = cc_formatter(self.config, fmt)
            else:
                # Never reached because the macro state.regex list the valid keys
                Error("Unknown macro name '%s'" % name)
            line = self.rgx.sub(txt, line, 1)
        return line


##############################################################################


