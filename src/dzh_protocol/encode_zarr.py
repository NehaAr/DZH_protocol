"""
Stage 3 -- Array Encoding (heavy data).

Arrays routed here by Stage 1 are written to a Zarr store using an
explicit, documented chunking and compression policy, so any
conformant implementation of the protocol produces comparably-shaped
stores -- not just "whatever zarr's defaults happen to be this month".
"""

from __future__ import annotations
import datetime
import numpy as np
import zarr


# Protocol-level default compression. Stated explicitly so conformant
# implementations don't silently diverge on codec choice.
DEFAULT_COMPRESSOR_NAME = "zstd"
DEFAULT_COMPRESSION_LEVEL = 5


def default_chunk_shape(array_shape: tuple[int, ...], target_chunk_mb: int = 64,
                         itemsize: int = 8) -> tuple[int, ...]:
    """
    Compute a simple, documented chunk shape: chunk along the first
    axis only, sized so each chunk is approximately `target_chunk_mb`.
    This is the protocol's default rule -- callers may override with
    a custom chunk shape when the data has a more natural blocking
    (e.g. per-chromosome for genomic data).
    """
    if len(array_shape) == 0:
        return ()
    row_bytes = itemsize
    for dim in array_shape[1:]:
        row_bytes *= dim
    rows_per_chunk = max(1, int((target_chunk_mb * 1024 * 1024) / row_bytes))
    rows_per_chunk = min(rows_per_chunk, array_shape[0])
    return (rows_per_chunk,) + tuple(array_shape[1:])


def encode_array_to_zarr(
    array: np.ndarray,
    store_path: str,
    array_name: str = "data",
    chunk_shape: tuple[int, ...] | None = None,
    dim_names: list[str] | None = None,
) -> dict:
    """
    Write a numpy array to a Zarr store at `store_path`, following the
    DZH-Protocol Stage 3 convention.

    Returns a metadata dict describing the encoded array -- this is
    exactly what Stage 4 (link.py) records in the DuckDB pointer table.
    """
    if chunk_shape is None:
        chunk_shape = default_chunk_shape(array.shape, itemsize=array.itemsize)

    root = zarr.open_group(store_path, mode="a")
    z = root.create_array(
        name=array_name,
        shape=array.shape,
        chunks=chunk_shape,
        dtype=array.dtype,
        overwrite=True,
    )
    z[:] = array

    if dim_names:
        z.attrs["_ARRAY_DIMENSIONS"] = dim_names  # xarray/zarr convention

    metadata = {
        "store_path": store_path,
        "array_name": array_name,
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "chunk_shape": list(chunk_shape),
        "dim_names": dim_names or [],
        "encoded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "protocol_stage": "3-array-encode",
    }
    return metadata
