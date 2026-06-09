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
from .tags import getTags
from .rules import getRules
from .regexes import getRegexes
from .processing import MaskMaster, BlockMaster, TitleMaster, TableMaster
from .output import (
    beautify_me, compile_filters, doEscape, doFinalEscape, doFooter, doHeader,
    dumpConfig, finish_him, fix_relative_path, get_file_body, post_voodoo,
    toc_inside_body, toc_tagger, toc_formatter,
    maskEscapeChar, unmaskEscapeChar, EscapeCharHandler,
    addLineBreaks, expandLineBreaks, enclose_me, get_tagged_link,
    get_image_align, parse_deflist_term, get_encoding_string,
    doProtect, get_escapes, doCommentLine, cc_formatter,
)
from .utils import Error, Debug, Message, Quit, Readfile, Savefile, dotted_spaces
from .cli import CsvOptions, DbOptions, FenOptions, PathMaster
from .config import ConfigLines, ConfigMaster, SourceDocument
from .aa import (
    aa_image, aa_line, aa_slide, aa_wrap, convert_to_table, parse_convert_table,
    aa_table,
)

def process_source_file(file_="", noconf=0, contents=[]):
    """
    Find and Join all the configuration available for a source file.
    No sanity checking is done on this step.
    It also extracts the source document parts into separate holders.

    The config scan order is:
        1. The user configuration file (i.e. $HOME/.txt2tagsrc)
        2. The source document's state.CONF area
        3. The command line options

    The return data is a tuple of two items:
        1. The parsed config dictionary
        2. The document's parts, as a (head, conf, body) tuple

    All the conversion process will be based on the data and
    configuration returned by this function.
    The source files is read on this step only.
    """
    if contents:
        source = SourceDocument(contents=contents)
    else:
        source = SourceDocument(file_)
    head, conf, body = source.split()
    Message(_("Source document contents stored"), 2)
    if not noconf:
        # Read document config
        source_raw = source.get_raw_config()
        # Join all the config directives found, then parse it
        full_raw = state.RC_RAW + source_raw + state.CMDLINE_RAW
        Message(
            _("Parsing and saving all config found (%03d items)") % (len(full_raw)), 1
        )
        full_parsed = ConfigMaster(full_raw).parse()
        # Add manually the filename to the conf dic
        if contents:
            full_parsed["sourcefile"] = MODULEIN
            full_parsed["currentsourcefile"] = MODULEIN
            full_parsed["infile"] = MODULEIN
            full_parsed["outfile"] = MODULEOUT
        else:
            full_parsed["sourcefile"] = file_
            full_parsed["currentsourcefile"] = file_
        # Maybe should we dump the config found?
        if full_parsed.get("dump-config"):
            dumpConfig(source_raw, full_parsed)
            Quit()
        # The user just want to know a single config value (hidden feature)
        # TODO pick a better name than --show-config-value
        elif full_parsed.get("show-config-value"):
            config_value = full_parsed.get(full_parsed["show-config-value"])
            if config_value:
                if type(config_value) == type([]):
                    print("\n".join(config_value))
                else:
                    print(config_value)
            Quit()
        # Okay, all done
        Debug("FULL config for this file: %s" % full_parsed, 1)
    else:
        full_parsed = {}
    return full_parsed, (head, conf, body)


def get_infiles_config(infiles):
    """
    Find and Join into a single list, all configuration available
    for each input file. This function is supposed to be the very
    first one to be called, before any processing.
    """
    return list(map(process_source_file, infiles))


