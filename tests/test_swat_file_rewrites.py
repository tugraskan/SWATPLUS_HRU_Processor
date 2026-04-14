import sys
import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SRC"))

from core.FileModifier import FileModifier
from core.RoutingTracer import RoutingTracer
from core.TxtinoutReader import TxtinoutReader
from core.object_counts import update_object_count_file
from core.swat_main import main


OBJECT_CNT = """object.cnt test
name                   ls_area      tot_area       obj       hru      lhru       rtu      gwfl       aqu       cha       res       rec      exco       dlr       can       pmp       out      lcha     aqu2d       hrd       wro
null               27267.16534   27267.16534       559       303         0        85         0        86         0         0         0         0         0         0         0         0        85         0         0         0
"""


@pytest.fixture
def work_dir(request):
    base = ROOT / "test_workspaces" / request.node.name
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    yield base
    shutil.rmtree(base, ignore_errors=True)


def write_minimal_txtinout(path):
    path.mkdir(exist_ok=True)
    (path / "hru.con").write_text(
        """hru.con test
id name gis_id area lat lon elev hru wst cst ovfl rule out_tot obj_typ obj_id hyd_typ frac
1 hru001 1 10.0 1.0 1.0 100.0 10 wst 0 0 0 1 sdc 1 tot 1.0
2 hru002 2 20.0 2.0 2.0 200.0 20 wst 0 0 0 1 sdc 2 tot 1.0
3 hru003 3 30.0 3.0 3.0 300.0 30 wst 0 0 0 0
"""
    )
    (path / "hru-data.hru").write_text(
        """hru-data.hru test
id name landuse soil
10 data010 corn soil_a
20 data020 wheat soil_b
30 data030 soy soil_c
"""
    )
    (path / "object.cnt").write_text(OBJECT_CNT)
    (path / "ls_unit.ele").write_text(
        """ls_unit.ele test
id name obj_typ obj_typ_no bsn_frac sub_frac reg_frac
1 hru001 hru 1 0.10 0.30 0.00
2 hru002 hru 2 0.20 0.70 0.00
3 hru003 hru 3 0.30 1.00 0.00
"""
    )
    (path / "ls_unit.def").write_text(
        """ls_unit.def test
2
id name area elem_tot elements
1 rtu010 30.0 2 1 -2
2 rtu020 30.0 1 3
"""
    )
    (path / "rout_unit.ele").write_text(
        """rout_unit.ele test
id name obj_typ obj_id frac dlr
1 hru001 hru 1 0.30 0
2 hru002 hru 2 0.70 0
3 hru003 hru 3 1.00 0
"""
    )
    (path / "rout_unit.def").write_text(
        """rout_unit.def test
id name elem_tot elements
1 rtu010 2 1 -2
2 rtu020 1 3
"""
    )
    (path / "rout_unit.rtu").write_text(
        """rout_unit.rtu test
id name define dlr topo field
1 rtu010 rtu010 null toportu010 fld010
2 rtu020 rtu020 null toportu020 fld020
"""
    )
    (path / "file.cio").write_text(
        """file.cio test
simulation time.sim print.prt object.prt object.cnt null
connect hru.con null rout_unit.con null aquifer.con null channel.con null reservoir.con null recall.con exco.con delratio.con outlet.con chandeg.con
routing_unit rout_unit.def rout_unit.ele rout_unit.rtu rout_unit.dr
hru hru-data.hru null
regions ls_unit.ele ls_unit.def
water_rights water_allocation.wro element.wro water_rights.wro
"""
    )
    (path / "print.prt").write_text(
        """print.prt test
nyskip day_start yrc_start day_end yrc_end interval
0 0 0 0 0 1
aa_int_cnt
0
csvout dbout cdfout
n n n
objects daily monthly yearly avann
lsunit_wb n y y y
lsunit_nb n y y y
lsunit_ls n y y y
lsunit_pw n y y y
hru_wb n y y y
ru n y y y
hru_salt n y y y
ru_salt n y y y
hru_cs n y y y
ru_cs n y y y
"""
    )


def row_by_header(path):
    lines = path.read_text().splitlines()
    headers = lines[1].split()
    values = lines[2].split()
    return dict(zip(headers, values))


def print_prt_rows(path):
    rows = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) >= 5:
            rows[fields[0]] = fields[1:5]
    return rows


