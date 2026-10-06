#!/usr/bin/env python3
"""Run PRISMA-S v1.3 keyword counts from frozen text only.

This script implements the required v1.3 rule: exact, case-insensitive regex
matching with alphanumeric boundaries, with dictionary variants rolled up to
canonical terms. It refuses to re-extract PDFs.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd
import yaml

MATCHING_RULE = "exact_case_insensitive_regex_with_alphanumeric_boundaries"


def compile_variant_pattern(variant: str) -> re.Pattern:
    escaped = re.escape(str(variant))
    # Alphanumeric boundaries: prevent matching inside longer alphanumeric tokens.
    # Underscore is treated as a word character by \w, so use explicit A-Za-z0-9.
    pattern = rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])"
    return re.compile(pattern, flags=re.IGNORECASE)


def count_variant(text: str, variant: str) -> int:
    if variant is None:
        return 0
    variant = str(variant).strip()
    if not variant or variant.lower() == "nan":
        return 0
    return len(compile_variant_pattern(variant).findall(text))


def load_frozen_text(row: pd.Series) -> str:
    for col in ["text_path", "normalized_text_path"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            p = Path(str(row[col]).strip())
            if p.exists():
                return p.read_text(encoding="utf-8", errors="ignore")
    raise FileNotFoundError(f"No frozen text file found for doc_id={row.get('doc_id', '')}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run v1.3 keyword counts from a frozen extracted-text corpus.")
    ap.add_argument("--manifest", required=True, help="Frozen text manifest CSV.")
    ap.add_argument("--dictionary", required=True, help="v1.3 executable keyword dictionary CSV.")
    ap.add_argument("--out", required=True, help="Output directory.")
    ap.add_argument("--params", default="config/frozen_text_protocol_params_v1_5.yml")
    ap.add_argument("--allow-warnings", action="store_true", help="Allow EXTRACTED_WITH_WARNINGS rows; blocking statuses still fail.")
    args = ap.parse_args()

    params = yaml.safe_load(Path(args.params).read_text(encoding="utf-8")) if Path(args.params).exists() else {}
    # Enforced only when the params file pins a count (v1.5 params pin 98).
    expected_terms = params.get("keyword_counting", {}).get("active_dictionary_terms_expected")
    declared_rule = params.get("keyword_counting", {}).get("matching_rule", MATCHING_RULE)
    if declared_rule != MATCHING_RULE:
        raise SystemExit(f"Refusing run: params matching_rule={declared_rule!r}; required={MATCHING_RULE!r}")

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(args.manifest)
    blocking = manifest[manifest.get("status", "").isin(["EXTRACTION_TIMEOUT", "EXTRACTION_ERROR", "MISSING_PDF", "EMPTY_TEXT", "MISSING_TEXT_ARTIFACT"])]
    if len(blocking):
        blocking.to_csv(out / "blocking_extraction_rows.csv", index=False)
        raise SystemExit(f"Refusing keyword run: {len(blocking)} blocking extraction rows. See blocking_extraction_rows.csv")

    dictionary = pd.read_csv(args.dictionary)
    if "active" in dictionary.columns:
        dictionary = dictionary[dictionary["active"].fillna("yes").astype(str).str.lower().eq("yes")]
    term_col = "canonical_term" if "canonical_term" in dictionary.columns else "term"
    variant_col = "search_variant" if "search_variant" in dictionary.columns else "variant"
    active_terms = dictionary[term_col].dropna().astype(str).nunique()
    if expected_terms is not None and active_terms != int(expected_terms):
        raise SystemExit(f"Refusing run: active canonical terms={active_terms}; expected v1.3={expected_terms}")

    count_rows = []
    matrix_rows = []
    grouped = list(dictionary.groupby([c for c in ["category", "term_id", term_col] if c in dictionary.columns], dropna=False))
    for _, doc in manifest.iterrows():
        text = load_frozen_text(doc)
        matrix_record = {
            "doc_id": doc.get("doc_id", ""),
            "previous_doc_id": doc.get("previous_doc_id", ""),
            "file_name": doc.get("file_name", ""),
            "title": doc.get("title", ""),
            "year": doc.get("year", ""),
        }
        for group_key, grp in grouped:
            if not isinstance(group_key, tuple):
                group_key = (group_key,)
            category = group_key[0] if "category" in dictionary.columns else ""
            term_id = group_key[1] if "term_id" in dictionary.columns else ""
            term = group_key[-1]
            variants = grp[variant_col].dropna().astype(str).tolist()
            variant_counts = {v: count_variant(text, v) for v in variants}
            total = int(sum(variant_counts.values()))
            count_rows.append({
                "doc_id": doc.get("doc_id", ""),
                "previous_doc_id": doc.get("previous_doc_id", ""),
                "file_name": doc.get("file_name", ""),
                "title": doc.get("title", ""),
                "year": doc.get("year", ""),
                "category": category,
                "term_id": term_id,
                "term": term,
                "variants_included": "; ".join(variants),
                "variant_counts_json": json.dumps(variant_counts, ensure_ascii=False, sort_keys=True),
                "count": total,
                "referenced": 1 if total > 0 else 0,
            })
            matrix_record[str(term)] = total
        matrix_rows.append(matrix_record)

    counts = pd.DataFrame(count_rows)
    matrix = pd.DataFrame(matrix_rows)
    denom = counts["doc_id"].nunique()
    term_summary = (counts.groupby(["category", "term_id", "term", "variants_included"], dropna=False)
                    .agg(reports_referencing=("referenced", "sum"), total_occurrences=("count", "sum"))
                    .reset_index())
    term_summary["percent_of_corpus_docs"] = term_summary["reports_referencing"] / max(denom, 1)
    zero = term_summary[term_summary["reports_referencing"] == 0].copy()
    d1 = term_summary[term_summary["reports_referencing"] > 0].copy()
    d1 = d1.sort_values(["category", "reports_referencing", "total_occurrences"], ascending=[True, False, False])
    d1["rank_in_category"] = d1.groupby("category").cumcount() + 1
    d1 = d1[["category", "rank_in_category", "term_id", "term", "variants_included", "reports_referencing", "total_occurrences", "percent_of_corpus_docs"]]

    counts.to_csv(out / "Document_Term_Counts.csv", index=False)
    matrix.to_csv(out / "Document_Term_Matrix.csv", index=False)
    term_summary.to_csv(out / "Term_Summary.csv", index=False)
    zero.to_csv(out / "Zero_Reference_Terms.csv", index=False)
    d1.to_csv(out / "D1_Key_Terms.csv", index=False)
    run_manifest = {
        "protocol": "PRISMA-S corpus term-count protocol v1.3",
        "state_package": "v1.5 frozen-text execution layer",
        "matching_rule": MATCHING_RULE,
        "variant_rollup": "canonical_term",
        "consume_only_frozen_text": True,
        "active_canonical_terms": active_terms,
        "documents_counted": denom,
    }
    (out / "keyword_run_manifest.json").write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")
    print(f"v1.3 keyword outputs written to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
