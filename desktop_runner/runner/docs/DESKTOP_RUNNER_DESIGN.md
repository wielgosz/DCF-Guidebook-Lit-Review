# Desktop runner design (v2.3)

## Principles

1. **Explicit inputs only.** A run reads a reference-tables folder (CSV), a
   PDF folder, a publication template, a figure style file and, optionally, a
   reference folder. All are hashed into `run_manifest.json`; the tables used
   are copied into `00_inputs/`. No earlier outputs, example snapshots or
   baseline workbooks are read. (v2.2 required a v1.3 results workbook that was
   not in git and was being restored from an archive of another repo; that
   dependency is gone.)
2. **Tables as tables.** Reference data lives in versioned CSV files, not in
   tabs of an uploaded workbook. Excel is used only for presentation: the
   publication template.
3. **Versioned with the tool.** Packaged tables carry `TABLES_VERSION.json`
   (version = tool `MAJOR.MINOR` + patch digit, e.g. 2.31) with per-file
   hashes, so a run states whether it used packaged tables unchanged or an
   edited copy.
4. **Presentation is separate from data.** The publication template keeps the
   RDI copy-edit format (header block rows, figure anchors, table header rows);
   the runner fills a copy and only refreshes tabs it computed. Figures are
   rendered by matplotlib from a YAML style file and are byte-reproducible.
5. **Same code from source and as an .exe.** Backend stage scripts run
   in-process (`stage_host.run_script` via `runpy`), never through
   `sys.executable`, which is the .exe itself in a PyInstaller build.

## Modules

| Module | Role |
|---|---|
| `reference_tables.py` | read/validate the CSV tables, snapshot them, make an editable copy |
| `tables_version.py` | tables version scheme, hash check, run label |
| `corpus_register.py` | validate B1 against PDFs, APA text, PDF first pages, template B1; write register workbook and proposed tables |
| `stage_host.py` | run a backend script in-process with streamed output |
| `run_protocol.py` | orchestration, run manifest, results workbook, CLI |
| `figures.py` | Figures 1-3 from `figure_style.yml` |
| `publication_pack.py` | fill a copy of the publication template; D1 vs template comparison |
| `selftest.py` | two-PDF end-to-end check used by tests, CI and `--selftest` |

## Stage order

01 register → 02 frozen text (pypdf) → 03 text QA → 04 preflight → 05 keyword
counts → 06 matrix comparison (reference only) → 07-10 dataset stages A-D
(non-blocking) → 11 results and figures → 12 publication pack.

ERROR rows in the register, structural table errors, blocking extraction
statuses and a failed preflight stop the run; everything else is recorded and
the run continues.
