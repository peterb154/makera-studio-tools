"""makera-check: print a project's operations and any warnings."""

import argparse
import contextlib

from . import library, project
from .check import check


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "file", nargs="?", default=project.AUTOSAVE, help=".mks or .prj (default: Studio autosave)"
    )
    ap.add_argument("--db", default=None, help="tool library (default: Studio's makera_library.db)")
    args = ap.parse_args(argv)

    con = None
    with contextlib.suppress(Exception):
        con = library.connect(args.db)
    r = check(project.load(args.file), con)

    m, s = r["machine"], r["stock"]
    print(f"{m['model']}: max {m['max_rpm']} rpm, {m['max_feed']} mm/min")
    print(f"Stock {s['length']} x {s['width']} x {s['height']} {s['material']}\n")
    for op in r["operations"]:
        print(f"{op['name']}  T{op['tool_number']} {op['tool_name']}")
        print(
            f"  {op['rpm']} rpm  feed {op['feed']}  plunge {op['plunge']}  chip load {op['chip_load']}"
            f"  step down {op['step_down']}  step over {op['step_over']}  stickout {op['stickout']}"
        )
    print("\nWarnings:" if r["warnings"] else "\nNo warnings.")
    for w in r["warnings"]:
        print(f"  - {w}")
    return 1 if r["warnings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
