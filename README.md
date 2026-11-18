# Supply Chain Data Review

A Windows desktop app (and command line) that turns a folder of PDFs into the tables and figures
of the literature review in the guidebook *Navigating data for deforestation and conversion free
(DCF) supply chain analyses: applied learnings from soy in Brazil* (World Resources Institute, 2026).
It implements the guidebook's PRISMA-S-aligned method (Appendix D): a validated corpus register,
keyword counts (Table D-1 and Figures 1 to 3), a dataset-mention crosswalk, and a filled copy of the
publication template.

Everything a run reads is explicit and recorded, with SHA-256 hashes, in `run_manifest.json`.

## Get it

- **Windows download:** the zip on the [Releases](https://github.com/wielgosz/DCF-Guidebook-Lit-Review/releases)
  page. Unzip it and start `SupplyChainDataReview.exe`.
- **From source:** `desktop_runner/runner/` holds the code. `setup.bat` creates a virtual environment,
  `run_gui.bat` starts the app. Python 3.12 on Windows.
- **Build the download yourself:** `desktop_runner/runner/build_windows.bat` runs the tests, builds with
  PyInstaller, self-tests the built `.exe` and zips it.

Full instructions, inputs, outputs and the update workflow are in
[`desktop_runner/runner/README.md`](desktop_runner/runner/README.md).

## The default corpus is the published one

The tool ships with the corpus printed in the guidebook, and nothing else:

| Table | Content | Rows |
|---|---|---|
| A-1 | organisations that publish sectoral guidance, with websites | 69 |
| B-1 | the sectoral guidance documents reviewed, as APA references | 125 |
| D-1 | key terms: the executable dictionary has 98 canonical terms, 44 of them printed in Table D-1 | 98 terms |

The packaged register has **no PDF file names**, because the tool does not redistribute the PDFs.
Point it at your own folder of PDFs and *Validate corpus register* proposes which published reference
each PDF is, from the title words on its first pages; you confirm and save your own copy of the tables.
Your register and any custom tables stay on your machine.

## Related resources

- [DCF-Guidebook-STAC](https://github.com/wielgosz/DCF-Guidebook-STAC): the guidebook's dataset review
  (Table C-1) as a STAC catalogue.
- [DCF-Guidebook-BR-Legal-Reserve-Ratios](https://github.com/wielgosz/DCF-Guidebook-BR-Legal-Reserve-Ratios):
  Appendix F (Table F-1) as a machine-readable table.

## Licence and citation

Code: MIT ([LICENSE](LICENSE)). Derived reference tables: CC BY 4.0
([LICENSE-CC-BY-4.0.txt](LICENSE-CC-BY-4.0.txt)), subject to the guidebook's own licence, which is pending;
see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Cite the guidebook and this software using
[CITATION.cff](CITATION.cff).
