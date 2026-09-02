---
title: 'DZH-Protocol: A Hybrid DuckDB and Zarr Ingestion Protocol for Heterogeneous Bioinformatics Data'
tags:
  - Python
  - bioinformatics
  - data engineering
  - reproducibility
  - DuckDB
  - Zarr
authors:
  - name: Neha
    orcid: 0009-0008-4196-2683
    affiliation: 1
affiliations:
  - name: School of Biomedical Sciences and Pharmacy, University of Newcastle, Australia
    index: 1
date: 14 August 2026
bibliography: paper.bib
---

# Summary

Bioinformatics analyses routinely combine two very different kinds of data:
small, structured tables that describe samples, phenotypes, or summary
statistics, and large, dense numeric arrays such as expression matrices or
genotype data. These two kinds of data are usually stored and queried very
differently; one favours a relational database, the other favours a
chunked array format and most workflows end up either forcing both into
a single tool that is good at only one of the two jobs, or gluing two
separate tools together by hand, in a way that is difficult to reproduce
or check.
DZH-Protocol is a lightweight, reproducible convention for routing each
input file to the storage layer best suited to its shape. Small tabular
files are ingested directly into a `DuckDB` relational database. Large
numeric arrays are instead encoded into chunked, compressed `Zarr` stores,
and a small "pointer table" inside DuckDB records where each array lives,
its shape, its data type, its chunking, and a checksum  without ever
copying the array's numeric contents into the database itself. Analysts
can then query the tabular data with ordinary SQL and retrieve linked
arrays, either fully loaded into memory or lazily sliced, from the same
DuckDB connection. A reference Python implementation is available on
GitHub [@arora2026dzhrepo] and has been exercised against a real
21-million-row summary-statistics dataset.

# Statement of need

Dense numeric arrays (expression matrices, genotype calls) do not fit
comfortably inside a relational table, and relational metadata (sample
manifests, phenotype tables, GWAS summary statistics) does not benefit
from being flattened into a chunked array format. Existing practice
typically forces a choice between the two, and the boundary between "this
file goes in the database" and "this file goes in the array store" is
usually decided informally, per project, and undocumented — which makes
it hard for a second person, or the original author six months later, to
reproduce how a given dataset was ingested.
DZH-Protocol is aimed at bioinformaticians and research-software
engineers who already work with both file types and want a documented,
scriptable, and checkable rule for splitting them, rather than a new
end-to-end analysis framework. It deliberately does not attempt to
replace either DuckDB or Zarr, and it does not prescribe a relational
schema beyond the pointer table itself — downstream, domain-specific
packages are expected to build their own tables on top of the layer the
protocol establishes. Because the classification rule, chunking
convention, pointer-table schema, and checksum validation are specified
explicitly rather than left as implementation detail, independently
written implementations of the protocol can, in principle, be checked
against one another for conformance, which is the property that
distinguishes a protocol from an ordinary ingestion script.

# State of the field

Several existing projects address part of the same problem space.
`duckdb-zarr` [@duckdbzarr] and `duckdb_zarr` [@duckdbzarr2] are DuckDB
extensions that expose Zarr arrays directly as SQL tables by "pivoting"
each array cell into a row, allowing array data to be queried with SQL
without an intermediate ingestion step. `xarray` [@hoyer2017xarray] and
related projects such as `xarray-sql` provide a labelled-array
abstraction over Zarr and similar formats from the Python side, with SQL
support layered on top in some of these tools.
DZH-Protocol takes a different position relative to these tools: rather
than querying array contents through SQL directly, it treats the array
and the relational layers as separate, and links them only through
lightweight pointer metadata (location, shape, dtype, chunking,
checksum), so that DuckDB never has to plan or execute a scan over array
cells. This trades away the ability to write a single SQL query that
touches both array values and relational metadata in one statement — the
capability the SQL-native Zarr extensions are built around — in exchange
for a smaller, easier-to-audit surface: the relational layer stays
exactly as fast as ordinary DuckDB, array data stays exactly as efficient
as ordinary chunked Zarr access, and a conformance check only has to
verify a pointer row and a checksum rather than the correctness of a
cell-by-cell SQL projection.


# Software Design

The protocol is built around four explicit decisions, each made to keep
the two storage layers independent and the boundary between them
auditable:

A configurable classification rule, not a fixed one. Any
array-native format (HDF5, NPY/NPZ, VCF) is always routed to Zarr.
Tabular formats are routed to DuckDB unless they exceed a size
threshold (500 MB by default), in which case they are treated as
arrays regardless of their on-disk format , the rationale given is
that a sufficiently large flat file behaves like a dense matrix once
loaded, independent of its original format. Making the threshold a
parameter, rather than a hard-coded constant, was a deliberate choice
so the rule can be tuned to a project's available memory rather than
forcing one global default on every use case.
Row-blocked, ~64 MB chunking with Zstandard compression as the
default, but overridable. The default chunk shape is a size-based
heuristic, not a domain-aware one; the protocol explicitly allows
overriding `chunk_shape` when the data has a more natural blocking
(the documentation gives per-chromosome genomic data as an example).
This keeps the default safe and general while not forcing every
dataset into a one-size-fits-all layout.

A pointer table instead of a federated query layer. DuckDB stores
only the array's location, shape, dtype, chunking, and checksum —
never its numeric contents. This is the central design trade-off
discussed in the previous section: it sacrifices in-database array
querying in exchange for a much smaller surface to validate and keep
consistent.

Checksum-based, round-trip validation as a first-class step, not
an optional afterthought. `verify_conversion` checks array shape
fidelity after encoding, and the tabular path is validated by
comparing `ingest_tabular`'s returned row count against an independent
count of the source file. Because the classification rule, chunking
convention, and pointer schema are all specified rather than left
implicit, this validation step doubles as a conformance check that
another, independently written implementation of the protocol could
also be run against.

# Research Impact Statement

The reference implementation has been run against a real 21-million-row
summary-statistics dataset, which is evidence that the protocol handles
GWAS-scale tabular data in practice rather than only in a toy example.
Beyond that single validation case, the material available for this
paper does not describe external users, downstream integrations,
citations, or independent implementations that have been checked for
conformance against the protocol's rules.


# AI usage disclosure

AI tools (GitHub Copilot) were used occasionally for code generation, particularly for debugging, and for grammar and language checks of the manuscript. All suggestions were reviewed and validated by the human authors.


# Acknowledgements

The author acknowledges the University of Newcastle, School of
Biomedical Sciences and Pharmacy, for supporting this work.

# References




