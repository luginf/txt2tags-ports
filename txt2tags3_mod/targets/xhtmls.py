# txt2tags3_mod/targets/xhtmls.py
# Tags and rules for the "xhtmls" target.
# Auto-generated — edit carefully.

TAGS = {
    "fontBoldOpen": "<strong>",
    "fontBoldClose": "</strong>",
    "fontItalicOpen": "<em>",
    "fontItalicClose": "</em>",
    "fontUnderlineOpen": '<span style="text-decoration:underline">',
    "fontUnderlineClose": "</span>",
    "fontStrikeOpen": '<span style="text-decoration:line-through">',  # use <del> instead ?
    "fontStrikeClose": "</span>",
    "listItemClose": "</li>",
    "numlistItemClose": "</li>",
    "deflistItem2Close": "</dd>",
    "bar1": '<hr class="light" />',
    "bar2": '<hr class="heavy" />',
    "img": '<img style="display: block;~a~" src="\a" alt=""/>',
    "imgEmbed": '<img~a~ src="\a" alt=""/>',
    "_imgAlignLeft": "margin: 0 auto 0 0;",
    "_imgAlignCenter": "margin: 0 auto 0 auto;",
    "_imgAlignRight": "margin: 0 0 0 auto;",
    "_tableAlignCenter": ' style="margin-left: auto; margin-right: auto;"',
    "_tableCellAlignRight": ' style="text-align:right"',
    "_tableCellAlignCenter": ' style="text-align:center"',
},

RULES = {
    # TIP xhtmls inherits all HTML state.rules
},
