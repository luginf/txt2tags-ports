# txt2tags - ASCII Art rendering functions

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


def aa_line(char, width):
    return char * width


def aa_under(txt, char, width, over):
    ret = []
    if over:
        ret.append(aa_line(char, aa_lencjk(txt)))
    for lin in aa_wrap(txt, width, False):
        ret.extend([lin, aa_line(char, aa_lencjk(lin))])
    return ret


def aa_quote(txt, quote_char, prefix_char, width, depth, web, blank=False):
    if quote_char and quote_char in "123456789":
        prefix = int(quote_char) * depth * prefix_char
    else:
        prefix = quote_char * depth + prefix_char
    wrap_width = width - aa_lencjk(prefix)
    wrap_txt = aa_wrap(txt, wrap_width, web)
    if blank:
        blank_prefix = aa_lencjk(prefix) * " "
        block_txt = [prefix + wrap_txt[0]] + [
            blank_prefix + line for line in wrap_txt[1:]
        ]
    else:
        block_txt = [prefix + line for line in wrap_txt]
    return block_txt


def aa_box(txt, chars, width, centred=True, web=False, slides=False):
    wrap_txt = []
    char_side = ""
    if slides:
        width = width - 2
        char_side = " "
    for lin in txt:
        wrap_txt.extend(aa_wrap(lin, width - 4, web))
    len_cjk = max([aa_lencjk(lin, web) for lin in wrap_txt])
    tline_box = (
        char_side
        + aa_center(
            chars["tlcorner"] + chars["border"] * (len_cjk + 2) + chars["trcorner"],
            width,
        )
        + char_side
    )
    bline_box = (
        char_side
        + aa_center(
            chars["blcorner"] + chars["border"] * (len_cjk + 2) + chars["brcorner"],
            width,
        )
        + char_side
    )
    line_txt = []
    for lin in wrap_txt:
        if centred:
            line_txt.append(
                char_side
                + aa_center(
                    chars["side"]
                    + " "
                    + aa_center(lin, len_cjk, web)
                    + " "
                    + chars["side"],
                    width,
                    web,
                )
                + char_side
            )
        else:
            line_txt.append(
                char_side
                + aa_center(
                    chars["side"]
                    + " "
                    + lin
                    + " " * (len_cjk - aa_lencjk(lin, web) + 1)
                    + chars["side"],
                    width,
                    web,
                )
                + char_side
            )
    return [tline_box] + line_txt + [bline_box]


def aa_header(header_data, chars, width, height, web, slides, printing):
    h = [
        header_data[v] for v in header_data if v.startswith("HEADER") and header_data[v]
    ]
    n_h = len(h)
    height_box = sum(
        [len(aa_box([header], chars, width, slides=slides)) for header in h]
    )
    if not n_h:
        return []
    if not slides:
        n, end = 2, 0
    else:
        x = height - 2 - height_box
        n = x / (n_h + 1)
        end = x % (n_h + 1)
    header = [aa_line(chars["bar2"], width)]
    header.extend([""] * n)
    for h in "HEADER1", "HEADER2", "HEADER3":
        if header_data[h]:
            header.extend(aa_box([header_data[h]], chars, width, slides=slides))
            header.extend([""] * n)
    header.extend([""] * end)
    header.append(aa_line(chars["bar2"], width))
    if slides:
        if web:
            header = (
                ["<section><pre>" + header[0]]
                + header[1:-1]
                + [header[-1] + "</pre></section>"]
            )
        elif printing:
            header = header[:-1] + [header[-1] + ""]
    if not slides or printing:
        header = [""] + header
    return header


def aa_slide(title, char, width, web):
    res = [aa_line(char, width)]
    res.append("")
    res.append(aa_slicecjk(aa_center(title, width), width)[0])
    res.append("")
    res.append(aa_line(char, width))
    if web:
        res = ["<section><pre>" + res[0]] + res[1:]
    return res


