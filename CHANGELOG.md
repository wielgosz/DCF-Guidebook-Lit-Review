# Changelog

All notable changes to this project will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Desktop runner 2.3.0] - 2026-10-06

Applies to `desktop_runner/runner/` only; the `prisma_s` package is unchanged.

### Changed - BREAKING
- **Reference tables are CSV files** in `desktop_runner/runner/reference_tables/`
  (A1, B1 corpus register, keyword dictionary, exclusions, C1 dataset registry,
  crosswalk, extraction patterns, run settings), versioned with the tool
  (tables 2.30 = tool 2.3.0) via `TABLES_VERSION.json`. The Excel input
  workbook (`Supply_Chain_Data_Review_Input_Template_v2_2.xlsx`) is removed.
- **No baseline workbook dependency.** The v1.3 results workbook under
  `outputs/reference_milestone/` (never in git) is no longer required; text and
  matrix comparisons run only against an explicit reference folder.
- **Bundled example snapshots removed** from the runner
  (`desktop_runner/runner/protocol_v2_1/examples/`), including the figure
  templates that step 07 read as a data source.
- Text extraction uses **pypdf** (pinned as in the package); PyMuPDF is no
  longer a runner dependency.
- Backend stages run **in-process**, so the PyInstaller build works.

### Added
- Corpus register validation (`--register-only` / "Validate corpus register"):
  file presence, exclusions, duplicates, organisations, APA year/title/URL
  consistency, title-on-PDF check, optional link check, reconciliation with a
  publication template's Table B1, and proposed corrected tables.
- Publication template filling with the RDI header block preserved; generic
  template derived from the RDI format; D1 vs template comparison.
- Figures 1-3 from a YAML style file (`templates/figure_style.yml`),
  byte-reproducible SVG + PNG.
- `run_manifest.json` with SHA-256 of every input and figure.
- `--selftest`, tests, `build_windows.bat`, `setup.bat`, `run_gui.bat`,
  `run_cli.bat`, PyInstaller spec, `build-runner-exe` workflow.

### Fixed
- Windows: per-document extraction timeout no longer uses POSIX-only SIGALRM.
- Dataset stage A read the `pattern_type` column instead of `pattern`; stage B
  joined on `dataset_id` where the v1.5 crosswalk uses `mapped_dataset_id`;
  stage A page numbers ignored the page-break marker.
- Keyword counting no longer refuses a dictionary whose active term count is
  not 98 unless a count is configured.
- Multi-organisation `publishing_org_id` values (`ORG-047; ORG-035`) validate.

## [1.6.0] - 2026-09-02

### Changed - BREAKING
- **PyMuPDF is removed.** PyMuPDF is AGPL-3.0; dropping it makes every runtime
  dependency permissively licensed (BSD / MIT / Apache-2.0 / PSF) and unblocks a
  clean MIT executable.
  - the `fast-pdf` and `ocr` optional-dependency groups are deleted;
  - PDF text extraction is **pypdf-only** - no OCR rung, no second PDF library,
    no per-document escalation. `prisma_s.extract` loses `_extract_pdf_pymupdf`,
    `_ocr_*`, `_HAVE_FITZ`, `_pdf_library_rungs`;
  - `run_analysis()` loses `enable_ocr` / `ocr_lang`; the CLI loses `--no-ocr` /
    `--ocr-lang`; the GUI loses the Enable-OCR controls;
  - a document with an empty or thin text layer is **flagged**, not repaired:
    `Run_Metadata` column `Escalated` -> `Needs OCR`; statuses are
    `"no text layer - OCR externally and re-run"` / `"thin text - verify
    extraction"`; `run_metadata.json` drops `ocr_enabled` / `ocr_available` /
    `escalated_documents` and adds `documents_needing_ocr`.
  - **Scanned / image-only PDFs must be OCR'd with an external tool (e.g.
    `ocrmypdf`) before analysis.**

### Added
- `prisma-s-gui` - a Tkinter desktop GUI over `run_analysis`: pick a corpus
  (local folder, file/zip, or Google Drive), an output folder, a keyword
  dictionary, and the figure / citation toggles, then watch the log. Ships with
  the pip package; also the front-end of the standalone Windows executable.
