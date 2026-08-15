"""
Stage 2 -- Relational Ingestion (light data).

Tabular/metadata files are loaded directly into DuckDB using DuckDB's
native readers, under a fixed, documented convention:
  - column names are lower-cased and whitespace-stripped
  - the source file path and ingestion timestamp are recorded alongside
    the table for provenance (Stage 6/7 of the protocol)
"""

from __future__ import annotations
import duckdb
import datetime
from pathlib import Path


def _reader_for(filepath: str) -> str:
    """Return the DuckDB read function call for a given file, based on
    its extension. Handles both dot-separated ('file.tsv.gz') and
    underscore-separated ('file_tsv.gz', e.g. FinnGen exports) naming,
    and compressed files (.gz) are handled natively by DuckDB either way."""
    p = Path(filepath)
    name_lower = p.name.lower()

    # strip a trailing compression suffix for matching purposes only --
    # DuckDB's readers auto-detect gzip from the real path regardless
    stem = name_lower
    for comp in (".gz", ".bz2", ".zst"):
        if stem.endswith(comp):
            stem = stem[: -len(comp)]
            break

    if stem.endswith(".tsv") or stem.endswith("_tsv"):
        return f"read_csv('{filepath}', delim='\\t', header=True, union_by_name=True)"
    if stem.endswith(".csv") or stem.endswith("_csv"):
        return f"read_csv('{filepath}', header=True, union_by_name=True)"
    if stem.endswith(".parquet") or stem.endswith("_parquet"):
        return f"read_parquet('{filepath}')"
    if stem.endswith((".json", ".jsonl")) or stem.endswith(("_json", "_jsonl")):
        return f"read_json_auto('{filepath}')"
    raise ValueError(f"No tabular reader registered for: {filepath}")


def ingest_tabular(
    con: duckdb.DuckDBPyConnection,
    filepath: str,
    table_name: str,
    if_exists: str = "replace",
) -> dict:
    """
    Ingest a single tabular file into DuckDB as `table_name`.

    Parameters
    ----------
    con : an open duckdb.DuckDBPyConnection (in-memory or file-backed)
    filepath : path to the source file
    table_name : destination table name in DuckDB
    if_exists : "replace" (default) or "append"

    Returns a small provenance dict recorded for Stage 7 (versioning).
    """
    reader = _reader_for(filepath)
    verb = "CREATE OR REPLACE TABLE" if if_exists == "replace" else "INSERT INTO"

    if if_exists == "append":
        con.execute(f"INSERT INTO {table_name} SELECT * FROM {reader}")
    else:
        con.execute(f"{verb} {table_name} AS SELECT * FROM {reader}")

    # normalise column names to the protocol convention
    cols = con.execute(f"PRAGMA table_info('{table_name}')").fetchdf()
    for _, row in cols.iterrows():
        old = row["name"]
        new = old.strip().lower().replace(" ", "_")
        if new != old:
            con.execute(f'ALTER TABLE {table_name} RENAME COLUMN "{old}" TO "{new}"')

    row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

    provenance = {
        "table_name": table_name,
        "source_path": filepath,
        "row_count": row_count,
        "ingested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "protocol_stage": "2-tabular-ingest",
    }
    return provenance
