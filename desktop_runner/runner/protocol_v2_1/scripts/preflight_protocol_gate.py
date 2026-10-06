#!/usr/bin/env python3
"""Blocking preflight gate for v1.5 frozen-corpus keyword runs."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml


def main() -> int:
    ap = argparse.ArgumentParser(description="Check that v1.5 inputs are ready for a protocol-valid v1.3 keyword run.")
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--dictionary", required=True)
    ap.add_argument("--qa-report", required=False)
    ap.add_argument("--params", default="config/frozen_text_protocol_params_v1_5.yml")
    ap.add_argument("--out", required=True)
    ap.add_argument("--expected-terms", type=int, default=None, help="Expected active canonical term count; overrides params. Omit both to skip the check.")
    args = ap.parse_args()

    params = yaml.safe_load(Path(args.params).read_text(encoding="utf-8")) if Path(args.params).exists() else {}
    blocking_statuses = set(params.get("qa_thresholds", {}).get("block_on_unresolved_statuses", []))
    expected_terms = args.expected_terms if args.expected_terms is not None else params.get("keyword_counting", {}).get("active_dictionary_terms_expected")
    expected_rule = params.get("keyword_counting", {}).get("matching_rule", "exact_case_insensitive_regex_with_alphanumeric_boundaries")

    checks = []
    def add(check, passed, detail=""):
        checks.append({"check": check, "passed": bool(passed), "detail": detail})

    corpus = pd.read_csv(args.corpus)
    manifest = pd.read_csv(args.manifest)
    dictionary = pd.read_csv(args.dictionary)

    add("frozen_manifest_exists", Path(args.manifest).exists(), args.manifest)
    add("dictionary_exists", Path(args.dictionary).exists(), args.dictionary)
    active = dictionary[dictionary.get("active", "yes").fillna("yes").astype(str).str.lower().eq("yes")]
    term_col = "canonical_term" if "canonical_term" in active.columns else "term"
    active_terms = active[term_col].dropna().astype(str).nunique()
    if expected_terms is not None:
        add("active_dictionary_term_count_matches_expected", active_terms == int(expected_terms), f"actual={active_terms}; expected={expected_terms}")
    else:
        add("active_dictionary_term_count_recorded", active_terms > 0, f"actual={active_terms}; no expected count configured")
    add("matching_rule_declared", expected_rule == "exact_case_insensitive_regex_with_alphanumeric_boundaries", expected_rule)

    if "status" in manifest.columns:
        unresolved = manifest[manifest["status"].isin(blocking_statuses)]
        add("no_blocking_extraction_statuses", len(unresolved) == 0, f"blocking_rows={len(unresolved)}")
    else:
        add("manifest_has_status_column", False, "missing status column")
    for col in ["doc_id", "text_path", "normalized_text_sha256", "char_count", "page_count"]:
        add(f"manifest_has_{col}", col in manifest.columns, "")
    if "text_path" in manifest.columns:
        missing_text = [p for p in manifest["text_path"].fillna("").astype(str) if not p or not Path(p).exists()]
        add("all_frozen_text_files_exist", len(missing_text) == 0, f"missing_text_files={len(missing_text)}")

    if args.qa_report:
        qa = pd.read_csv(args.qa_report)
        if "blocking_qa" in qa.columns:
            blocking_qa = qa[qa["blocking_qa"].fillna(False).astype(bool)]
            add("no_blocking_text_extraction_qa", len(blocking_qa) == 0, f"blocking_qa_rows={len(blocking_qa)}")
        else:
            add("qa_report_has_blocking_column", False, "missing blocking_qa column")

    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(checks).to_csv(out, index=False)
    failed = [c for c in checks if not c["passed"]]
    print(f"Preflight gate report written: {out}")
    print(f"Checks: {len(checks)}; failed: {len(failed)}")
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
