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
from .utils import Error, Debug, Readfile, Savefile, dotted_spaces
from .aa import (
    aa_box, aa_header, aa_lencjk, aa_line, aa_slicecjk, aa_slide, aa_under,
)
from .cli import PathMaster
from .usage import HEADER_TEMPLATE, AAPW_FOOT, Usage



def cc_formatter(conf, size):
    cc, target = conf["cc"].lower(), conf["target"]
    licenses = "by, by-sa, by-nc-sa, by-nd, by-nc-nd, by-nc"
    if cc not in licenses.split(", "):
        Error(
            _("Please, choose one of the six valid Creative Commons licenses : %s.")
            % licenses
        )
    if target in ("html", "xhtml", "xhtmls", "html5") or (
        target == "aat" and conf["web"]
    ):
        if size == "small":
            end_img = "/3.0/80x15.png"
        else:
            end_img = "/3.0/88x31.png"
        url = "http://creativecommons.org/licenses/" + cc + "/3.0"
        img = "http://i.creativecommons.org/l/" + cc + end_img
        alt = "Creative Commons " + cc
        ret = '<a href="' + url + '"><img src="' + img + '" alt="' + alt + '"></a>'
    else:
        if size == "small":
            ret = "Creative Commons %s" % cc
        else:
            ret = "Creative Commons %s" % cc.upper()
    return ret


def listTargets():
    """list all available targets"""
    for typ in TARGET_TYPES:
        targets = list(TARGET_TYPES[typ][1])
        targets.sort()
        print()
        print(TARGET_TYPES[typ][0] + ":")
        for target in targets:
            print("\t%s\t%s" % (target, TARGET_NAMES.get(target)))
    if OTHER_TARGETS:
        print()
        print(_("OTHERS:"))
        for target in OTHER_TARGETS:
            print("\t%s\t%s" % (target, TARGET_NAMES.get(target)))
    print()
    if NOT_LOADED:
        print(
            _(
                "Targets %s from the targets directory not loaded, because there is already targets with the same name in txt2tags core."
            )
            % ", ".join(NOT_LOADED)
        )
        print()


def dumpConfig(source_raw, parsed_config):
    onoff = {1: _("ON"), 0: _("OFF")}
    data = [
        (_("RC file"), state.RC_RAW),
        (_("source document"), source_raw),
        (_("command line"), state.CMDLINE_RAW),
    ]
    # First show all RAW data found
    for label, cfg in data:
        print(_("RAW config for %s") % label)
        for target, key, val in cfg:
            target = "(%s)" % target
            key = dotted_spaces("%-14s" % key)
            val = val or _("ON")
            print("  %-8s %s: %s" % (target, key, val))
        print()
    # Then the parsed results of all of them
    print(_("Full PARSED config"))
    keys = list(parsed_config.keys())
    keys.sort()  # sorted
    for key in keys:
        val = parsed_config[key]
        # Filters are the last
        if key in ["preproc", "postproc", "postvoodoo"]:
            continue
        # Flag beautifier
        if key in FLAGS or key in ACTIONS:
            val = onoff.get(val) or val
        # List beautifier
        if type(val) == type([]):
            if key == "options":
                sep = " "
            else:
                sep = ", "
            val = sep.join(val)
        print("%25s: %s" % (dotted_spaces("%-14s" % key), val))
    print()
    print(_("Active filters"))
    for filter_ in ["preproc", "postproc", "postvoodoo"]:
        for rule in parsed_config.get(filter_) or []:
            print(
                "%25s: %s  ->  %s"
                % (dotted_spaces("%-14s" % filter_), rule[0], rule[1])
            )


def get_file_body(file_):
    from .converter import process_source_file
    "Returns all the document BODY lines"
    return process_source_file(file_, noconf=1)[1][2]


def post_voodoo(lines, config):
    r"""
    %!postvoodoo handler - Beware! Voodoo here. For advanced users only.

    Your entire output document will be put in a single string, to your
    search/replace pleasure. Line breaks are single \n's in all platforms.
    You can change multiple lines at once, or even delete them. This is the
    last txt2tags processing in your file. All %!postproc's were already
    applied. It's the same as:

        $ txt2tags myfile.t2t | postvoodoo

    Your state.regex will be compiled with no modifiers. The default behavior is:

        ^ and $ match begin/end of entire string
        . doesn't match \n
        \w is not locale aware
        \w is not Unicode aware

    You can use (?...) in the beginning of your state.regex to change behavior:

        (?s)    the dot . will match \n, so .* will get everything
        (?m)    the ^ and $ match begin/end of EACH inner line
        (?u)    the \w, \d, \s and friends will be Unicode aware

    You can also use (?smu) or any combination of those.
    Learn more in http://docs.python.org/library/re.html
    """

    loser1 = _("No, no. Your PostVoodoo state.regex is wrong. Maybe you should call mommy?")
    loser2 = _(
        "Dear PostVoodoo apprentice: You got the state.regex right, but messed the replacement"
    )

    subject = "\n".join(lines)
    spells = compile_filters(config["postvoodoo"], loser1)

    for magic, words in spells:
        try:
            subject = magic.sub(words, subject)
        except:
            Error("%s: '%s'" % (loser2, words))

    return subject.split("\n")