def aa_table(data, chars, width, borders, h_header, v_header, align, spread, web):
    n = max([len(lin[0]) for lin in data])
    data3 = []
    for lin in data:
        if max(lin[1]) == 1:
            data3.append(lin[0])
        else:
            newline = []
            for i, el in enumerate(lin[0]):
                if lin[1][i] == 1:
                    newline.append(el)
                else:
                    newline.extend(lin[1][i] * [""])
            data3.append(newline)
    tab = []
    for i in range(n):
        tab.append([lin[i] for lin in data3])
    if web:
        length = [
            max([aa_lencjk(re.sub('<a.*">|</a>', "", el)) for el in lin]) for lin in tab
        ]
    else:
        length = [max([aa_lencjk(el) for el in lin]) for lin in tab]
    if spread:
        data[0][0] = [data[0][0][i].center(length[i]) for i in range(n)]
    (
        tcross,
        border,
        bcross,
        lcross,
        side,
        rcross,
        tlcorner,
        trcorner,
        cross,
        blcorner,
        brcorner,
        tvhead,
        vhead,
        vheadcross,
        bvhead,
        headerscross,
        hhead,
        hheadcross,
        lhhead,
        rhhead,
    ) = (
        chars["tcross"],
        chars["border"],
        chars["bcross"],
        chars["lcross"],
        chars["side"],
        chars["rcross"],
        chars["tlcorner"],
        chars["trcorner"],
        chars["cross"],
        chars["blcorner"],
        chars["brcorner"],
        chars["tvhead"],
        chars["vhead"],
        chars["vheadcross"],
        chars["bvhead"],
        chars["headerscross"],
        chars["hhead"],
        chars["hheadcross"],
        chars["lhhead"],
        chars["rhhead"],
    )
    if not v_header:
        tvhead, bvhead = tcross, bcross
        if borders:
            vheadcross = cross
            if h_header:
                headerscross = hheadcross
    if not borders:
        hhead, hheadcross, lhhead, rhhead, headerscross = (
            border,
            cross,
            lcross,
            rcross,
            vheadcross,
        )
        if h_header and not v_header:
            headerscross = cross
    if v_header and not h_header:
        headerscross = vheadcross

    len0 = length[0] + 2
    res = lcross + len0 * border + vheadcross
    resh = lhhead + len0 * hhead + headerscross
    rest = tlcorner + len0 * border + tvhead
    resb = blcorner + len0 * border + bvhead
    for i in range(1, n):
        res = res + (length[i] + 2) * border + cross
        resh = resh + (length[i] + 2) * hhead + hheadcross
        rest = rest + (length[i] + 2) * border + tcross
        resb = resb + (length[i] + 2) * border + bcross
    res = res[:-1] + rcross
    resh = resh[:-1] + rhhead
    rest = rest[:-1] + trcorner
    resb = resb[:-1] + brcorner
    ret = []
    for i, lin in enumerate(data):
        aff = side
        if i == 1 and h_header:
            ret.append(resh)
        elif i == 0:
            ret.append(rest)
        elif borders:
            ret.append(res)
        for j, el in enumerate(lin[0]):
            if web:
                aff = (
                    aff
                    + " "
                    + el
                    + (
                        sum(length[j : (j + lin[1][j])])
                        + lin[1][j] * 3
                        - aa_lencjk(re.sub('<a.*">|</a>', "", el))
                        - 2
                    )
                    * " "
                    + side
                )
            else:
                aff = (
                    aff
                    + " "
                    + el
                    + (
                        sum(length[j : (j + lin[1][j])])
                        + lin[1][j] * 3
                        - aa_lencjk(el)
                        - 2
                    )
                    * " "
                    + side
                )
            if j == 0 and v_header:
                aff = aff[:-1] + vhead
        ret.append(aff)
    ret.append(resb)
    if align == "Left":
        ret = [" " * 2 + lin for lin in ret]
    elif align == "Center" and not (web and spread):
        ret = [aa_center(lin, width) for lin in ret]
    return ret


def aa_image(image):
    art_table = "#$!;:,. "
    art_image = []
    for lin in image:
        art_line = ""
        for pixel in lin:
            art_line = art_line + art_table[pixel / 32]
        art_image.append(art_line)
    return art_image


