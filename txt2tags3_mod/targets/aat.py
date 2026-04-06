# txt2tags3_mod/targets/aat.py
# Tags and rules for the "aat" target.
# Auto-generated — edit carefully.
from ..constants import AA
from ..aa import aa_line

TAGS = {
    "title1": "\a",
    "title2": "\a",
    "title3": "\a",
    "title4": "\a",
    "title5": "\a",
    "blockQuoteLine": AA["quote"],
    "listItemOpen": AA["bullet"] + " ",
    "numlistItemOpen": "\a. ",
    "bar1": aa_line(AA["bar1"], config["width"]),
    "bar2": aa_line(AA["bar2"], config["width"]),
    "url": "\a",
    "urlMark": "\a[\a]",
    "email": "\a",
    "emailMark": "\a[\a]",
    "img": "[\a]",
    "imgEmbed": "\a",
    "fontBoldOpen": "*",
    "fontBoldClose": "*",
    "fontItalicOpen": "/",
    "fontItalicClose": "/",
    "fontUnderlineOpen": "_",
    "fontUnderlineClose": "_",
    "fontStrikeOpen": "-",
    "fontStrikeClose": "-",
},

RULES = {
    # TIP art inherits all TXT state.rules
},