def finish_him(outlist, config):
    from .processing import MacroMaster
    "Writing output to screen or file"
    outfile = config["outfile"]
    outlist = unmaskEscapeChar(outlist)
    outlist = expandLineBreaks(outlist)

    # Apply PostProc filters
    if config["postproc"]:
        filters = compile_filters(
            config["postproc"], _("Invalid PostProc filter state.regex")
        )
        postoutlist = []
        errmsg = _("Invalid PostProc filter replacement")
        for line in outlist:
            for rgx, repl in filters:
                try:
                    line = rgx.sub(repl, line)
                except:
                    Error("%s: '%s'" % (errmsg, repl))
            postoutlist.append(line)
        outlist = postoutlist[:]

    if config["postvoodoo"]:
        outlist = post_voodoo(outlist, config)

    if state.MAILING and not state.rules["tableonly"]:
        reader = state.MAILING
        repl_dict = {}
        for i, val in enumerate(reader):
            if i == 0:
                for j, el in enumerate(val):
                    repl_dict[el] = j
            else:
                write_file = outfile
                for key in repl_dict:
                    write_file = write_file.replace("<<%s>>" % key, val[repl_dict[key]])
                point = write_file.rfind(".")
                if write_file == outfile or write_file in state.file_dict:
                    if point == -1:
                        write_file = write_file + "_" + str(i)
                    else:
                        write_file = (
                            write_file[:point] + "_" + str(i) + write_file[point:]
                        )
                newout = []
                for line in outlist:
                    for key in repl_dict:
                        line = line.replace("<<%s>>" % key, val[repl_dict[key]])
                    newout.append(line)
                state.file_dict[write_file] = newout
    elif config["target"] not in ["csv", "csvs"]:
        state.file_dict[outfile] = outlist

    if config["target"] == "db":
        DBC.close()
        if outfile in [MODULEOUT, STDOUT]:
            outlist = [open(config["outfile"]).read()]
            os.remove(config["outfile"])

    outlist = []
    if outfile == MODULEOUT:
        for write_file in state.file_dict:
            outlist.append(state.file_dict[write_file])
        return outlist
    elif outfile == STDOUT:
        for write_file in state.file_dict:
            outlist.extend(state.file_dict[write_file])
        if state.GUI:
            return outlist, config
        else:
            for line in outlist:
                if isinstance(line, str):
                    line = line.encode("utf-8")
                print(line)
    else:
        if not config["target"] == "db":
            for write_file in state.file_dict:
                Savefile(write_file, addLineBreaks(state.file_dict[write_file]))
        if not state.GUI and not state.QUIET:
            for write_file in state.file_dict:
                print(_("%s wrote %s") % (my_name, write_file))

    if config["split"]:
        if not state.QUIET:
            print("--- html...")
        sgml2html = "sgml2html -s %s -l %s %s" % (
            config["split"],
            config["state.lang"] or state.lang,
            outfile,
        )
        if not state.QUIET:
            print("Running system command:", sgml2html)
        os.system(sgml2html)


def toc_inside_body(body, toc, config):
    from .processing import MaskMaster
    ret = []
    if AUTOTOC:
        return body  # nothing to expand
    toc_mark = MaskMaster().tocmask
    # Expand toc mark with TOC contents
    flag, n = False, 0
    for i, line in enumerate(body):
        if line.count(toc_mark):  # toc mark found
            if config["toc"]:
                if config["target"] == "aat" and config["slides"]:
                    j = i % config["height"]
                    title = body[i - j + 2 + n]
                    ret.extend([""] * (config["height"] - j - 1 + n))
                    ret.extend(
                        [aa_line(AA["bar1"], config["width"])]
                        + toc
                        + aa_slide(title, AA["bar2"], config["width"], state.CONF["web"])
                        + [""]
                    )
                    flag = True
                else:
                    ret.extend(toc)  # include if --toc
            else:
                pass  # or remove %%toc line
        else:
            if (
                flag
                and config["target"] == "aat"
                and config["slides"]
                and body[i] == body[i + 4] == aa_line(AA["bar2"], config["width"])
            ):
                end = [ret[-1]]
                del ret[-1]
                ret.extend([""] * (j - 6 - n) + end)
                flag, n = False, n + 1
                ret.append(line)  # common line
            else:
                ret.append(line)  # common line
    return ret


