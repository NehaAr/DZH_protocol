# Contributing to DZH-Protocol

Thanks for your interest in DZH-Protocol.

## Reporting issues
Please open a GitHub issue describing the problem, including a minimal
reproducible example where possible (a small sample file and the code
that triggers the issue).

## Proposing changes
1. Fork the repository and create a branch for your change.
2. Add or update tests in `tests/` covering your change — PRs without
   test coverage for new behaviour are unlikely to be merged as-is.
3. Run the test suite locally (`pytest tests/`) before opening a pull
   request.
4. If your change affects the protocol's rules (Sections 3-7 of
   `docs/PROTOCOL.md`), please open an issue to discuss first, since
   these are meant to be stable across implementations.

## Scope
Bug fixes, documentation improvements, and additional format support
(new tabular/array readers) are welcome. Changes to the core protocol
specification itself should be proposed as an issue before a PR, since
they affect conformance for any other implementation.

## Code of conduct
Be respectful and constructive. Harassment or discriminatory language
will not be tolerated.
