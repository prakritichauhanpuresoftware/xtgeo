"""Tests for 3D grid."""
import math
import pathlib
from collections import OrderedDict

import numpy as np
import pytest
from hypothesis import given

import xtgeo
from xtgeo.common import XTGeoDialog
from xtgeo.grid3d import Grid, GridProperty

from .grid_generator import dimensions, increments, xtgeo_grids

xtg = XTGeoDialog()
logger = xtg.basiclogger(__name__, info=True)

if not xtg.testsetup():
    raise SystemExit

TPATH = xtg.testpathobj

EMEGFILE = TPATH / "3dgrids/eme/1/emerald_hetero_grid.roff"
REEKFILE = TPATH / "3dgrids/reek/REEK.EGRID"
REEKFIL2 = TPATH / "3dgrids/reek3/reek_sim.grdecl"  # ASCII GRDECL
REEKFIL3 = TPATH / "3dgrids/reek3/reek_sim.bgrdecl"  # binary GRDECL
REEKFIL4 = TPATH / "3dgrids/reek/reek_geo_grid.roff"
REEKFIL5 = TPATH / "3dgrids/reek/reek_geo2_grid_3props.roff"
REEKROOT = TPATH / "3dgrids/reek/REEK"
SPROOT = TPATH / "3dgrids/etc/TEST_SP"
# brilfile = '../xtgeo-testdata/3dgrids/bri/B.GRID' ...disabled
BRILGRDECL = TPATH / "3dgrids/bri/b.grdecl"
BANAL6 = TPATH / "3dgrids/etc/banal6.roff"
GRIDQC1 = TPATH / "3dgrids/etc/gridqc1.roff"
GRIDQC1_CELLVOL = TPATH / "3dgrids/etc/gridqc1_totbulk.roff"
GRIDQC2 = TPATH / "3dgrids/etc/gridqc_negthick_twisted.roff"

DUALFIL1 = TPATH / "3dgrids/etc/dual_grid.roff"
DUALFIL2 = TPATH / "3dgrids/etc/dual_grid_noactivetag.roff"

DUALFIL3 = TPATH / "3dgrids/etc/TEST_DPDK.EGRID"

# =============================================================================
# Do tests
# =============================================================================
# pylint: disable=redefined-outer-name


@pytest.fixture()
def load_gfile1():
    """Fixture for loading EMEGFILE grid."""
    return xtgeo.grid3d.Grid(EMEGFILE)


def test_import_wrong():
    """Importing wrong fformat, etc."""
    with pytest.raises(ValueError):
        grd = Grid()
        grd.from_file(EMEGFILE, fformat="stupid_wrong_name")
        assert grd.ncol == 70


def test_import_guess(load_gfile1):
    """Import with guessing fformat, and also test name attribute."""
    grd = load_gfile1

    assert grd.ncol == 70
    assert grd.name == "emerald_hetero_grid"

    grd.name = "xxx"
    assert grd.name == "xxx"


def test_create_shoebox(tmp_path):
    """Make a shoebox grid from scratch."""
    grd = xtgeo.Grid()
    grd.create_box()
    grd.to_file(tmp_path / "shoebox_default.roff")

    grd.create_box(flip=-1)
    grd.to_file(tmp_path / "shoebox_default_flipped.roff")

    timer1 = xtg.timer()
    grd.create_box(
        origin=(0, 0, 1000), dimension=(300, 200, 30), increment=(20, 20, 1), flip=-1
    )
    logger.info("Making a a 1,8 mill cell grid took %5.3f secs", xtg.timer(timer1))

    dx, dy = grd.get_dxdy()

    assert dx.values.mean() == pytest.approx(20.0, abs=0.0001)
    assert dy.values.mean() == pytest.approx(20.0, abs=0.0001)

    grd.create_box(
        origin=(0, 0, 1000), dimension=(30, 30, 3), rotation=45, increment=(20, 20, 1)
    )

    x, y, z = grd.get_xyz()

    assert x.values1d[0] == pytest.approx(0.0, abs=0.001)
    assert y.values1d[0] == pytest.approx(20 * math.cos(45 * math.pi / 180), abs=0.001)
    assert z.values1d[0] == pytest.approx(1000.5, abs=0.001)

    grd.create_box(
        origin=(0, 0, 1000),
        dimension=(30, 30, 3),
        rotation=45,
        increment=(20, 20, 1),
        oricenter=True,
    )

    x, y, z = grd.get_xyz()

    assert x.values1d[0] == pytest.approx(0.0, abs=0.001)
    assert y.values1d[0] == pytest.approx(0.0, abs=0.001)
    assert z.values1d[0] == pytest.approx(1000.0, abs=0.001)