- `desktop/` - a PyInstaller `--onedir` build (`desktop/build_exe.ps1`,
  `desktop/prisma-s.spec`) with no copyleft components, plus
  `desktop/build-exe.workflow.yml` (a GitHub Actions workflow, kept outside
  `.github/` - see `desktop/README.md`) that attaches the zipped build to a
  `v*` tag's Release. The build script adapts to any Windows Python distro
  (python.org, pyenv-win, Miniconda/Anaconda): it probes the chosen interpreter
  for its native DLL directories (`desktop/_pyenv_probe.py`) so `_ctypes` /
  `_bz2` / `_tkinter` resolve wherever the distro puts `ffi.dll` etc., then runs
  `prisma-s selftest` inside the finished bundle - a missing DLL fails the build
  with the DLL named, not the user's first launch.
- `prisma-s selftest` - an undocumented subcommand that imports every runtime
  dependency and renders a figure; used by the desktop build verification.
- WRI data-policy / provenance files: `THIRD_PARTY_NOTICES.md`,
  `DEPENDENCY_LICENSES.csv`, `DATA_PROVENANCE.csv`.

### Changed
- `prisma_s/data/DATA_LICENSE.md` no longer asserts CC BY 4.0 over the
  WRI-guidebook-derived `keyword_dictionary_v1.3.csv` and protocol specs - their
  licence is **pending** confirmation of the guidebook's own licence on
  publication (co-authored WRI publications are frequently All Rights Reserved).
  Only the project's own `keyword_dictionary_v1.1.csv`, `citation/*.md`,
  generated figures and `docs/` remain CC BY 4.0.
- `citation/{en,pt_br,es}.md` gain a "Data & attribution policy" section
  (WRI Open Data Commitment / Permissions & Licensing / Data Platforms ToS, and
  the "state that modifications were made" requirement).
- `install.ps1` verifies a candidate interpreter by **building a throwaway
  venv**, instead of rejecting it because its path string contained "QGIS" or
  "WindowsApps".
- **`pypdf` is now pinned to a narrow range (`>=6.17,<6.18`), not just a
  floor.** Confirmed by direct comparison (desktop `.exe` build vs. a pip
  install done at a different time): pypdf 6.16.2 vs. 6.17.0 extracted exactly
  one different word/character on 2 of 136 real corpus documents. Every
  keyword count (`Long_AllTerms`, `Term_Summary`, `D1_Key_Terms`) was
  unaffected - the drift landed only in `Run_Metadata`'s diagnostic
  `Words`/`Chars` columns. See README.md "A note on the pypdf dependency".

---

## [1.5.0] - 2026-09-01

### Changed - BREAKING
- **The default keyword dictionary is now the v1.3 canonicalization registry**
  (`prisma_s/data/keyword_dictionary_v1.3.csv`, 98 canonical terms). Many
  explicit `search_variant`s roll up to one `canonical_term`; a document's count
  for a canonical term is the sum of its variant counts. `--keywords bundled:1.1`
  restores the flat v1.1 dictionary and the exact v1.4 output.
- Registry-mode output: `Long_AllTerms` is now one row per (document x canonical
  term) with `Category`, `Term ID`, `Canonical Term`, `Variants Included`,
  `Variant Counts`, `Referenced`; new sheets `Term_Summary`, `D1_Key_Terms`
  (report-ready, ranked by document frequency within category, filtered to
  `include_in_visuals` terms with at least one referencing document) and
  `Zero_Reference_Terms`. `Protocol Version` is stamped `1.3`.
- Registry mode normalises each document's text first (NFC, LF line endings,
  trailing-whitespace strip - `prisma_s/normalize.py`) and matches each variant
  with a strict single literal space between words, mirroring the published
  protocol. Flat (v1.1) mode is byte-identical to v1.4.
- `matplotlib` is now a core dependency.

### Added
- **Term-frequency figures** (`prisma_s/figures.py`), on by default
  (`--no-figures` to skip), written to `<output>/figures/` as SVG **and** PNG.
  When the three canonical categories are present the guidebook's three figures
  are produced with their legacy `DCF_PRISMA_S_Figure_{1,2,3}_*` filenames
  (amber `#F0B310`, shared x-scale, ranked by document frequency); otherwise one
  figure per category.
- `--keywords bundled:1.1` / `bundled:1.3` selectors.
- `run_metadata.json`: `dictionary_mode`, `n_canonical_terms`, `n_variants`,
  `figures`.
- Bundled `prisma_s/data/PRISMA_keyword_protocol_v1.3.md`.

### Deferred to 1.6
- Tkinter folder/file pickers + wizard `RunConfig` refactor; `prisma-s template`;
  dated run-output folders.

