"""Runtime orchestration for the Supply Chain Data Review desktop runner (v2.3).

Inputs (all explicit, all recorded in the run manifest with SHA-256 hashes):

- a reference-tables folder (CSV; packaged copy by default) - see
  ``reference_tables.py``;
- a PDF corpus folder (PDFs and/or ZIPs of PDFs);
- a publication template (.xlsx; packaged generic template by default);
- optionally, a reference folder from an earlier accepted run
  (``text_qa_reference.csv`` / ``document_term_matrix_reference.csv``) for
  regression comparison. Without one, comparison steps are skipped.

Nothing else is read: no earlier outputs, no bundled example snapshots.

Stages (each runs in-process, so the same code works from source and as a
PyInstaller .exe):

  01 corpus register   validate B1 against PDFs / APA; build manifest
  02 frozen text       extract text with pypdf
  03 text QA           extraction checks (+ reference comparison if given)
  04 preflight         dictionary / manifest gate
  05 keyword counts    Table D1, Term Summary, matrices
  06 matrix compare    only with a reference folder
  07-10 datasets       stage A-D dataset mention crosswalk (optional)
  11 results           results workbook, figures (SVG + PNG)
  12 publication pack  filled copy of the publication template
"""
from __future__ import annotations

import argparse
import json
import re
import platform
import shutil
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pandas as pd

from . import __version__
from .figures import render_term_figures
from .corpus_register import publication_b1, validate_register, write_proposed_tables, write_register_outputs
from .publication_pack import build_publication_pack
from .reference_tables import (
    packaged_tables_dir,
    read_reference_tables,
    run_settings,
    setting_flag,
    sha256_file,
    snapshot_tables,
    table_path,
    validate_reference_tables,
    write_issues_csv,
)
from .stage_host import run_script
from .tables_version import describe as describe_tables

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
BACKEND = ROOT / "protocol_v2_1"
SCRIPTS = BACKEND / "scripts"
PARAMS = BACKEND / "config" / "frozen_text_protocol_params_v2_3.yml"
PACKAGED_TEMPLATE = ROOT / "templates" / "Publication_Template.xlsx"
PACKAGED_STYLE = ROOT / "templates" / "figure_style.yml"
ILLEGAL_XLSX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

Log = Callable[[str], None]


@dataclass
class RunOptions:
    pdf_folder: Path
    output_folder: Path
    tables_dir: Optional[Path] = None
    publication_template: Optional[Path] = None
    reference_dir: Optional[Path] = None
    check_links: bool = False
    register_only: bool = False
    figure_style: Optional[Path] = None


def create_dated_output_root(base_output: Path, register_only: bool) -> Path:
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    kind = "Register_Check" if register_only else "Supply_Chain_Data_Review_Output"
    out = Path(base_output) / f"{kind}_{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    return out


def _sanitize(df: pd.DataFrame) -> pd.DataFrame:
    """Strip characters Excel cannot store."""
    return df.apply(lambda col: col.map(lambda v: ILLEGAL_XLSX.sub("", v) if isinstance(v, str) else v)) if len(df) else df


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path).fillna("") if path.exists() and path.stat().st_size > 0 else pd.DataFrame()


