import re

from makera_studio_tools.rotary import MAX_LINE, Job, depths, thread, turn

JOB = Job(tool=1, rpm=12000, safe_z=40)


def moves(code):
    """Yield dicts of the axis words on each G0/G1 line."""
    for line in code.splitlines():
        if re.match(r"G[01] ", line):
            yield dict((k, float(v)) for k, v in re.findall(r"([XYZAF])(-?[\d.]+)", line))


def test_depths_end_exactly_at_final_and_never_exceed_step():
    d = depths(12.95, 12.45, 0.15)
    assert d[-1] == 12.45
    steps = [a - b for a, b in zip([12.95] + d, d, strict=False)]
    assert max(steps) <= 0.15 + 1e-9


def test_turn_stays_in_x_range_and_reaches_final_radius():
    code = turn(JOB, 43.7, 53.0, 12.95, 12.45)
    ms = list(moves(code))
    assert all(43.7 <= m["X"] <= 53.0 for m in ms if "X" in m)
    assert min(m["Z"] for m in ms if "Z" in m) == 12.45
    assert all(len(line) <= MAX_LINE for line in code.splitlines())


def test_thread_passes_follow_the_picked_up_helix():
    x0, pitch, hand = 70.0, 1.5, 1
    code = thread(JOB, pitch, 75.5, 58.5, x0, hand, 7.0, 6.1)
    for m in moves(code):
        if "X" in m and "A" in m:  # every pass start and end lies on the groove
            assert abs(m["X"] - (x0 + hand * pitch * m["A"] / 360)) < 0.01
    cuts = [m["Z"] for m in moves(code) if set(m) == {"Z", "F"} and m["F"] == 100]
    assert cuts[-1] == cuts[-2] == 6.1  # last depth plus a spring pass
    assert all(len(line) <= MAX_LINE for line in code.splitlines())


def test_thread_check_turns_spindle_off_and_stays_above_root():
    code = thread(JOB, 2.0, 27.5, 35.5, 30.0, -1, 17.8, 16.77, check=True)
    assert "M5" in code and not re.search(r"\bM3\b", code)  # M30 is fine
    assert min(m["Z"] for m in moves(code) if "Z" in m) > 16.77


def test_turn_with_y_offset_keeps_z_as_radius():
    code = turn(Job(tool=1, rpm=12000, safe_z=40, y=1.6), 43.7, 53.0, 12.95, 12.45)
    assert "G0 Y1.6" in code
    assert min(m["Z"] for m in moves(code) if "Z" in m) == 12.45


def test_verify_parks_above_reference_before_spindle_starts():
    code = turn(Job(tool=1, rpm=12000, safe_z=40, y=1.6, verify=(48, 12.45)), 60.75, 74, 7.05, 6.925)
    lines = code.splitlines()
    park = lines.index("G1 Z14.45 F100")
    assert lines[park - 1] == "G0 Z22.45"
    assert lines[park + 1] == "G4 S10"
    assert park < lines.index("S12000 M3")


def test_every_line_is_one_command():
    """Catches implicit string concatenation gluing two G-code lines together."""
    job = Job(tool=2, rpm=8000, safe_z=40, verify=(48, 12.45))
    for code in (
        thread(job, 1.5, 75.5, 59.4, 63.68, -1, 6.75, 6.07, check=True),
        thread(job, 1.5, 75.5, 59.4, 63.68, -1, 6.75, 6.07),
        turn(job, 60.75, 74, 7.05, 6.925),
    ):
        for line in code.splitlines():
            if not line.startswith("("):
                assert not re.search(r"\d[GMXYZAFS]", line.split("(")[0]), line
    check = thread(job, 1.5, 75.5, 59.4, 63.68, -1, 6.75, 6.07, check=True)
    assert "G1 Z14.45 F100" in check and not re.search(r"\bM3\b", check)


def test_thread_rewinds_low_when_asked_and_ends_at_safe_z():
    code = thread(JOB, 1.5, 71.9, 59.4, 63.68, -1, 6.75, 6.07, retract=8.0)
    lines = code.splitlines()
    rewinds = [i for i, ln in enumerate(lines) if ln.startswith("G0 X71.9")]
    assert all(lines[i - 1] in ("G0 Z8", "G0 Y0") for i in rewinds)
    assert "G0 Z40" in lines[-5:]


def test_cone_ball_tip_follows_offset_surface():
    from makera_studio_tools.rotary import cone

    # 53.97 deg cone, r 17.91 at X 34.92 falling to 13.557 at X 38.086; 1/4" ball
    code = cone(JOB, 34.92, 17.91, 38.086, 13.557, 3.175, offsets=(0.0,))
    ends = [m for m in moves(code) if {"X", "Z", "A"} <= set(m)]
    assert abs(ends[0]["X"] - 40.654) < 0.01 and abs(ends[0]["Z"] - 12.25) < 0.01
    start = [m for m in moves(code) if set(m) == {"X"}][0]
    assert abs(start["X"] - 37.488) < 0.01