---

## [1.4.0] - 2026-08-31

### Fixed (correctness)
- A user keyword CSV saved from Excel (byte-order mark, capitalised headers, or
  `term,group` column order) is now parsed correctly. A CSV with no `term`
  column, or that yields zero terms, raises `ValueError` instead of silently
  writing an empty workbook. `category` is accepted as a synonym for `group`.
- An empty run (no documents, all extractions failed) no longer produces a
  `(0, 0)` DataFrame; the frame always has the documented columns, and
  `run_analysis` raises with an actionable message when there is nothing to do.
- Matching now uses **alphanumeric boundaries** (`(?<![A-Za-z0-9]) ... (?![A-Za-z0-9])`)
  instead of `\b`: terms that start or end with punctuation (`(CO2)`, `+ve`)
  match, `_` is treated as a separator, and multi-word phrases tolerate a
  hyphenated line break between words. A term listed under two groups is now
  counted under each rather than silently dropped.
- `guess_year` takes the first-page text year first and the document metadata
  date only as a fallback (matching the protocol spec); returns `None` when
  absent, so the `Year` column is a single nullable `Int64` dtype.
- `.zip` input no longer leaks a full corpus copy into the temp directory;
  `__MACOSX/` and `._*` entries are ignored.
- The `PRISMA-S_Compliance` sheet no longer contains statements that are false
  at runtime: it references the real `Run_Metadata` sheet, and the multi-lingual
  note is formatted from the dictionary version actually used.
- The compliance document count is the number of documents **processed**, not
  discovered.
- `token.json` (Drive OAuth) is written `0600`; a failed token refresh falls
  back to interactive consent instead of aborting the run.

### Added
- `Run_Metadata` sheet + `run_metadata.json`: per-document extraction backend,
  page / word / character counts, and status; run-level discovered / processed /
  skipped totals. This is the artifact for checking extraction completeness.
- `prisma-s cite [--lang en|pt-br|es|all]` in English, Brazilian Portuguese,
  and Spanish; the block
  is printed when a run finishes (suppress with `--no-citation`) and written to
  `HOW_TO_CITE.txt` beside the results.
- `LICENSE` (MIT, code), `LICENSE-CC-BY-4.0.txt` + `prisma_s/data/DATA_LICENSE.md`
  (CC BY 4.0 for the dictionary, protocol spec, figures, and docs), and
  `CITATION.cff` with the associated WRI guidebook as the preferred citation.
- `docs/USAGE.md` and `docs/METHOD.md` (each protocol rule paired with its code);
  `prisma_s/py.typed`.
- Regression tests: `test_keywords.py`, `test_runner.py`, `test_extract.py`,
  `test_cli.py`, `test_cite.py`, and additions to `test_search.py`; synthetic
  multi-page PDF fixtures via `reportlab` (dev extra). `--doctest-modules` on.

### Changed
- **PDF extraction is now a per-document escalation chain.** A light PDF
  library runs first; the other PDF library is tried only for documents that
  come back with no text or fewer than ~40 words per page (the richer result
  is kept); an OCR rung (PyMuPDF + Tesseract, `[ocr]` extra, `--no-ocr` to
  disable, `--ocr-lang` to set the language) runs only for documents still
  textless. `Run_Metadata` gains an `Escalated` column and the chain trace in
  `Status`; `run_metadata.json` gains `backend_counts` / `escalated_documents`
  / `textless_documents`.
- **Default PDF backend is now pypdf** (BSD). PyMuPDF (AGPL-3.0) moves to an
  optional extra: `pip install "prisma-s-lit-review[fast-pdf]"`. The backend
  used is recorded per document.
- Dependency bounds added (`pandas>=2.0,<3`, `openpyxl>=3.1,<4`); 3.13 classifier
  added.
- `prisma_s/__init__.py` no longer imports pandas at import time (`run_analysis`
  is a lazy re-export); `__version__` / `PROTOCOL_VERSION` moved to a
  dependency-free `prisma_s/_version.py`.
- Version 1.4.0.

### Removed
- `scripts/keyword_corpus_analysis.py` — a pre-package monolith that duplicated
  the extraction / matching logic and carried a third copy of the keyword list.

### Deferred to 1.5
- Term-frequency figures (port of the desktop-runner SVG spec), the v1.3
  canonicalization dictionary (variant roll-up) as the default, Tkinter folder
  pickers, `prisma-s template`, dated run-output folders.

