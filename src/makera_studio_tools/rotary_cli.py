"""makera-rotary: write 4th-axis turning and threading G-code (check it before you run it)."""

import argparse
import sys

from .rotary import Job, thread, turn


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--out", help="output .nc (default: stdout)")
    ap.add_argument("--tool", type=int, required=True)
    ap.add_argument("--rpm", type=int, default=12000)
    ap.add_argument("--safe-z", type=float, default=40, help="retract radius, above all stock")
    ap.add_argument("--no-air", action="store_true")
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
    a = ap.parse_args(argv)

    job = Job(tool=a.tool, rpm=a.rpm, safe_z=a.safe_z, air=not a.no_air)
    if a.cmd == "turn":
        job.y = a.y_offset
        code = turn(job, a.x1, a.x2, a.r_start, a.r, a.step, a.lead, a.feed)
    else:
        code = thread(
            job, a.pitch, a.x_start, a.x_end, a.x0, a.hand, a.r_start, a.r_root, feed=a.feed, check=a.check
        )
    if a.out:
        with open(a.out, "w") as f:
            f.write(code)
    else:
        sys.stdout.write(code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
