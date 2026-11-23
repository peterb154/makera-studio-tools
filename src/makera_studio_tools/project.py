"""Read Makera Studio projects.

A .mks file is a zip holding makera.prj (JSON: stock, machine, toolpaths),
makera.bin (meshes/toolpath data) and a thumbnail. Studio also autosaves the
bare JSON to ~/Library/Application Support/MakeraStudio/temp/autosave/temp_makera.prj.
"""

import json
import zipfile
from pathlib import Path

AUTOSAVE = Path.home() / "Library/Application Support/MakeraStudio/temp/autosave/temp_makera.prj"


def load(path: str | Path) -> dict:
    """Return the 'project' dict from a .mks or .prj file."""
    path = Path(path).expanduser()
    if zipfile.is_zipfile(path):
        raw = zipfile.ZipFile(path).read("makera.prj")
    else:
        raw = path.read_bytes()
    return json.loads(raw)["project"]


def operations(project: dict) -> list[dict]:
    """Flatten every toolpath into a plain dict with the settings people care about."""
    ops = []
    for wcs in project["lstCoordinate"].values():
        for p in wcs["path"]:
            t = p["tools"][0]
            ops.append(
                {
                    "wcs": wcs["name"],
                    "name": p["pathName"],
                    "type": p["type"],
                    "tool_name": t["toolName"],
                    "tool_number": t["toolNumber"],
                    "tool_type": t["toolType"],
                    "diameter": t["diameter"],
                    "tip_diameter": t["tipDiameter"],
                    "half_angle": t["halfAngle"],
                    "flute_length": t["fluteLength"],
                    "stickout": t["stickoutLength"],
                    "rpm": t["spindleSpeed"],
                    "feed": t["feedrate"],
                    "plunge": t["plungeFeedrate"],
                    "step_down": t["stepDown"],
                    "step_over": t["stepOverMM"],
                    "feeds_preset_id": t.get("materialPropertyId"),
                    "multiple_depths": not p["finishing"][0],
                    "max_depth_enabled": p["depth"].get("enablelastlayer", False),
                    "max_depth": p["depth"].get("finishStepDown"),
                    "tailstock": p["haveTailTop"],
                    "ramping": p["Ramping_clear"]["useRamping"],
                    "safe_z": p["safe"]["safeZ"],
                    "side_allowance": p["lstSideAllowance"][0],
                    "bottom_allowance": p["machining_allowance"][0],
                }
            )
    return ops


def summary(project: dict) -> dict:
    stock, mach = project["stStockInfo"], project["machine"]
    return {
        "machine": {
            "model": mach["model"],
            "max_rpm": mach["maxRPM"],
            "max_feed": mach["maxFeedRate"],
            "range_a_diameter": mach["range_A_Diameter"],
            "range_a_length": mach["range_A_Length"],
        },
        "four_axis": project["b4DType"],
        "stock": {
            "length": stock["length"],
            "width": stock["width"],
            "height": stock["height"],
            "material": stock["materialobj"]["materialSubcategoryName"],
            "material_id": stock["materialobj"]["materialId"],
        },
        "models": [m["name"] for m in project.get("lst3DModels", [])],
        "operations": operations(project),
    }
