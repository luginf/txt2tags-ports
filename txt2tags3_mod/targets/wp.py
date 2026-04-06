# txt2tags3_mod/targets/wp.py
# Tags and rules for the "wp" target.
# Auto-generated — edit carefully.

TAGS = {
    # Exclusions to let the WordPress code cleaner
    "bodyOpen": "",
    "bodyClose": "",
    "paragraphOpen": "",
    "paragraphClose": "",
    "comment": "",
    "EOD": "",
    # All list items must be closed
    "listItemClose": "</li>",
    "numlistItemClose": "</li>",
    "deflistItem2Close": "</dd>",
    # WP likes tags this way
    "bar1": "<hr>",
    "bar2": "<hr>",
    "fontBoldOpen": "<strong>",
    "fontBoldClose": "</strong>",
    "fontItalicOpen": "<em>",
    "fontItalicClose": "</em>",
},

RULES = {
    # TIP wp inherits all HTML state.rules
    "onelinepara": 1,
    "onelinequote": 1,
    "tagnotindentable": 1,
    "blanksaroundpara": 1,
    "quotemaxdepth": 1,
    "keepquoteindent": 0,
    "keeplistindent": 0,
    "notbreaklistitemclose": 1,
},