def toc_tagger(toc, config):
    "Returns the tagged TOC, as a single tag or a tagged list"
    from .converter import convert, set_global_config
    ret = []
    # Convert the TOC list (t2t-marked) to the target's list format
    if config["toc-only"] or (config["toc"] and not state.TAGS["TOC"]):
        fakeconf = config.copy()
        fakeconf["headers"] = 0
        fakeconf["toc-only"] = 0
        fakeconf["mask-email"] = 0
        fakeconf["preproc"] = []
        fakeconf["postproc"] = []
        fakeconf["postvoodoo"] = []
        fakeconf["css-sugar"] = 0
        fakeconf["fix-path"] = 0
        fakeconf["art-no-title"] = (
            1  # needed for --toc and --slides together, avoids slide title before TOC
        )
        ret, foo = convert(toc, fakeconf)
        set_global_config(config)  # restore config
    # Our TOC list is not needed, the target already knows how to do a TOC
    elif config["toc"] and state.TAGS["TOC"]:
        ret = [state.TAGS["TOC"]]
    return ret


def toc_formatter(toc, config):
    from .converter import convert, set_global_config
    "Formats TOC for automatic placement between headers and body"

    if config["toc-only"]:
        return toc  # no formatting needed
    if not config["toc"]:
        return []  # TOC disabled
    ret = toc

    # Art: An automatic "Table of Contents" header is added to the TOC slide
    if config["target"] == "aat" and config["slides"]:
        n = config["height"] - (len(toc) + 6) % config["height"]
        toc = (
            aa_slide(
                config["toc-title"] or _("Table of Contents"),
                AA["bar2"],
                config["width"],
                state.CONF["web"],
            )
            + toc
            + ([""] * n)
        )
        end_toc = aa_line(AA["bar2"], config["width"])
        if config["web"]:
            end_toc = end_toc + "</pre></section>"
        toc.append(end_toc)
        return toc
    if config["target"] == "aat" and not config["slides"]:
        ret = (
            aa_box([config["toc-title"] or _("Table of Contents")], AA, config["width"])
            + toc
        )

    # TOC open/close tags (if any)
    if state.TAGS["tocOpen"]:
        ret.insert(0, state.TAGS["tocOpen"])
    if state.TAGS["tocClose"]:
        ret.append(state.TAGS["tocClose"])

    # Autotoc specific formatting
    if AUTOTOC:
        if state.rules["autotocwithbars"]:  # TOC between bars
            para = state.TAGS["paragraphOpen"] + state.TAGS["paragraphClose"]
            bar = state.regex["x"].sub("-" * DFT_TEXT_WIDTH, state.TAGS["bar1"])
            tocbar = [para, bar, para]
            if config["target"] == "aat" and config["headers"]:
                # exception: header already printed a bar
                ret = [para] + ret + tocbar
            else:
                ret = tocbar + ret + tocbar
        if state.rules["blankendautotoc"]:  # blank line after TOC
            ret.append("")
        if state.rules["autotocnewpagebefore"]:  # page break before TOC
            ret.insert(0, state.TAGS["pageBreak"])
        if state.rules["autotocnewpageafter"]:  # page break after TOC
            ret.append(state.TAGS["pageBreak"])
    return ret


