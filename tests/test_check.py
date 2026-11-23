import copy
import sqlite3
from pathlib import Path

import pytest

from makera_studio_tools import library, project
from makera_studio_tools.check import check, flutes

FIXTURE = Path(__file__).parent / "fixtures" / "post.mks"
AL6061 = "019bfae0-a419-7c0b-879e-62ee78df95d4"
AL7075 = "019bfae0-a419-7718-88a0-ca1275ef5d9b"


@pytest.fixture
def prj():
    return project.load(FIXTURE)


@pytest.fixture
def con(tmp_path):
    db = tmp_path / "lib.db"
    c = sqlite3.connect(db)
    c.executescript(
        f"""
        create table t_MaterialList (materialID text, materialSubcategoryName text);
        insert into t_MaterialList values ('{AL6061}', '6061 Aluminum'), ('{AL7075}', '7075 Aluminum');
        create table t_MakeraCutterProperties (propertiesId text, materialId text, cutterID text,
            spindleSpeed int, feedRate int, plungeFeedRate real, stepDown real, stepOver real,
            stepOverPercent real, coolant int);
        insert into t_MakeraCutterProperties values
            ('019c2c27-953a-76c5-80a6-06149f151ee8', '{AL7075}', 'vbit', 12000, 500, 200, 0.2, 0.15, 50, 1);
        create table t_CustomerCutterProperties as select * from t_MakeraCutterProperties where 0;
        """
    )
    c.commit()
    c.close()
    return library.connect(db)


def test_load_and_summary(prj):
    s = project.summary(prj)
    assert s["machine"]["model"] == "Makera Z1"
    assert s["stock"]["material"] == "6061 Aluminum"
    assert [op["tool_number"] for op in s["operations"]] == [1, 2]


def test_fixture_warnings(prj, con):
    w = check(prj, con)["warnings"]
    assert any("stickout not set" in x for x in w)
    assert any("Max Depth" in x for x in w)
    assert any("7075" in x for x in w)
    assert not any("Tailstock" in x for x in w)
    assert not any("shared" in x for x in w)


def test_shared_tool_number(prj):
    p = copy.deepcopy(prj)
    paths = next(iter(p["lstCoordinate"].values()))["path"]
    paths[1]["tools"][0]["toolNumber"] = 1
    assert any("won't change tools" in x for x in check(p)["warnings"])


def test_tailstock_off(prj):
    p = copy.deepcopy(prj)
    next(iter(p["lstCoordinate"].values()))["path"][0]["haveTailTop"] = False
    assert any("Tailstock unchecked" in x for x in check(p)["warnings"])


def test_flutes():
    assert flutes("Sharpro 1flute carbide upcut") == 1
    assert flutes("2 Flute Flat End Mill") == 2
    assert flutes("3.175*0.3mm*30º Engraving(Metal)") == 1
