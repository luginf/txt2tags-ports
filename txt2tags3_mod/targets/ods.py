# txt2tags3_mod/targets/ods.py
# Tags and rules for the "ods" target.
# Auto-generated — edit carefully.

TAGS = {
    "tableOpen": '<table:table table:name="' + "table_name" + 'n_table">',
    "tableClose": "</table:table>",
    "tableRowOpen": "<table:table-row>",
    "tableRowClose": "</table:table-row>",
    "tableCellOpen": "<table:table-cell~A~~S~><text:p>",
    "tableCellClose": "</text:p></table:table-cell>",
    "tableTitleCellOpen": '<table:table-cell~A~~S~><text:p><text:span text:style-name="T1">',
    "tableTitleCellClose": "</text:span></text:p></table:table-cell>",
    "tableCellCovered": '<table:covered-table-cell table:number-columns-repeated="\a"/>',
    "_tableCellAlignCenter": ' table:style-name="ce1"',
    "_tableCellAlignRight": ' table:style-name="ce2"',
    "_tableCellAlignLeftBorder": ' table:style-name="ce3"',
    "_tableCellAlignCenterBorder": ' table:style-name="ce4"',
    "_tableCellAlignRightBorder": ' table:style-name="ce5"',
    "_tableCellColSpan": ' table:number-columns-spanned="\a"',
    "EOD": "</office:spreadsheet></office:body></office:document>",
},

RULES = {
    "escapexmlchars": 1,
    "tableable": 1,
    "tableonly": 1,
    "tablecellstrip": 1,
    "tablecellspannable": 1,
    "tablecellcovered": 1,
    "tablecellaligntype": "cell",
},
