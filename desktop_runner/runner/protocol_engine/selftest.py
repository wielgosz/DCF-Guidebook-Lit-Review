"""End-to-end selftest: generate a two-PDF corpus and run the full protocol.

    python -m protocol_engine.selftest            (from source)
    SupplyChainDataReview.exe --selftest          (built app; exit code 0 = pass)

Uses the packaged keyword dictionary, A1 table, dataset tables and generic
publication template, with a synthetic two-row B1 register, so it checks the
whole chain (register -> extraction -> counts -> datasets -> results ->
publication pack) without any real corpus.
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path

from .reference_tables import packaged_tables_dir, read_csv_rows

DOCS = [
    ("SELF-001", "selftest_landscape.pdf", "Landscape and jurisdiction monitoring guide",
     "Landscape and jurisdiction monitoring guide. This landscape approach covers the jurisdiction, "
     "the municipality and the supply shed. Traceability to the farm and plot uses PRODES and MapBiomas."),
    ("SELF-002", "selftest_supply_chain.pdf", "Supply chain traceability manual",
     "Supply chain traceability manual. The trader, the mill and the slaughterhouse report the farm "
     "polygon. Global Forest Watch alerts support the supplier and the region of origin."),
]


def make_pdf(path: Path, text: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import textwrap

    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.08, 0.92, "\n".join(textwrap.wrap(text, 80)), va="top", family="DejaVu Sans", fontsize=11)
    fig.savefig(path, format="pdf")
    plt.close(fig)


def build_fixture(root: Path) -> tuple[Path, Path]:
    tables = root / "tables"
    shutil.copytree(packaged_tables_dir(), tables)
    org = read_csv_rows(tables / "A1_organizations.csv")[0]["org_id"]
    b1_cols = ["doc_id", "file_name", "title", "year", "authors_or_orgs", "publishing_org_id", "source_url", "apa_reference"]
    with (tables / "B1_corpus_register.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(b1_cols)
        for doc_id, fn, title, _ in DOCS:
            w.writerow([doc_id, fn, title, "2026", "Selftest Org", org, "https://example.org/" + doc_id,
                        f"Selftest Org. (2026). {title}. https://example.org/{doc_id}"])
    with (tables / "exclusions_duplicates.csv").open("w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerow(["file_name", "rule", "retain_file_name", "notes"])
    pdfs = root / "pdfs"
    pdfs.mkdir()
    for _, fn, _, text in DOCS:
        make_pdf(pdfs / fn, text)
    return tables, pdfs


def run_selftest(keep: bool = False) -> int:
    from .run_protocol import RunOptions, run_desktop_protocol

    root = Path(tempfile.mkdtemp(prefix="scdr_selftest_"))
    try:
        tables, pdfs = build_fixture(root)
        out = run_desktop_protocol(RunOptions(pdf_folder=pdfs, output_folder=root / "out", tables_dir=tables))
        manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
        checks = {
            "status completed": manifest["status"] in {"completed", "completed_with_warnings"},
            "two documents counted": any(s.get("documents_counted") == 2 for s in manifest["stages"]),
            "D1 written": (out / "05_keyword_outputs" / "D1_Key_Terms.csv").exists(),
            "figures written": len(list((out / "figures").glob("*.png"))) == 3,
            "results workbook": (out / "Supply_Chain_Data_Review_Results.xlsx").exists(),
            "publication pack": any(out.glob("Publication_Tables_*.xlsx")),
            "register workbook": (out / "01_corpus_register" / "Table_B1_Corpus_Register.xlsx").exists(),
        }
        d1 = (out / "05_keyword_outputs" / "D1_Key_Terms.csv").read_text(encoding="utf-8") if checks["D1 written"] else ""
        checks["landscape counted"] = "landscape" in d1
        for name, ok in checks.items():
            print(f"{'PASS' if ok else 'FAIL'}  {name}")
        return 0 if all(checks.values()) else 1
    finally:
        if keep:
            print(f"Selftest files kept in {root}")
        else:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(run_selftest(keep="--keep" in sys.argv))