def test_isolated_hru_rewrite_preserves_object_cnt_area_columns(work_dir):
    write_minimal_txtinout(work_dir)
    modifier = FileModifier(work_dir)

    props = modifier.modify_hru_con([2])
    modifier.modify_hru_data(props)
    modifier.modify_secondary_references()
    modifier.modify_object_cnt(1)
    modifier.modify_file_cio()

    hru_lines = (work_dir / "hru.con").read_text().splitlines()
    assert len(hru_lines) == 3
    hru_fields = hru_lines[2].split()
    assert hru_fields[0] == "1"
    assert hru_fields[7] == "1"
    assert hru_fields[12] == "0"
    assert "sdc" not in hru_fields

    data_fields = (work_dir / "hru-data.hru").read_text().splitlines()[2].split()
    assert data_fields[:3] == ["1", "data020", "wheat"]

    lsu_ele_lines = (work_dir / "ls_unit.ele").read_text().splitlines()
    assert len(lsu_ele_lines) == 3
    assert lsu_ele_lines[2].split()[:4] == ["1", "hru002", "hru", "1"]

    lsu_def_lines = (work_dir / "ls_unit.def").read_text().splitlines()
    assert lsu_def_lines[1].strip() == "1"
    assert len(lsu_def_lines) == 4
    assert lsu_def_lines[3].split()[0:5] == ["1", "rtu010", "30.0", "1", "1"]

    ru_ele_lines = (work_dir / "rout_unit.ele").read_text().splitlines()
    assert len(ru_ele_lines) == 3
    assert ru_ele_lines[2].split()[:4] == ["1", "hru002", "hru", "1"]

    ru_def_lines = (work_dir / "rout_unit.def").read_text().splitlines()
    assert len(ru_def_lines) == 3
    assert ru_def_lines[2].split()[0:4] == ["1", "rtu010", "1", "1"]

    rtu_lines = (work_dir / "rout_unit.rtu").read_text().splitlines()
    assert len(rtu_lines) == 3
    assert rtu_lines[2].split()[:3] == ["1", "rtu010", "rtu010"]

    counts = row_by_header(work_dir / "object.cnt")
    assert counts["ls_area"] == "27267.16534"
    assert counts["tot_area"] == "27267.16534"
    assert counts["obj"] == "1"
    assert counts["hru"] == "1"
    assert counts["rtu"] == "0"
    assert counts["aqu"] == "0"
    assert counts["lcha"] == "0"

    cio = (work_dir / "file.cio").read_text()
    assert "hru.con" in cio
    assert "rout_unit.con" not in cio
    assert "rout_unit.def" in cio
    assert "rout_unit.ele" in cio
    assert "rout_unit.rtu" in cio
    assert "rout_unit.dr" not in cio
    assert "aquifer.con" not in cio
    assert "chandeg.con" not in cio
    assert "ls_unit.ele" in cio
    assert "ls_unit.def" in cio


def test_missing_hru_fails_before_count_rewrite(work_dir):
    write_minimal_txtinout(work_dir)
    modifier = FileModifier(work_dir)

    with pytest.raises(ValueError, match="HRU ID"):
        modifier.modify_hru_con([99])


def test_isolated_main_disables_routing_unit_print_outputs(work_dir):
    write_minimal_txtinout(work_dir)

    main(src_dir=work_dir, filter_ids=[2], run_simulation=False, keep_routing=False)

    rows = print_prt_rows(work_dir / "solo_2" / "print.prt")
    for name in ("lsunit_wb", "lsunit_nb", "lsunit_ls", "lsunit_pw", "ru", "ru_salt", "ru_cs"):
        assert rows[name] == ["n", "n", "n", "n"]
    assert rows["hru_wb"] == ["n", "y", "y", "y"]
    assert rows["hru_salt"] == ["n", "y", "y", "y"]
    assert rows["hru_cs"] == ["n", "y", "y", "y"]


def test_keep_routing_main_preserves_routing_unit_print_outputs(work_dir):
    write_minimal_txtinout(work_dir)

    main(src_dir=work_dir, filter_ids=[2], run_simulation=False, keep_routing=True)

    output_dir = work_dir / "solo_2"
    rows = print_prt_rows(output_dir / "print.prt")
    for name in ("lsunit_wb", "lsunit_nb", "lsunit_ls", "lsunit_pw", "ru", "ru_salt", "ru_cs"):
        assert rows[name] == ["n", "y", "y", "y"]

    counts = row_by_header(output_dir / "object.cnt")
    assert counts["hru"] == "1"
    assert counts["rtu"] == "1"
    assert counts["lcha"] == "1"


def test_object_count_helper_updates_routing_counts_by_header(work_dir):
    object_cnt = work_dir / "object.cnt"
    object_cnt.write_text(OBJECT_CNT)

    update_object_count_file(object_cnt, {"hru": 2, "ru": 1, "sdc": 3, "aqu": 1})

    counts = row_by_header(object_cnt)
    assert counts["ls_area"] == "27267.16534"
    assert counts["tot_area"] == "27267.16534"
    assert counts["obj"] == "7"
    assert counts["hru"] == "2"
    assert counts["rtu"] == "1"
    assert counts["lcha"] == "3"
    assert counts["aqu"] == "1"


def test_txtinout_reader_does_not_require_exe_and_copy_excludes_outputs(work_dir):
    src = work_dir / "src"
    dest = work_dir / "dest"
    src.mkdir()
    (src / "file.cio").write_text("input")
    (src / "simulation.out").write_text("generated")
    (src / "hru_wb_mon.txt").write_text("generated")
    (src / "swatplus_output.sqlite").write_text("generated")

    reader = TxtinoutReader(src)
    assert reader.swat_exe_paths == []
    assert reader.swat_exe_path is None

    TxtinoutReader.copy_swat(src, dest)

    assert (dest / "file.cio").exists()
    assert not (dest / "simulation.out").exists()
    assert not (dest / "hru_wb_mon.txt").exists()
    assert not (dest / "swatplus_output.sqlite").exists()


def test_routing_unit_element_ranges_expand_like_swat(work_dir):
    tracer = RoutingTracer(work_dir)

    assert tracer._expand_element_tokens(["302", "-303", "400"]) == [302, 303, 400]
    assert tracer._expand_element_tokens(["285"]) == [285]
