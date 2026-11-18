"""Reference tables: the runner's source of truth, stored as CSV files.

A reference-tables folder holds one CSV per table. The runner ships a packaged
copy (``reference_tables/`` next to the app); users can copy it, edit it, and
point the runner at their copy. No metadata is read from Excel tabs, earlier
run outputs, or bundled example snapshots.

| File                            | Table                                   | Required |
|---------------------------------|-----------------------------------------|----------|
| A1_organizations.csv            | publishing organizations (Table A1)     | yes      |
| B1_corpus_register.csv          | file name -> doc_id -> APA (Table B1)   | yes      |
| keyword_dictionary.csv          | executable keyword dictionary (D1)      | yes      |
| exclusions_duplicates.csv       | excluded / duplicate PDF file names     | yes      |
| run_settings.csv                | run switches                            | yes      |
| C1_dataset_registry.csv         | canonical dataset registry (Table C1)   | for datasets |
| dataset_name_crosswalk.csv      | mention string -> dataset_id            | for datasets |
| dataset_extraction_patterns.csv | dataset mention seed patterns           | for datasets |
| new_documents.csv               | staging for PDFs not yet in B1          | no       |

CSV files are read and written as UTF-8 with a byte-order mark so they open
correctly in Excel.
"""
from __future__ import annotations

import csv
import hashlib
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

TABLES = {
    # logical name: (file name, required columns, required)
    "A1_Organizations": ("A1_organizations.csv", ["org_id", "canonical_org_name"], True),
    "B1_Corpus_Documents": ("B1_corpus_register.csv", ["doc_id", "file_name", "title", "publishing_org_id", "apa_reference"], True),
    "Dictionary": ("keyword_dictionary.csv", ["category", "term_id", "canonical_term", "search_variant", "variant_type", "roll_up_to_canonical", "active"], True),
    "Exclusions_Duplicates": ("exclusions_duplicates.csv", ["file_name", "rule"], True),
    "Run_Settings": ("run_settings.csv", ["setting", "value"], True),
    "C1_Datasets": ("C1_dataset_registry.csv", ["dataset_id", "preferred_dataset_name"], False),
    "Dataset_Crosswalk": ("dataset_name_crosswalk.csv", [], False),
    "Dataset_Patterns": ("dataset_extraction_patterns.csv", ["pattern"], False),
    "New_Documents": ("new_documents.csv", ["file_name"], False),
}
DATASET_TABLES = ["C1_Datasets", "Dataset_Crosswalk", "Dataset_Patterns"]
TRUE_VALUES = {"yes", "true", "1", "y"}


@dataclass
class ValidationIssue:
    severity: str
    sheet: str
    row: str
    field: str
    message: str


