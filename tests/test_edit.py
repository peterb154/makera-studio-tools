import zipfile
from pathlib import Path

import pytest

from makera_studio_tools import edit, project

FIXTURE = Path(__file__).parent / "fixtures" / "post.mks"


def test_edit_roundtrip(tmp_path):
    p = project.load(FIXTURE)
    log = edit.set_op(p, 1, max_depth_enabled=False, stickout=15, multiple_depths=False)
    assert "stickout 0 -> 15.0" in log[1]
    out = edit.save(p, FIXTURE, tmp_path / "out.mks")

    op = project.operations(project.load(out))[1]
    assert op["max_depth_enabled"] is False
    assert op["stickout"] == 15.0
    assert op["multiple_depths"] is False
    assert zipfile.ZipFile(out).namelist() == zipfile.ZipFile(FIXTURE).namelist()


def test_refuses_overwrite_and_unknown_field():
    p = project.load(FIXTURE)
    with pytest.raises(ValueError):
        edit.save(p, FIXTURE, FIXTURE)
    with pytest.raises(KeyError):
        edit.set_op(p, 0, colour="red")
