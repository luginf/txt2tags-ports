# txt2tags3_mod/targets/csv.py
# Tags and rules for the "csv" target.
# Auto-generated — edit carefully.
from ..constants import CSV

TAGS = {
    "tableCellSep": CSV["separator"],
    "tableCellOpen": CSV.get("quotechar") or "",
    "tableCellClose": CSV.get("quotechar") or "",
},

RULES = {
    "tableable": 1,
    "tableonly": 1,
    "tablecellstrip": 1,
},