def aa_wrap(txt, width, web):
    twcjk = TextWrapperCJK(width=width)
    if not web:
        return twcjk.wrap(txt)
    txt = re.split("(<a href=.*?>)|(</a>)|(<img src=.*?>)", txt)
    lin, length, ret = "", 0, []
    for el in txt:
        if el:
            if el[0] != "<":
                if len(el) > width:
                    lin = lin + el
                    multi = twcjk.wrap(lin)
                    ret.extend(multi[:-1])
                    lin = multi[-1]
                elif length + len(el) <= width:
                    length = length + len(el)
                    lin = lin + el
                else:
                    ret.append(lin)
                    lin, length = el, len(el)
            else:
                lin = lin + el
    ret.append(lin)
    return ret


def aa_lencjk(txt, web=False):
    if web:
        txt = re.sub("(<a href=.*?>)|(</a>)|(<img src=.*?>)", "", txt)
    if isinstance(txt, str):
        return len(txt)
    l = 0
    for char in txt:
        if unicodedata.east_asian_width(str(char)) in ("F", "W"):
            l = l + 2
        else:
            l = l + 1
    return l


def aa_slicecjk(txt, space_left):
    if isinstance(txt, str):
        return txt[:space_left], txt[space_left:]
    if aa_lencjk(txt) <= space_left:
        return txt, ""
    i = 1
    while aa_lencjk(txt[:i]) <= space_left:
        # <= and index i-1
        # to catch the last double length char of odd line
        i = i + 1
    return txt[: i - 1], txt[i - 1 :]


class TextWrapperCJK(textwrap.TextWrapper):
    # CJK fix for the Greg Ward textwrap lib.
    def _handle_long_word(self, reversed_chunks, cur_line, cur_len, width):
        if width < 1:
            space_left = 1
        else:
            space_left = width - cur_len
        if self.break_long_words:
            chunk_start, chunk_end = aa_slicecjk(reversed_chunks[-1], space_left)
            cur_line.append(chunk_start)
            reversed_chunks[-1] = chunk_end
        elif not cur_line:
            cur_line.append(reversed_chunks.pop())

    def _wrap_chunks(self, chunks):
        lines = []
        if self.width <= 0:
            raise ValueError("invalid width %r (must be > 0)" % self.width)
        if self.width == 1 and sum(aa_lencjk(chunk) for chunk in chunks) > sum(
            len(chunk) for chunk in chunks
        ):
            raise ValueError("invalid width %r (must be > 1 if CJK chars)" % self.width)
        chunks.reverse()
        while chunks:
            cur_line = []
            cur_len = 0
            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent
            width = self.width - len(indent)
            if chunks[-1].strip() == "" and lines:
                del chunks[-1]
            while chunks:
                l = aa_lencjk(chunks[-1])
                if cur_len + l <= width:
                    cur_line.append(chunks.pop())
                    cur_len += l
                else:
                    break
            if chunks and aa_lencjk(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)
            if cur_line and cur_line[-1].strip() == "":
                del cur_line[-1]
            if cur_line:
                lines.append(indent + "".join(cur_line))
        return lines


def aa_center(txt, width, web=False):
    n_before = (width - aa_lencjk(txt, web)) / 2
    n_after = width - aa_lencjk(txt, web) - n_before

    return " " * int(n_before) + txt + " " * int(n_after)


# The Spreadsheet library

ascii_uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class SpreadSheet:
    """Raymond Hettinger's recipe
    http://code.activestate.com/recipes/355045-spreadsheet
    """

    _cells = {}

    def __setitem__(self, key, formula):
        self._cells[key] = formula

    def getformula(self, key):
        return self._cells[key]

    def __getitem__(self, key):
        if self._cells[key].strip()[0] == "=":
            try:
                return eval(self._cells[key].strip()[1:], globals(), self)
            except Exception as e:
                return e
        else:
            return self._cells[key].strip()