# XXX change function name. Now it's called at the end of the execution, dumping the full template.
def doHeader(headers, config):
    from .processing import MacroMaster
    if not config["headers"]:
        return config["fullBody"]
    if not headers:
        empty_headers = True
        headers = ["", "", ""]
    else:
        empty_headers = False
    target = config["target"]
    if target not in HEADER_TEMPLATE:
        Error("doHeader: Unknown target '%s'" % target)

    # Use default templates
    if config["template"] == "":
        if target in ("html", "xhtml", "xhtmls", "html5") and config.get("css-sugar"):
            template = HEADER_TEMPLATE[target + "css"].split("\n")
        else:
            template = HEADER_TEMPLATE[target].split("\n")

        template.append("%(BODY)s")

        if state.TAGS["EOD"]:
            template.append(state.TAGS["EOD"].replace("%", "%%"))  # escape % chars

    # Read user's template file
    else:
        if PathMaster().is_url(config["template"]):
            template = Readfile(config["template"], remove_linebreaks=1)
        else:
            templatefile = ""
            names = [config["template"] + "." + target, config["template"]]
            for filename in names:
                if os.path.isfile(filename):
                    templatefile = filename
                    break
            if not templatefile:
                Error(_("Cannot find template file:") + " " + config["template"])
            template = Readfile(templatefile, remove_linebreaks=1)

    head_data = {"STYLE": [], "ENCODING": ""}

    # Fix CSS files path
    config["stylepath_out"] = fix_css_out_path(config)

    # Populate head_data with config info
    for key in list(head_data.keys()):
        val = config.get(key.lower())
        if key == "STYLE" and "html" in target:
            val = config.get("stylepath_out") or []
        # Remove .sty extension from each style filename (freaking tex)
        # XXX Can't handle --style foo.sty, bar.sty
        if target in ["tex", "texs"] and key == "STYLE":
            val = [re.sub(r"(?i)\.sty$", "", x) for x in val]
        if key == "ENCODING":
            val = get_encoding_string(val, target)
        head_data[key] = val

    # Parse header contents
    for i in 0, 1, 2:
        # Expand macros
        contents = MacroMaster(config=config).expand(headers[i])
        # Escapes - on tex, just do it if any \tag{} present
        if target not in ["tex", "texs"] or (
            target in ["tex", "texs"] and re.search(r"\\\w+{", contents)
        ):
            contents = doEscape(target, contents)
        if target == "lout":
            contents = doFinalEscape(target, contents)

        head_data["HEADER%d" % (i + 1)] = contents

    # When using --css-inside, the template's <STYLE> line must be removed.
    # Template line removal for empty header keys is made some lines above.
    # That's why we will clean STYLE now.
    if (
        target in ("html", "xhtml", "xhtmls", "html5", "htmls", "wp")
        and config.get("css-inside")
        and config.get("style")
    ):
        head_data["STYLE"] = []

    Debug("Header Data: %s" % head_data, 1)

    # ASCII Art and rst don't use a header template, aa_header() formats the header
    if target == "aat" and not (config["spread"] and not config["web"]):
        template = aa_header(
            head_data,
            AA,
            config["width"],
            config["height"],
            state.CONF["web"],
            state.CONF["slides"],
            state.CONF["print"],
        )
        if config["slides"]:
            l = aa_lencjk(head_data["HEADER2"]) + aa_lencjk(head_data["HEADER3"]) + 2
            bar_1 = bar_2 = aa_line(AA["bar2"], config["width"])
            if config["web"]:
                bar_1 = "<section><pre>" + bar_1
            n_page = 0
            for i, line in enumerate(config["fullBody"]):
                if (
                    config["fullBody"][i - 1] == bar_1
                    and config["fullBody"][i + 3] == bar_2
                ):
                    n_page += 1
            page = 1
            for i, line in enumerate(config["fullBody"]):
                if (
                    config["fullBody"][i - 1] == bar_1
                    and config["fullBody"][i + 3] == bar_2
                ):
                    pages = str(page) + "/" + str(n_page)
                    l1 = aa_lencjk(head_data["HEADER1"]) + len(pages) + 3
                    config["fullBody"][i] = (
                        " "
                        + aa_slicecjk(
                            head_data["HEADER1"], config["width"] - len(pages) - 3
                        )[0]
                        + " " * (config["width"] - l1)
                        + " "
                        + pages
                        + " "
                    )
                    page += 1
                if (
                    config["fullBody"][i - 3] == bar_1
                    and config["fullBody"][i + 1] == bar_2
                ):
                    if l < config["width"]:
                        config["fullBody"][i] = (
                            " "
                            + head_data["HEADER2"]
                            + " " * (config["width"] - l)
                            + head_data["HEADER3"]
                            + " "
                        )
            if config["print"] and empty_headers:
                config["fullBody"] = [""] + config["fullBody"]
        # Header done, let's get out
        if config["web"]:
            encoding = ""
            if state.CONF["encoding"] and state.CONF["encoding"] != "not_utf-8":
                encoding = "<meta charset=" + state.CONF["encoding"] + ">"
            if config["spread"]:
                pre = '<pre style="text-align:center">'
            elif config["slides"]:
                pre = ""
            else:
                pre = "<pre>"
            head_web = [
                "<!doctype html><html>"
                + encoding
                + "<title>"
                + config["header1"]
                + "</title>"
                + pre
            ]
            foot_web = ["</pre></html>"]
            if config["slides"]:
                foot_web = [AAPW_FOOT]
            if config["spread"]:
                return head_web + config["fullBody"] + foot_web
            else:
                return head_web + template + config["fullBody"] + foot_web
        else:
            return template + config["fullBody"]

    if target == "rst":
        template = []
        if head_data["HEADER1"]:
            template.extend(aa_under(head_data["HEADER1"], RST["title"], 10000, True))
        if head_data["HEADER2"]:
            template.append(":Author: " + head_data["HEADER2"])
        if head_data["HEADER3"]:
            template.append(":Date: " + head_data["HEADER3"])
        return template + config["fullBody"]

    # Scan for empty dictionary keys
    # If found, scan template lines for that key reference
    # If found, remove the reference
    # If there isn't any other key reference on the same line, remove it
    # TODO loop by template line > key
    for key in list(head_data.keys()):
        if head_data.get(key):
            continue
        for line in template:
            if line.count("%%(%s)s" % key):
                sline = line.replace("%%(%s)s" % key, "")
                if (
                    not re.search(r"%\([A-Z0-9]+\)s", sline)
                    and not state.rules["keepblankheaderline"]
                ):
                    template.remove(line)

    # Style is a multiple tag.
    # - If none or just one, use default template
    # - If two or more, insert extra lines in a loop (and remove original)
    styles = head_data["STYLE"]
    if len(styles) == 1:
        head_data["STYLE"] = styles[0]
    elif len(styles) > 1:
        style_mark = "%(STYLE)s"
        for i in range(len(template)):
            if template[i].count(style_mark):
                while styles:
                    template.insert(
                        i + 1, template[i].replace(style_mark, styles.pop())
                    )
                del template[i]
                break

    # Expand macros on *all* lines of the template
    template = list(map(MacroMaster(config=config).expand, template))
    # Add Body contents to template data
    head_data["BODY"] = "\n".join(config["fullBody"])
    # Populate template with data (dict expansion)
    template = "\n".join(template) % head_data

    # Adding CSS contents into template (for --css-inside)
    # This code sux. Dirty++
    if (
        target in ("html", "xhtml", "xhtmls", "html5", "htmls", "wp")
        and config.get("css-inside")
        and config.get("stylepath")
    ):
        set_global_config(config)  # usually on convert(), needed here
        for i in range(len(config["stylepath"])):
            cssfile = config["stylepath"][i]
            try:
                contents = Readfile(cssfile, remove_linebreaks=1)
                css = "\n%s\n%s\n%s\n%s\n" % (
                    doCommentLine("Included %s" % cssfile),
                    state.TAGS["cssOpen"],
                    "\n".join(contents),
                    state.TAGS["cssClose"],
                )
                # Style now is content, needs escaping (tex)
                # css = maskEscapeChar(css)
            except:
                Error(_("CSS include failed for %s") % cssfile)
            # Insert this CSS file contents on the template
            template = re.sub("(?i)(</HEAD>)", css + r"\1", template)
            # template = re.sub(r'(?i)(\\begin{document})',
            #       css + '\n' + r'\1', template)  # tex

        # The last blank line to keep everything separated
        template = re.sub("(?i)(</HEAD>)", "\n" + r"\1", template)

    return template.split("\n")


