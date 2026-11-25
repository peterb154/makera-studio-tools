"""makera-rotary: write 4th-axis turning and threading G-code (check it before you run it)."""

import argparse
import sys

from .rotary import Job, cone, groove, thread, turn


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--out", help="output .nc (default: stdout)")
    ap.add_argument("--tool", type=int, required=True)
    ap.add_argument("--rpm", type=int, default=12000)
    ap.add_argument("--safe-z", type=float, default=40, help="retract radius, above all stock")
    ap.add_argument("--no-air", action="store_true")
    ap.add_argument(
        "--verify",
        type=float,
        nargs=2,
        metavar=("X", "R"),
        help="park 2 mm above radius R at X for 10 s before starting",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("turn", help="turn a cylinder with a flat end mill")
    t.add_argument("--x1", type=float, required=True, help="tool centre X at one end")
    t.add_argument("--x2", type=float, required=True, help="tool centre X at the other end")
    t.add_argument("--r-start", type=float, required=True, help="largest radius of the stock now")
    t.add_argument("--r", type=float, required=True, help="final radius")
    t.add_argument("--step", type=float, default=0.15, help="max depth per pass")
    t.add_argument("--lead", type=float, default=2.0, help="X advance per turn")
    t.add_argument("--feed", type=float, default=300)
    t.add_argument("--y-offset", type=float, default=0.0, help="tool centre Y; ~tool diameter / 4")

    h = sub.add_parser("thread", help="single-point thread along a helix with a V-bit")
    h.add_argument("--pitch", type=float, required=True)
    h.add_argument("--x-start", type=float, required=True, help="tip X where each pass starts (in air)")
    h.add_argument("--x-end", type=float, required=True, help="tip X where each pass ends")
    h.add_argument("--x0", type=float, required=True, help="groove centre X at A=0 (pick-up)")
    h.add_argument(
        "--hand", type=int, choices=(1, -1), required=True, help="+1 if the groove moves +X as A increases"
    )
    h.add_argument("--r-start", type=float, required=True, help="tip radius of the first pass")
    h.add_argument("--r-root", type=float, required=True, help="tip radius of the last pass")
    h.add_argument("--feed", type=float, default=150)
    h.add_argument("--check", action="store_true", help="spindle-off pick-up check instead")
    h.add_argument("--retract", type=float, help="rewind radius between passes (just above crests)")
    c = sub.add_parser("cone", help="finish a straight profile (cone) with a ball end mill")
    c.add_argument("--x1", type=float, required=True, help="surface start X")
    c.add_argument("--r1", type=float, required=True, help="surface start radius")
    c.add_argument("--x2", type=float, required=True, help="surface end X")
    c.add_argument("--r2", type=float, required=True, help="surface end radius")
    c.add_argument("--ball-r", type=float, required=True)
    c.add_argument("--offsets", type=float, nargs="+", default=[0.15, 0.0])
    c.add_argument("--step", type=float, default=0.3, help="advance along the surface per turn")
    c.add_argument("--feed", type=float, default=300)
    g = sub.add_parser("groove", help="spiral a groove down at fixed X (cut-off with a tab)")
    g.add_argument("--x", type=float, required=True, help="tool centre X")
    g.add_argument("--r-start", type=float, required=True, help="start radius, above the stock")
    g.add_argument("--r", type=float, required=True, help="final radius (tab)")
    g.add_argument("--per-turn", type=float, default=0.15)
    g.add_argument("--feed", type=float, default=300)
    g.add_argument("--y-offset", type=float, default=0.0)
    a = ap.parse_args(argv)

    job = Job(
        tool=a.tool,
        rpm=a.rpm,
        safe_z=a.safe_z,
        air=not a.no_air,
        verify=tuple(a.verify) if a.verify else None,
    )
    if a.cmd == "turn":
        job.y = a.y_offset
        code = turn(job, a.x1, a.x2, a.r_start, a.r, a.step, a.lead, a.feed)
    elif a.cmd == "groove":
        job.y = a.y_offset
        code = groove(job, a.x, a.r_start, a.r, a.per_turn, a.feed)
    elif a.cmd == "cone":
        code = cone(job, a.x1, a.r1, a.x2, a.r2, a.ball_r, tuple(a.offsets), a.step, a.feed)
    else:
        code = thread(
            job,
            a.pitch,
            a.x_start,
            a.x_end,
            a.x0,
            a.hand,
            a.r_start,
            a.r_root,
            feed=a.feed,
            check=a.check,
            retract=a.retract,
        )
    if a.out:
        with open(a.out, "w") as f:
            f.write(code)
    else:
        sys.stdout.write(code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
