"""Read Makera Studio's tool and feeds library (SQLite).

Makera's presets live in t_Makera* tables, user-defined ones in t_Custom*/t_Customer*.
Feeds are per (tool, material) in t_*CutterProperties.
Never read config.ini in the same folder: it holds login tokens.
"""

import sqlite3
from pathlib import Path

DEFAULT_DB = Path.home() / "Library/Application Support/MakeraStudio/makera_library.db"

_TOOLS = """
select cutterId, cutterName, cutterCategoryId, cutterDiameter, cutterTipDiameter, cutterHalfAngle,
       cutterFluteLength, cutterStickoutLength, '{src}' as source
from {table}
"""

_FEEDS = """
select l.cutterName, m.materialSubcategoryName, p.spindleSpeed, p.feedRate, p.plungeFeedRate,
       p.stepDown, p.stepOver, p.stepOverPercent, '{src}' as source
from {props} p
join {tools} l on l.cutterId = p.cutterID
left join t_MaterialList m on m.materialID = p.materialId
"""


def connect(db: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db).expanduser() if db else DEFAULT_DB
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def materials(con) -> dict[str, str]:
    return {r[0]: r[1] for r in con.execute("select materialID, materialSubcategoryName from t_MaterialList")}


def tools(con, name: str = "") -> list[dict]:
    sql = " union all ".join(
        [
            _TOOLS.format(table="t_MakeraCutterList", src="makera"),
            _TOOLS.format(table="t_CustomCutterList", src="custom"),
        ]
    )
    rows = con.execute(f"select * from ({sql}) where cutterName like ? order by cutterName", (f"%{name}%",))
    return [dict(r) for r in rows]


def feeds(con, tool: str = "", material: str = "") -> list[dict]:
    sql = " union all ".join(
        [
            _FEEDS.format(props="t_MakeraCutterProperties", tools="t_MakeraCutterList", src="makera"),
            _FEEDS.format(props="t_CustomerCutterProperties", tools="t_CustomCutterList", src="custom"),
        ]
    )
    rows = con.execute(
        f"select * from ({sql}) where cutterName like ? and coalesce(materialSubcategoryName,'') like ?"
        " order by cutterName, materialSubcategoryName",
        (f"%{tool}%", f"%{material}%"),
    )
    return [dict(r) for r in rows]


def preset_material(con, preset_id: str | None) -> str | None:
    """Material ID a feeds preset was made for."""
    if not preset_id:
        return None
    for table in ("t_CustomerCutterProperties", "t_MakeraCutterProperties"):
        row = con.execute(f"select materialId from {table} where propertiesId = ?", (preset_id,)).fetchone()
        if row:
            return row[0]
    return None