@pytest.mark.parametrize(
    "dimensions",
    [
        (100, 1, 1),
        (100, 1, 20),
        (300, 20, 30),
    ],
)
def test_shoebox_egrid(tmp_path, dimensions):
    grd = xtgeo.Grid()
    grd.create_box(dimension=dimensions)
    grd.to_file(tmp_path / "E1.EGRID", fformat="egrid")
    grd1 = xtgeo.Grid(tmp_path / "E1.EGRID")
    assert grd1.dimensions == dimensions


def test_shoebox_xtgeo_vs_roff(tmp_path):
    """Test timing for xtgeo xtgcpgeom format vs roff vs egrid."""
    dimens = (20, 30, 50)

    grd = xtgeo.Grid()
    grd.create_box(dimension=dimens)
    grd._xtgformat2()
    t0 = xtg.timer()
    grd.to_xtgf(tmp_path / "show.xtgf")
    t1 = xtg.timer(t0)
    logger.info("TIME XTGEO %s", t1)
    t0 = xtg.timer()
    grd.to_file(tmp_path / "show.roff", fformat="roff")
    t1 = xtg.timer(t0)
    logger.info("TIME ROFF %s", t1)
    t0 = xtg.timer()
    grd.to_file(tmp_path / "show.egrid", fformat="egrid")
    t1 = xtg.timer(t0)
    logger.info("TIME EGRID (incl conv) %s", t1)

    t0 = xtg.timer()
    grd2 = xtgeo.Grid()
    grd2.from_xtgf(tmp_path / "show.xtgf")
    t1 = xtg.timer(t0)
    logger.info("TIME READ xtgeo %s", t1)

    t0 = xtg.timer()
    grd2 = xtgeo.Grid()
    grd2.from_file(tmp_path / "show.roff", fformat="roff")
    t1 = xtg.timer(t0)
    logger.info("TIME READ roff %s", t1)


def test_roffbin_get_dataframe_for_grid(load_gfile1):
    """Import ROFF grid and return a grid dataframe (no props)."""
    grd = load_gfile1

    assert isinstance(grd, Grid)

    df = grd.dataframe()
    print(df.head())

    assert len(df) == grd.nactive

    assert df["X_UTME"][0] == pytest.approx(459176.7937727844, abs=0.1)

    assert len(df.columns) == 6

    df = grd.dataframe(activeonly=False)
    print(df.head())

    assert len(df.columns) == 7
    assert len(df) != grd.nactive

    assert len(df) == grd.ncol * grd.nrow * grd.nlay


def test_subgrids(load_gfile1):
    """Import ROFF and test different subgrid functions."""
    grd = load_gfile1

    assert isinstance(grd, Grid)

    logger.info(grd.subgrids)

    newsub = OrderedDict()
    newsub["XX1"] = 20
    newsub["XX2"] = 2
    newsub["XX3"] = 24

    grd.set_subgrids(newsub)
    logger.info(grd.subgrids)

    subs = grd.get_subgrids()
    logger.info(subs)

    assert subs == newsub

    _i_index, _j_index, k_index = grd.get_ijk()

    zprop = k_index.copy()
    zprop.values[k_index.values > 4] = 2
    zprop.values[k_index.values <= 4] = 1
    print(zprop.values)
    grd.describe()
    grd.subgrids_from_zoneprop(zprop)

    grd.describe()

    # rename
    grd.rename_subgrids(["AAAA", "BBBB"])
    assert "AAAA" in grd.subgrids.keys()

    # set to None
    grd.subgrids = None
    assert grd._subgrids is None


def test_roffbin_import1(load_gfile1):
    """Test roff binary import case 1."""
    grd = load_gfile1

    assert grd.ncol == 70, "Grid NCOL Emerald"
    assert grd.nlay == 46, "Grid NLAY Emerald"

    # extract ACTNUM parameter as a property instance (a GridProperty)
    act = grd.get_actnum()

    # get dZ...
    dzv = grd.get_dz()

    logger.info("ACTNUM is %s", act)
    logger.debug("DZ values are \n%s", dzv.values1d[888:999])

    dzval = dzv.values
    print("DZ mean and shape: ", dzval.mean(), dzval.shape)
    # get the value is cell 32 73 1 shall be 2.761
    mydz = float(dzval[31:32, 72:73, 0:1])
    assert mydz == pytest.approx(2.761, abs=0.001), "Grid DZ Emerald"

    # get dX dY
    logger.info("Get dX dY")
    dxv, dyv = grd.get_dxdy()

    mydx = float(dxv.values3d[31:32, 72:73, 0:1])
    mydy = float(dyv.values3d[31:32, 72:73, 0:1])

    assert mydx == pytest.approx(118.51, abs=0.01), "Grid DX Emerald"
    assert mydy == pytest.approx(141.26, abs=0.01), "Grid DY Emerald"

    # get X Y Z coordinates (as GridProperty objects) in one go
    logger.info("Get X Y Z...")
    xvv, yvv, zvv = grd.get_xyz(names=["xxx", "yyy", "zzz"])

    assert xvv.name == "xxx", "Name of X coord"
    xvv.name = "Xerxes"

    # attach some properties to grid
    grd.props = [xvv, yvv]

    logger.info(grd.props)
    grd.props = [zvv]

    logger.info(grd.props)

    grd.props.append(xvv)
    logger.info(grd.propnames)

    # get the property of name Xerxes
    myx = grd.get_prop_by_name("Xerxes")
    if myx is None:
        logger.info(myx)
    else:
        logger.info("Got nothing!")


