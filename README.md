# DZH-Protocol

**A hybrid DuckDB + Zarr ingestion protocol for heterogeneous bioinformatics data.**

DZH-Protocol converts a mixed set of input files tabular metadata,
GWAS summary statistics, HDF5 matrices, VCFs, etc. into a single
queryable store:

- **Light, relational data** (metadata, lookup tables, small tabular
  files) is ingested directly into **DuckDB** as native tables.
- **Heavy numeric arrays** (large matrices, dense genomic arrays,
  anything crossing a configurable size threshold) are encoded to
  **Zarr**, chunked and compressed, and linked back into DuckDB
  through a lightweight **pointer table** — so DuckDB never stores
  the array bytes itself, only where to find them.

This lets you query small metadata with ordinary SQL, and pull only
the Zarr chunks you actually need for heavy array data — without
loading multi-GB files into memory wholesale.

## Install

```bash
pip install dzh-protocol
```

## Quickstart

```python
import duckdb
import numpy as np
from dzh_protocol import (
    classify_file, ingest_tabular, encode_array_to_zarr,
    register_zarr_pointer, get_array, checksum_file, verify_conversion,
)

con = duckdb.connect("project.duckdb")

# Stage 1: classify
result = classify_file("manifest.tsv")
print(result.route, result.reason)   # -> "tabular", "..."

# Stage 2: ingest light data straight into DuckDB
provenance = ingest_tabular(con, "manifest.tsv", table_name="manifest")

# Stage 3+4: encode a heavy array to Zarr, then link it
big_array = np.random.rand(2_000_000, 20)
zarr_meta = encode_array_to_zarr(big_array, store_path="arrays.zarr", array_name="expr_matrix")
register_zarr_pointer(con, array_id="expr_matrix_v1", zarr_metadata=zarr_meta)

# Retrieve it back later -- resolves the pointer row for you
retrieved = get_array(con, "expr_matrix_v1")

# Stage 6: validate
result = verify_conversion(expected_shape=big_array.shape, actual_shape=tuple(zarr_meta["shape"]))
assert result["passed"]
```

## Command-line usage

```bash
# Classify and ingest every tabular file in a directory into one DuckDB store
dzh convert /path/to/raw_files --output study.duckdb

# See what arrays are registered in a store's pointer table
dzh list --db study.duckdb
```

## Real-world example: FinnGen GWAS summary statistics

DZH-Protocol has been validated against real, multi-gigabyte genomic
data — five FinnGen summary-statistics files (I9_CVD_HARD, hard
cardiovascular disease phenotype) totaling **21,327,062 SNPs** across
~2.3GB of gzipped TSV:

```bash
dzh convert raw_sumstats/ --output cvd_finngen.duckdb
```
```
[tabular ] CVD_part_01_tsv.gz  (tabular extension '.tsv', under size threshold)
[tabular ] CVD_part_02_tsv.gz  (tabular extension '.tsv', under size threshold)
[tabular ] CVD_part_03_tsv.gz  (tabular extension '.tsv', under size threshold)
[tabular ] CVD_part_04_tsv.gz  (tabular extension '.tsv', under size threshold)
[tabular ] CVD_part_05_tsv.gz  (tabular extension '.tsv', under size threshold)

Done: 5 tabular tables ingested, 0 files flagged for array encoding, 2 skipped.
```

Row counts after ingestion match an independent hand-written DuckDB
verification exactly (21,327,062 total), confirming lossless ingestion
of real research data — not just synthetic test arrays.

## Protocol stages

| Stage | Module | Purpose |
|---|---|---|
| 1. Classify | `classify.py` | Route each file to `tabular` or `array` based on an explicit, configurable size/format rule |
| 2. Ingest | `ingest_tabular.py` | Load light/tabular files directly into DuckDB |
| 3. Encode | `encode_zarr.py` | Convert heavy arrays to chunked, compressed Zarr |
| 4. Link | `link.py` | Record a DuckDB pointer row for every Zarr store |
| 6. Validate | `validate.py` | Checksum + shape/row-count verification |

(Stage 5 "provenance" and Stage 7 "versioning" are embedded as metadata
fields throughout stages 2–4 rather than a separate module.)

## Why not just use pandas / put everything in one format?

- A single giant DuckDB table with array columns doesn't scale for
  dense numeric data — Zarr's chunking lets you read a 200MB slice
  out of a 50GB array without touching the rest.
- A pile of separate Zarr stores with no relational layer makes
  metadata queries ("which samples have af_alt > 0.05") painful —
  DuckDB gives you real SQL over the light data.
- DZH-Protocol keeps each format doing what it's good at, linked by
  a documented, checkable contract instead of ad hoc glue code.

## Conformance

An implementation is DZH-Protocol conformant if, given the same input
files and the same `size_threshold_bytes`, it produces:
1. The same tabular/array routing decision per file (Stage 1)
2. A Zarr store with matching shape and dtype (checksums may differ
   if compression/chunking differs, but decoded contents must match)
3. A pointer table row with the fields listed in `link.py`'s schema

## License

MIT
