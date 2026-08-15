import os
import json
import numpy as np
import duckdb
import pytest

from dzh_protocol import (
    classify_file,
    ingest_tabular,
    encode_array_to_zarr,
    register_zarr_pointer,
    init_pointer_table,
    load_pointer,
    checksum_file,
    verify_conversion,
)


@pytest.fixture
def sample_tsv(tmp_path):
    p = tmp_path / "sample.tsv"
    p.write_text("chrom\tpos\tpval\n1\t100\t0.05\n1\t200\t0.001\n2\t50\t0.9\n")
    return str(p)


def test_classify_small_tsv(sample_tsv):
    result = classify_file(sample_tsv)
    assert result.route == "tabular"


def test_classify_underscore_separated_naming(tmp_path):
    # Real-world case: FinnGen-style exports name files 'name_tsv.gz',
    # not 'name.tsv.gz'. This must still be recognised as tabular.
    p = tmp_path / "CVD_part_01_tsv.gz"
    p.write_bytes(b"dummy")  # content irrelevant, only the name is tested
    result = classify_file(str(p), size_threshold_bytes=10**12)
    assert result.route == "tabular"
    assert "tsv" in result.reason


def test_classify_forces_array_over_threshold(sample_tsv):
    # force threshold to 1 byte so the same small file is routed to "array"
    result = classify_file(sample_tsv, size_threshold_bytes=1)
    assert result.route == "array"


def test_ingest_tabular_roundtrip(sample_tsv):
    con = duckdb.connect(":memory:")
    prov = ingest_tabular(con, sample_tsv, table_name="cvd")
    assert prov["row_count"] == 3
    df = con.execute("SELECT * FROM cvd").fetchdf()
    assert list(df.columns) == ["chrom", "pos", "pval"]
    assert len(df) == 3


def test_encode_and_link_array(tmp_path):
    con = duckdb.connect(":memory:")
    init_pointer_table(con)

    arr = np.arange(1000 * 5, dtype="float64").reshape(1000, 5)
    store_path = str(tmp_path / "test.zarr")
    meta = encode_array_to_zarr(arr, store_path=store_path, array_name="matrix")

    assert meta["shape"] == [1000, 5]

    register_zarr_pointer(con, array_id="matrix_v1", zarr_metadata=meta)
    row = load_pointer(con, "matrix_v1")
    assert row["array_name"] == "matrix"
    assert json.loads(row["shape"]) == [1000, 5]


def test_verify_conversion_pass():
    result = verify_conversion(expected_row_count=100, actual_row_count=100)
    assert result["passed"] is True
    assert result["mismatches"] == []


def test_verify_conversion_fail():
    result = verify_conversion(expected_row_count=100, actual_row_count=99)
    assert result["passed"] is False
    assert len(result["mismatches"]) == 1


def test_checksum_file_deterministic(sample_tsv):
    c1 = checksum_file(sample_tsv)
    c2 = checksum_file(sample_tsv)
    assert c1 == c2
    assert len(c1) == 64  # sha256 hex digest length