def build_results(run_root: Path, register: pd.DataFrame, tables: Dict[str, List[Dict[str, str]]],
                  keyword: Path, dataset: Path, style: Path, log: Log) -> Dict[str, object]:
    """Write the results workbook and Figures 1-3; return tables for the publication pack."""
    d1_all = _read_csv(keyword / "D1_Key_Terms.csv")
    # The published Table D1 lists the dictionary's include_in_visuals terms only.
    visual = {
        r.get("canonical_term", "").strip().lower()
        for r in tables.get("Dictionary", [])
        if r.get("active", "").lower() in {"yes", "true", "1", "y"} and r.get("include_in_visuals", "yes").lower() in {"yes", "true", "1", "y"}
    }
    d1 = d1_all[d1_all["term"].astype(str).str.lower().isin(visual)].reset_index(drop=True) if len(d1_all) else d1_all
    term_summary = _read_csv(keyword / "Term_Summary.csv")

    included_orgs = set()
    for org in register.loc[register["register_status"].ne("ERROR"), "publishing_org_id"]:
        included_orgs.update(o.strip() for o in str(org).replace(",", ";").split(";") if o.strip())
    a1 = pd.DataFrame([
        {"org_id": r.get("org_id", ""), "organization": r.get("canonical_org_name", ""), "website_url": r.get("website_url", "")}
        for r in tables.get("A1_Organizations", []) if r.get("org_id", "") in included_orgs
    ])
    if len(a1):
        a1 = a1.sort_values("organization", key=lambda s: s.str.casefold()).reset_index(drop=True)
    b1 = publication_b1(register)

    sheets = {
        "Table A1": a1,
        "Table B1": b1,
        "Table D1": d1,
        "D1 all terms": d1_all,
        "Term Summary": term_summary,
        "Zero Reference Terms": _read_csv(keyword / "Zero_Reference_Terms.csv"),
        "Document Term Matrix": _read_csv(keyword / "Document_Term_Matrix.csv"),
        "Document Term Counts": _read_csv(keyword / "Document_Term_Counts.csv"),
        "Corpus Register": register,
        "Dataset Summary": _read_csv(dataset / "stageD" / "Dataset_Summary_Ranking.csv"),
        "Dataset by Document": _read_csv(dataset / "stageC" / "Dataset_by_Document.csv"),
        "Dataset QA Queue": _read_csv(dataset / "stageB" / "Dataset_QA_Review_Queue.csv"),
    }
    results = run_root / "Supply_Chain_Data_Review_Results.xlsx"
    with pd.ExcelWriter(results, engine="openpyxl") as xw:
        for name, df in sheets.items():
            _sanitize(df).to_excel(xw, sheet_name=name[:31], index=False)
            ws = xw.sheets[name[:31]]
            ws.freeze_panes = "A2"
            for col in ws.columns:
                width = max((len(str(c.value)) for c in list(col)[:200] if c.value is not None), default=8)
                ws.column_dimensions[col[0].column_letter].width = min(width + 2, 70)
    log(f"Results workbook: {results.name}")

    fig_dir = run_root / "figures"
    visual_summary = term_summary[term_summary["term"].astype(str).str.lower().isin(visual)] if len(term_summary) else term_summary
    figure_hashes = render_term_figures(visual_summary, fig_dir, style)
    log(f"Figures 1-3 written to {fig_dir.name}/ ({len(figure_hashes)} files, style {style.name})")
    return {"a1": a1, "b1": b1, "d1": d1, "figure_dir": fig_dir, "figure_sha256": figure_hashes}


def write_reference_snapshot(run_root: Path, frozen_manifest: Path, keyword: Path) -> Path:
    """Write files that can serve as the reference folder for a later run."""
    snap = run_root / "reference_snapshot"
    snap.mkdir(exist_ok=True)
    fm = _read_csv(frozen_manifest)
    if len(fm):
        cols = [c for c in ["doc_id", "file_name", "page_count", "char_count", "normalized_text_sha256", "extractor", "extractor_version"] if c in fm.columns]
        fm[cols].to_csv(snap / "text_qa_reference.csv", index=False)
    if (keyword / "Document_Term_Matrix.csv").exists():
        shutil.copy2(keyword / "Document_Term_Matrix.csv", snap / "document_term_matrix_reference.csv")
    (snap / "README.txt").write_text(
        "Reference snapshot of this run. If the run is accepted, pass this folder as the\n"
        "'reference folder' of a later run to compare page/character counts and keyword\n"
        "counts document by document.\n", encoding="utf-8")
    return snap


