"""Edit toolpath settings in a Makera Studio project.

Only makera.prj is changed; every other file in the .mks zip is copied byte for byte.
Toolpaths already generated in makera.bin are NOT recalculated: regenerate them in Studio
after editing. Never edit a project that is open in Studio.
"""

import json
import shutil
import zipfile
from pathlib import Path

# friendly name -> (key path inside a toolpath dict, converter from user value)
FIELDS = {
    "rpm": (("tools", 0, "spindleSpeed"), int),
    "feed": (("tools", 0, "feedrate"), float),
    "plunge": (("tools", 0, "plungeFeedrate"), float),
    "step_down": (("tools", 0, "stepDown"), float),
    "step_over": (("tools", 0, "stepOverMM"), float),
    "stickout": (("tools", 0, "stickoutLength"), float),
    "tool_number": (("tools", 0, "toolNumber"), int),
    "tailstock": (("haveTailTop",), bool),
    "ramping": (("Ramping_clear", "useRamping"), bool),
    "max_depth_enabled": (("depth", "enablelastlayer"), bool),
    "max_depth": (("depth", "finishStepDown"), float),
    "safe_z": (("safe", "safeZ"), float),
    "multiple_depths": (("finishing", 0), lambda v: not bool(v)),  # stored inverted
}


def _paths(project: dict) -> list[dict]:
    return [p for wcs in project["lstCoordinate"].values() for p in wcs["path"]]


def set_op(project: dict, op: int, **changes) -> list[str]:
    """Apply changes to toolpath number `op` (0-based, as listed by operations()). Returns a change log."""
    path = _paths(project)[op]
    log = []
    for name, value in changes.items():
        if name not in FIELDS:
            raise KeyError(f"unknown field {name!r}; choose from {sorted(FIELDS)}")
        keys, convert = FIELDS[name]
        node = path
        for k in keys[:-1]:
            node = node[k]
        old, node[keys[-1]] = node[keys[-1]], convert(value)
        log.append(f"{path['pathName']}: {name} {old!r} -> {node[keys[-1]]!r}")
    return log


def save(project: dict, src: str | Path, dst: str | Path) -> Path:
    """Write `project` into a copy of the .mks `src` at `dst` (dst must differ from src)."""
    src, dst = Path(src).expanduser(), Path(dst).expanduser()
    if src.resolve() == dst.resolve():
        raise ValueError("refusing to overwrite the source; write to a new file")
    text = json.dumps({"project": project}, indent=4, ensure_ascii=False)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            if info.filename == "makera.prj":
                zout.writestr(info, text.encode("utf-8"))
            else:
                with zin.open(info) as f, zout.open(info, "w") as g:
                    shutil.copyfileobj(f, g, 1 << 20)
    tmp.replace(dst)
    return dst