def doCommentLine(txt):
    # The -- string ends a (h|sg|xht)ml comment :(
    txt = maskEscapeChar(txt)
    if state.TAGS["comment"].count("--") and txt.count("--"):
        txt = re.sub("-(?=-)", r"-\\", txt)

    if state.TAGS["comment"]:
        return state.regex["x"].sub(txt, state.TAGS["comment"])
    return ""


def doFooter(config):
    ret = []

    # No footer. The --no-headers option hides header AND footer
    if not config["headers"]:
        return []

    # Only add blank line before footer if last block doesn't added by itself
    if not state.rules.get("blanksaround" + state.BLOCK.last):
        ret.append("")

    # Add txt2tags info at footer, if target supports comments
    if state.TAGS["comment"]:
        # Not using TARGET_NAMES because it's i18n'ed.
        # It's best to always present this info in english.
        target = config["target"]
        if config["target"] == "tex":
            target = "LaTeX2e"
        if config["target"] == "aat":
            target = "ASCII Art"

        t2t_version = "%s code generated by %s %s (%s)" % (
            target,
            my_name,
            my_version,
            my_url,
        )
        cmdline = "cmdline: %s %s" % (my_name, " ".join(config["realcmdline"]))

        ret.append(doCommentLine(t2t_version))
        ret.append(doCommentLine(cmdline))

    # Maybe we have a specific tag to close the document?
    # if state.TAGS['EOD']:
    #   ret.append(state.TAGS['EOD'])

    return ret


# this converts proper \ue37f escapes to RTF \u-7297 escapes
def convertUnicodeRTF(match):
    num = int(match.group(1), 16)
    if num > 32767:
        num = num | -65536
    return ESCCHAR + "u" + str(num) + "?"


