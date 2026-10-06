# Supply Chain Data Review Protocol v2.1

This package consolidates the PRISMA-S / DCF corpus workflow into a single, numbered, IDE-readable Python module sequence.

The package preserves the dependency logic established in v1.3, v1.4 and v1.5:

- **v1.3 keyword protocol** remains the authoritative keyword-count protocol.
- **v1.4 dataset protocol** remains the authoritative dataset mention/canonicalization/crosswalk protocol.
- **v1.5 frozen-text layer** is retained as the reproducibility and QA layer.
- **v2.0** is the integrated execution package and naming layer: corpus reconciliation -> frozen text -> keyword outputs -> dataset crosswalk -> final workbook/SVG/CSV package.

## Non-negotiable keyword rule

All keyword counts must use the v1.3 rule:

> exact, case-insensitive regex matching with alphanumeric boundaries, with variants/aliases rolled up to canonical terms.

Table D1 is a report-facing summary unless explicitly expanded. It must not replace `config/keyword_dictionary_v1_3.csv` as the executable dictionary.

## Numbered module sequence

1. `scripts/01_reconcile_corpus_v20.py`
2. `scripts/02_freeze_extract_text_corpus_v20.py`
3. `scripts/03_validate_frozen_corpus_v20.py`
4. `scripts/04_preflight_protocol_gate_v20.py`
5. `scripts/05_run_v13_keyword_counts_frozen_v20.py`
6. `scripts/06_compare_keyword_matrix_to_baseline_v20.py`
7. `scripts/07_normalize_c1_registry_v20.py`
8. `scripts/08_run_v14_stageA_extract_dataset_mentions_v20.py`
9. `scripts/09_run_v14_stageB_canonicalize_v20.py`
10. `scripts/10_run_v14_stageC_crosswalk_v20.py`
11. `scripts/11_run_v14_stageD_summary_v20.py`
12. `scripts/12_build_v20_output_package.py`

A wrapper is provided:

```bash
python scripts/run_v20_full_protocol.py \
  --input-root data/input_batches \
  --out-root outputs/v20_final \
  --historical-v13 outputs/reference_milestone/prisma_s_v13_complete_results_QA_metadata_visuals_2026-05-13.xlsx \
  --template <publication template .xlsx, optional>
```

For first execution, place uploaded Batch ZIPs/PDFs in `data/input_batches/`. The wrapper will use the numbered module sequence and will stop on hard QA failures.

## Outputs

The final package builder produces:

- Excel workbook based on the v2.0 output template with A1, B1, C1, D1, E1 and QA/output tabs.
- Figures 1, 2, and 3 as standalone SVGs.
- v1.3 keyword CSV outputs.
- v1.4 dataset crosswalk CSV outputs.
- corpus reconciliation and frozen-text QA reports.
- run manifest.


## Export-repair note
See `docs/protocol_v2_0_export_repairs.md` for the repaired Stage 12 workbook and SVG export behavior.


## Figure contract
The canonical figure outputs are `DCF_PRISMA_S_Figure_1_jurisdictional_terms.svg`, `DCF_PRISMA_S_Figure_2_supply_chain_terms.svg`, and `DCF_PRISMA_S_Figure_3_farm_level_terms.svg`. These figures use the `reports_referencing` metric. Figure 1 excludes AOI terms and is limited to jurisdictional / landscape terms.


## v2.1 release highlights
- Canonical SVG outputs only, with axes only and unnumbered titles.
- Figures 1-3 plot `reports_referencing`; Figure 1 excludes AOI terms.
- Output workbook simplified toward the v1.3 tabular style.
- APA references added for the two newly uploaded corpus additions (RTRS and ECF).
