#!/usr/bin/env python3
"""Validate a frozen extracted-text corpus.

Extraction-status checks always run. Comparison against a reference
Text_Extraction_QA table (page and character counts) runs only when
--baseline is given and exists; without one, rows are marked NO_REFERENCE.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import yaml


def load_table(path: str, sheet: Optional[str] = None) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(p, sheet_name=sheet or 0)
    return pd.read_csv(p)


def first_existing_col(df: pd.DataFrame, names: list[str]) -> Optional[str]:
    lower = {c.lower(): c for c in df.columns}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare frozen text manifest to a prior Text_Extraction_QA baseline.")
    ap.add_argument("--manifest", required=True, help="Frozen text manifest CSV.")
    ap.add_argument("--baseline", default="", help="Optional reference Text_Extraction_QA workbook or CSV.")
    ap.add_argument("--baseline-sheet", default="Text_Extraction_QA", help="Sheet name if baseline is workbook.")
    ap.add_argument("--out", required=True, help="Output CSV path for QA report.")
    ap.add_argument("--params", default="config/frozen_text_protocol_params_v1_5.yml")
    args = ap.parse_args()

    params = yaml.safe_load(Path(args.params).read_text(encoding="utf-8")) if Path(args.params).exists() else {}
    thresholds = params.get("qa_thresholds", {})
    tolerance = float(thresholds.get("char_count_relative_tolerance", 0.02))
    page_must_match = bool(thresholds.get("page_count_must_match_baseline", True))

    current = pd.read_csv(args.manifest)
    has_reference = bool(args.baseline) and Path(args.baseline).exists()
    baseline = load_table(args.baseline, args.baseline_sheet) if has_reference else pd.DataFrame()

    base_doc_col = first_existing_col(baseline, ["doc_id", "document_id", "Doc ID"])
    base_file_col = first_existing_col(baseline, ["file_name", "filename", "pdf_filename"])
    base_page_col = first_existing_col(baseline, ["page_count", "pages", "pdf_page_count"])
    base_char_col = first_existing_col(baseline, ["char_count", "character_count", "text_char_count", "extracted_char_count"])
    base_hash_col = first_existing_col(baseline, ["text_sha256", "normalized_text_sha256", "text_hash", "extracted_text_hash"])

    cur_doc_key = "previous_doc_id" if "previous_doc_id" in current.columns and current["previous_doc_id"].fillna("").astype(str).str.len().gt(0).any() else "doc_id"

    # Build a baseline lookup primarily by doc_id, secondarily by file_name.
    baseline_by_doc: Dict[str, pd.Series] = {}
    if base_doc_col:
        for _, r in baseline.iterrows():
            key = str(r.get(base_doc_col, "")).strip()
            if key:
                baseline_by_doc[key] = r
    baseline_by_file: Dict[str, pd.Series] = {}
    if base_file_col:
        for _, r in baseline.iterrows():
            key = Path(str(r.get(base_file_col, "")).strip()).name
            if key:
                baseline_by_file[key] = r

    records = []
    for _, r in current.iterrows():
        cur_key = str(r.get(cur_doc_key, "")).strip()
        cur_file = Path(str(r.get("file_name", "")).strip()).name
        b = baseline_by_doc.get(cur_key) or baseline_by_file.get(cur_file)
        status = str(r.get("status", ""))
        flags = []
        if not has_reference:
            flags.append("NO_REFERENCE")
            base_page = base_char = base_hash = ""
        elif b is None:
            flags.append("NO_BASELINE_ROW")
            base_page = base_char = base_hash = ""
        else:  # compare against the reference row
            base_page = b.get(base_page_col, "") if base_page_col else ""
            base_char = b.get(base_char_col, "") if base_char_col else ""
            base_hash = b.get(base_hash_col, "") if base_hash_col else ""
            try:
                if page_must_match and str(base_page) != "" and int(float(r.get("page_count", -1))) != int(float(base_page)):
                    flags.append("PAGE_COUNT_CHANGED")
            except Exception:
                flags.append("PAGE_COUNT_COMPARE_FAILED")
            try:
                cc = float(r.get("char_count", 0))
                bc = float(base_char)
                rel = abs(cc - bc) / max(bc, 1.0)
                if rel > tolerance:
                    flags.append("CHAR_COUNT_OUTSIDE_TOLERANCE")
            except Exception:
                flags.append("CHAR_COUNT_COMPARE_FAILED")
            if base_hash and "normalized_text_sha256" in current.columns:
                # Hash equality can only be expected if normalization/extractor are identical.
                if str(base_hash).strip() and str(r.get("normalized_text_sha256", "")).strip() != str(base_hash).strip():
                    flags.append("TEXT_HASH_DIFFERS_FROM_BASELINE")
        if status in {"EXTRACTION_TIMEOUT", "EXTRACTION_ERROR", "MISSING_PDF", "EMPTY_TEXT"}:
            flags.append("BLOCKING_EXTRACTION_STATUS")
        records.append({
            "doc_id": r.get("doc_id", ""),
            "comparison_key": cur_key,
            "file_name": r.get("file_name", ""),
            "current_status": status,
            "current_page_count": r.get("page_count", ""),
            "baseline_page_count": base_page,
            "current_char_count": r.get("char_count", ""),
            "baseline_char_count": base_char,
            "current_normalized_text_sha256": r.get("normalized_text_sha256", ""),
            "baseline_text_hash": base_hash,
            "qa_flags": ";".join(flags),
            "blocking_qa": any(f in flags for f in ["BLOCKING_EXTRACTION_STATUS", "PAGE_COUNT_CHANGED", "CHAR_COUNT_OUTSIDE_TOLERANCE"]),
        })
    report = pd.DataFrame(records)
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(out, index=False)
    blocking = int(report["blocking_qa"].fillna(False).sum()) if len(report) else 0
    print(f"Frozen corpus QA report written: {out}")
    print(f"Rows: {len(report)}; blocking QA rows: {blocking}")
    return 2 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