def spreadsheet(data, markup, grid):
    n = max([len(line[0]) for line in data])
    if n > 676:
        Error(
            "Spreadsheet tables are limited to 676 columns, and your table has %i columns."
            % n
        )
    s = SpreadSheet()
    for j, row in enumerate(data):
        for i, el in enumerate(row[0]):
            ind = (
                ascii_uppercase[int(i / 26) - 1].replace("Z", "")
                + ascii_uppercase[i % 26]
                + str(j + 1)
            )
            if el and el.strip():
                s[ind] = el
    for j, row in enumerate(data):
        for i, el in enumerate(row[0]):
            ind = (
                ascii_uppercase[int(i / 26) - 1].replace("Z", "")
                + ascii_uppercase[i % 26]
                + str(j + 1)
            )
            if el and el.strip():
                if markup == "html":
                    row[0][i] = '<a title="' + el.strip() + '">' + str(s[ind]) + "</a>"
                elif markup == "tex":
                    if el.strip()[0] == "=":
                        tooltip = "formula: "
                    else:
                        tooltip = "value: "
                    row[0][i] = (
                        r"\href{" + tooltip + el.strip() + "}{" + str(s[ind]) + "}"
                    )
                elif markup == "txt":
                    row[0][i] = str(s[ind])
    if grid:
        h = [
            (
                ascii_uppercase[int(i / 26) - 1].replace("Z", "")
                + ascii_uppercase[i % 26]
            )
            for i in range(n)
        ]
        data = [[h, [1] * n]] + data
        data = [[[str(i)] + line[0], [1] + line[1]] for i, line in enumerate(data)]
        data[0][0][0] = ""
    return data


def completes_table(table):
    data = [[row["cells"], row["cellspan"]] for row in table]
    n = max([len(line[0]) for line in data])
    data2 = []
    for line in data:
        if not line[1]:
            data2.append([n * [""], n * [1]])
        else:
            data2.append(
                [
                    line[0] + (n - sum(line[1])) * [""],
                    line[1] + (n - sum(line[1])) * [1],
                ]
            )
    return data2


def convert_to_table(itera, headers, borders, center):
    if center:
        row_ini = " | "
    else:
        row_ini = "| "
    if borders:
        row_end = " |"
    else:
        row_end = ""
    table = []
    for row in itera:
        table.append(row_ini + " | ".join(row).expandtabs() + row_end)
    if headers:
        table[0] = table[0].replace("|", "||", 1)
    return table


def parse_convert_table(table, tableable, target):
    ret = []
    from .processing import TableMaster
    from .output import doEscape
    # Note: cell contents is raw, no t2t marks are parsed
    if tableable:
        ret.extend(state.BLOCK.blockin("table"))
        if table:
            state.BLOCK.tableparser.__init__(table[0])
            for row in table:
                tablerow = TableMaster().parse_row(row)
                state.BLOCK.tableparser.add_row(tablerow)

                # Very ugly, but necessary for escapes
                line = SEPARATOR.join(tablerow["cells"])
                state.BLOCK.holdadd(doEscape(target, line))
            ret.extend(state.BLOCK.blockout())

    # Tables are mapped to verb when target is not table-aware
    else:
        ret.extend(state.BLOCK.blockin("verb"))
        state.BLOCK.propset("mapped", "table")
        for row in table:
            state.BLOCK.holdadd(row)
        ret.extend(state.BLOCK.blockout())
    return ret


def math_print(target, txt):
    try:
        import sympy
    except:
        Error(_("$$math$$: You need SymPy to use math formula"))
    if sympy.__version__ < "0.7.4":
        Error(_("$$math$$: You need SymPy 0.7.4 or > to use math formula"))
    exec("from sympy import *")
    if target == "aat":
        return pretty(sympify(txt, evaluate=False), use_unicode=state.CONF["unicode_art"])
    elif target == "tex":
        return latex(sympify(txt, evaluate=False))
    elif target == "html5":
        from sympy.printing.mathml import mathml
        from sympy.utilities.mathml import c2p

        return c2p(mathml(sympify(txt, evaluate=False)))


##############################################################################


