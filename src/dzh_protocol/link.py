"""
Stage 4 -- Cross-Reference Linking.

This is the core of the "hybrid" design: DuckDB never stores the heavy
array bytes itself. Instead, a lightweight pointer table records where
each Zarr-encoded array lives, its shape/dtype/chunking, and a
checksum -- ordinary DuckDB rows that queries can join against, then
follow to load only the Zarr chunks actually needed.
"""

from __future__ import annotations
import duckdb

POINTER_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS zarr_pointers (
    array_id        VARCHAR PRIMARY KEY,
    store_path      VARCHAR NOT NULL,
    array_name      VARCHAR NOT NULL,
    shape           VARCHAR NOT NULL,   -- JSON-encoded list
    dtype           VARCHAR NOT NULL,
    chunk_shape     VARCHAR NOT NULL,   -- JSON-encoded list
    dim_names       VARCHAR,            -- JSON-encoded list
    source_checksum VARCHAR,
    encoded_at      VARCHAR NOT NULL,
    protocol_version VARCHAR NOT NULL
)
"""


def init_pointer_table(con: duckdb.DuckDBPyConnection) -> None:
    """Create the zarr_pointers table if it doesn't already exist."""
    con.execute(POINTER_TABLE_SCHEMA)


def register_zarr_pointer(
    con: duckdb.DuckDBPyConnection,
    array_id: str,
    zarr_metadata: dict,
    source_checksum: str | None = None,
    protocol_version: str = "0.1.0",
) -> None:
    """
    Insert (or replace) a pointer row for a Zarr-encoded array, using
    the metadata dict returned by `encode_array_to_zarr`.
    """
    import json

    init_pointer_table(con)
    con.execute(
        """
        INSERT OR REPLACE INTO zarr_pointers
        (array_id, store_path, array_name, shape, dtype, chunk_shape,
         dim_names, source_checksum, encoded_at, protocol_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            array_id,
            zarr_metadata["store_path"],
            zarr_metadata["array_name"],
            json.dumps(zarr_metadata["shape"]),
            zarr_metadata["dtype"],
            json.dumps(zarr_metadata["chunk_shape"]),
            json.dumps(zarr_metadata.get("dim_names", [])),
            source_checksum,
            zarr_metadata["encoded_at"],
            protocol_version,
        ],
    )


def load_pointer(con: duckdb.DuckDBPyConnection, array_id: str) -> dict:
    """Retrieve a pointer row as a plain dict (e.g. to then open the
    referenced Zarr store with zarr.open())."""
    row = con.execute(
        "SELECT * FROM zarr_pointers WHERE array_id = ?", [array_id]
    ).fetchdf()
    if row.empty:
        raise KeyError(f"No pointer registered for array_id={array_id!r}")
    return row.iloc[0].to_dict()