def test_roffbin_import_v2_banal():
    """Test roff binary import ROFF using new API, banal case."""
    t0 = xtg.timer()
    grd1 = Grid()
    grd1._xtgformat = 1
    grd1.from_file(BANAL6)
    print("V1: ", xtg.timer(t0))

    t0 = xtg.timer()

    grd2 = Grid()
    grd2._xtgformat = 2
    grd2.from_file(BANAL6)
    print("V2: ", xtg.timer(t0))

    t0 = xtg.timer()
    grd3 = Grid()
    grd3._xtgformat = 2
    grd3.from_file(BANAL6)
    grd3._convert_xtgformat2to1()
    print("V3: ", xtg.timer(t0))

    t0 = xtg.timer()
    grd4 = Grid()
    grd4._xtgformat = 1
    grd4.from_file(BANAL6)
    grd4._convert_xtgformat1to2()
    print("V4: ", xtg.timer(t0))

    for irange in range(grd1.ncol):
        for jrange in range(grd1.nrow):
            for krange in range(grd1.nlay):
                cell = (irange + 1, jrange + 1, krange + 1)

                xx1 = grd1.get_xyz_cell_corners(cell, activeonly=False)
                xx2 = grd2.get_xyz_cell_corners(cell, activeonly=False)
                xx3 = grd3.get_xyz_cell_corners(cell, activeonly=False)
                xx4 = grd4.get_xyz_cell_corners(cell, activeonly=False)

                assert np.allclose(np.array(xx1), np.array(xx2)) is True
                assert np.allclose(np.array(xx1), np.array(xx3)) is True
                assert np.allclose(np.array(xx1), np.array(xx4)) is True


def test_roffbin_import_v2stress():
    """Test roff binary import ROFF using new API, comapre timing etc."""
    t0 = xtg.timer()
    for _ino in range(100):
        grd1 = Grid()
        grd1.from_file(REEKFIL4)
    t1 = xtg.timer(t0)
    print("100 loops with ROXAPIV 2 took: ", t1)


def test_roffbin_banal6():
    """Test roff binary for banal no. 6 case."""
    grd1 = Grid()
    grd1.from_file(BANAL6)

    grd2 = Grid()
    grd2._xtgformat = 2
    grd2.from_file(BANAL6)

    assert grd1.get_xyz_cell_corners() == grd2.get_xyz_cell_corners()

    assert grd1.get_xyz_cell_corners((4, 2, 3)) == grd2.get_xyz_cell_corners((4, 2, 3))

    grd2._convert_xtgformat2to1()

    assert grd1.get_xyz_cell_corners((4, 2, 3)) == grd2.get_xyz_cell_corners((4, 2, 3))

    grd2._convert_xtgformat1to2()

    assert grd1.get_xyz_cell_corners((4, 2, 3)) == grd2.get_xyz_cell_corners((4, 2, 3))


def test_roffbin_export_v2_banal6(tmp_path):
    """Test roff binary export v2 for banal no. 6 case."""
    # export
    grd1 = Grid()
    grd1._xtgformat = 2

    logger.info("EXPORT")
    grd1.to_file(tmp_path / "b6_export.roffasc", fformat="roff_asc")
    grd1.to_file(tmp_path / "b6_export.roffbin", fformat="roff_bin")

    grd2 = Grid(tmp_path / "b6_export.roffbin")
    cell1 = grd1.get_xyz_cell_corners((2, 2, 2))
    cell2 = grd2.get_xyz_cell_corners((2, 2, 2))

    assert cell1 == pytest.approx(cell2)


@pytest.mark.parametrize("xtgformat", [1, 2])
@pytest.mark.benchmark()
def test_benchmark_get_xyz_cell_cornerns(benchmark, xtgformat):
    grd = xtgeo.create_box_grid(dimension=(10, 10, 10))
    if xtgformat == 1:
        grd._xtgformat1()
    else:
        grd._xtgformat2()

    def run():
        return grd.get_xyz_cell_corners((5, 6, 7))

    corners = benchmark(run)

    assert corners == pytest.approx(
        [4, 5, 6, 5, 5, 6, 4, 6, 6, 5, 6, 6, 4, 5, 7, 5, 5, 7, 4, 6, 7, 5, 6, 7]
    )


