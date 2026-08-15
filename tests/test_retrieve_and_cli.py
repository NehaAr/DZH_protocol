import numpy as np
import duckdb
import subprocess
import sys

from dzh_protocol import (
    encode_array_to_zarr,
    register_zarr_pointer,
    init_pointer_table,
    get_array,
    list_arrays,
)


def test_get_array_roundtrip(tmp_path):
    con = duckdb.connect(":memory:")
    init_pointer_table(con)

    original = np.arange(200 * 4, dtype="float64").reshape(200, 4)
    store_path = str(tmp_path / "roundtrip.zarr")
    meta = encode_array_to_zarr(original, store_path=store_path, array_name="mat")
    register_zarr_pointer(con, array_id="mat_v1", zarr_metadata=meta)

    retrieved = get_array(con, "mat_v1")
    assert np.array_equal(original, retrieved)


def test_get_array_lazy_mode(tmp_path):
    con = duckdb.connect(":memory:")
    init_pointer_table(con)

    original = np.ones((50, 3))
    store_path = str(tmp_path / "lazy.zarr")
    meta = encode_array_to_zarr(original, store_path=store_path, array_name="ones")
    register_zarr_pointer(con, array_id="ones_v1", zarr_metadata=meta)

    lazy = get_array(con, "ones_v1", as_numpy=False)
    # should support slicing without materialising the whole array
    assert lazy[0:5, :].shape == (5, 3)


def test_list_arrays(tmp_path):
    con = duckdb.connect(":memory:")
    init_pointer_table(con)
    arr = np.zeros((10, 2))
    store_path = str(tmp_path / "listed.zarr")
    meta = encode_array_to_zarr(arr, store_path=store_path, array_name="z")
    register_zarr_pointer(con, array_id="z_v1", zarr_metadata=meta)

    df = list_arrays(con)
    assert len(df) == 1
    assert df.iloc[0]["array_id"] == "z_v1"


def test_cli_convert_and_list(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "small.tsv").write_text("a\tb\n1\t2\n3\t4\n")

    db_path = str(tmp_path / "out.duckdb")

    result = subprocess.run(
        [sys.executable, "-m", "dzh_protocol.cli", "convert", str(src_dir), "--output", db_path],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "tabular tables ingested" in result.stdout

    con = duckdb.connect(db_path, read_only=True)
    df = con.execute("SELECT * FROM small").fetchdf()
    assert len(df) == 2
