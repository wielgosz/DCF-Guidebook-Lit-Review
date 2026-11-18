# Backend protocol scripts

The desktop runner (`protocol_engine/`) runs these standalone scripts in-process, one per stage.
They are not meant to be run by hand; the runner passes every input explicitly and records it in
`run_manifest.json`.

| Stage | Script | What it does |
|---|---|---|
| 02 | `freeze_extract_text_corpus.py` | extract and freeze each PDF's text layer (pypdf) |
| 03 | `validate_frozen_corpus.py` | text QA, and comparison with a reference run if one is given |
| 04 | `preflight_protocol_gate.py` | blocking checks before counting |
| 05 | `run_v13_keyword_counts_frozen.py` | keyword counts per document and term |
| 06 | `compare_keyword_matrix_to_baseline.py` | compare with a reference run's matrix (optional) |
| 07 | `run_v14_stageA_extract_dataset_mentions.py` | dataset mentions by seed pattern |
| 08 | `run_v14_stageB_canonicalize.py` | map mentions to the dataset registry |
| 09 | `run_v14_stageC_crosswalk.py` | dataset by document crosswalk |
| 10 | `run_v14_stageD_summary.py` | ranked dataset, provider and type summaries and charts |

## Keyword rule

All keyword counts use one rule: exact, case-insensitive regex matching with alphanumeric
boundaries, with variants rolled up to canonical terms. Table D-1 is a report-facing summary; the
executable dictionary is `reference_tables/keyword_dictionary.csv`.

## Percentages

Dataset percentages use the number of documents in the run as the denominator (`--n-docs`, passed by
the runner), not a fixed corpus size.

`config/frozen_text_protocol_params_v2_3.yml` holds the extraction and QA parameters.