def test_roffbin_import_v2_wsubgrids():
    """Test roff binary import ROFF using new API, now with subgrids."""
    grd1 = Grid()
    grd1.from_file(REEKFIL5)
    print(grd1.subgrids)


def test_import_grdecl_and_bgrdecl():
    """Eclipse import of GRDECL and binary GRDECL."""
    grd1 = Grid(REEKFIL2, fformat="grdecl")

    grd1.describe()
    assert grd1.dimensions == (40, 64, 14)
    assert grd1.nactive == 35812

    # get dZ...
    dzv1 = grd1.get_dz()

    grd2 = Grid(REEKFIL3, fformat="bgrdecl")

    grd2.describe()
    assert grd2.dimensions == (40, 64, 14)
    assert grd2.nactive == 35812

    # get dZ...
    dzv2 = grd2.get_dz()

    assert dzv1.values.mean() == pytest.approx(dzv2.values.mean(), abs=0.001)


def test_eclgrid_import2(tmp_path):
    """Eclipse EGRID import, also change ACTNUM."""
    grd = Grid()
    logger.info("Import Eclipse GRID...")
    grd.from_file(REEKFILE, fformat="egrid")

    assert grd.ncol == 40, "EGrid NX from Eclipse"
    assert grd.nrow == 64, "EGrid NY from Eclipse"
    assert grd.nactive == 35838, "EGrid NTOTAL from Eclipse"
    assert grd.ntotal == 35840, "EGrid NACTIVE from Eclipse"

    actnum = grd.get_actnum()
    print(actnum.values[12:13, 22:24, 5:6])
    assert actnum.values[12, 22, 5] == 0, "ACTNUM 0"

    actnum.values[:, :, :] = 1
    actnum.values[:, :, 4:6] = 0
    grd.set_actnum(actnum)
    newactive = grd.ncol * grd.nrow * grd.nlay - 2 * (grd.ncol * grd.nrow)
    assert grd.nactive == newactive, "Changed ACTNUM"
    grd.to_file(tmp_path / "reek_new_actnum.roff")


def test_eclgrid_import3(tmp_path):
    """Eclipse GRDECL import and translate."""
    grd = Grid(BRILGRDECL, fformat="grdecl")

    mylist = grd.get_geometrics()

    xori1 = mylist[0]

    # translate the coordinates
    grd.translate_coordinates(translate=(100, 100, 10), flip=(1, 1, 1))

    mylist = grd.get_geometrics()

    xori2 = mylist[0]

    # check if origin is translated 100m in X
    assert xori1 + 100 == xori2, "Translate X distance"

    grd.to_file(tmp_path / "g1_translate.roff", fformat="roff_binary")

    grd.to_file(tmp_path / "g1_translate.bgrdecl", fformat="bgrdecl")


def test_geometrics_reek():
    """Import Reek and test geometrics."""
    grd = Grid(REEKFILE, fformat="egrid")

    geom = grd.get_geometrics(return_dict=True, cellcenter=False)

    for key, val in geom.items():
        logger.info("%s is %s", key, val)

    # compared with RMS info:
    assert geom["xmin"] == pytest.approx(456510.6, abs=0.1), "Xmin"
    assert geom["ymax"] == pytest.approx(5938935.5, abs=0.1), "Ymax"

    # cellcenter True:
    geom = grd.get_geometrics(return_dict=True, cellcenter=True)
    assert geom["xmin"] == pytest.approx(456620, abs=1), "Xmin cell center"


def test_activate_all_cells(tmp_path):
    """Make the grid active for all cells."""
    grid = Grid(EMEGFILE)
    logger.info("Number of active cells %s before", grid.nactive)
    grid.activate_all()
    logger.info("Number of active cells %s after", grid.nactive)

    assert grid.nactive == grid.ntotal
    grid.to_file(tmp_path / "emerald_all_active.roff")


def test_get_adjacent_cells(tmp_path):
    """Get the cell indices for discrete value X vs Y, if connected."""
    grid = Grid(EMEGFILE)
    actnum = grid.get_actnum()
    actnum.to_file(tmp_path / "emerald_actnum.roff")
    result = grid.get_adjacent_cells(actnum, 0, 1, activeonly=False)
    result.to_file(tmp_path / "emerald_adj_cells.roff")


