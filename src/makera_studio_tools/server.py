"""MCP server exposing read-only access to Makera Studio projects and its tool library."""

from contextlib import closing
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from . import edit, library, project
from .check import check

mcp = MCPServer("makera-studio")


@mcp.tool()
def read_project(path: str = "") -> dict:
    """Stock, machine and every toolpath's settings from a .mks/.prj. Empty path = Studio's autosave."""
    return project.summary(project.load(path or project.AUTOSAVE))


@mcp.tool()
def check_project(path: str = "") -> dict:
    """read_project plus warnings: machine limits, chip load, stickout, tailstock, safe Z, Max Depth,
    feeds-preset material mismatch, shared tool numbers. Empty path = Studio's autosave."""
    with closing(library.connect()) as con:
        return check(project.load(path or project.AUTOSAVE), con)


@mcp.tool()
def list_tools(name: str = "") -> list[dict]:
    """Tools in the Studio library (Makera presets + custom), filtered by name substring."""
    with closing(library.connect()) as con:
        return library.tools(con, name)


@mcp.tool()
def get_feeds(tool: str = "", material: str = "") -> list[dict]:
    """Preset speeds/feeds per tool and material, filtered by name substrings (e.g. '30º', '6061')."""
    with closing(library.connect()) as con:
        return library.feeds(con, tool, material)


@mcp.tool()
def edit_operation(path: str, op: int, changes: dict, out_path: str = "") -> dict:
    """Change settings of toolpath `op` (0-based, order from read_project) in a .mks and save a COPY.

    changes keys: rpm, feed, plunge, step_down, step_over, stickout, tool_number, tailstock, ramping,
    max_depth_enabled, max_depth, safe_z, multiple_depths. Default out_path is <name>-edited.mks.
    The source is never overwritten. Close the project in Studio first, then open the copy and
    regenerate the edited toolpaths (saved toolpaths are not recalculated).
    """
    src = Path(path).expanduser()
    out = Path(out_path).expanduser() if out_path else src.with_name(src.stem + "-edited.mks")
    p = project.load(src)
    log = edit.set_op(p, op, **changes)
    edit.save(p, src, out)
    with closing(library.connect()) as con:
        return {"saved": str(out), "changes": log, "warnings": check(p, con)["warnings"]}


def main():
    mcp.run()


if __name__ == "__main__":
    main()