def get_escapes(target):
    if target == "texs":
        target = "tex"
    return ESCAPES.get(target, [])


def doProtect(target, txt):
    "Protect text in tagged blocks from being escaped."
    for before, protected, after in get_escapes(target):
        txt = txt.replace(before, protected)
    return txt


def doEscape(target, txt):
    "Target-specific special escapes. Apply *before* insert any tag."
    tmpmask = "vvvvThisEscapingSuxvvvv"

    if state.rules["escapexmlchars"]:
        txt = re.sub("&", "&amp;", txt)
        txt = re.sub("<", "&lt;", txt)
        txt = re.sub(">", "&gt;", txt)

    if target == "sgml":
        txt = re.sub("\xff", "&yuml;", txt)  # "+y
    elif target == "pm6":
        txt = re.sub(r"<", r"<\#60>", txt)
    elif target == "mgp":
        txt = re.sub("^%", " %", txt)  # add leading blank to avoid parse
    elif target == "man":
        txt = re.sub("^([.'])", "\\&\\1", txt)  # command ID
        txt = txt.replace(ESCCHAR, ESCCHAR + "e")  # \e
    elif target == "lout":
        # TIP: / moved to FinalEscape to avoid //italic//
        # TIP: these are also converted by lout:  ...  ---  --
        txt = txt.replace(ESCCHAR, tmpmask)  # \
        txt = txt.replace('"', '"%s""' % ESCCHAR)  # "\""
        txt = re.sub("([|&{}@#^~])", '"\\1"', txt)  # "@"
        txt = txt.replace(tmpmask, '"%s"' % (ESCCHAR * 2))  # "\\"
    elif target in ["tex", "texs"]:
        # Mark literal \ to be changed to $\backslash$ later
        txt = txt.replace(ESCCHAR, tmpmask)
        txt = re.sub("([#$&%{}])", ESCCHAR + r"\1", txt)  # \%
        txt = re.sub("([~^])", ESCCHAR + r"\1{}", txt)  # \~{}
        txt = re.sub("([<|>])", r"$\1$", txt)  # $>$
        txt = txt.replace(tmpmask, maskEscapeChar(r"$\backslash$"))
        # TIP the _ is escaped at the end
    elif target == "rtf":
        txt = txt.replace(ESCCHAR, ESCCHAR + ESCCHAR)
        txt = re.sub("([{}])", ESCCHAR + r"\1", txt)
        # RTF is ascii only
        # If an encoding is declared, try to convert to RTF unicode
        enc = get_encoding_string(state.CONF["encoding"], "rtf")
        if enc:
            # Python 3: txt is already a str; encode to cp1252 then decode back
            txt = txt.encode("cp1252", "backslashreplace").decode("cp1252")
            # escape ANSI codes above ascii range
            for code in range(128, 255):
                txt = re.sub("%c" % code, ESCCHAR + "'" + hex(code)[2:], txt)
            # some code were preescaped by txt.encode
            txt = re.sub(r"\\x([0-9a-f]{2})", r"\\\'\1", txt)
            # finally, convert escaped unicode chars to RTF format
            txt = re.sub(r"\\u([0-9a-f]{4})", convertUnicodeRTF, txt)
    return txt


# TODO man: where - really needs to be escaped?
def doFinalEscape(target, txt):
    "Last escapes of each line"
    for before, protected, after in get_escapes(target):
        # If the string has not been protected, replace it.
        txt = txt.replace(before, after)
        # If the string has been protected, restore it.
        txt = txt.replace(protected, before)
    return txt


def EscapeCharHandler(action, data):
    "Mask/Unmask the Escape Char on the given string"
    if not data.strip():
        return data
    if action not in ("mask", "unmask"):
        Error("EscapeCharHandler: Invalid action '%s'" % action)
    if action == "mask":
        return data.replace("\\", ESCCHAR)
    else:
        return data.replace(ESCCHAR, "\\")


def maskEscapeChar(data):
    r"Replace any Escape Char \ with a text mask (Input: str or list)"
    if type(data) == type([]):
        return [EscapeCharHandler("mask", x) for x in data]
    return EscapeCharHandler("mask", data)


def unmaskEscapeChar(data):
    r"Undo the Escape char \ masking (Input: str or list)"
    if type(data) == type([]):
        return [EscapeCharHandler("unmask", x) for x in data]
    return EscapeCharHandler("unmask", data)


def addLineBreaks(mylist):
    "use LB to respect sys.platform"
    ret = []
    for line in mylist:
        line = line.replace("\n", LB)  # embedded \n's
        ret.append(line + LB)  # add final line break
    return ret