def convert_this_files(configs):
    # global (use state.) CONF, AA_COUNT, AA_TITLE
    for myconf, doc in configs:  # multifile support
        state.AA_COUNT = 0
        state.AA_TITLE = ""
        target_toc = []
        target_body = []
        target_foot = []
        source_head, source_conf, source_body = doc
        myconf = ConfigMaster().sanity(myconf)

        if (
            myconf["target"] in ["aat", "txt", "rst", "mgp"]
            and myconf["encoding"].lower() == "utf-8"
        ):
            decode_head, decode_body = [], []
            try:
                for line in source_head:
                    decode_head.append(line.decode("utf-8"))
                for line in source_body:
                    decode_body.append(line.decode("utf-8"))
                source_head, source_body = decode_head, decode_body
            except:
                myconf["encoding"] = "not_utf-8"
                myconf = ConfigMaster().sanity(myconf)

        # Save header info for %%header1..3 macros
        if not source_head:
            myconf["header1"] = ""
            myconf["header2"] = ""
            myconf["header3"] = ""
        else:
            myconf["header1"] = source_head[0]
            myconf["header2"] = source_head[1]
            myconf["header3"] = source_head[2]

        # Parse the full marked body into tagged target
        first_body_line = (len(source_head) or 1) + len(source_conf) + 1
        Message(_("Composing target Body"), 1)
        target_body, marked_toc = convert(
            source_body, myconf, firstlinenr=first_body_line
        )

        # If dump-source, we're done
        if myconf["dump-source"]:
            for line in source_head + source_conf + target_body:
                print(line)
            return

        # Close the last slide
        if myconf["slides"] and not myconf["toc-only"] and myconf["target"] == "aat":
            n = myconf["height"] - (state.AA_COUNT % myconf["height"] + 1)
            spaces = [""] * n
            end_line = aa_line(AA["bar2"], state.CONF["width"])
            if myconf["web"]:
                target_body = target_body + spaces + [end_line + "</pre></section>"]
            elif myconf["print"] and myconf["qa"]:
                target_body = target_body + spaces + [end_line + " "]
            else:
                target_body = target_body + spaces + [end_line]
            if myconf["qa"]:
                n_before = (myconf["height"] - 23) / 2
                n_after = myconf["height"] - 23 - n_before
                head = aa_slide(_("Q&A"), AA["bar2"], myconf["width"], myconf["web"])
                end_qa = aa_line(AA["bar2"], myconf["width"])
                if myconf["web"]:
                    end_qa = end_qa + "</pre></section>"
                if myconf["height"] > 22 and myconf["width"] > 22:
                    target_body = (
                        target_body
                        + head
                        + [""] * n_before
                        + [(myconf["width"] - 23) / 2 * " " + line for line in AA_QA]
                        + [""] * n_after
                        + [end_qa]
                    )
                else:
                    target_body = (
                        target_body + head + [""] * (myconf["height"] - 6) + [end_qa]
                    )

        # Uncomment the three next lines and specify your qa_image to use --qa option with the mgp target
        # if myconf['target'] == 'mgp' and myconf['qa']:
        #        qa_image = path_to_your_qa_image
        #        target_body = target_body + ['%page', '', 'Q&A', '', '%center', '%newimage "' + qa_image + '"', '']

        if (
            myconf["target"] == "aat"
            and not myconf["slides"]
            and not myconf["web"]
            and not myconf["spread"]
            and not myconf["toc-only"]
        ):
            for i, url in enumerate(state.AA_MARKS):
                target_body.extend(
                    aa_wrap(
                        "[" + str(i + 1) + "] " + url, myconf["width"], myconf["web"]
                    )
                )

        # Compose the target file Footer
        Message(_("Composing target Footer"), 1)
        target_foot = doFooter(myconf)

        # Make TOC (if needed)
        Message(_("Composing target TOC"), 1)
        tagged_toc = toc_tagger(marked_toc, myconf)
        target_toc = toc_formatter(tagged_toc, myconf)
        target_body = toc_inside_body(target_body, target_toc, myconf)
        if not AUTOTOC and not myconf["toc-only"]:
            target_toc = []
        # Finally, we have our document
        myconf["fullBody"] = target_toc + target_body + target_foot

        # Compose the target file Headers
        # TODO escape line before?
        # TODO see exceptions by tex and mgp
        Message(_("Composing target Headers"), 1)
        outlist = doHeader(source_head, myconf)

        if myconf["target"] == "aat" and myconf["web"] and not myconf["headers"]:
            outlist = ["<pre>"] + outlist + ["</pre>"]

        # If on state.GUI, abort before finish_him
        # If module, return finish_him as list
        # Else, write results to file or STDOUT
        if state.GUI:
            return outlist, myconf
        elif myconf.get("outfile") == MODULEOUT:
            return finish_him(outlist, myconf), myconf
        else:
            Message(_("Saving results to the output file"), 1)
            finish_him(outlist, myconf)


def getImageInfo(filename):
    "Get image type, dimensions, and pixel size."
    try:
        f = open(filename, "rb")
        head = f.read(2)
        # Default DPI (if none specified in image metadata) of 72
        dpix = 72
        dpiy = 72

        if head == b"\x89\x50":  # PNG format image
            imgtype = "png"
            magic, length, chunkid, width, height, bit_depth, colour_type = (
                struct.unpack("!6sI4sIIBBxxxxxxx", f.read(31))
            )
            if (
                (magic == b"\x4e\x47\x0d\x0a\x1a\x0a")
                and (length > 0)
                and (chunkid == b"IHDR")
            ):
                chunk = f.read(8)
                # Now to find the DPI / Pixel dimensions
                while chunk:
                    length, chunkid = struct.unpack("!I4s", chunk)
                    if chunkid == b"pHYs":
                        dpix, dpiy, units = struct.unpack("!IIbxxxx", f.read(13))
                        if units == 1:
                            # PNG images have pixel dimensions in pixels per meter,
                            # convert to pixels per inch
                            dpix = dpix * 0.0257
                            dpiy = dpiy * 0.0257
                        else:
                            # No pixel dimensions, set back to default
                            dpix = 72
                            dpiy = 72
                    elif chunkid == b"IDAT":
                        data = f.read(length)
                        f.seek(4, 1)
                    else:
                        f.seek(length + 4, 1)
                    chunk = f.read(8)
                f.close()
                return imgtype, width, height, bit_depth, colour_type, dpix, dpiy, data
            else:
                f.close()
                Error("Cannot embed PNG image " + filename + ". Badly formatted.")

        elif head == b"\xff\xd8":  # JPG format image
            imgtype = "jpeg"
            # Jpeg format is insane. The image size chunk could be anywhere,
            # so we need to search the whole file.
            b = f.read(1)
            while b != "":
                # Each chunk in a jpeg file is delimited by at least one
                # \xff character, and possibly more for padding. Seek past 'em
                while b != b"\xff":
                    b = f.read(1)
                while b == b"\xff":
                    b = f.read(1)

                # Past them, now to find the type of this particular chunk
                if b == b"\xe0":
                    # Header, should be the first chunk in the file.
                    size = struct.unpack("!H", f.read(2))
                    if f.read(5) == b"JFIF\0":
                        # This Jpeg has JFIF metadata, which should include pixel dimensions
                        units, dpix, dpiy = struct.unpack("!xxbHH", f.read(7))
                        if units == 0:
                            # No exact pixel dimensions, just return defaults
                            dpix = 72
                            dpiy = 72
                        elif units == 2:
                            # Pixel dimensions in pixels per centimeter, so convert.
                            #  units == 1 would mean the field is in pixels per inch,
                            #  so no conversion needed in that case.
                            dpix = dpix * 2.57
                            dpiy = dpiy * 2.57
                        f.seek(size[0] - 12, 1)
                    else:
                        # No metadata, just keep the default 72 dpi and
                        # find the image size.
                        f.seek(size[0] - 7, 1)
                    b = f.read(1)
                elif (b >= b"\xc0") and (b <= b"\xc3"):
                    # Image info chunk, which should include size in pixels
                    height, width = struct.unpack("!xxxHH", f.read(7))
                    f.close()
                    return (
                        imgtype,
                        width,
                        height,
                        "bit_depth",
                        "colour_type",
                        dpix,
                        dpiy,
                        "data",
                    )

                else:
                    # Wrong chunk type. Get length of chunk and skip to the next one
                    size = struct.unpack("!H", f.read(2))
                    f.seek(size[0] - 2, 1)
                    b = f.read(1)
            f.close()
            # No size information found
            Error("Cannot embed JPG image " + filename + ". Badly formatted.")
        else:  # Not a supported image format
            f.close()
            Error("Cannot embed image " + filename + ". Unsupported format.")
    except:
        Error("Cannot embed image " + filename + ". Unable to open file.")


