#!/usr/bin/env python3
"""
03_validate_frozen_corpus_v20.py
================================

Stage 3 of the Supply Chain Data Review Protocol v2.0.

Purpose
-------
Validate the frozen extracted-text corpus against the prior v1.3 baseline where
available. This stage checks hashes, page counts, character counts and warning
statuses so extraction differences are explicit before keyword or dataset runs.

Important design point
----------------------
A changed character count does not automatically mean the keyword matrix will be
wrong; the v1.5 QA run showed exact keyword reproduction can coexist with some
text-QA warnings. But every warning must be surfaced and either fixed or
accepted before final commit.
"""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser(description="03 - Validate frozen text against v1.3 baseline.")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--baseline", default="")
    ap.add_argument("--baseline-sheet", default="Text_Extraction_QA")
    ap.add_argument("--out", required=True)
    ap.add_argument("--params", default="config/protocol_v2_0_params.yml")
    args = ap.parse_args()
    script = Path(__file__).with_name("validate_frozen_corpus.py")
    cmd = [sys.executable, str(script), "--manifest", args.manifest, "--baseline", args.baseline, "--baseline-sheet", args.baseline_sheet, "--out", args.out, "--params", args.params]
    print("03 executing:", " ".join(cmd))
    return subprocess.call(cmd)
if __name__ == "__main__": raise SystemExit(main())
