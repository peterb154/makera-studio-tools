"""Hand-rolled 4th-axis G-code for round parts: turning cylinders and cutting threads.

Coordinates are the job's work coordinates: X along the axis, Y = 0, Z = radius from the
A axis centreline, A in degrees. Nothing here knows your setup; check every program first.

Z1 firmware note (Robot.cpp, append_milestone): on any move that turns A, F is treated as a
surface speed around the part (mm/min, with a +30 mm fudge on the perimeter), so feeds below
are surface feeds.
"""

import math
from dataclasses import dataclass

MAX_LINE = 63  # the Z1 firmware cuts longer lines short without a warning


def _f(v: float) -> str:
    return f"{v:.3f}".rstrip("0").rstrip(".")


@dataclass
class Job:
    tool: int
    rpm: int
    safe_z: float
    air: bool = True
    y: float = 0.0  # tool centre offset from the axis in Y
    # (x, radius) of a known surface: before the spindle starts, the tool parks 2 mm above it
    # for 10 s so a wrong tool length or Z zero shows as the wrong gap, not as a crash.
    verify: tuple[float, float] | None = None

    def header(self, title: str) -> list[str]:
        lines = [f"({title[: MAX_LINE - 2]})", "G90 G21", f"T{self.tool} M6"]
        if self.verify:
            x, r = self.verify
            lines += [
                "M5",
                f"G0 Z{_f(self.safe_z)}",
                f"G0 Y{_f(self.y)}",
                f"G0 X{_f(x)}",
                f"(VERIFY: tip 2mm above R{_f(r)} for 10s)",
                f"G0 Z{_f(r + 10)}",
                f"G1 Z{_f(r + 2)} F100",  # slow: a wrong Z shows before it can hit
                "G4 S10",
                f"G0 Z{_f(self.safe_z)}",
            ]
        if self.air:
            lines.append("M7")
        lines += [f"S{self.rpm} M3", f"G0 Z{_f(self.safe_z)}", f"G0 Y{_f(self.y)}"]
        return lines

    def footer(self) -> list[str]:
        return [f"G0 Z{_f(self.safe_z)}", "M5", "M9" if self.air else "", "M30"]


def depths(start: float, final: float, step: float) -> list[float]:
    """Radii from just below `start` down to `final`, at most `step` apart."""
    n = max(1, math.ceil(round((start - final) / step, 6)))
    return [final + (start - final) * (n - i - 1) / n for i in range(n)]


def turn(
    job: Job,
    x1: float,
    x2: float,
    r_start: float,
    r_final: float,
    step: float = 0.15,
    lead: float = 2.0,
    feed: float = 300,
    plunge: float = 100,
) -> str:
    """Turn a true cylinder of radius r_final with a flat end mill, tool centre from x1 to x2.

    Each pass ramps down over one turn, then spirals along X by `lead` per turn
    (keep lead under half the cut width), then makes one more turn at the end.
    The end mill's flat bottom touches the part along the line Y = 0. With job.y = 0 that line
    runs through the tool centre, where the cutting speed is zero, so set job.y to about a
    quarter of the tool diameter: the bottom still meets the part at Z = radius, but every
    point of the cut moves. Cut width along X is then 2 * sqrt(r_tool^2 - y^2).
    """
    out = job.header(f"turn R{_f(r_final)} X{_f(x1)}-{_f(x2)}")
    a = 0.0
    out += [f"G0 X{_f(x1)}", "G0 A0", f"G0 Z{_f(r_start + 1)}"]
    for i, r in enumerate(depths(r_start, r_final, step)):
        xa, xb = (x1, x2) if i % 2 == 0 else (x2, x1)
        a += 360
        out.append(f"G1 Z{_f(r)} A{_f(a)} F{_f(plunge)}")
        turns = abs(xb - xa) / lead
        a += 360 * turns
        out.append(f"G1 X{_f(xb)} A{_f(a)} F{_f(feed)}")
        a += 360
        out.append(f"G1 A{_f(a)}")
    return "\n".join(line for line in out + job.footer() if line) + "\n"


def thread(
    job: Job,
    pitch: float,
    x_start: float,
    x_end: float,
    x0: float,
    hand: int,
    r_start: float,
    r_root: float,
    infeed: list[float] | None = None,
    feed: float = 150,
    spring: bool = True,
    check: bool = False,
    retract: float | None = None,
) -> str:
    """Single-point thread along an existing (or new) helix with a V-bit.

    The groove centre is at X = x0 + hand * pitch * A / 360 (x0 and hand from the pick-up:
    hand = +1 if the groove moves +X as A increases). Every pass starts at x_start and runs to
    x_end on that helix, so passes stay in step. `infeed` is the depth of each pass; by default
    passes get lighter as the cut gets wider. check=True writes a spindle-off program that stops
    the tip 0.8 mm above r_root at four points on the helix so you can see it sits in the groove.
    """

    def a_at(x: float) -> float:
        return (x - x0) * 360 / (hand * pitch)

    a1, a2 = a_at(x_start), a_at(x_end)
    if check:
        out = [
            f"(thread check P{_f(pitch)} x0 {_f(x0)})",
            "G90 G21",
            f"T{job.tool} M6",
            "M5",
            f"G0 Z{_f(job.safe_z)}",
            "G0 Y0",
        ]
        if job.verify:
            out = job.header(f"thread check P{_f(pitch)} x0 {_f(x0)}")
            out = [ln for ln in out if not ln.startswith(("S", "M7"))] + ["M5"]
        for k in range(4):
            x = x_start + (x_end - x_start) * k / 3
            out += [
                f"G0 X{_f(x)} A{_f(a_at(x))}",
                f"G1 Z{_f(r_root + 0.8)} F200",
                "G4 S8",  # S = seconds in every firmware mode; P is ms in reprap mode
                f"G0 Z{_f(r_root + 2)}",
            ]
        out += [f"G0 Z{_f(job.safe_z)}", "M30"]
        return "\n".join(out) + "\n"

    total = r_start - r_root
    if infeed is None:
        infeed, left, k = [], total, 1
        while left > 1e-6:
            d = min(left, max(0.03, round(0.2 / math.sqrt(k), 3)))
            infeed.append(d)
            left -= d
            k += 1
    out = job.header(f"thread P{_f(pitch)} X{_f(x_start)}-{_f(x_end)} R{_f(r_root)}")
    r = r_start
    passes = infeed + ([0.0] if spring else [])
    # Rewind between passes at `retract` (a radius just above the crests) instead of safe Z:
    # the firmware caps A by surface speed at the current radius, so a low rewind is far faster.
    # The rewind follows the same helix, so the tip stays over the groove.
    back = job.safe_z if retract is None else retract
    for d in passes:
        r = max(r_root, r - d)
        out += [
            f"G0 X{_f(x_start)} A{_f(a1)}",
            f"G0 Z{_f(r + 1)}",
            f"G1 Z{_f(r)} F100",
            f"G1 X{_f(x_end)} A{_f(a2)} F{_f(feed)}",
            f"G0 Z{_f(back)}",
        ]
    out.append(f"G0 Z{_f(job.safe_z)}")
    return "\n".join(line for line in out + job.footer() if line) + "\n"
