# makera-studio-tools

Unofficial tools for [Makera Studio](https://www.makera.com/) projects. Not affiliated with Makera.

- **`makera-check`**: prints each toolpath's speeds and feeds, chip load, and warnings for common mistakes.
- **`makera-studio-mcp`**: MCP server so an AI assistant can read projects, check them, and look up tool presets.

Read-only. Nothing here writes to your projects or the Studio library.

## Quick start

```bash
uv sync
uv run makera-check ~/Downloads/Part.mks   # or no argument = Studio's current autosave
```

Add the MCP server to Claude Code:

```bash
claude mcp add makera-studio -- uv --directory /path/to/makera-studio-tools run makera-studio-mcp
```

Tools: `read_project`, `check_project`, `list_tools`, `get_feeds`.

## What it checks

- rpm / feed above the machine's limits
- chip load outside 0.005–0.08 mm/tooth (flute count is guessed from the tool name)
- tool stickout not set (simulation collision check can't be trusted)
- "Max Depth" ticked (it defaults on, at 3 mm)
- 4th axis: Tailstock unchecked (toolpath then spans the whole stock, including the chuck end)
- 4th axis: safe Z within 2 mm of the stock's corners
- feeds preset made for a different material than the stock
- two different tools sharing a tool number (the machine won't stop to change tools)

## File formats (reverse-engineered, macOS)

| What | Where |
|---|---|
| Project | `.mks` = zip of `makera.prj` (JSON), `makera.bin`, `prjImg.png` |
| Autosave | `~/Library/Application Support/MakeraStudio/temp/autosave/temp_makera.prj` |
| Tool + feeds library | `~/Library/Application Support/MakeraStudio/makera_library.db` (SQLite) |

In `makera.prj`, toolpaths are under `project.lstCoordinate.<n>.path[]`, each with `tools[0]`
(speeds, feeds, stickout), `haveTailTop` (the Tailstock checkbox), `Ramping_clear`, `safe`, and
`depth.enablelastlayer` / `finishStepDown` (the "Max Depth" checkbox and value).

`config.ini` in the same folder holds login tokens. These tools never read it.

## Development

```bash
uv run pytest
uv run ruff check . && uv run ruff format .
```
