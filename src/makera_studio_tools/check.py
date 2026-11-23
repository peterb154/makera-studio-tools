"""Sanity checks for a Makera Studio project. Each check returns plain-English warnings."""

import math

from . import library
from .project import summary

CHIP_LOAD_RANGE = (0.005, 0.08)  # mm/tooth, loose bounds for small carbide tools


def flutes(tool_name: str) -> int:
    """Flute count isn't stored in the project; guess from the name, default 1."""
    n = tool_name.lower().replace(" ", "")
    for k in (4, 3, 2):
        if f"{k}flute" in n:
            return k
    return 1


def chip_load(op: dict) -> float:
    return op["feed"] / (op["rpm"] * flutes(op["tool_name"]))


def check(project: dict, con=None) -> dict:
    s = summary(project)
    mach, stock = s["machine"], s["stock"]
    corner_r = math.hypot(stock["width"], stock["height"]) / 2
    warnings = []

    def warn(op, msg):
        warnings.append(f"{op['name']} ({op['tool_name']}): {msg}")

    names_by_number: dict[int, set[str]] = {}
    for op in s["operations"]:
        op["chip_load"] = round(chip_load(op), 4)
        names_by_number.setdefault(op["tool_number"], set()).add(op["tool_name"])

        if op["rpm"] > mach["max_rpm"]:
            warn(op, f"{op['rpm']} rpm exceeds machine max {mach['max_rpm']}")
        if op["feed"] > mach["max_feed"]:
            warn(op, f"feed {op['feed']} exceeds machine max {mach['max_feed']}")
        lo, hi = CHIP_LOAD_RANGE
        if not lo <= op["chip_load"] <= hi:
            warn(op, f"chip load {op['chip_load']} mm/tooth outside {lo}-{hi}")
        if op["stickout"] <= 0:
            warn(op, "tool stickout not set; holder collision check in the simulation is unreliable")
        if op["max_depth_enabled"]:
            warn(op, f"'Max Depth' ticked ({op['max_depth']} mm); untick unless you want a shallow cut")
        if s["four_axis"]:
            if not op["tailstock"]:
                warn(
                    op, "Tailstock unchecked: toolpath spans the whole stock length, including the chuck end"
                )
            if op["safe_z"] < corner_r + 2:
                warn(op, f"safe Z {op['safe_z']} is within 2 mm of the stock corners (r {corner_r:.1f})")
        if con is not None:
            preset = library.preset_material(con, op["feeds_preset_id"])
            if preset and preset != stock["material_id"]:
                mats = library.materials(con)
                warn(op, f"feeds preset is for {mats.get(preset, preset)}, stock is {stock['material']}")

    for number, names in names_by_number.items():
        if len(names) > 1:
            warnings.append(f"T{number} is shared by {sorted(names)}: the machine won't change tools")

    return {**s, "warnings": warnings}
