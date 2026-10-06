#!/usr/bin/env python3
"""
run_v20_full_protocol.py
========================

Single wrapper for the Supply Chain Data Review Protocol v2.0.

This wrapper executes the numbered dependency sequence 1-12. It is designed for
use from an IDE such as Anaconda/Spyder or from a terminal. Each stage also
exists as a standalone module so the workflow can be debugged step-by-step.

Typical use
-----------
1. Put uploaded PDF/ZIP batches in `data/input_batches/`.
2. Optionally pass --historical-v13 / reference files; comparison stages are
   skipped when no reference is supplied.
3. Run this wrapper. The desktop runner (protocol_engine.run_protocol) is the
   supported entry point; it reads all metadata from the input workbook.

The wrapper stops on the first hard failure unless `--continue-on-error` is set.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(stage: str, cmd: list[str], continue_on_error: bool = False) -> int:
    print("\n" + "=" * 80)
    print(stage)
    print(" ".join(cmd))
    print("=" * 80)
    rc = subprocess.call(cmd)
    if rc != 0 and not continue_on_error:
        raise SystemExit(f"{stage} failed with exit code {rc}")
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the full numbered Supply Chain Data Review Protocol v2.0 workflow.")
    ap.add_argument("--input-root", default="data/input_batches", help="Directory containing PDF and ZIP batches.")
    ap.add_argument("--out-root", default="outputs/v20_final", help="Output root for all stages.")
    ap.add_argument("--historical-v13", default="", help="Optional reference workbook (metadata, Text_Extraction_QA, Document_Term_Matrix).")
    ap.add_argument("--template", default="", help="Optional workbook to use as the base of the output workbook.")
    ap.add_argument("--c1-source", default="", help="Optional workbook/CSV with Table C1; default uses --registry directly.")
    ap.add_argument("--registry", default="config/dataset_canonical_registry_v1_5.csv")
    ap.add_argument("--c1-sheet", default="Table C1")
    ap.add_argument("--params", default="config/protocol_v2_0_params.yml")
    ap.add_argument("--dictionary", default="config/keyword_dictionary_v1_3.csv")
    ap.add_argument("--continue-on-error", action="store_true", help="Continue after a failed stage for diagnostic runs.")
    args = ap.parse_args()

    py = sys.executable
    out = Path(args.out_root)
    raw = out / "00_raw_pdfs"
    recon = out / "01_corpus_reconciliation"
    frozen = out / "02_frozen_text"
    validation = out / "03_validation"
    keyword = out / "05_keyword_outputs"
    dataset = out / "07_11_dataset_workflow"
    final = out / "12_final_package"

    run("01 Corpus Generation and Reconciliation", [py, "scripts/01_reconcile_corpus_v20.py", "--input-root", args.input_root, "--work-raw", str(raw), "--historical-v13", args.historical_v13, "--params", args.params, "--out", str(recon)], args.continue_on_error)
    corpus_manifest = recon / "v20_corpus_manifest.csv"

    run("02 Freeze extracted-text corpus", [py, "scripts/02_freeze_extract_text_corpus_v20.py", "--corpus", str(corpus_manifest), "--pdf-root", str(raw), "--out-root", str(frozen), "--params", args.params], args.continue_on_error)
    frozen_manifest = frozen / "frozen_text_manifest.csv"

    has_ref = bool(args.historical_v13) and Path(args.historical_v13).exists()
    run("03 Validate frozen corpus", [py, "scripts/validate_frozen_corpus.py", "--manifest", str(frozen_manifest), "--baseline", args.historical_v13 if has_ref else "", "--baseline-sheet", "Text_Extraction_QA", "--out", str(validation / "frozen_text_qa_report.csv"), "--params", args.params], args.continue_on_error)

    run("04 Preflight protocol gate", [py, "scripts/04_preflight_protocol_gate_v20.py", "--corpus", str(corpus_manifest), "--manifest", str(frozen_manifest), "--dictionary", args.dictionary, "--qa-report", str(validation / "frozen_text_qa_report.csv"), "--out", str(validation / "preflight_gate_report.csv"), "--params", args.params], args.continue_on_error)

    run("05 v1.3 keyword analysis from frozen text", [py, "scripts/05_run_v13_keyword_counts_frozen_v20.py", "--manifest", str(frozen_manifest), "--dictionary", args.dictionary, "--out", str(keyword), "--params", args.params, "--allow-warnings"], args.continue_on_error)

    if has_ref:
      run("06 Compare keyword matrix to v1.3 baseline", [py, "scripts/06_compare_keyword_matrix_to_baseline_v20.py", "--current", str(keyword / "Document_Term_Matrix.csv"), "--baseline", args.historical_v13, "--baseline-sheet", "Document_Term_Matrix", "--out-dir", str(validation / "matrix_comparison")], args.continue_on_error)

    registry = args.registry
    if args.c1_source:
        run("07 Normalize C1 registry and E1 subset", [py, "scripts/07_normalize_c1_registry_v20.py", "--c1-source", args.c1_source, "--sheet", args.c1_sheet, "--out-dir", str(dataset / "c1_normalized")], args.continue_on_error)
        registry = str(dataset / "c1_normalized" / "dataset_canonical_registry_v2_0.csv")

    run("08 v1.4 Stage A extract dataset mentions", [py, "scripts/08_run_v14_stageA_extract_dataset_mentions_v20.py", "--corpus", str(corpus_manifest), "--text-root", str(frozen / "text"), "--patterns", "config/dataset_extraction_patterns_v1_5.csv", "--out", str(dataset / "stageA")], args.continue_on_error)

    run("09 v1.4 Stage B canonicalize mentions", [py, "scripts/09_run_v14_stageB_canonicalize_v20.py", "--stageA", str(dataset / "stageA" / "Dataset_Mentions_Raw.csv"), "--registry", registry, "--crosswalk", "config/dataset_name_crosswalk_v1_5.csv", "--out", str(dataset / "stageB")], args.continue_on_error)

    run("10 v1.4 Stage C dataset-document crosswalk", [py, "scripts/10_run_v14_stageC_crosswalk_v20.py", "--stageB", str(dataset / "stageB" / "Dataset_Mentions_StageB_Mapped.csv"), "--out", str(dataset / "stageC")], args.continue_on_error)

    run("11 v1.4 Stage D summaries", [py, "scripts/11_run_v14_stageD_summary_v20.py", "--stageC", str(dataset / "stageC" / "Dataset_by_Document.csv"), "--out", str(dataset / "stageD")], args.continue_on_error)

    run("12 Build final output package", [py, "scripts/12_build_v20_output_package.py", "--template", args.template, "--corpus-manifest", str(corpus_manifest), "--keyword-dir", str(keyword), "--dataset-dir", str(dataset), "--qa-dir", str(validation), "--out-dir", str(final)], args.continue_on_error)

    print(f"\nProtocol v2.0 workflow completed. Final outputs: {final}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
