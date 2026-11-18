# Third-Party Notices

This file inventories third-party software and data used by the Supply Chain Data Review desktop
tool. Inclusion here does not replace the original licence terms. Machine-readable detail is in
[`DEPENDENCY_LICENSES.csv`](DEPENDENCY_LICENSES.csv).

## Runtime dependencies

Every runtime dependency is permissively licensed (no copyleft, no network copyleft). The tool does
not use PyMuPDF (AGPL-3.0); a CI step fails the build if it is installed.

| Component | Source | Licence | How used |
|---|---|---|---|
| pandas | https://github.com/pandas-dev/pandas | BSD-3-Clause | dataframes, Excel output |
| openpyxl | https://foss.heptapod.net/openpyxl/openpyxl | MIT | `.xlsx` reading and writing |
| pypdf | https://github.com/py-pdf/pypdf | BSD-3-Clause | PDF text-layer extraction |
| matplotlib | https://github.com/matplotlib/matplotlib | Matplotlib licence (BSD-style, PSF-based) | Figures 1-3 and dataset charts (Agg backend) |
| PyYAML | https://github.com/yaml/pyyaml | MIT | figure style file |

## Build and test dependencies

| Component | Licence |
|---|---|
| pytest | MIT |
| pyinstaller *(Windows build only)* | GPL-2.0-or-later **with a bundling exception**: the exception permits distributing the frozen application under the application's own licence; PyInstaller itself is not redistributed |

## Inputs derived from the guidebook

The reference tables shipped with the tool come from the guidebook:

> Wielgosz, B., dos Santos, A. B., Carter, S., Berger, A., Schneider, M., Despontin, M., Immelman, J.,
> Richter, J., Couto, A., Fitts, L. A., Gao, Y., & Dionizio, E. (2026). *Navigating data for
> deforestation and conversion free (DCF) supply chain analyses: applied learnings from soy in
> Brazil*. World Resources Institute.

- `A1_organizations.csv` and `B1_corpus_register.csv` reproduce Tables A-1 and B-1 (organisations,
  websites and the APA reference list), which are bibliographic facts.
- `keyword_dictionary.csv` is the executable form of the key terms in Table D-1.
- `C1_dataset_registry.csv`, `dataset_name_crosswalk.csv` and `dataset_extraction_patterns.csv`
  support the dataset-mention stages (Table C-1).
- `templates/Publication_Template.xlsx` keeps the layout of WRI's figure template (header block and
  table headers) with all data removed.

WRI's standard licences are CC BY 4.0 for data and publications and MIT for code
([Open Data Commitment](https://www.wri.org/data/open-data-commitment)). Its
[Permissions & Licensing](https://www.wri.org/research/permissions-licensing) policy notes that
co-authored publications are frequently marked "All Rights Reserved". The licence of the guidebook
itself is therefore treated as pending until its wri.org page states one. The software is MIT
licensed (see `LICENSE`); the derived tables are offered under CC BY 4.0
(see `LICENSE-CC-BY-4.0.txt`) subject to that caveat. Attribution: credit the guidebook as shown on
its wri.org page, link to it, and state that modifications were made.
