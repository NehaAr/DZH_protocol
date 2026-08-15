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

Bioinformatics research routinely combines two very different shapes
of data: lightweight relational or tabular content (sample manifests,
phenotype tables, GWAS summary statistics) and heavy, dense numeric
arrays (expression matrices, genotype arrays, large derived matrices).
`dzh-protocol` provides a reproducible method, together with a Python
reference implementation, for ingesting a mixed set of such files into
a single hybrid store: light data is loaded directly into DuckDB
[@duckdb2019] as native, SQL-queryable tables, while heavy numeric
arrays are encoded into chunked, compressed Zarr [@zarr] stores and
linked back into DuckDB through a lightweight pointer table. Routing
between the two layers is governed by an explicit, caller-configurable
classification rule rather than hard-coded behaviour, and every
conversion step is checksum-validated so that outputs can be
independently verified against the source data.

# Statement of need

Researchers working with large, heterogeneous bioinformatics datasets
are commonly forced to choose between a relational database, which
handles metadata and small tabular data well but does not scale
efficiently to dense numeric arrays, and a chunked array format, which
handles large numeric data well but offers no native relational query
layer for accompanying metadata. In practice, this leads to ad hoc,
project-specific glue code that is rewritten for each new dataset and
is rarely documented as a reusable, checkable method.

`dzh-protocol` addresses this by formalising the routing decision, the
array encoding conventions (chunk shape, compression), and the
relational pointer-table schema as an explicit specification
(`PROTOCOL.md`), independent of the reference implementation. This
allows a second, independently written tool to be checked for
conformance against the same rules, rather than relying on informal
compatibility with one author's code. The reference implementation has
been validated against real FinnGen GWAS summary statistics data
[@finngen] — five files totalling 21,327,062 SNPs across
approximately 2.3GB of compressed text — with ingested row counts
matching an independently computed reference count exactly.

The package is intended for bioinformatics researchers and research
software engineers who need a documented, checkable method for
combining relational and array-shaped data in a single store, without
adopting a full data warehouse or writing bespoke ingestion code for
every project.

# Design

`dzh-protocol` is organised around five stages, each implemented as an
independent module: classification (`classify.py`), tabular ingestion
(`ingest_tabular.py`), array encoding (`encode_zarr.py`), relational
linking (`link.py`), and validation (`validate.py`), with a retrieval
convenience layer (`retrieve.py`) that resolves a pointer row and
returns the corresponding array, and a command-line interface
(`cli.py`) for directory-level batch conversion. Each stage's
behaviour is governed by explicit, caller-overridable parameters
(e.g. the size threshold used to route files, or the chunk shape used
when encoding an array) rather than fixed internal defaults, so that
routing and encoding decisions are always attributable to a stated
rule rather than implicit tool behaviour.

# Acknowledgements

The author acknowledges the University of Newcastle, School of
Biomedical Sciences and Pharmacy, for supporting this work.

# References
