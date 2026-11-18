# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Versioning follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). The tool is versioned with its reference
tables: tool 2.4.0 ships tables 2.40.

## [2.4.0] - 2026-11-18

First public release of the repository in its final form. Earlier branches, tags and the prototype
package they contained were removed; this history starts here.

### Changed
- **The packaged default corpus is the guidebook's:** Table A-1 (69 organisations) and Table B-1 (125
  references), rebuilt from the final figure template (v8.6) by `tools/build_default_tables.py`. The
  default register has no file names, no earlier-run state, and empty exclusion and staging tables.
- The publication template is derived from the final figure template (v8.6).
- Dataset percentages use the number of documents in the run instead of a fixed corpus size.

### Added
- *Validate corpus register* proposes which published reference each unregistered PDF is
  (`suggested_doc_id`, `suggestion_score`), and writes the register with those file names filled in.
- Tests for the default corpus and the matcher.

### Removed
- Backend config tables, numbered wrapper scripts, protocol notes and example material from earlier
  corpus runs.

### Carried over from the 2.3 desktop runner
- CSV reference tables versioned with the tool, register validation, RDI template fill, byte-reproducible
  Figures 1 to 3, `run_manifest.json`, `--selftest`, and the Windows build (`build_windows.bat`, CI on
  `runner-v*` tags).