def run_desktop_protocol(opts: RunOptions, log_callback: Optional[Log] = None) -> Path:
    tables_dir = Path(opts.tables_dir) if opts.tables_dir else packaged_tables_dir()
    template = Path(opts.publication_template) if opts.publication_template else PACKAGED_TEMPLATE
    style = Path(opts.figure_style) if opts.figure_style else PACKAGED_STYLE
    pdf_folder = Path(opts.pdf_folder)
    run_root = create_dated_output_root(Path(opts.output_folder), opts.register_only)
    logs_dir = run_root / "logs"
    logs_dir.mkdir()
    log_file = (logs_dir / "run.log").open("w", encoding="utf-8")

    console = sys.stdout  # captured before stages redirect stdout into log()

    def log(msg: str) -> None:
        if console is not None:
            console.write(msg + "\n")
            console.flush()
        log_file.write(msg + "\n")
        log_file.flush()
        if log_callback:
            log_callback(msg)

    stages: List[Dict[str, object]] = []
    manifest: Dict[str, object] = {
        "runner_version": __version__,
        "backend_protocol": "2.1 scripts, v2.3 extraction params",
        "started": datetime.now().isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "frozen_app": bool(getattr(sys, "frozen", False)),
        "mode": "register_only" if opts.register_only else "full",
        "inputs": {},
        "stages": stages,
    }

    def finish(status: str) -> Path:
        manifest["status"] = status
        manifest["finished"] = datetime.now().isoformat(timespec="seconds")
        (run_root / "run_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        log(f"Run status: {status}. Output: {run_root}")
        log_file.close()
        return run_root

    def stage(name: str, script: str, args: List[str], blocking: bool = True) -> bool:
        log(f"--- {name}")
        try:
            code = run_script(SCRIPTS / script, args, cwd=BACKEND, emit=log, stage=name)
        except Exception:
            log(traceback.format_exc())
            code = 99
        stages.append({"stage": name, "script": script, "exit_code": code, "blocking": blocking})
        if code != 0:
            log(f"{name}: exit code {code}" + ("" if blocking else " (non-blocking, continuing)"))
        return code == 0 or not blocking

    try:
        log(f"Supply Chain Data Review runner {__version__}")
        log(f"Reference tables: {tables_dir}")
        log(f"PDF folder:       {pdf_folder}")
        log(f"Template:         {template}")
        if not pdf_folder.is_dir():
            raise ValueError(f"PDF folder not found: {pdf_folder}")
        if not style.exists():
            raise ValueError(f"Figure style file not found: {style}")
        if not template.exists():
            raise ValueError(f"Publication template not found: {template}")
        tables = read_reference_tables(tables_dir)
        settings = run_settings(tables)
        tables_info = describe_tables(tables_dir)
        log(f"Tables version:   {tables_info['label']}")
        if tables_info["changed_files"]:
            log(f"  edited since that version: {tables_info['changed_files']}")
        run_datasets = setting_flag(settings, "run_dataset_crosswalk", True)
        run_keywords = setting_flag(settings, "run_keyword_analysis", True)

        inputs_dir = run_root / "00_inputs"
        manifest["inputs"] = {
            "reference_tables_dir": str(tables_dir),
            "reference_tables_version": tables_info["tables_version"],
            "reference_tables_label": tables_info["label"],
            "reference_tables_changed_files": tables_info["changed_files"],
            "reference_tables_sha256": snapshot_tables(tables_dir, inputs_dir / "reference_tables"),
            "publication_template": str(template),
            "publication_template_sha256": sha256_file(template),
            "figure_style": str(style),
            "figure_style_sha256": sha256_file(style),
            "pdf_folder": str(pdf_folder),
            "reference_dir": str(opts.reference_dir or ""),
        }

        issues = validate_reference_tables(tables_dir, tables, need_datasets=run_datasets and not opts.register_only)
        write_issues_csv(issues, run_root / "reference_table_issues.csv")
        table_errors = [i for i in issues if i.severity == "ERROR"]
        for i in table_errors:
            log(f"ERROR {i.sheet} row {i.row} {i.field}: {i.message}")

        # 01 corpus register ------------------------------------------------
        log("--- 01 Corpus register")
        reg_dir = run_root / "01_corpus_register"
        user_template = opts.publication_template is not None
        result = validate_register(
            tables, pdf_folder, run_root / "_work",
            publication_template=template if user_template else None,
            check_links=opts.check_links,
            block_on_missing_pdf=setting_flag(settings, "block_on_missing_pdf", True),
            log=log,
        )
        xlsx = write_register_outputs(result, reg_dir, run_label=run_root.name)
        proposed = write_proposed_tables(tables.get("B1_Corpus_Documents", []), result, reg_dir / "proposed_reference_tables")
        log(f"Register workbook: {xlsx.relative_to(run_root)}; proposed tables: {', '.join(p.name for p in proposed)}")
        stages.append({"stage": "01 corpus register", "errors": len(result.errors), "warnings": len(result.warnings),
                       "documents_counted": len(result.manifest), "unregistered_pdfs": len(result.unregistered)})
        for i in result.errors:
            log(f"ERROR {i.doc_id or i.file_name}: {i.check}: {i.message}")

        if opts.register_only:
            return finish("register_checked_with_errors" if (result.errors or table_errors) else "register_ok")
        if result.errors or table_errors:
            log("Blocked: fix the ERROR rows above (see 01_corpus_register/Table_B1_Corpus_Register.xlsx), then rerun.")
            return finish("blocked_by_validation")

        corpus_manifest = reg_dir / "corpus_manifest.csv"
        dictionary = inputs_dir / "reference_tables" / table_path(tables_dir, "Dictionary").name
        frozen = run_root / "02_frozen_text"
        qa = run_root / "03_qa"
        keyword = run_root / "05_keyword_outputs"
        dataset = run_root / "07_dataset_workflow"
        frozen_manifest = frozen / "frozen_text_manifest.csv"
        ref = Path(opts.reference_dir) if opts.reference_dir else None

        if not stage("02 Frozen text extraction", "freeze_extract_text_corpus.py",
                     ["--corpus", corpus_manifest, "--pdf-root", pdf_folder, "--out-root", frozen, "--params", PARAMS]):
            return finish("blocked_by_extraction")

        ref_text = ref / "text_qa_reference.csv" if ref else None
        stage("03 Text QA", "validate_frozen_corpus.py",
              ["--manifest", frozen_manifest, "--baseline", ref_text if ref_text and ref_text.exists() else "",
               "--out", qa / "frozen_text_qa_report.csv", "--params", PARAMS], blocking=False)

        pre_args = ["--corpus", corpus_manifest, "--manifest", frozen_manifest, "--dictionary", dictionary,
                    "--out", qa / "preflight_gate_report.csv", "--params", PARAMS]
        if settings.get("expected_active_terms"):
            pre_args += ["--expected-terms", settings["expected_active_terms"]]
        if not stage("04 Preflight gate", "preflight_protocol_gate.py", pre_args):
            return finish("blocked_by_preflight")

        if run_keywords:
            if not stage("05 Keyword counts", "run_v13_keyword_counts_frozen.py",
                         ["--manifest", frozen_manifest, "--dictionary", dictionary, "--out", keyword,
                          "--params", PARAMS, "--allow-warnings"]):
                return finish("failed_keyword_counts")
            ref_matrix = ref / "document_term_matrix_reference.csv" if ref else None
            if ref_matrix and ref_matrix.exists():
                stage("06 Matrix comparison", "compare_keyword_matrix_to_baseline.py",
                      ["--current", keyword / "Document_Term_Matrix.csv", "--baseline", ref_matrix,
                       "--current-key", "doc_id", "--out-dir", qa / "matrix_comparison"], blocking=False)
            else:
                log("--- 06 Matrix comparison skipped (no reference folder)")

        if run_datasets:
            snap = inputs_dir / "reference_tables"
            ok = stage("07 Dataset stage A (mentions)", "run_v14_stageA_extract_dataset_mentions.py",
                       ["--corpus", corpus_manifest, "--text-root", frozen / "text",
                        "--patterns", snap / "dataset_extraction_patterns.csv", "--out", dataset / "stageA"], blocking=False)
            ok = ok and stage("08 Dataset stage B (canonicalize)", "run_v14_stageB_canonicalize.py",
                              ["--stageA", dataset / "stageA" / "Dataset_Mentions_Raw.csv",
                               "--registry", snap / "C1_dataset_registry.csv",
                               "--crosswalk", snap / "dataset_name_crosswalk.csv", "--out", dataset / "stageB"], blocking=False)
            ok = ok and stage("09 Dataset stage C (crosswalk)", "run_v14_stageC_crosswalk.py",
                              ["--stageB", dataset / "stageB" / "Dataset_Mentions_StageB_Mapped.csv", "--out", dataset / "stageC"], blocking=False)
            ok = ok and stage("10 Dataset stage D (summaries)", "run_v14_stageD_summary.py",
                              ["--stageC", dataset / "stageC" / "Dataset_by_Document.csv", "--out", dataset / "stageD"], blocking=False)

        log("--- 11 Results and figures")
        built = build_results(run_root, result.register, tables, keyword, dataset, style, log)
        manifest["outputs"] = {"figure_sha256": built["figure_sha256"]}
        write_reference_snapshot(run_root, frozen_manifest, keyword)

        log("--- 12 Publication pack")
        pack = build_publication_pack(
            template, run_root / f"Publication_Tables_{run_root.name.split('_Output_')[-1]}.xlsx",
            d1=built["d1"], a1=built["a1"], b1=built["b1"], figure_dir=built["figure_dir"],
            run_info={"Run folder": run_root.name, "Reference tables": str(tables_dir),
                      "Reference tables version": tables_info["label"],
                      "Documents counted": str(len(result.manifest))},
            log=log,
        )
        if len(pack["d1_compare"]):
            pack["d1_compare"].to_csv(qa / "D1_vs_template.csv", index=False)
            changed = pack["d1_compare"]
            changed = changed[pd.to_numeric(changed["reports_referencing_delta"], errors="coerce").fillna(1) != 0]
            log(f"D1 vs template: {len(changed)} of {len(pack['d1_compare'])} terms differ (03_qa/D1_vs_template.csv)")
        stages.append({"stage": "12 publication pack", "refreshed": pack["refreshed"], "skipped": pack["skipped"]})

        failed = [s for s in stages if s.get("exit_code") not in (None, 0)]
        return finish("completed_with_warnings" if failed else "completed")
    except Exception as exc:
        log(f"ERROR: {exc}")
        log(traceback.format_exc())
        return finish("error")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Supply Chain Data Review desktop runner (command line).")
    ap.add_argument("--pdf-folder", required=True)
    ap.add_argument("--output-folder", required=True)
    ap.add_argument("--tables", default=None, help="Reference tables folder (default: packaged tables).")
    ap.add_argument("--template", default=None, help="Publication template .xlsx (default: packaged generic template).")
    ap.add_argument("--figure-style", default=None, help="Figure style YAML (default: packaged templates/figure_style.yml).")
    ap.add_argument("--reference", default=None, help="Reference folder from an accepted earlier run (optional).")
    ap.add_argument("--check-links", action="store_true", help="Check every source_url over the network.")
    ap.add_argument("--register-only", action="store_true", help="Only validate the corpus register (Table B1).")
    args = ap.parse_args(argv)
    out = run_desktop_protocol(RunOptions(
        pdf_folder=Path(args.pdf_folder), output_folder=Path(args.output_folder),
        tables_dir=Path(args.tables) if args.tables else None,
        publication_template=Path(args.template) if args.template else None,
        reference_dir=Path(args.reference) if args.reference else None,
        check_links=args.check_links, register_only=args.register_only,
        figure_style=Path(args.figure_style) if args.figure_style else None,
    ))
    status = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))["status"]
    return 0 if status in {"completed", "completed_with_warnings", "register_ok"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