# Convert ['foo\nbar'] to ['foo', 'bar']
def expandLineBreaks(mylist):
    ret = []
    for line in mylist:
        ret.extend(line.split("\n"))
    return ret


def compile_filters(filters, errmsg="Filter"):
    if filters:
        for i in range(len(filters)):
            patt, repl = filters[i]
            try:
                rgx = re.compile(patt)
            except:
                Error("%s: '%s'" % (errmsg, patt))
            filters[i] = (rgx, repl)
    return filters


def enclose_me(tagname, txt):
    return state.TAGS.get(tagname + "Open") + txt + state.TAGS.get(tagname + "Close")


def fix_relative_path(path):
    """
    Fix image/link path to be relative to the source file path (issues 62, 63)

    Leave the path untouched when:
    - not using --fix-path
    - path is an URL (or email)
    - path is an #anchor
    - path is absolute
    - infile is STDIN
    - outfile is STDOUT

    Note: Keep this state.rules in sync with fix_css_out_path()
    """
    if (
        not state.CONF["fix-path"]
        or state.regex["link"].match(path)
        or path[0] == "#"
        or os.path.isabs(path)
        or state.CONF["sourcefile"] in [STDIN, MODULEIN]
        or state.CONF["outfile"] in [STDOUT, MODULEOUT]
    ):
        return path

    # Make sure the input path is relative to the correct source file.
    # The path may be different from original source file when using %!include
    inputpath = PathMaster().join(os.path.dirname(state.CONF["currentsourcefile"]), path)

    # Now adjust the inputpath to be reachable from the output folder
    return PathMaster().relpath(inputpath, os.path.dirname(state.CONF["outfile"]))


def fix_css_out_path(config):
    """
    Fix CSS files path to be reached from the output folder (issue 71)

    Needed when the output file is in a different folder than the sources.
    This will affect the HTML's <link rel="stylesheet"> header tag.

    Leave the path untouched when:
    - not using --fix-path
    - path is an URL
    - path is absolute
    - infile is STDIN
    - outfile is STDOUT

    Note: Keep this state.rules in sync with fix_relative_path()
    """

    # No CSS files
    if not config.get("style"):
        return None

    # Defaults to user-typed paths
    default = config["style"][:]

    if (
        not config["fix-path"]
        or config["sourcefile"] in [STDIN, MODULEIN]
        or config["outfile"] in [STDOUT, MODULEOUT]
    ):
        return default

    # Sanity
    if len(config["style"]) != len(config["stylepath"]):
        Error("stylepath corrupted. Sorry, this shouldn't happen :(")

    # The stylepath paths are relative to the INPUT file folder.
    # Now we must make them relative to the OUTPUT file folder.
    stylepath_out = []
    for userpath, fixedpath in zip(config["style"], config["stylepath"]):
        if os.path.isabs(userpath):
            # Never fix user-typed absolute paths
            path = userpath
        else:
            path = PathMaster().relpath(fixedpath, os.path.dirname(config["outfile"]))
        stylepath_out.append(path)
    return stylepath_out


def beautify_me(font, line):
    # Exception: Doesn't parse an horizontal bar as strike
    if font == "fontStrike" and state.regex["bar"].search(line):
        return line

    open_ = state.TAGS["%sOpen" % font]
    close = state.TAGS["%sClose" % font]
    txt = r"%s\1%s" % (open_, close)
    line = state.regex[font].sub(txt, line)
    return line


