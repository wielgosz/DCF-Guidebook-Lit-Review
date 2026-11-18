#!/usr/bin/env python3
"""Compare a current Document_Term_Matrix to a v1.3 baseline matrix."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import pandas as pd


def load_table(path: str, sheet: Optional[str] = None) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(p, sheet_name=sheet or 0)
    return pd.read_csv(p)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare current v1.3 keyword matrix output to a baseline matrix.")
    ap.add_argument("--current", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--baseline-sheet", default="Document_Term_Matrix")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--current-key", default="previous_doc_id", help="Column in current matrix used to match v1.3 baseline doc_id.")
    ap.add_argument("--baseline-key", default="doc_id")
    args = ap.parse_args()

    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    current = load_table(args.current)
    baseline = load_table(args.baseline, args.baseline_sheet)
    ckey = args.current_key if args.current_key in current.columns else "doc_id"
    bkey = args.baseline_key if args.baseline_key in baseline.columns else "doc_id"

    id_cols = {"doc_id", "previous_doc_id", "file_name", "title", "year", "authors_or_orgs", "batch_id"}
    terms = sorted((set(current.columns) & set(baseline.columns)) - id_cols)
    doc_rows = []
    diff_rows = []
    baseline_map = {str(r[bkey]).strip(): r for _, r in baseline.iterrows() if str(r.get(bkey, "")).strip()}
    for _, cur in current.iterrows():
        key = str(cur.get(ckey, "")).strip()
        base = baseline_map.get(key)
        if base is None:
            doc_rows.append({"current_doc_id": cur.get("doc_id", ""), "baseline_doc_id": key, "file_name": cur.get("file_name", ""), "status": "NO_BASELINE_MATCH"})
            continue
        diffs = 0
        prior_total = 0
        current_total = 0
        for term in terms:
            try:
                c = int(cur.get(term, 0) or 0)
                b = int(base.get(term, 0) or 0)
            except Exception:
                c = pd.to_numeric(cur.get(term, 0), errors="coerce") or 0
                b = pd.to_numeric(base.get(term, 0), errors="coerce") or 0
            prior_total += b
            current_total += c
            if c != b:
                diffs += 1
                diff_rows.append({
                    "current_doc_id": cur.get("doc_id", ""),
                    "baseline_doc_id": key,
                    "file_name": cur.get("file_name", ""),
                    "term": term,
                    "baseline_count": b,
                    "current_count": c,
                    "delta": c - b,
                })
        doc_rows.append({
            "current_doc_id": cur.get("doc_id", ""),
            "baseline_doc_id": key,
            "file_name": cur.get("file_name", ""),
            "status": "EXACT_MATCH" if diffs == 0 else "COUNT_DIFFERENCES",
            "term_columns_compared": len(terms),
            "terms_with_differences": diffs,
            "baseline_total": prior_total,
            "current_total": current_total,
            "delta_total": current_total - prior_total,
        })
    pd.DataFrame(doc_rows).to_csv(out / "document_matrix_comparison.csv", index=False)
    pd.DataFrame(diff_rows).to_csv(out / "term_differences_long.csv", index=False)
    print(f"Comparison outputs written to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
