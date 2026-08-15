"""
Stage 1 -- Format Detection & Classification.

Every input file is classified as either:
  - "tabular"   -> ingested directly into DuckDB (Stage 2)
  - "array"     -> encoded to Zarr and linked via pointer table (Stages 3-4)

The routing rule is deliberately explicit and configurable, not
hard-coded behaviour buried in a script -- this is what makes the
threshold a *protocol rule* rather than a personal preference.
"""

from dataclasses import dataclass
from pathlib import Path
import os

# Protocol-level default: any single file/array over this size (bytes)
# is routed to Zarr rather than ingested as a flat DuckDB table.
# Override per-call via `size_threshold_bytes` -- this is a protocol
# *parameter*, not a fixed constant.
DEFAULT_SIZE_THRESHOLD_BYTES = 500 * 1024 * 1024  # 500 MB

TABULAR_EXTENSIONS = {".csv", ".tsv", ".parquet", ".json", ".jsonl"}
ARRAY_CANDIDATE_EXTENSIONS = {".h5", ".hdf5", ".npy", ".npz", ".vcf", ".vcf.gz"}
COMPRESSED_TABULAR_SUFFIXES = {".gz", ".bz2", ".zst"}


@dataclass
class ClassificationResult:
    path: str
    route: str          # "tabular" or "array"
    reason: str          # human-readable justification, for provenance logs
    size_bytes: int


def _base_extension(path: Path) -> str:
    """
    Return the effective tabular-format extension, robust to two
    naming conventions seen in real-world data drops:
      - dot-separated:  'file.tsv.gz'  -> '.tsv'
      - underscore-separated: 'file_tsv.gz' -> '.tsv'  (e.g. FinnGen
        summary-stat exports, which use 'name_tsv.gz' rather than
        'name.tsv.gz')
    Falls back to the plain suffix if neither pattern matches.
    """
    name = path.name.lower()
    known_tokens = {"tsv", "csv", "parquet", "json", "jsonl"}

    # Strip a trailing compression suffix first, if present
    stem = name
    for comp in COMPRESSED_TABULAR_SUFFIXES:
        if stem.endswith(comp):
            stem = stem[: -len(comp)]
            break

    for token in known_tokens:
        if stem.endswith("." + token) or stem.endswith("_" + token):
            return "." + token

    # fall back to whatever pathlib thinks the suffix is
    suffixes = path.suffixes
    if not suffixes:
        return ""
    if suffixes[-1] in COMPRESSED_TABULAR_SUFFIXES and len(suffixes) > 1:
        return suffixes[-2]
    return suffixes[-1]


def classify_file(
    filepath: str,
    size_threshold_bytes: int = DEFAULT_SIZE_THRESHOLD_BYTES,
) -> ClassificationResult:
    """
    Classify a single file as 'tabular' or 'array' per the DZH-Protocol
    Stage 1 rule.

    Rule (in priority order):
      1. Known array-native formats (.h5, .npy, .vcf, ...) -> always 'array'
      2. Known flat tabular formats under the size threshold -> 'tabular'
      3. Known flat tabular formats OVER the size threshold -> 'array'
         (still routed to Zarr, since a giant TSV is functionally a
         dense matrix once loaded -- e.g. GWAS summary stats)
      4. Unknown extension -> 'tabular' by default, flagged in `reason`
         for manual review.
    """
    p = Path(filepath)
    size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
    ext = _base_extension(p)

    if ext in ARRAY_CANDIDATE_EXTENSIONS:
        return ClassificationResult(
            path=filepath, route="array",
            reason=f"array-native extension '{ext}'", size_bytes=size,
        )

    if ext in TABULAR_EXTENSIONS:
        if size > size_threshold_bytes:
            return ClassificationResult(
                path=filepath, route="array",
                reason=(f"tabular extension '{ext}' but size {size:,}B "
                        f"exceeds threshold {size_threshold_bytes:,}B"),
                size_bytes=size,
            )
        return ClassificationResult(
            path=filepath, route="tabular",
            reason=f"tabular extension '{ext}', under size threshold",
            size_bytes=size,
        )

    return ClassificationResult(
        path=filepath, route="tabular",
        reason=f"unrecognised extension '{ext}' -- defaulted to tabular, review manually",
        size_bytes=size,
    )


def classify_directory(
    dirpath: str,
    size_threshold_bytes: int = DEFAULT_SIZE_THRESHOLD_BYTES,
) -> list[ClassificationResult]:
    """Classify every file in a directory (non-recursive)."""
    results = []
    for entry in sorted(Path(dirpath).iterdir()):
        if entry.is_file():
            results.append(classify_file(str(entry), size_threshold_bytes))
    return results
