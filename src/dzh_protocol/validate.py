"""
Stage 6 -- Validation & Checksums.

Every conversion (tabular or array) should be independently verifiable:
same source file -> same checksum -> same row/element counts. This is
what lets a second, independently-written implementation claim
"DZH-Protocol conformance" -- it can be checked, not just asserted.
"""

from __future__ import annotations
import hashlib
import numpy as np


def checksum_file(filepath: str, algorithm: str = "sha256", chunk_size: int = 1024 * 1024) -> str:
    """Compute a streaming checksum of a file without loading it fully
    into memory -- important for the multi-GB files this protocol
    targets."""
    h = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def checksum_array(array: np.ndarray) -> str:
    """Checksum of array contents (used to verify a Zarr-encoded array
    matches its in-memory source before the source is discarded)."""
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def verify_conversion(
    expected_row_count: int | None = None,
    actual_row_count: int | None = None,
    expected_shape: tuple | None = None,
    actual_shape: tuple | None = None,
) -> dict:
    """
    Compare expected vs. actual counts/shapes after a conversion step.
    Returns a result dict with `passed: bool` and a list of any
    mismatches found -- intended to be logged as part of Stage 7
    provenance, and used in the package's own test suite.
    """
    mismatches = []

    if expected_row_count is not None and actual_row_count is not None:
        if expected_row_count != actual_row_count:
            mismatches.append(
                f"row count mismatch: expected {expected_row_count}, got {actual_row_count}"
            )

    if expected_shape is not None and actual_shape is not None:
        if tuple(expected_shape) != tuple(actual_shape):
            mismatches.append(
                f"shape mismatch: expected {tuple(expected_shape)}, got {tuple(actual_shape)}"
            )

    return {"passed": len(mismatches) == 0, "mismatches": mismatches}