def test_simple_io(tmp_path):
    """Test various import and export formats, incl egrid and bgrdecl."""
    gg = Grid(REEKFILE, fformat="egrid")

    assert gg.ncol == 40

    filex = tmp_path / "grid_test_simple_io.roff"

    gg.to_file(filex)

    gg2 = Grid(filex, fformat="roff")

    assert gg2.ncol == 40

    filex = tmp_path / "grid_test_simple_io.EGRID"
    filey = tmp_path / "grid_test_simple_io.bgrdecl"

    gg.to_file(filex, fformat="egrid")
    gg.to_file(filey, fformat="bgrdecl")

    gg2 = Grid(filex, fformat="egrid")
    gg3 = Grid(filey, fformat="bgrdecl")

    assert gg2.ncol == 40

    dz1 = gg.get_dz()
    dz2 = gg2.get_dz()
    dz3 = gg3.get_dz()

    assert dz1.values.mean() == pytest.approx(dz2.values.mean(), abs=0.001)
    assert dz1.values.std() == pytest.approx(dz2.values.std(), abs=0.001)
    assert dz1.values.mean() == pytest.approx(dz3.values.mean(), abs=0.001)
    assert dz1.values.std() == pytest.approx(dz3.values.std(), abs=0.001)


def test_ecl_run(tmp_path):
    """Test import an eclrun with dates and export to roff after a diff."""
    dates = [19991201, 20030101]
    rprops = ["PRESSURE", "SWAT"]

    gg = Grid(REEKROOT, fformat="eclipserun", restartdates=dates, restartprops=rprops)

    # get the property object:
    pres1 = gg.get_prop_by_name("PRESSURE_20030101")
    assert pres1.values.mean() == pytest.approx(308.45, abs=0.001)

    pres1.to_file(tmp_path / "pres1.roff")

    pres2 = gg.get_prop_by_name("PRESSURE_19991201")

    if isinstance(pres2, GridProperty):
        pass

    logger.debug(pres1.values)
    logger.debug(pres2.values)

    pres1.values = pres1.values - pres2.values
    # logger.debug(pres1.values)
    # logger.debug(pres1)
    avg = pres1.values.mean()
    # ok checked in RMS:
    assert avg == pytest.approx(-26.073, abs=0.001)

    pres1.to_file(tmp_path / "pressurediff.roff", name="PRESSUREDIFF")


def test_ecl_run_all():
    """Test import an eclrun with all dates and props."""
    gg = Grid()
    gg.from_file(
        REEKROOT,
        fformat="eclipserun",
        initprops="all",
        restartdates="all",
        restartprops="all",
    )

    assert len(gg.gridprops.names) == 287


def test_ecl_run_all_sp(testpath):
    """Test import an eclrun with all dates and props."""
    gg = Grid()
    gg.from_file(
        SPROOT,
        fformat="eclipserun",
        initprops="all",
        restartdates="all",
        restartprops="all",
    )

    assert len(gg.gridprops.names) == 59


def test_npvalues1d():
    """Different ways of getting np arrays."""
    grd = Grid(DUALFIL3)
    dz = grd.get_dz()

    dz1 = dz.get_npvalues1d(activeonly=False)  # [  1.   1.   1.   1.   1.  nan  ...]
    dz2 = dz.get_npvalues1d(activeonly=True)  # [  1.   1.   1.   1.   1.  1. ...]

    assert dz1[0] == 1.0
    assert np.isnan(dz1[5])
    assert dz1[0] == 1.0
    assert not np.isnan(dz2[5])

    grd = Grid(DUALFIL1)  # all cells active
    dz = grd.get_dz()

    dz1 = dz.get_npvalues1d(activeonly=False)
    dz2 = dz.get_npvalues1d(activeonly=True)

    assert dz1.all() == dz2.all()


def test_pathlib(tmp_path):
    """Import and export via pathlib."""
    pfile = pathlib.Path(DUALFIL1)
    grd = Grid()
    grd.from_file(pfile)

    assert grd.dimensions == (5, 3, 1)

    out = tmp_path / "grdpathtest.roff"
    grd.to_file(out, fformat="roff")

    with pytest.raises(OSError):
        out = pathlib.Path() / "nosuchdir" / "grdpathtest.roff"
        grd.to_file(out, fformat="roff")


def test_grid_design(load_gfile1):
    """Determine if a subgrid is topconform (T), baseconform (B), proportional (P).

    "design" refers to type of conformity
    "dzsimbox" is avg or representative simbox thickness per cell

    """
    grd = load_gfile1

    print(grd.subgrids)

    code = grd.estimate_design(1)
    assert code["design"] == "P"
    assert code["dzsimbox"] == pytest.approx(2.5488, abs=0.001)

    code = grd.estimate_design(2)
    assert code["design"] == "T"
    assert code["dzsimbox"] == pytest.approx(3.0000, abs=0.001)

    code = grd.estimate_design("subgrid_0")
    assert code["design"] == "P"

    code = grd.estimate_design("subgrid_1")
    assert code["design"] == "T"

    code = grd.estimate_design("subgrid_2")
    assert code is None

    with pytest.raises(ValueError):
        code = grd.estimate_design(nsub=None)


