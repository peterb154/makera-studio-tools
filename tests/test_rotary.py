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