RTFIMGID = 1000  # Needed so each embedded image can have a unique ID number


def embedImage(filename):
    mytype, width, height, bit_depth, colour_type, dpix, dpiy, data = getImageInfo(
        filename
    )
    if state.TARGET in ("html", "xhtml", "xhtmls", "html5", "htmls"):
        ## return a data uri with the image embed.
        ## see: http://en.wikipedia.org/wiki/Data_URI_scheme

        line = "data: image/%s;base64," % mytype
        line = line + base64.b64encode(file(filename).read())
        return line

    elif state.TARGET == "rtf":
        global RTFIMGID
        RTFIMGID += 1
        # Defalt DPI of images.
        if dpix == 0 and dpiy == 0:
            dpix = 72
            dpiy = 72
        try:
            filein = open(filename, "rb")
            # RTF tags for an embedded bitmap image, with size in pixels and intended display size in twips.
            # Size and dpi converted to float for division, as by default Python 2 will return an integer,
            # probably truncated to 0 in most cases. This behavior is changed in Python3.
            line = (
                r"\\%sblip\\picw%d\\pich%d\\picwgoal%d\\picscalex100\\pichgoal%d\\picscaley100\\bliptag%d{\\*\\blipuid%016x}"
                % (
                    mytype,
                    width,
                    height,
                    int(float(width) / float(dpix) * 1440.0),
                    int(float(height) / float(dpiy) * 1440.0),
                    RTFIMGID,
                    RTFIMGID,
                )
            )
            line = line + str(binascii.hexlify(filein.read()))
            filein.close()
            return line
        except:
            Error("Unable to embed image: " + filename)

    elif state.TARGET == "aat":
        if mytype not in ["png"]:
            Error(
                "Cannot embed image "
                + filename
                + ". Unsupported "
                + mytype
                + " format with Ascii Art targets. You should use PNG."
            )
        if colour_type == 3:
            Error(
                "Cannot embed image "
                + filename
                + ". Unsupported indexed-colour image type with Ascii Art targets. You should use greyscale or RGB."
            )
        if bit_depth not in [8]:
            Error(
                "Cannot embed image "
                + filename
                + ". Unsupported bit depth with Ascii Art targets. You should use 8-bit pixels."
            )
        import zlib

        decomp = zlib.decompress(data)
        n_byte = n_byte_alpha = colour_type % 4 + 1
        if colour_type in [4, 6]:
            n_byte_alpha = n_byte + 1
        image = []
        end_line = n_byte_alpha * width + 1
        while decomp:
            line = decomp[1:end_line]
            line_img = []
            while line:
                if n_byte == 1:
                    (L,) = struct.unpack("!B", line[:n_byte])
                else:
                    R, G, B = struct.unpack("!BBB", line[:n_byte])
                    # ITU-R 601-2 luma transform
                    L = int(0.299 * R + 0.587 * G + 0.114 * B)
                line_img.append(L)
                line = line[n_byte_alpha:]
            image.append(line_img)
            decomp = decomp[end_line:]
        return aa_image(image)