def test_flip(load_gfile1):
    """Determine if grid is flipped (lefthanded vs righthanded)."""
    grd = load_gfile1

    assert grd.estimate_flip() == 1

    grd.create_box(dimension=(30, 20, 3), flip=-1)
    assert grd.estimate_flip() == -1

    grd.create_box(dimension=(30, 20, 3), rotation=30, flip=-1)
    assert grd.estimate_flip() == -1

    grd.create_box(dimension=(30, 20, 3), rotation=190, flip=-1)
    assert grd.estimate_flip() == -1


def test_xyz_cell_corners():
    """Test xyz variations."""
    grd = Grid(DUALFIL1)

    allcorners = grd.get_xyz_corners()
    assert len(allcorners) == 24
    assert allcorners[0].get_npvalues1d()[0] == 0.0
    assert allcorners[23].get_npvalues1d()[-1] == 1001.0


def test_grid_layer_slice():
    """Test grid slice coordinates."""
    grd = Grid()
    grd.from_file(REEKFILE)

    sarr1, _ibarr = grd.get_layer_slice(1)
    sarrn, _ibarr = grd.get_layer_slice(grd.nlay, top=False)

    cell1 = grd.get_xyz_cell_corners(ijk=(1, 1, 1))
    celln = grd.get_xyz_cell_corners(ijk=(1, 1, grd.nlay))
    celll = grd.get_xyz_cell_corners(ijk=(grd.ncol, grd.nrow, grd.nlay))

    assert sarr1[0, 0, 0] == cell1[0]
    assert sarr1[0, 0, 1] == cell1[1]

    assert sarrn[0, 0, 0] == celln[12]
    assert sarrn[0, 0, 1] == celln[13]

    assert sarrn[-1, 0, 0] == celll[12]
    assert sarrn[-1, 0, 1] == celll[13]


def test_generate_hash():
    """Generate hash for two grid instances with same input and compare."""
    grd1 = Grid(REEKFILE)
    grd2 = Grid(REEKFILE)

    assert id(grd1) != id(grd2)

    assert grd1.generate_hash() == grd2.generate_hash()


def test_gridquality_properties(show_plot):
    """Get grid quality props."""
    grd1 = Grid(GRIDQC1)

    props1 = grd1.get_gridquality_properties()
    minang = props1.get_prop_by_name("minangle_topbase")
    assert minang.values[5, 2, 1] == pytest.approx(71.05561, abs=0.001)
    if show_plot:
        lay = 1
        layslice = xtgeo.plot.Grid3DSlice()
        layslice.canvas(title=f"Layer {lay}")
        layslice.plot_gridslice(
            grd1,
            prop=minang,
            mode="layer",
            index=lay + 1,
            window=None,
            linecolor="black",
        )

        layslice.show()

    grd2 = Grid(GRIDQC2)
    props2 = grd2.get_gridquality_properties()

    neg = props2.get_prop_by_name("negative_thickness")
    assert neg.values[0, 0, 0] == 0
    assert neg.values[2, 1, 0] == 1

    grd3 = Grid(EMEGFILE)
    props3 = grd3.get_gridquality_properties()

    concp = props3.get_prop_by_name("concave_proj")
    if show_plot:
        lay = 23
        layslice = xtgeo.plot.Grid3DSlice()
        layslice.canvas(title=f"Layer {lay}")
        layslice.plot_gridslice(
            grd3,
            prop=concp,
            mode="layer",
            index=lay + 1,
            window=None,
            linecolor="black",
        )

        layslice.show()

    # assert concp.values.sum() == 7949


def test_bulkvol():
    """Test cell bulk volume calculation."""
    grd = Grid(GRIDQC1)
    cellvol_rms = GridProperty(GRIDQC1_CELLVOL)

    bulk = grd.get_bulk_volume()
    logger.info("Sum this: %s", bulk.values.sum())
    logger.info("Sum RMS: %s", cellvol_rms.values.sum())

    assert bulk.values.sum() == pytest.approx(cellvol_rms.values.sum(), rel=0.001)


def test_bulkvol_speed():
    """Test cell bulk volume calculation speed."""
    dimens = (100, 500, 50)
    grd = Grid()
    grd.create_box(dimension=dimens)
    grd._xtgformat2()

    t0 = xtg.timer()
    _ = grd.get_bulk_volume()
    ncells = np.prod(dimens)
    print(xtg.timer(t0), ncells)


def test_bad_egrid_ends_before_kw(tmp_path):
    egrid_file = tmp_path / "test.egrid"
    with open(egrid_file, "wb") as fh:
        fh.write(b"\x00\x00\x00\x10")
    with pytest.raises(Exception, match="end-of-file while reading keyword"):
        xtgeo.grid_from_file(egrid_file, fformat="egrid")