def packaged_tables_dir() -> Path:
    """Folder of the reference tables shipped with the runner (source or frozen)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / "reference_tables"


def table_path(folder: Path, name: str) -> Path:
    return Path(folder) / TABLES[name][0]


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = []
        for i, rec in enumerate(csv.DictReader(f), start=2):
            clean = {(k or "").strip(): (v or "").strip() for k, v in rec.items() if k is not None}
            if not any(clean.values()):
                continue
            clean["__excel_row"] = str(i)  # CSV line number, for messages
            rows.append(clean)
        return rows


def read_reference_tables(folder: Path) -> Dict[str, List[Dict[str, str]]]:
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"Reference tables folder not found: {folder}")
    missing = [spec[0] for name, spec in TABLES.items() if spec[2] and not (folder / spec[0]).exists()]
    if missing:
        raise ValueError(f"Reference tables folder {folder} is missing: {', '.join(missing)}")
    data: Dict[str, List[Dict[str, str]]] = {}
    for name, (fn, _, _) in TABLES.items():
        p = folder / fn
        if p.exists():
            data[name] = read_csv_rows(p)
    return data


def _header(path: Path) -> List[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [h.strip() for h in next(csv.reader(f), [])]


def validate_reference_tables(folder: Path, data: Dict[str, List[Dict[str, str]]], need_datasets: bool) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    for name, (fn, required, is_required) in TABLES.items():
        p = Path(folder) / fn
        if not p.exists():
            if name in DATASET_TABLES and need_datasets:
                issues.append(ValidationIssue("ERROR", fn, "file", "", "Dataset crosswalk is enabled but this table is missing."))
            continue
        cols = set(_header(p))
        missing = [c for c in required if c not in cols]
        if missing:
            issues.append(ValidationIssue("ERROR", fn, "header", ", ".join(missing), f"Missing required columns: {', '.join(missing)}"))

    seen, active_rows = set(), 0
    for r in data.get("Dictionary", []):
        if r.get("active", "").lower() not in TRUE_VALUES:
            continue
        active_rows += 1
        for f_ in ["term_id", "canonical_term", "search_variant", "category"]:
            if not r.get(f_, ""):
                issues.append(ValidationIssue("ERROR", "keyword_dictionary.csv", r["__excel_row"], f_, "Active dictionary row is missing a required value."))
        key = (r.get("term_id", "").lower(), r.get("search_variant", "").lower())
        if key in seen:
            issues.append(ValidationIssue("WARNING", "keyword_dictionary.csv", r["__excel_row"], "search_variant", "Duplicate active term_id + search_variant."))
        seen.add(key)
    if active_rows == 0:
        issues.append(ValidationIssue("ERROR", "keyword_dictionary.csv", "all", "active", "No active dictionary rows."))

    expected = run_settings(data).get("expected_active_terms", "")
    if expected:
        terms = {r.get("canonical_term", "").lower() for r in data.get("Dictionary", []) if r.get("active", "").lower() in TRUE_VALUES}
        if str(len(terms)) != expected.strip():
            issues.append(ValidationIssue("ERROR", "keyword_dictionary.csv", "all", "active",
                                          f"{len(terms)} active canonical terms; run_settings expects {expected}."))
    return issues


def run_settings(data: Dict[str, List[Dict[str, str]]]) -> Dict[str, str]:
    return {r.get("setting", "").lower(): r.get("value", "") for r in data.get("Run_Settings", []) if r.get("setting", "")}


def setting_flag(settings: Dict[str, str], name: str, default: bool) -> bool:
    value = settings.get(name.lower(), "")
    return default if value == "" else value.lower() in TRUE_VALUES


def write_issues_csv(issues: List[ValidationIssue], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "severity", "table", "row", "field", "message"])
        writer.writeheader()
        now = datetime.now().isoformat(timespec="seconds")
        for issue in issues:
            d = asdict(issue)
            d["table"] = d.pop("sheet")
            writer.writerow({"timestamp": now, **d})


def write_rows_csv(rows: List[Dict[str, str]], out_csv: Path, fieldnames: List[str] | None = None) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = fieldnames or ([c for c in rows[0].keys() if c != "__excel_row"] if rows else [])
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot_tables(folder: Path, dest: Path) -> Dict[str, str]:
    """Copy every reference table used by a run into ``dest``; return {file: sha256}."""
    dest.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for _, (fn, _, _) in TABLES.items():
        src = Path(folder) / fn
        if src.exists():
            shutil.copy2(src, dest / fn)
            hashes[fn] = sha256_file(src)
    stamp = Path(folder) / "TABLES_VERSION.json"
    if stamp.exists():
        shutil.copy2(stamp, dest / stamp.name)
    return hashes


def copy_packaged_tables(dest: Path) -> Path:
    """Create an editable copy of the packaged reference tables."""
    dest = Path(dest)
    if dest.exists() and any(dest.iterdir()):
        raise ValueError(f"{dest} is not empty; choose an empty folder.")
    shutil.copytree(packaged_tables_dir(), dest, dirs_exist_ok=True)
    return dest