def parse_images(line):
    "Tag all images found"
    # global (use state.) CONF
    while state.regex["img"].search(line):
        txt = state.regex["img"].search(line).group(1)
        tag = state.TAGS["img"]

        txt = fix_relative_path(txt)

        # If target supports image alignment, here we go
        if state.rules["imgalignable"]:
            align = get_image_align(line)  # right
            align_name = align.capitalize()  # Right

            # The align is a full tag, or part of the image tag (~A~)
            if state.TAGS["imgAlign" + align_name]:
                tag = state.TAGS["imgAlign" + align_name]
            else:
                align_tag = state.TAGS["_imgAlign" + align_name]
                tag = state.regex["_imgAlign"].sub(align_tag, tag, 1)

            # Dirty fix to allow centered solo images
            if align == "center" and state.TARGET in ("html", "xhtml"):
                rest = state.regex["img"].sub("", line, 1)
                if re.match(r"^\s+$", rest):
                    tag = "<center>%s</center>" % tag
            if align == "center" and state.TARGET == "xhtmls":
                rest = state.regex["img"].sub("", line, 1)
                if re.match(r"^\s+$", rest):
                    ## original (not validating):
                    # tag = '<div style="text-align: center;">%s</div>' % tag
                    ## dirty fix:
                    # tag = '</p><div style="text-align: center;">%s</div><p>' % tag
                    ## will validate, though img won't be centered:
                    tag = "%s" % tag

        # Rtf needs some tweaking
        if state.TARGET == "rtf" and not state.CONF.get("embed-images"):
            # insert './' for relative paths if needed
            if not re.match(r":/|:\\", txt):
                tag = state.regex["x"].sub("./\a", tag, 1)
            # insert image filename an extra time for readers that don't grok linked images
            tag = state.regex["x"].sub(txt, tag, 1)

        if state.TARGET in ["tex", "texs"]:
            tag = re.sub(r"\\b", r"\\\\b", tag)
            txt = txt.replace("_", "vvvvTexUndervvvv")

        if state.CONF.get("embed-images"):
            # Embedded images find files from the same location as linked images,
            # for consistant behaviour.
            basedir = os.path.dirname(state.CONF.get("outfile"))
            fullpath = PathMaster().join(basedir, txt)
            txt = embedImage(fullpath)
            if state.TARGET == "aat":
                return txt

        if state.TARGET == "aat" and state.CONF["slides"] and state.CONF["web"]:
            # global (use state.) AA_IMG
            mytype, width, height, bit_depth, colour_type, dpix, dpiy, data = (
                getImageInfo(txt)
            )
            state.AA_IMG = int((height / 600.0) * state.CONF["height"])

        # Ugly hack to avoid infinite loop when target's image tag contains []
        tag = tag.replace("[", "vvvvEscapeSquareBracketvvvv")

        line = state.regex["img"].sub(tag, line, 1)
        line = state.regex["x"].sub(txt, line, 1)

        if state.TARGET == "rst":
            line = line.split("ENDIMG")[0] + line.split("ENDIMG")[1].strip()

    return line.replace("vvvvEscapeSquareBracketvvvv", "[")


def add_inline_tags(line):
    # We can't use beauti.capitalize() for the beautifiers, because
    # 'i'.capitalize != 'I' for turkish locales.
    for font in ("fontBold", "fontItalic", "fontUnderline", "fontStrike"):
        if state.regex[font].search(line):
            line = beautify_me(font, line)

    line = parse_images(line)
    return line


def get_include_contents(file_, path=""):
    "Parses %!include: value and extract file contents"
    ids = {"`": "verb", '"': "raw", "'": "tagged"}
    id_ = "t2t"
    # Set include type and remove identifier marks
    mark = file_[0]
    if mark in ids:
        if file_[:2] == file_[-2:] == mark * 2:
            id_ = ids[mark]  # set type
            file_ = file_[2:-2]  # remove marks
    # Handle remote dir execution
    filepath = PathMaster().join(path, file_)
    # Read included file contents
    lines = Readfile(filepath, remove_linebreaks=1)
    # Default txt2tags marked text, just BODY matters
    if id_ == "t2t":
        lines = get_file_body(filepath)
        lines.insert(0, "%%!currentfile: %s" % (filepath))
        # This appears when included hit EOF with verbatim area open
        # lines.append('%%INCLUDED(%s) ends here: %s' % (id_, file_))
    process_source_file(filepath)[0]

    return id_, lines


def set_global_config(config):
    # global (use state.) CONF, TAGS, regex, rules, TARGET
    state.CONF = config
    state.rules = getRules(state.CONF)
    state.TAGS = getTags(state.CONF)
    state.regex = getRegexes()
    state.TARGET = config["target"]  # save for buggy functions that need global

    if state.rules.get("spread"):
        # Python math functions
        exec("from math import *", globals())
        # LibreOffice compatibility
        global SIN, COS, TAN, ASIN, ACOS, ATAN, SINH, COSH, TANH
        SIN = sin
        COS = cos
        TAN = tan
        ASIN = asin
        ACOS = acos
        ATAN = atan
        SINH = sinh
        COSH = cosh
        TANH = tanh


