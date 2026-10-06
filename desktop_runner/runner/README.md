# Supply Chain Data Review — desktop runner (v2.3)

A Windows desktop app (and command line) that turns a folder of PDFs into the
review's tables and figures:

- a validated **corpus register** (Table B1: file name → doc_id → APA reference,
  with hyperlinks), plus proposed fixes;
- keyword counts (**Table D1**, Term Summary, document × term matrices);
- **Figures 1–3** (SVG + PNG, byte-reproducible);
- dataset-mention crosswalk (stages A–D);
- a filled copy of the **publication template** (RDI copy-edit format).

Everything the run reads is explicit and recorded, with SHA-256 hashes, in
`run_manifest.json`. Nothing is read from earlier runs or bundled snapshots.

## Inputs

| Input | Default | What it is |
|---|---|---|
| Reference tables folder | packaged `reference_tables/` | CSV tables — see below |
| PDF corpus folder | — (required) | PDFs and/or ZIPs of PDFs |
| Publication template | packaged `templates/Publication_Template.xlsx` | layout only; your own RDI template (e.g. FIGURE-TEMPLATE v8.0) also works |
| Figure style | packaged `templates/figure_style.yml` | colours, font, sizes for Figures 1–3 |
| Reference folder | none | `reference_snapshot/` of an accepted earlier run, for regression comparison |

### Reference tables (`reference_tables/`)

| File | Table |
|---|---|
| `B1_corpus_register.csv` | corpus register: file name → doc_id → title, year, org, URL, APA |
| `A1_organizations.csv` | publishing organisations |
| `keyword_dictionary.csv` | executable keyword dictionary (one search variant per row) |
| `exclusions_duplicates.csv` | PDFs to exclude, and duplicate → file to retain |
| `C1_dataset_registry.csv` | canonical dataset registry |
| `dataset_name_crosswalk.csv` | dataset mention string → dataset_id |
| `dataset_extraction_patterns.csv` | dataset mention seed patterns |
| `run_settings.csv` | run switches |
| `new_documents.csv` | staging area for PDFs not yet registered |
| `TABLES_VERSION.json`, `CHANGELOG.md` | version stamp and history |

CSV files are UTF-8 with BOM, so they open correctly in Excel.

### Versioning

The packaged tables are versioned with the tool: tool **2.3.0** ships tables
**2.30**; a corrected or extended register is released as tool **2.3.1** /
tables **2.31**. Each run reports either `packaged 2.31` or
`custom, based on 2.31` (an edited copy), with the list of edited files.

To release an updated edition after editing the packaged CSVs:

```bat
.venv\Scripts\python tools\release_tables.py --notes "Registered 5 PDFs added 2026-10-06"
```

A test fails if a packaged CSV changes without a release.

## Typical update: adding PDFs to the corpus

1. Put the new PDFs in the corpus folder.
2. **Validate corpus register** (GUI button, or `run_cli.bat --register-only ...`).
3. Open `01_corpus_register/Table_B1_Corpus_Register.xlsx`:
   *Unregistered PDFs* lists files to add; *Register* shows every row's status
   (OK / CHECK / ERROR) and issues; *Publication B1 check* compares against
   your template's Table B1.
4. `01_corpus_register/proposed_reference_tables/` holds
   `new_documents_proposed.csv` (stub rows with guessed title/year) and
   `B1_corpus_register_proposed.csv` (APA text updated to the template's
   revised wording). Complete the rows and copy them into your tables folder
   (or the packaged one, then release a new tables version).
5. Validate again until there are no ERROR rows, then **Run full protocol**.

ERROR rows block a full run (missing PDF, file listed as excluded, unknown
organisation, duplicate doc_id/file name, unreadable PDF). CHECK rows run but
should be reviewed: title not found on the PDF's first pages, title is just
the file name, APA year/title/URL disagreeing with the columns, duplicate
content, no text layer.

## Running

**Downloaded app:** unzip `SupplyChainDataReview-<version>-tables-<tables>-win64.zip`
and start `SupplyChainDataReview.exe`. Command line:
`SupplyChainDataReview.exe --cli --pdf-folder ... --output-folder ...`;
`--selftest` runs a built-in two-PDF end-to-end check; `--version`.

**From source:**

```bat
setup.bat
run_gui.bat
run_cli.bat --register-only --pdf-folder "C:\corpus" --output-folder "C:\runs"
run_cli.bat --pdf-folder "C:\corpus" --output-folder "C:\runs" --template "C:\FIGURE-TEMPLATE v8.0.xlsx"
```

**Build the download:** `build_windows.bat` (tests → PyInstaller → selftest of
the built .exe → zip). The `build-runner-exe` GitHub workflow does the same on
a `runner-vX.Y.Z` tag and attaches the zip to the release.

## Outputs

```
<output>/Supply_Chain_Data_Review_Output_<date_time>/
  run_manifest.json                 inputs + hashes, versions, stage results
  00_inputs/reference_tables/       exact copy of the tables used
  01_corpus_register/               Table_B1_Corpus_Register.xlsx, CSVs, proposed tables
  02_frozen_text/                   extracted text per document + manifest
  03_qa/                            text QA, preflight, D1_vs_template.csv, matrix comparison
  05_keyword_outputs/               D1_Key_Terms, Term_Summary, matrices
  07_dataset_workflow/              dataset stages A-D
  figures/                          Figures 1-3 (SVG + PNG)
  reference_snapshot/               use as the reference folder of a later run
  Supply_Chain_Data_Review_Results.xlsx
  Publication_Tables_<date_time>.xlsx
  logs/run.log
```

The publication pack refreshes Tables A1, B1, D1 and Figures 1–3 and leaves
every other tab (curated C1/E1, other figures) exactly as in the template; the
*Run Info* tab lists what was refreshed. Rows above each table header (the RDI
caption/source/copy-edit block) are never changed.

## Method notes

- Text extraction: pypdf (permissive licence; PyMuPDF/AGPL is not used).
- Matching: exact, case-insensitive, alphanumeric word boundaries; variants
  roll up to canonical terms (unchanged from protocol v1.3).
- Figures plot `reports_referencing`; Figure 1 excludes AOI terms.
- The published Table D1 and Figures 1–3 use the dictionary terms marked
  `include_in_visuals = yes`; the results workbook's *D1 all terms* sheet keeps
  every active term.
- The backend scripts in `protocol_v2_1/` run in-process (so the .exe works);
  the reference copy of the protocol lives in `/protocols/v2_1`.
