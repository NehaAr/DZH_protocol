"""
DZH-Protocol: Hybrid DuckDB + Zarr Ingestion Protocol
======================================================

A reproducible protocol for converting heterogeneous data files into a
hybrid store: lightweight relational/tabular data lives natively in
DuckDB, while heavy numeric arrays are encoded to Zarr and linked back
into DuckDB through a pointer table.

Pipeline stages (see docs/PROTOCOL.md for the full specification):
    1. classify   -- detect file type & route tabular vs. array-heavy
    2. ingest      -- load tabular/metadata files directly into DuckDB
    3. encode      -- convert heavy arrays to chunked, compressed Zarr
    4. link        -- record a pointer row in DuckDB for each Zarr store
    5. validate    -- checksum + shape verification across conversions
"""

from .classify import classify_file, ClassificationResult
from .ingest_tabular import ingest_tabular
from .encode_zarr import encode_array_to_zarr
from .link import register_zarr_pointer, init_pointer_table, load_pointer
from .validate import checksum_file, verify_conversion
from .retrieve import get_array, list_arrays

__version__ = "0.2.0"

__all__ = [
    "classify_file",
    "ClassificationResult",
    "ingest_tabular",
    "encode_array_to_zarr",
    "register_zarr_pointer",
    "init_pointer_table",
    "load_pointer",
    "checksum_file",
    "verify_conversion",
    "get_array",
    "list_arrays",
    "__version__",
]