def get_tagged_link(label, url):
    ret = ""
    target = state.CONF["target"]
    image_re = state.regex["img"]

    # Set link type
    if state.regex["email"].match(url):
        linktype = "email"
    else:
        linktype = "url"

    # Escape specials from TEXT parts
    label = doEscape(target, label)

    # Escape specials from link URL
    if not state.rules["linkable"] or state.rules["escapeurl"]:
        url = doEscape(target, url)

    # Adding protocol to guessed link
    guessurl = ""
    if linktype == "url" and re.match("(?i)" + state.regex["_urlskel"]["guess"], url):
        if url[0] in "Ww":
            guessurl = "http://" + url
        else:
            guessurl = "ftp://" + url

        # Not link aware targets -> protocol is useless
        if not state.rules["linkable"]:
            guessurl = ""

    # Simple link (not guessed)
    if not label and not guessurl:
        if state.CONF["mask-email"] and linktype == "email":
            # Do the email mask feature (no TAGs, just text)
            url = url.replace("@", " (a) ")
            url = url.replace(".", " ")
            url = "<%s>" % url
            if state.rules["linkable"]:
                url = doEscape(target, url)
            ret = url
        else:
            # Just add link data to tag
            tag = state.TAGS[linktype]
            ret = state.regex["x"].sub(url, tag)

    # Named link or guessed simple link
    else:
        # Adjusts for guessed link
        if not label:
            label = url  # no protocol
        if guessurl:
            url = guessurl  # with protocol

        # Image inside link!
        if image_re.match(label):
            if state.rules["imglinkable"]:  # get image tag
                from .converter import parse_images
                label = parse_images(label)
            else:  # img@link !supported
                img_path = image_re.match(label).group(1)
                label = "(%s)" % fix_relative_path(img_path)

        if (
            state.TARGET == "aat"
            and not state.CONF["slides"]
            and not state.CONF["web"]
            and not state.CONF["spread"]
            and not state.CONF["toc-only"]
        ):
            url_unmasked = state.MASK.undo(url)
            if url_unmasked not in state.AA_MARKS:
                state.AA_MARKS.append(url_unmasked)
            url = str(state.AA_MARKS.index(url_unmasked) + 1)

        # Putting data on the right appearance order
        if state.rules["labelbeforelink"] or not state.rules["linkable"]:
            urlorder = [label, url]  # label before link
        else:
            urlorder = [url, label]  # link before label

        ret = state.TAGS["%sMark" % linktype]

        # Exception: tag for anchor link is different from the link tag
        if url.startswith("#") and state.TAGS["urlMarkAnchor"]:
            ret = state.TAGS["urlMarkAnchor"]

        # Add link data to tag (replace \a's)
        for data in urlorder:
            ret = state.regex["x"].sub(data, ret, 1)

        if state.TARGET == "rst" and ".. image::" in label:
            ret = label[:-2] + state.TAGS["urlImg"] + url + label[-2:]

    return ret


def parse_deflist_term(line):
    "Extract and parse definition list term contents"
    img_re = state.regex["img"]
    term = state.regex["deflist"].search(line).group(3)

    # Mask image inside term as (image.jpg), where not supported
    if not state.rules["imgasdefterm"] and img_re.search(term):
        while img_re.search(term):
            imgfile = img_re.search(term).group(1)
            term = img_re.sub("(%s)" % imgfile, term, 1)

    # TODO tex: escape ] on term. \], \rbrack{} and \verb!]! don't work :(
    return term


def get_image_align(line):
    "Return the image (first found) align for the given line"

    # First clear marks that can mess align detection
    line = re.sub(SEPARATOR + "$", "", line)  # remove deflist sep
    line = re.sub("^" + SEPARATOR, "", line)  # remove list sep
    line = re.sub("^[\t]+", "", line)  # remove quote mark

    # Get image position on the line
    m = state.regex["img"].search(line)
    ini = m.start()
    head = 0
    end = m.end()
    tail = len(line)

    # The align detection algorithm
    if ini == head and end != tail:
        align = "left"  # ^img + text$
    elif ini != head and end == tail:
        align = "right"  # ^text + img$
    else:
        align = "center"  # default align

    # Some special cases
    if state.BLOCK.isblock("table"):
        align = "center"  # ignore when table
    #   if state.TARGET == 'mgp' and align == 'center': align = 'center'

    return align


# Reference: http://www.iana.org/assignments/character-sets
# http://www.drclue.net/F1.cgi/HTML/META/META.html
def get_encoding_string(enc, target):
    if not enc:
        return ""
    if target == "texs":
        target = "tex"
    # Target specific translation table
    translate = {
        "tex": {
            # missing: ansinew , applemac , cp437 , cp437de , cp865
            "utf-8": "utf8",
            "us-ascii": "ascii",
            "windows-1250": "cp1250",
            "windows-1252": "cp1252",
            "ibm850": "cp850",
            "ibm852": "cp852",
            "iso-8859-1": "latin1",
            "iso-8859-2": "latin2",
            "iso-8859-3": "latin3",
            "iso-8859-4": "latin4",
            "iso-8859-5": "latin5",
            "iso-8859-9": "latin9",
            "koi8-r": "koi8-r",
        },
        "rtf": {
            "utf-8": "utf8",
        },
    }
    # Normalization
    enc = re.sub("(?i)(us[-_]?)?ascii|us|ibm367", "us-ascii", enc)
    enc = re.sub("(?i)(ibm|cp)?85([02])", "ibm85\\2", enc)
    enc = re.sub("(?i)(iso[_-]?)?8859[_-]?", "iso-8859-", enc)
    enc = re.sub("iso-8859-($|[^1-9]).*", "iso-8859-1", enc)
    # Apply translation table
    try:
        enc = translate[target][enc.lower()]
    except:
        pass
    return enc


##############################################################################
##MerryChristmas,IdontwanttofighttonightwithyouImissyourbodyandIneedyourlove##
##############################################################################