def convert(bodylines, config, firstlinenr=1):
    # global (use state.) BLOCK, TITLE, MASK

    set_global_config(config)

    target = config["target"]
    state.BLOCK = BlockMaster()
    state.MASK = MaskMaster()
    state.TITLE = TitleMaster()

    ret = []
    dump_source = []
    f_lastwasblank = 0

    # Compiling all PreProc regexes
    pre_filter = compile_filters(state.CONF["preproc"], _("Invalid PreProc filter state.regex"))

    # Let's mark it up!
    linenr = firstlinenr - 1
    lineref = 0
    while lineref < len(bodylines):
        # Defaults
        results_box = ""

        if (
            state.CONF.get("encoding")
            and state.CONF.get("encoding").lower() == "utf-8"
            and not isinstance(bodylines[lineref], str)
        ):
            untouchedline = bodylines[lineref].decode("utf-8")
        else:
            untouchedline = bodylines[lineref]

        dump_source.append(untouchedline)

        line = re.sub("[\n\r]+$", "", untouchedline)  # del line break

        # Apply PreProc filters
        if pre_filter:
            errmsg = _("Invalid PreProc filter replacement")
            for rgx, repl in pre_filter:
                try:
                    line = rgx.sub(repl, line)
                except:
                    Error("%s: '%s'" % (errmsg, repl))

        line = maskEscapeChar(line)  # protect \ char
        linenr += 1
        lineref += 1

        Debug(repr(line), 2, linenr)  # heavy debug: show each line

        # ------------------[ Comment Block ]------------------------

        # We're already on a comment block
        if state.BLOCK.block() == "comment":
            # Closing comment
            if state.regex["blockCommentClose"].search(line):
                ret.extend(state.BLOCK.blockout() or [])
                continue

            # Normal comment-inside line. Ignore it.
            continue

        # Detecting comment block init
        if (
            state.regex["blockCommentOpen"].search(line)
            and state.BLOCK.block() not in state.BLOCK.exclusive
        ):
            ret.extend(state.BLOCK.blockin("comment"))
            continue

        # -------------------------[ Tagged Text ]----------------------

        # We're already on a tagged block
        if state.BLOCK.block() == "tagged":
            # Closing tagged
            if state.regex["blockTaggedClose"].search(line):
                ret.extend(state.BLOCK.blockout())
                continue

            # Normal tagged-inside line
            state.BLOCK.holdadd(line)
            continue

        # Detecting tagged block init
        if (
            state.regex["blockTaggedOpen"].search(line)
            and state.BLOCK.block() not in state.BLOCK.exclusive
        ):
            ret.extend(state.BLOCK.blockin("tagged"))
            continue

        # One line tagged text
        if state.regex["1lineTagged"].search(line) and state.BLOCK.block() not in state.BLOCK.exclusive:
            ret.extend(state.BLOCK.blockin("tagged"))
            line = state.regex["1lineTagged"].sub("", line)
            state.BLOCK.holdadd(line)
            ret.extend(state.BLOCK.blockout())
            continue

        # -------------------------[ Raw Text ]----------------------

        # We're already on a raw block
        if state.BLOCK.block() == "raw":
            # Closing raw
            if state.regex["blockRawClose"].search(line):
                ret.extend(state.BLOCK.blockout())
                continue

            # Normal raw-inside line
            state.BLOCK.holdadd(line)
            continue

        # Detecting raw block init
        if state.regex["blockRawOpen"].search(line) and state.BLOCK.block() not in state.BLOCK.exclusive:
            ret.extend(state.BLOCK.blockin("raw"))
            continue

        # One line raw text
        if state.regex["1lineRaw"].search(line) and state.BLOCK.block() not in state.BLOCK.exclusive:
            ret.extend(state.BLOCK.blockin("raw"))
            line = state.regex["1lineRaw"].sub("", line)
            state.BLOCK.holdadd(line)
            ret.extend(state.BLOCK.blockout())
            continue

        # ------------------------[ Verbatim  ]----------------------

        # TIP We'll never support beautifiers inside verbatim

        # Closing table mapped to verb
        if (
            state.BLOCK.block() == "verb"
            and state.BLOCK.prop("mapped") == "table"
            and not state.regex["table"].search(line)
        ):
            ret.extend(state.BLOCK.blockout())

        # We're already on a verb block
        if state.BLOCK.block() == "verb":
            # Closing verb
            if state.regex["blockVerbClose"].search(line):
                ret.extend(state.BLOCK.blockout())
                continue

            # Normal verb-inside line
            state.BLOCK.holdadd(line)
            continue

        # Detecting verb block init
        if state.regex["blockVerbOpen"].search(line) and state.BLOCK.block() not in state.BLOCK.exclusive:
            ret.extend(state.BLOCK.blockin("verb"))
            f_lastwasblank = 0
            continue

        # One line verb-formatted text
        if state.regex["1lineVerb"].search(line) and state.BLOCK.block() not in state.BLOCK.exclusive:
            ret.extend(state.BLOCK.blockin("verb"))
            line = state.regex["1lineVerb"].sub("", line)
            state.BLOCK.holdadd(line)
            ret.extend(state.BLOCK.blockout())
            f_lastwasblank = 0
            continue

        # Tables are mapped to verb when target is not table-aware
        if not state.rules["tableable"] and state.regex["table"].search(line):
            if not state.BLOCK.isblock("verb"):
                ret.extend(state.BLOCK.blockin("verb"))
                state.BLOCK.propset("mapped", "table")
                state.BLOCK.holdadd(line)
                continue

        # ---------------------[ blank lines ]-----------------------

        if state.regex["blankline"].search(line):
            # Close open paragraph
            if state.BLOCK.isblock("para"):
                ret.extend(state.BLOCK.blockout())
                f_lastwasblank = 1
                continue

            # Close all open tables
            if state.BLOCK.isblock("table"):
                ret.extend(state.BLOCK.blockout())
                f_lastwasblank = 1
                continue

            # Close all open quotes
            while state.BLOCK.isblock("quote"):
                ret.extend(state.BLOCK.blockout())

            # Closing all open lists
            if f_lastwasblank:  # 2nd consecutive blank
                if state.BLOCK.block().endswith("list"):
                    state.BLOCK.holdaddsub("")  # helps parser
                while state.BLOCK.depth:  # closes list (if any)
                    ret.extend(state.BLOCK.blockout())
                continue  # ignore consecutive blanks

            # Paragraph (if any) is wanted inside lists also
            if state.BLOCK.block().endswith("list"):
                state.BLOCK.holdaddsub("")

            f_lastwasblank = 1
            continue

        # ---------------------[ special ]---------------------------

        if state.regex["special"].search(line):
            targ, key, val = ConfigLines().parse_line(line, None, target)
            # global (use state.) MAILING

            if key:
                Debug("Found config '%s', value '%s'" % (key, val), 1, linenr)
            else:
                Debug("Bogus Special Line", 1, linenr)

            # %!include command
            if key == "include":
                # The current path is always relative to the file where %!include appeared
                incfile = val
                incpath = os.path.dirname(state.CONF["currentsourcefile"])
                fullpath = PathMaster().join(incpath, incfile)

                # Infinite loop detection
                if os.path.abspath(fullpath) == os.path.abspath(
                    state.CONF["currentsourcefile"]
                ):
                    Error(
                        "%s: %s" % (_("A file cannot include itself (loop!)"), fullpath)
                    )

                inctype, inclines = get_include_contents(incfile, incpath)

                # Verb, raw and tagged are easy
                if inctype != "t2t":
                    ret.extend(state.BLOCK.blockin(inctype))
                    state.BLOCK.holdextend(inclines)
                    ret.extend(state.BLOCK.blockout())
                else:
                    # Insert include lines into body
                    # TODO include maxdepth limit
                    bodylines = (
                        bodylines[:lineref]
                        + inclines
                        + ["%%!currentfile: %s" % (state.CONF["currentsourcefile"])]
                        + bodylines[lineref:]
                    )
                    # Remove %!include call
                    if state.CONF["dump-source"]:
                        dump_source.pop()

            # %!currentfile command
            elif key == "currentfile":
                targ, key, val = ConfigLines().parse_line(line, "currentfile", target)
                if key:
                    Debug("Found config '%s', value '%s'" % (key, val), 1, linenr)
                    state.CONF["currentsourcefile"] = val
                # This line is done, go to next
                continue

            # %!fen command
            # Forsyth-Edward Notation
            elif key == "fen":
                # Handle options and arguments
                fenopt = FenOptions(val)
                filename = fenopt.get("infile")
                fen_unicode = fenopt.get("unicode")

                if fen_unicode:
                    if state.CONF["encoding"].lower() != "utf-8":
                        if not config["encoding"]:
                            Error(
                                _(
                                    "%!fen: Expected an UTF-8 file to use unicode fen option, you could set %!encoding: UTF-8"
                                )
                            )
                        else:
                            Error(
                                _(
                                    "%!fen: Expected an UTF-8 file to use unicode fen option"
                                )
                            )
                    unicode_chars = [chr(char) for char in range(0x2654, 0x2660)]
                    uni = dict(list(zip("KQRBNPkqrbnp", unicode_chars)))

                for line in Readfile(filename):
                    board = line.split()[0]
                    for i in range(1, 9):
                        board = board.replace(str(i), i * " ")
                    if fen_unicode:
                        for piece in uni:
                            board = board.replace(piece, uni[piece])
                    board = board.split("/")
                    table = convert_to_table(board, False, True, True)
                    ret.extend(
                        parse_convert_table(table, state.rules["tableable"], state.CONF["target"])
                    )
                # This line is done, go to next
                continue

            # %!db command
            elif key == "db":
                try:
                    import sqlite3
                except:
                    Error("No sqlite3 module")

                # Handle options and arguments
                dbopt = DbOptions(val)
                filename = dbopt.get("infile")
                db_query = dbopt.get("query")
                db_borders = dbopt.get("borders")
                db_center = dbopt.get("center")
                db_headers = dbopt.get("headers")
                db_mailing = dbopt.get("mailing")
                if db_mailing:
                    db_headers = True

                sqlite3.register_converter("NULL", str)
                sqlite3.register_converter("INTEGER", str)
                sqlite3.register_converter("REAL", str)
                sqlite3.register_converter("BLOB", str)

                db = sqlite3.connect(filename, detect_types=sqlite3.PARSE_DECLTYPES)
                dbc = db.cursor()

                if db_query:
                    res = dbc.execute(db_query)
                    if db_headers:
                        result = [
                            [[header[0] for header in dbc.description]] + res.fetchall()
                        ]
                    else:
                        result = [res.fetchall()]
                else:
                    result = []
                    table_names = dbc.execute(
                        "select name from sqlite_master where type='table'"
                    ).fetchall()
                    for table_name in table_names:
                        res = dbc.execute("select * from " + table_name[0])
                        if db_headers:
                            result.append(
                                [[header[0] for header in dbc.description]]
                                + res.fetchall()
                            )
                        else:
                            result.append(res.fetchall())

                db.close()

                if not db_mailing:
                    for tab in result:
                        # Convert each DB line to a txt2tags' table line
                        table = convert_to_table(tab, db_headers, db_borders, db_center)
                        # Parse and convert the new table
                        ret.extend(
                            parse_convert_table(
                                table, state.rules["tableable"], state.CONF["target"]
                            )
                        )
                else:
                    if not state.MAILING and not len(result) > 1:
                        state.MAILING = result[0]
                    else:
                        Error("Mailing: a document can't be linked to more than one db")

                # This line is done, go to next
                continue

            # %!csv command
            elif key == "csv":
                # Handle options and arguments
                csvopt = CsvOptions(val)
                filename = csvopt.get("infile")
                csv_separator = csvopt.get("separator")
                csv_quotechar = csvopt.get("quotechar")
                csv_headers = csvopt.get("headers")
                csv_borders = csvopt.get("borders")
                csv_center = csvopt.get("center")
                csvopt.get("utf8")
                csv_mailing = csvopt.get("mailing")

                if not filename:
                    Error(_("%!CSV command: Missing CSV file path:") + " " + val)

                if csv_separator == "space":
                    csv_separator = " "
                elif csv_separator == "tab":
                    csv_separator = "\t"

                if csv_quotechar:
                    reader = csv.reader(
                        Readfile(filename),
                        delimiter=csv_separator,
                        quotechar=csv_quotechar,
                        quoting=csv.QUOTE_MINIMAL,
                    )
                else:
                    reader = csv.reader(
                        Readfile(filename),
                        delimiter=csv_separator,
                        quoting=csv.QUOTE_NONE,
                    )

                # Convert each CSV line to a txt2tags' table line
                # foo,bar,baz -> | foo | bar | baz |
                if not csv_mailing:
                    try:
                        table = convert_to_table(
                            reader, csv_headers, csv_borders, csv_center
                        )
                    except csv.Error as e:
                        Error("CSV: file %s: %s" % (filename, e))
                    else:
                        # Parse and convert the new table
                        ret.extend(
                            parse_convert_table(
                                table, state.rules["tableable"], state.CONF["target"]
                            )
                        )
                else:
                    if not state.MAILING:
                        state.MAILING = reader
                    else:
                        Error("Mailing: a document can't be linked to more than one db")

                # This line is done, go to next
                continue

        # ---------------------[ dump-source ]-----------------------

        # We don't need to go any further
        if state.CONF["dump-source"]:
            continue

        # ---------------------[ Comments ]--------------------------

        # Just skip them (if not macro)
        if (
            state.regex["comment"].search(line)
            and not state.regex["macros"].match(line)
            and not state.regex["toc"].match(line)
        ):
            continue

        # ---------------------[ Triggers ]--------------------------

        # Valid line, reset blank status
        f_lastwasblank = 0

        # Any NOT quote line closes all open quotes
        if state.BLOCK.isblock("quote") and not state.regex["quote"].search(line):
            while state.BLOCK.isblock("quote"):
                ret.extend(state.BLOCK.blockout())

        # Any NOT table line closes an open table
        if state.BLOCK.isblock("table") and not state.regex["table"].search(line):
            ret.extend(state.BLOCK.blockout())

        # ---------------------[ Horizontal Bar ]--------------------

        if state.regex["bar"].search(line):
            # Bars inside quotes are handled on the Quote processing
            # Otherwise we parse the bars right here
            #
            if not (state.BLOCK.isblock("quote") or state.regex["quote"].search(line)) or (
                state.BLOCK.isblock("quote") and not state.rules["barinsidequote"]
            ):
                # Close all the opened blocks
                ret.extend(state.BLOCK.blockin("bar"))

                # Extract the bar chars (- or =)
                m = state.regex["bar"].search(line)
                bar_chars = m.group(2)

                # Process and dump the tagged bar
                state.BLOCK.holdadd(bar_chars)
                ret.extend(state.BLOCK.blockout())
                Debug("BAR: %s" % line, 6)

                # We're done, nothing more to process
                continue

        # ---------------------[ Title ]-----------------------------

        if (
            state.regex["title"].search(line) or state.regex["numtitle"].search(line)
        ) and not state.BLOCK.block().endswith("list"):
            if state.regex["title"].search(line):
                name = "title"
            else:
                name = "numtitle"

            # Close all the opened blocks
            ret.extend(state.BLOCK.blockin(name))

            # Process title
            state.TITLE.add(line)
            ret.extend(state.BLOCK.blockout())

            # We're done, nothing more to process
            continue

        # ---------------------[ %%toc ]-----------------------

        # %%toc line closes paragraph
        if state.BLOCK.block() == "para" and state.regex["toc"].search(line):
            ret.extend(state.BLOCK.blockout())

        # ---------------------[ apply masks ]-----------------------

        line = state.MASK.mask(line)

        # XXX from here, only block-inside lines will pass

        # ---------------------[ Quote ]-----------------------------

        if state.regex["quote"].search(line):
            # Store number of leading TABS
            quotedepth = len(state.regex["quote"].search(line).group(0))

            # Don't cross depth limit
            maxdepth = state.rules["quotemaxdepth"]
            if maxdepth and quotedepth > maxdepth:
                quotedepth = maxdepth

            # New quote
            if not state.BLOCK.isblock("quote"):
                ret.extend(state.BLOCK.blockin("quote"))

            # New subquotes
            while state.BLOCK.depth < quotedepth:
                state.BLOCK.blockin("quote")

            # Closing quotes
            while quotedepth < state.BLOCK.depth:
                ret.extend(state.BLOCK.blockout())

            # Bar inside quote
            if state.regex["bar"].search(line) and state.rules["barinsidequote"]:
                tempBlock = BlockMaster()
                tagged_bar = []
                tagged_bar.extend(tempBlock.blockin("bar"))
                tempBlock.holdadd(line)
                tagged_bar.extend(tempBlock.blockout())
                state.BLOCK.holdextend(tagged_bar)
                continue

        # ---------------------[ Lists ]-----------------------------

        # An empty item also closes the current list
        if state.BLOCK.block().endswith("list"):
            m = state.regex["listclose"].match(line)
            if m:
                listindent = m.group(1)
                listtype = m.group(2)
                currlisttype = state.BLOCK.prop("type")
                currlistindent = state.BLOCK.prop("indent")
                if listindent == currlistindent and listtype == currlisttype:
                    ret.extend(state.BLOCK.blockout())
                    continue

        if (
            state.regex["list"].search(line)
            or state.regex["numlist"].search(line)
            or state.regex["deflist"].search(line)
        ):
            listindent = state.BLOCK.prop("indent")
            listids = "".join(list(LISTNAMES.keys()))
            m = re.match("^( *)([%s]) " % listids, line)
            listitemindent = m.group(1)
            listtype = m.group(2)
            listname = LISTNAMES[listtype]
            results_box = state.BLOCK.holdadd

            # Del list ID (and separate term from definition)
            if listname == "deflist":
                term = parse_deflist_term(line)
                line = state.regex["deflist"].sub(SEPARATOR + term + SEPARATOR, line)
            else:
                line = state.regex[listname].sub(SEPARATOR, line)

            # Don't cross depth limit
            maxdepth = state.rules["listmaxdepth"]
            if maxdepth and state.BLOCK.depth == maxdepth:
                if len(listitemindent) > len(listindent):
                    listitemindent = listindent

            # List bumping (same indent, diff mark)
            # Close the currently open list to clear the mess
            if (
                state.BLOCK.block().endswith("list")
                and listname != state.BLOCK.block()
                and len(listitemindent) == len(listindent)
            ):
                ret.extend(state.BLOCK.blockout())
                listindent = state.BLOCK.prop("indent")

            # Open mother list or sublist
            if not state.BLOCK.block().endswith("list") or len(listitemindent) > len(
                listindent
            ):
                ret.extend(state.BLOCK.blockin(listname))
                state.BLOCK.propset("indent", listitemindent)
                state.BLOCK.propset("type", listtype)

            # Closing sublists
            while len(listitemindent) < len(state.BLOCK.prop("indent")):
                ret.extend(state.BLOCK.blockout())

            # O-oh, sublist before list ("\n\n  - foo\n- foo")
            # Fix: close sublist (as mother), open another list
            if not state.BLOCK.block().endswith("list"):
                ret.extend(state.BLOCK.blockin(listname))
                state.BLOCK.propset("indent", listitemindent)
                state.BLOCK.propset("type", listtype)

        # ---------------------[ Table ]-----------------------------

        # TODO escape undesired format inside table
        # TODO add pm6 target
        if state.regex["table"].search(line):
            if not state.BLOCK.isblock("table"):  # first table line!
                ret.extend(state.BLOCK.blockin("table"))
                state.BLOCK.tableparser.__init__(line)

            tablerow = TableMaster().parse_row(line)
            state.BLOCK.tableparser.add_row(tablerow)  # save config

            # Maintain line to unmask and inlines
            # XXX Bug: | **bo | ld** | turns **bo\x01ld** and gets converted :(
            # TODO isolate unmask+inlines parsing to use here
            line = SEPARATOR.join(tablerow["cells"])

        # ---------------------[ Paragraph ]-------------------------

        if not state.BLOCK.block() and not line.count(state.MASK.tocmask):  # new para!
            ret.extend(state.BLOCK.blockin("para"))

        ############################################################
        ############################################################
        ############################################################

        # ---------------------[ Final Parses ]----------------------

        # The target-specific special char escapes for body lines
        line = doEscape(target, line)

        line = add_inline_tags(line)
        line = state.MASK.undo(line)

        # ---------------------[ Hold or Return? ]-------------------

        ### Now we must choose where to put the parsed line
        #
        if not results_box:
            # List item extra lines
            if state.BLOCK.block().endswith("list"):
                results_box = state.BLOCK.holdaddsub
            # Other blocks
            elif state.BLOCK.block():
                results_box = state.BLOCK.holdadd
            # No blocks
            else:
                line = doFinalEscape(target, line)
                results_box = ret.append

        results_box(line)

    # EOF: close any open para/verb/lists/table/quotes
    Debug("EOF", 7)
    while state.BLOCK.block():
        ret.extend(state.BLOCK.blockout())

    # Maybe close some opened title area?
    if state.rules["titleblocks"]:
        ret.extend(state.TITLE.close_all())

    # Maybe a major tag to enclose body? (like DIV for CSS)
    if state.TAGS["bodyOpen"]:
        ret.insert(0, state.TAGS["bodyOpen"])
    if state.TAGS["bodyClose"]:
        ret.append(state.TAGS["bodyClose"])

    if state.CONF["toc-only"]:
        ret = []
    marked_toc = state.TITLE.dump_marked_toc(state.CONF["toc-level"])

    # If dump-source, all parsing is ignored
    if state.CONF["dump-source"]:
        ret = dump_source[:]

    return ret, marked_toc


##############################################################################
################################### state.GUI ######################################
##############################################################################
#
# Tk help: http://python.org/topics/tkinter/
#    Tuto: http://ibiblio.org/obp/py4fun/gui/tkPhone.html
#          /usr/lib/python*/lib-tk/state.Tkinter.py
#
# grid table : row=0, column=0, columnspan=2, rowspan=2
# grid align : sticky='n,s,e,w' (North, South, East, West)
# pack place : side='top,bottom,right,left'
# pack fill  : fill='x,y,both,none', expand=1
# pack align : anchor='n,s,e,w' (North, South, East, West)
# padding    : padx=10, pady=10, ipadx=10, ipady=10 (internal)
# checkbox   : offvalue is return if the _user_ deselected the box
# label align: justify=left,right,center