@given(dimensions, increments, increments, increments)
def test_grid_get_dx(dimension, dx, dy, dz):
    grd = Grid()
    grd.create_box(dimension=dimension, increment=(dx, dy, dz), rotation=0.0)
    np.testing.assert_allclose(grd.get_dx(metric="euclid").values, dx, atol=0.01)
    np.testing.assert_allclose(
        grd.get_dx(metric="north south vertical").values, 0.0, atol=0.01
    )
    np.testing.assert_allclose(
        grd.get_dx(metric="east west vertical").values, dx, atol=0.01
    )
    np.testing.assert_allclose(grd.get_dx(metric="horizontal").values, dx, atol=0.01)
    np.testing.assert_allclose(grd.get_dx(metric="x projection").values, dx, atol=0.01)
    np.testing.assert_allclose(grd.get_dx(metric="y projection").values, 0.0, atol=0.01)
    np.testing.assert_allclose(grd.get_dx(metric="z projection").values, 0.0, atol=0.01)

    grd._actnumsv[0, 0, 0] = 0

    assert grd.get_dx(asmasked=True).values[0, 0, 0] is np.ma.masked
    assert np.isclose(grd.get_dx(asmasked=False).values[0, 0, 0], dx, atol=0.01)


@given(dimensions, increments, increments, increments)
def test_grid_get_dy(dimension, dx, dy, dz):
    grd = Grid()
    grd.create_box(dimension=dimension, increment=(dx, dy, dz), rotation=0.0)
    np.testing.assert_allclose(grd.get_dy(metric="euclid").values, dy, atol=0.01)
    np.testing.assert_allclose(
        grd.get_dy(metric="north south vertical").values, dy, atol=0.01
    )
    np.testing.assert_allclose(
        grd.get_dy(metric="east west vertical").values, 0.0, atol=0.01
    )
    np.testing.assert_allclose(grd.get_dy(metric="horizontal").values, dy, atol=0.01)
    np.testing.assert_allclose(grd.get_dy(metric="x projection").values, 0.0, atol=0.01)
    np.testing.assert_allclose(grd.get_dy(metric="y projection").values, dy, atol=0.01)
    np.testing.assert_allclose(grd.get_dy(metric="z projection").values, 0.0, atol=0.01)

    grd._actnumsv[0, 0, 0] = 0

    assert grd.get_dy(asmasked=True).values[0, 0, 0] is np.ma.masked
    assert np.isclose(grd.get_dy(asmasked=False).values[0, 0, 0], dy, atol=0.01)


@given(dimensions, increments, increments, increments)
def test_grid_get_dz(dimension, dx, dy, dz):
    grd = Grid()
    grd.create_box(dimension=dimension, increment=(dx, dy, dz))
    np.testing.assert_allclose(grd.get_dz(metric="euclid").values, dz, atol=0.01)
    np.testing.assert_allclose(
        grd.get_dz(metric="north south vertical").values, dz, atol=0.01
    )
    np.testing.assert_allclose(
        grd.get_dz(metric="east west vertical").values, dz, atol=0.01
    )
    np.testing.assert_allclose(grd.get_dz(metric="horizontal").values, 0.0, atol=0.01)
    np.testing.assert_allclose(grd.get_dz(metric="x projection").values, 0.0, atol=0.01)
    np.testing.assert_allclose(grd.get_dz(metric="y projection").values, 0.0, atol=0.01)
    np.testing.assert_allclose(grd.get_dz(metric="z projection").values, dz, atol=0.01)
    np.testing.assert_allclose(grd.get_dz(flip=False).values, -dz, atol=0.01)

    grd._actnumsv[0, 0, 0] = 0

    assert grd.get_dz(asmasked=True).values[0, 0, 0] is np.ma.masked
    assert np.isclose(grd.get_dz(asmasked=False).values[0, 0, 0], dz, atol=0.01)


@given(xtgeo_grids)
def test_get_dxdy_is_get_dx_and_dy(grid):
    assert np.all(grid.get_dxdy(asmasked=True)[0].values == grid.get_dx().values)
    assert np.all(grid.get_dxdy(asmasked=True)[1].values == grid.get_dy().values)


def test_benchmark_grid_get_dz(benchmark):
    grd = Grid()
    grd.create_box(dimension=(100, 100, 100))

    def run():
        grd.get_dz()

    benchmark(run)


def test_benchmark_grid_get_dxdy(benchmark):
    grd = Grid()
    grd.create_box(dimension=(100, 100, 100))

    def run():
        grd.get_dxdy()

    benchmark(run)


def test_grid_get_dxdydz_zero_size():
    grd = Grid()
    grd.create_box(dimension=(0, 0, 0))

    assert grd.get_dx().values.shape == (0, 0, 0)
    assert grd.get_dy().values.shape == (0, 0, 0)
    assert grd.get_dz().values.shape == (0, 0, 0)