---

## [1.3.0] - 2026-08-31

### Fixed
- `prisma-s run` with no `--keywords` no longer crashes with `No such file or directory: .../keywords/keyword_dictionary_v1.1.csv`. The bundled dictionary and the locked protocol spec now ship inside the package at `prisma_s/data/` and are resolved with `importlib.resources`.
- Console output is forced to UTF-8 at CLI start-up, fixing `'charmap' codec can't encode character` on legacy Windows code pages (the `->` in the run summary, the wizard's rule characters) and making accented keyword dictionaries (Portuguese, Spanish) safe to print.
- `git clone` on Windows no longer fails with "Filename too long": paths under `desktop_runner/` and `protocols/` were shortened (longest 161 -> 106 chars) and the redundant 11 MB `archive_zips/` was removed.

### Added
- `install.ps1` / `install.sh` - locate a usable Python (skipping broken embedded interpreters), build a virtual environment at a short stable path, and install the package.
- `INSTALL.md` with install and troubleshooting guidance; `.gitattributes` pinning shell-script line endings.

### Changed
- Package version unified at 1.3.0 and sourced from `prisma_s.__version__` via `[tool.setuptools.dynamic]` (was `pyproject` 1.1.0 vs package 1.2.0).
- `README.md` now leads with the installable package; the Supply Chain Data Review Protocol / Desktop Runner material moved to a separate section.

---

## [1.2.0] — 2026-03-17

### Added
- `prisma-s wizard` — interactive CLI that prompts for search terms, source
  location (Drive URL or local path), batch ID, and output folder before running
- `prisma_s/wizard.py` — full wizard implementation with step-by-step prompts;
  supports manual term entry, bundled dictionary, or custom CSV
- `prisma_s/compliance.py` — full PRISMA-S 16-item checklist (Rethlefsen et al.
  2021; https://doi.org/10.1186/s13643-020-01542-z) with per-item status
  (APPLIED / PARTIAL / NOT_APPLICABLE / NOT_APPLIED) and runtime-injected notes
- Second Excel sheet `PRISMA-S_Compliance` written to every output workbook —
  documents which PRISMA-S search reporting items were addressed and which were not
- `drive.parse_folder_id()` — accepts full Drive folder URLs
  (`https://drive.google.com/drive/folders/...`) in addition to bare folder IDs,
  in both `prisma-s wizard` and `prisma-s run --drive-folder`
- Comprehensive package-level docstring in `prisma_s/__init__.py` referencing
  the PRISMA-S statement and linking to all submodules

### Changed
- Package version bumped to 1.2.0
- `prisma-s run --drive-folder` now accepts full Drive URLs as well as folder IDs
- README updated with `prisma-s wizard` as the recommended entry point

---

## [1.1.0] — 2026-03-17

### Added
- `prisma_s` installable Python package with CLI (`prisma-s run`)
- Google Drive integration — download PDFs and DOCX files from a Drive folder by folder ID
- DOCX support via `python-docx` (previously PDF-only)
- Keyword dictionary loaded from versioned CSV (`keywords/keyword_dictionary_v1.1.csv`) — no longer hardcoded
- Reproducibility columns in every output row: `Protocol Version`, `Keyword Dict Version`, `Run UTC`, `Source Ref`
- `Group` column in output (AOI / Commodity / Supply Chain Node)
- `pyproject.toml` for pip-installable packaging
- Test suite (`tests/test_search.py`) encoding all PRISMA-S protocol matching rules
- Comprehensive README with Google Drive setup guide and replication instructions

### Changed
- Output columns extended: `Group` added; reproducibility metadata columns added
- Package now reads keyword dictionary from CSV rather than a hardcoded list

### Retained
- `scripts/keyword_corpus_analysis.py` — original standalone script kept for reference

---

## [1.0.0] — 2026-03-16

### Added
- Initial standalone script `keyword_corpus_analysis.py`
- Hardcoded 120-term keyword list across AOI, Commodity, and Supply Chain Node groups
- PDF text extraction via PyMuPDF with PyPDF2 fallback
- Batch processing from local directory, single file, or ZIP archive
- Long-format Excel output: Batch, Document Name, Title, Year, Term, Count
- Title and year metadata extraction from PDF metadata and first-page text
- PRISMA-S Keyword Protocol v1.1 specification document
- Keyword dictionary CSV `keyword_dictionary_v1.1.csv`
