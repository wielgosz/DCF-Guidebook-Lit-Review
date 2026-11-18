#!/usr/bin/env python3
"""Freeze a PRISMA-S PDF corpus as stable extracted-text artifacts.

This stage is intentionally separate from keyword counting. It extracts each
included PDF once, writes per-document text files and hashes, and records any
failure/time-out as a blocking QA event rather than silently omitting text.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import threading
import time
import traceback
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml

try:
    import pypdf
except Exception:  # pragma: no cover
    pypdf = None

try:  # Optional legacy extractor (AGPL); only used when params ask for it.
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None

PAGE_BREAK = "\n\n[[PRISMA_PAGE_BREAK]]\n\n"

BLOCKING_STATUSES = {"EXTRACTION_TIMEOUT", "EXTRACTION_ERROR", "MISSING_PDF", "EMPTY_TEXT"}


class TimeoutErrorForDocument(Exception):
    pass


def run_with_timeout(func, timeout_seconds: int, *args):
    """Run func(*args) on a worker thread; raise TimeoutErrorForDocument on timeout.

    Thread-based so it works on Windows (SIGALRM is POSIX-only). A timed-out
    worker cannot be killed, but it is a daemon thread and the run moves on.
    """
    box: Dict[str, Any] = {}

    def target() -> None:
        try:
            box["result"] = func(*args)
        except BaseException as exc:  # pragma: no cover - re-raised below
            box["error"] = exc

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(timeout_seconds)
    if worker.is_alive():
        raise TimeoutErrorForDocument(f"document extraction timed out after {timeout_seconds}s")
    if "error" in box:
        raise box["error"]
    return box["result"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_text(text: str, params: Dict[str, Any]) -> str:
    norm = params.get("normalize_unicode", "NFC")
    if norm:
        text = unicodedata.normalize(str(norm), text)
    if params.get("normalize_line_endings", True):
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    if params.get("strip_trailing_whitespace", True):
        text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text


def hashable_text(text: str, params: Dict[str, Any]) -> str:
    if params.get("collapse_internal_whitespace_for_hash", False):
        return " ".join(text.split())
    return text


def extract_pdf_pymupdf(pdf_path: Path) -> Tuple[str, int, List[int], List[bool]]:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed; install PyMuPDF or adjust extractor parameters.")
    doc = fitz.open(pdf_path)
    pages: List[str] = []
    page_char_counts: List[int] = []
    empty_page_flags: List[bool] = []
    try:
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            page_text = page.get_text("text") or ""
            pages.append(page_text)
            page_char_counts.append(len(page_text))
            empty_page_flags.append(len(page_text.strip()) == 0)
        return PAGE_BREAK.join(pages), doc.page_count, page_char_counts, empty_page_flags
    finally:
        doc.close()


def extract_pdf_pypdf(pdf_path: Path) -> Tuple[str, int, List[int], List[bool]]:
    if pypdf is None:
        raise RuntimeError("pypdf is not installed; install the runner requirements.")
    reader = pypdf.PdfReader(str(pdf_path))
    pages: List[str] = []
    page_char_counts: List[int] = []
    empty_page_flags: List[bool] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages.append(page_text)
        page_char_counts.append(len(page_text))
        empty_page_flags.append(len(page_text.strip()) == 0)
    return PAGE_BREAK.join(pages), len(reader.pages), page_char_counts, empty_page_flags


def choose_extractor(params: Dict[str, Any]):
    """Return (name, version, function) for the configured extractor (default pypdf)."""
    name = str(params.get("primary_extractor", "pypdf")).lower()
    if name == "pymupdf" and fitz is not None:
        return "pymupdf", getattr(fitz, "version", ("", "", ""))[0], extract_pdf_pymupdf
    version = getattr(pypdf, "__version__", "") if pypdf is not None else "not_installed"
    return "pypdf", version, extract_pdf_pypdf


def resolve_pdf_path(row: pd.Series, pdf_root: Path) -> Optional[Path]:
    # A manifest from the corpus register carries the resolved absolute path.
    if "pdf_path" in row and pd.notna(row["pdf_path"]) and str(row["pdf_path"]).strip():
        candidate = Path(str(row["pdf_path"]).strip())
        if candidate.is_absolute() and candidate.exists():
            return candidate
    for col in ["file_name", "pdf_file", "pdf_filename", "filename"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            candidate = pdf_root / str(row[col]).strip()
            if candidate.exists():
                return candidate
            # Some manifests include subdirectories; search by basename as fallback.
            matches = list(pdf_root.rglob(Path(str(row[col]).strip()).name))
            if matches:
                return matches[0]
    return None


def should_include(row: pd.Series) -> bool:
    status_cols = ["include_in_corpus", "included", "count_status", "corpus_status", "status"]
    for col in status_cols:
        if col in row and pd.notna(row[col]):
            value = str(row[col]).strip().lower()
            if value in {"false", "no", "0", "exclude", "excluded", "not_counted_no_file", "not_counted"}:
                return False
            if value.startswith("exclude"):
                return False
    return True


def extract_one(row: pd.Series, pdf_root: Path, text_dir: Path, norm_dir: Path, params: Dict[str, Any]) -> Dict[str, Any]:
    doc_id = str(row.get("doc_id", "")).strip()
    if not doc_id:
        doc_id = f"row_{int(row.name) + 2}"
    previous_doc_id = str(row.get("previous_doc_id", row.get("baseline_v13_doc_id", ""))).strip()
    file_name = str(row.get("file_name", "")).strip()
    started = time.time()
    extractor_name, extractor_version, extractor = choose_extractor(params)
    record: Dict[str, Any] = {
        "doc_id": doc_id,
        "previous_doc_id": previous_doc_id,
        "file_name": file_name,
        "title": row.get("title", ""),
        "year": row.get("year", ""),
        "status": "PENDING",
        "warning_flags": "",
        "error_message": "",
        "extractor": extractor_name,
        "extractor_version": extractor_version,
        "started_at_epoch": started,
        "finished_at_epoch": "",
        "duration_seconds": "",
        "pdf_path": "",
        "pdf_sha256": "",
        "pdf_size_bytes": "",
        "page_count": "",
        "char_count": "",
        "word_count": "",
        "page_char_counts_json": "[]",
        "empty_page_count": "",
        "empty_page_numbers_json": "[]",
        "text_path": "",
        "normalized_text_path": "",
        "text_sha256": "",
        "normalized_text_sha256": "",
        "blocking_status": False,
    }
    pdf_path = resolve_pdf_path(row, pdf_root)
    if pdf_path is None:
        record.update(status="MISSING_PDF", error_message="PDF file not found under pdf-root", blocking_status=True)
    else:
        record["pdf_path"] = str(pdf_path)
        record["pdf_sha256"] = sha256_file(pdf_path)
        record["pdf_size_bytes"] = pdf_path.stat().st_size
        timeout_seconds = int(params.get("per_document_timeout_seconds", 180))
        try:
            raw_text, page_count, page_counts, empty_flags = run_with_timeout(extractor, timeout_seconds, pdf_path)
            text = normalize_text(raw_text, params)
            norm_text = hashable_text(text, params)
            text_path = text_dir / f"{doc_id}.txt"
            norm_path = norm_dir / f"{doc_id}.normalized.txt"
            text_path.write_text(text, encoding="utf-8")
            norm_path.write_text(norm_text, encoding="utf-8")
            empty_pages = [i + 1 for i, flag in enumerate(empty_flags) if flag]
            status = "EXTRACTED_OK"
            warnings: List[str] = []
            if empty_pages and params.get("warn_on_empty_pages", True):
                warnings.append("EMPTY_PAGES")
                status = "EXTRACTED_WITH_WARNINGS"
            if len(text.strip()) == 0:
                status = "EMPTY_TEXT"
            record.update(
                status=status,
                warning_flags=";".join(warnings),
                page_count=page_count,
                char_count=len(text),
                word_count=len(text.split()),
                page_char_counts_json=json.dumps(page_counts, ensure_ascii=False),
                empty_page_count=len(empty_pages),
                empty_page_numbers_json=json.dumps(empty_pages),
                text_path=str(text_path),
                normalized_text_path=str(norm_path),
                text_sha256=sha256_bytes(text.encode("utf-8")),
                normalized_text_sha256=sha256_bytes(norm_text.encode("utf-8")),
                blocking_status=status in BLOCKING_STATUSES,
            )
        except TimeoutErrorForDocument as exc:
            record.update(status="EXTRACTION_TIMEOUT", error_message=str(exc), blocking_status=True)
        except Exception as exc:  # pragma: no cover - defensive logging
            record.update(status="EXTRACTION_ERROR", error_message=f"{exc}\n{traceback.format_exc()}", blocking_status=True)
    finished = time.time()
    record["finished_at_epoch"] = finished
    record["duration_seconds"] = round(finished - started, 3)
    return record


def main() -> int:
    ap = argparse.ArgumentParser(description="Freeze PRISMA-S corpus PDFs into extracted text artifacts with blocking QA statuses.")
    ap.add_argument("--corpus", required=True, help="CSV with at least doc_id and file_name columns.")
    ap.add_argument("--pdf-root", required=True, help="Directory containing raw PDFs, recursively searched by basename.")
    ap.add_argument("--out-root", required=True, help="Output root for frozen text corpus.")
    ap.add_argument("--params", default="config/frozen_text_protocol_params_v1_5.yml", help="YAML parameters file.")
    ap.add_argument("--include-all", action="store_true", help="Extract all rows even if status columns indicate exclusion.")
    args = ap.parse_args()

    params_path = Path(args.params)
    params = yaml.safe_load(params_path.read_text(encoding="utf-8")) if params_path.exists() else {}
    extraction_params = params.get("extraction", params)
    qa_params = params.get("qa_thresholds", {})
    extraction_params.update({k: v for k, v in qa_params.items() if k == "warn_on_empty_pages"})

    out_root = Path(args.out_root)
    text_dir = out_root / "text"
    norm_dir = out_root / "normalized_text"
    text_dir.mkdir(parents=True, exist_ok=True)
    norm_dir.mkdir(parents=True, exist_ok=True)
    events_path = out_root / "extraction_events.jsonl"
    manifest_path = out_root / "frozen_text_manifest.csv"

    corpus = pd.read_csv(args.corpus)
    rows = []
    with events_path.open("w", encoding="utf-8") as events:
        for _, row in corpus.iterrows():
            if not args.include_all and not should_include(row):
                continue
            record = extract_one(row, Path(args.pdf_root), text_dir, norm_dir, extraction_params)
            rows.append(record)
            events.write(json.dumps(record, ensure_ascii=False) + "\n")
            events.flush()
    pd.DataFrame(rows).to_csv(manifest_path, index=False)
    blocking = sum(bool(r.get("blocking_status")) for r in rows)
    print(f"Frozen text manifest written: {manifest_path}")
    print(f"Documents processed: {len(rows)}; blocking extraction statuses: {blocking}")
    return 2 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
