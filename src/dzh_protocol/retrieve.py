"""
Retrieval helper -- closes the loop between the DuckDB pointer table
and the underlying Zarr store.

Without this, a user has to manually read a pointer row, then
separately know to call zarr.open() on its store_path. This is the
"real added value" layer on top of what DuckDB and Zarr each do
independently -- it's the part of DZH-Protocol that's genuinely more
than a thin wrapper around either library.
"""

from __future__ import annotations
import duckdb
import numpy as np
import zarr

from .link import load_pointer


def get_array(
    con: duckdb.DuckDBPyConnection,
    array_id: str,
    as_numpy: bool = True,
):
    """
    Resolve a pointer row by `array_id` and return the underlying array.

    Parameters
    ----------
    con : an open DuckDB connection with a populated zarr_pointers table
    array_id : the identifier used when the array was registered
        (see `register_zarr_pointer`)
    as_numpy : if True (default), materialise the full array into memory
        as a numpy array. If False, return the lazy zarr.Array itself,
        which supports slicing without loading the whole array --
        important for the multi-GB arrays this protocol targets.

    Returns
    -------
    np.ndarray or zarr.Array
    """
    pointer = load_pointer(con, array_id)
    root = zarr.open_group(pointer["store_path"], mode="r")
    z = root[pointer["array_name"]]

    if as_numpy:
        return z[:]
    return z


def list_arrays(con: duckdb.DuckDBPyConnection):
    """Return a DataFrame of every array currently registered in the
    pointer table -- a quick way to discover what's available in a
    given DuckDB store without knowing array_ids in advance."""
    return con.execute(
        "SELECT array_id, store_path, array_name, shape, dtype, encoded_at "
        "FROM zarr_pointers ORDER BY encoded_at"
    ).fetchdf()
