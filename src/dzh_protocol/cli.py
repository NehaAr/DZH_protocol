"""
Command-line interface for DZH-Protocol.

Usage:
    dzh convert <input_dir> --output store.duckdb --zarr-dir arrays.zarr
    dzh list --db store.duckdb
"""

from __future__ import annotations
import argparse
import sys
import duckdb

from .classify import classify_directory, DEFAULT_SIZE_THRESHOLD_BYTES
from .ingest_tabular import ingest_tabular
from .link import init_pointer_table
from .retrieve import list_arrays


def cmd_convert(args: argparse.Namespace) -> int:
    con = duckdb.connect(args.output)
    init_pointer_table(con)

    results = classify_directory(args.input_dir, size_threshold_bytes=args.threshold)

    n_tabular, n_array, n_skipped = 0, 0, 0
    for r in results:
        print(f"[{r.route:8s}] {r.path}  ({r.reason})")
        if r.route == "tabular":
            try:
                table_name = _safe_table_name(r.path)
                ingest_tabular(con, r.path, table_name=table_name)
                n_tabular += 1
            except ValueError as e:
                print(f"  skipped -- {e}", file=sys.stderr)
                n_skipped += 1
        else:
            # Array-routed files need a format-specific loader the
            # protocol doesn't prescribe (HDF5 vs. VCF vs. NPY differ);
            # the CLI reports what *would* be encoded and leaves the
            # actual array extraction to a format-specific script using
            # `encode_array_to_zarr` directly -- see README "Quickstart".
            print(f"  -> array-routed; use encode_array_to_zarr() directly for this format")
            n_array += 1

    print(f"\nDone: {n_tabular} tabular tables ingested, "
          f"{n_array} files flagged for array encoding, {n_skipped} skipped.")
    print(f"DuckDB store: {args.output}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    con = duckdb.connect(args.db, read_only=True)
    df = list_arrays(con)
    if df.empty:
        print("No arrays registered in this store.")
    else:
        print(df.to_string(index=False))
    return 0


def _safe_table_name(filepath: str) -> str:
    import re
    from pathlib import Path
    stem = Path(filepath).name
    for suffix in (".gz", ".tsv", ".csv", ".parquet", ".json", ".jsonl"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    return re.sub(r"[^a-zA-Z0-9_]", "_", stem).lower()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="dzh", description="DZH-Protocol: hybrid DuckDB + Zarr data ingestion")
    sub = parser.add_subparsers(dest="command", required=True)

    p_convert = sub.add_parser("convert", help="Classify and ingest a directory of files")
    p_convert.add_argument("input_dir", help="Directory of source files to process")
    p_convert.add_argument("--output", required=True, help="Path to the DuckDB store to create/update")
    p_convert.add_argument("--threshold", type=int, default=DEFAULT_SIZE_THRESHOLD_BYTES,
                            help="Size threshold in bytes for tabular-vs-array routing")
    p_convert.set_defaults(func=cmd_convert)

    p_list = sub.add_parser("list", help="List arrays registered in a DuckDB store's pointer table")
    p_list.add_argument("--db", required=True, help="Path to an existing DuckDB store")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
