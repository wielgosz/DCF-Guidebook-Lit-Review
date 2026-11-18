"""Build the packaged default corpus tables (A1, B1) from the published guidebook's figure template.

    python tools/build_default_tables.py --from "FIGURE-TEMPLATE ... (v8.6).xlsx"

The default corpus is the one printed in the publication:
  Table A-1 (organisations and websites)  -> reference_tables/A1_organizations.csv
  Table B-1 (APA reference list)          -> reference_tables/B1_corpus_register.csv
and nothing else: no file names, no earlier run state. Documents are numbered DOC-001... in the order
of the published list. `file_name` is left blank; the register validator proposes a match for each PDF
you add (see `suggested_*` columns of the Unregistered PDFs sheet) and you copy the confirmed file names
into your own tables folder. The exclusions and staging tables are shipped empty.

After rebuilding, release the tables:  python tools/release_tables.py --notes "..."
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from openpyxl import load_workbook

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from protocol_engine.corpus_register import fold, parse_apa  # noqa: E402

TABLES = HERE / "reference_tables"
ORG_ALIASES = {  # published org name -> extra spellings used in APA author positions
    "Accountability Framework initiative (AFi)": ["Accountability Framework initiative", "AFi"],
    "AFR100 Terra-Fund": ["AFR100 / TerraFund for AFR100", "TerraFund for AFR100", "AFR100"],
    "World Resources Institute": ["World Resources Institute", "WRI"],
    "Carbon Disclosure Project (CDP.net)": ["CDP"],
    "Google Cloud and NGIS": ["Google & NGIS"],
    # Table A-1 prints "High Carbon Value (HCV) Network"; Table B-1 cites "High Conservation Value Network".
    "High Carbon Value (HCV) Network": ["High Conservation Value Network"],
    "Olam International Group": ["Olam Group"],
    "RaboFoundation": ["Rabo Foundation"],
    "UN Food and Agriculture Organization (FAO)": ["Food and Agriculture Organization of the United Nations",
                                                   "Food and Agriculture Organization", "FAO"],
    "WBCSD Soft Commodity Forum (SCF)": ["World Business Council for Sustainable Development"],
}


def read_a1(ws):
    rows = list(ws.iter_rows(values_only=True))
    hdr = next(i for i, r in enumerate(rows) if r[2] and str(r[2]).strip().lower() in ("organization", "organisation"))
    return [(str(r[2]).strip(), str(r[3] or "").strip()) for r in rows[hdr + 1:] if r[2] and str(r[2]).strip()]


def read_b1(ws):
    rows = list(ws.iter_rows(values_only=True))
    start = next(i for i, r in enumerate(rows) if i > 8 and r[1] and re.match(r".+\(\d{4}[a-z]?[,)]", str(r[1])))
    return [str(r[1]).strip() for r in rows[start:] if r[1] and str(r[1]).strip()]


def aliases(name: str):
    out = {fold(name)}
    out.add(fold(re.sub(r"\s*\([^)]*\)", "", name)))
    for m in re.findall(r"\(([^)]+)\)", name):
        out.add(fold(m))
    out.update(fold(a) for a in ORG_ALIASES.get(name, []))
    return {a for a in out if a}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from", dest="source", required=True)
    args = ap.parse_args()
    wb = load_workbook(args.source, read_only=True, data_only=True)
    orgs = read_a1(wb["Table A1"])
    refs = read_b1(wb["Table B1"])
    org_rows = [{"org_id": f"ORG-{i:03d}", "canonical_org_name": n, "website_url": u} for i, (n, u) in enumerate(orgs, 1)]
    alias_of = {o["org_id"]: aliases(o["canonical_org_name"]) for o in org_rows}

    b1, unmatched = [], []
    for i, apa in enumerate(refs, 1):
        p = parse_apa(apa)
        author = fold(p["author"])
        hits = []
        for oid, al in alias_of.items():
            for a in sorted(al, key=len, reverse=True):
                if re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", author):
                    hits.append((oid, a))
                    break
        # keep the orgs whose matched alias is not inside another matched alias
        keep = [oid for oid, a in hits if not any(a != b and a in b for _, b in hits)]
        if not keep:
            unmatched.append(apa[:110])
        doc_id = f"DOC-{i:03d}"
        b1.append({"doc_id": doc_id, "file_name": "", "title": p["title"], "year": p["year"], "authors_or_orgs": p["author"],
                   "publishing_org_id": ";".join(keep), "source_url": p["url"], "apa_reference": apa, "in_text_citation": ""})
    linked = {o["org_id"]: [] for o in org_rows}
    authors = {o["org_id"]: [] for o in org_rows}
    for r in b1:
        for oid in filter(None, r["publishing_org_id"].split(";")):
            linked[oid].append(r["doc_id"])
            authors[oid].append(r["authors_or_orgs"])
    for o in org_rows:
        forms = authors[o["org_id"]]
        o["apa_author_form"] = max(set(forms), key=forms.count) if forms else o["canonical_org_name"]
        o["linked_doc_ids"] = "; ".join(linked[o["org_id"]])

    def write(name, cols, rows):
        with open(TABLES / name, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\r\n")
            w.writeheader()
            w.writerows(rows)

    write("A1_organizations.csv", ["org_id", "canonical_org_name", "apa_author_form", "website_url", "linked_doc_ids"], org_rows)
    write("B1_corpus_register.csv", ["doc_id", "file_name", "title", "year", "authors_or_orgs", "publishing_org_id",
                                     "source_url", "apa_reference", "in_text_citation"], b1)
    write("exclusions_duplicates.csv", ["file_name", "rule", "retain_file_name", "notes"], [])
    write("new_documents.csv", ["file_name", "title", "year", "notes"], [])
    print(f"A1: {len(org_rows)} organisations | B1: {len(b1)} references")
    print("References with no organisation match:", len(unmatched))
    for u in unmatched:
        print("  -", u)
    print("Organisations with no reference:", [o["canonical_org_name"] for o in org_rows if not linked[o["org_id"]]])


if __name__ == "__main__":
    main()