def test_grid_get_dxdydz_bad_coordsv_size():
    grd = Grid()
    grd.create_box(dimension=(10, 10, 10))
    grd._coordsv = np.zeros(shape=(0, 0, 0))

    with pytest.raises(xtgeo.XTGeoCLibError, match="Incorrect size of coordsv"):
        grd.get_dx()
    with pytest.raises(xtgeo.XTGeoCLibError, match="Incorrect size of coordsv"):
        grd.get_dy()
    with pytest.raises(xtgeo.XTGeoCLibError, match="Incorrect size of coordsv"):
        grd.get_dz()


def test_grid_get_dxdydz_bad_zcorn_size():
    grd = Grid()
    grd.create_box(dimension=(10, 10, 10))
    grd._zcornsv = np.zeros(shape=(0, 0, 0, 0))

    with pytest.raises(xtgeo.XTGeoCLibError, match="Incorrect size of zcornsv"):
        grd.get_dx()
    with pytest.raises(xtgeo.XTGeoCLibError, match="Incorrect size of zcornsv"):
        grd.get_dy()
    with pytest.raises(xtgeo.XTGeoCLibError, match="Incorrect size of zcornsv"):
        grd.get_dz()


def test_grid_get_dxdydz_bad_grid_top():
    grd = Grid()
    grd.create_box(dimension=(10, 10, 10))

    grd._coordsv[:, :, 2] = 0.0
    grd._coordsv[:, :, 5] = 0.0
    grd._coordsv[:, :, 0] += 1.0

    with pytest.raises(xtgeo.XTGeoCLibError, match="has near zero height"):
        grd.get_dx()
    with pytest.raises(xtgeo.XTGeoCLibError, match="has near zero height"):
        grd.get_dy()
    with pytest.raises(xtgeo.XTGeoCLibError, match="has near zero height"):
        grd.get_dz()


def test_grid_get_dxdydz_bad_metric():
    grd = Grid()
    grd.create_box(dimension=(10, 10, 10))

    with pytest.raises(ValueError, match="Unknown metric"):
        grd.get_dx(metric="foo")
    with pytest.raises(ValueError, match="Unknown metric"):
        grd.get_dy(metric="foo")
    with pytest.raises(ValueError, match="Unknown metric"):
        grd.get_dz(metric="foo")


def test_grid_roff_subgrids_import_regression(tmp_path):
    grid = Grid()
    grid.create_box(dimension=(5, 5, 67))
    grid.subgrids = OrderedDict(
        [
            ("subgrid_0", list(range(1, 21))),
            ("subgrid_1", list(range(21, 53))),
            ("subgrid_2", list(range(53, 68))),
        ]
    )
    grid.to_file(tmp_path / "grid.roff")

    grid2 = xtgeo.grid_from_file(tmp_path / "grid.roff")
    assert grid2.subgrids == OrderedDict(
        [
            ("subgrid_0", range(1, 21)),
            ("subgrid_1", range(21, 53)),
            ("subgrid_2", range(53, 68)),
        ]
    )


@pytest.mark.parametrize(
    "coordsv_dtype, zcornsv_dtype, actnumsv_dtype, match",
    [
        (np.float32, np.float32, np.int32, "The dtype of the coordsv"),
        (np.float64, np.float64, np.int32, "The dtype of the zcornsv"),
        (np.float64, np.float32, np.uint8, "The dtype of the actnumsv"),
    ],
)
def test_grid_bad_dtype_construction(
    coordsv_dtype, zcornsv_dtype, actnumsv_dtype, match
):
    with pytest.raises(TypeError, match=match):
        Grid(
            np.zeros((2, 2, 6), dtype=coordsv_dtype),
            np.zeros((2, 2, 2, 4), dtype=zcornsv_dtype),
            np.zeros((1, 1, 1), dtype=actnumsv_dtype),
        )


@pytest.mark.parametrize(
    "coordsv_dimensions, zcornsv_dimensions, actnumsv_dimensions, match",
    [
        ((2, 2, 2), (2, 2, 2, 4), (1, 1, 1), "shape of coordsv"),
        ((2, 2, 6), (2, 2, 2, 3), (1, 1, 1), "shape of zcornsv"),
        ((2, 2, 6), (2, 1, 2, 4), (1, 1, 1), "Mismatch between zcornsv and coordsv"),
        ((2, 2, 6), (2, 2, 2, 4), (1, 2, 1), "Mismatch between zcornsv and actnumsv"),
    ],
)
def test_grid_bad_dimensions_construction(
    coordsv_dimensions, zcornsv_dimensions, actnumsv_dimensions, match
):
    with pytest.raises(ValueError, match=match):
        Grid(
            np.zeros(coordsv_dimensions, dtype=np.float64),
            np.zeros(zcornsv_dimensions, dtype=np.float32),
            np.zeros(actnumsv_dimensions, dtype=np.int32),
        )
