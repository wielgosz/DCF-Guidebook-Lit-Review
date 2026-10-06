"""Release a new edition of the packaged reference tables.

    python tools/release_tables.py --notes "Registered 5 PDFs added 2026-10-06"

Run this after editing any CSV in reference_tables/. It

1. bumps the tool patch version in protocol_engine/__init__.py
   (2.3.0 -> 2.3.1), which makes the tables version 2.30 -> 2.31;
2. rewrites reference_tables/TABLES_VERSION.json with the new version, today's
   date and a SHA-256 per table;
3. adds an entry to reference_tables/CHANGELOG.md.

Use --minor for a tool feature release (2.3.x -> 2.4.0, tables 2.40), and
--init to stamp the current version without bumping (first release only).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
INIT = HERE / "protocol_engine" / "__init__.py"
TABLES = HERE / "reference_tables"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--notes", required=True, help="What changed in the tables.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--minor", action="store_true", help="Bump the minor version instead of the patch.")
    g.add_argument("--init", action="store_true", help="Stamp the current version without bumping.")
    args = ap.parse_args()

    text = INIT.read_text(encoding="utf-8")
    m = re.search(r'__version__ = "(\d+)\.(\d+)\.(\d+)"', text)
    if not m:
        raise SystemExit("Could not find __version__ in protocol_engine/__init__.py")
    major, minor, patch = (int(x) for x in m.groups())
    if args.minor:
        minor, patch = minor + 1, 0
    elif not args.init:
        patch += 1
    tool_version = f"{major}.{minor}.{patch}"
    INIT.write_text(text.replace(m.group(0), f'__version__ = "{tool_version}"'), encoding="utf-8")

    from protocol_engine.tables_version import VERSION_FILE, table_hashes, tables_version_for

    tables_version = tables_version_for(tool_version)
    today = date.today().isoformat()
    stamp = {
        "tables_version": tables_version,
        "tool_version": tool_version,
        "released": today,
        "notes": args.notes,
        "files": table_hashes(TABLES),
    }
    (TABLES / VERSION_FILE).write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")

    log = TABLES / "CHANGELOG.md"
    head = "# Reference tables changelog\n\n"
    body = log.read_text(encoding="utf-8")[len(head):] if log.exists() else ""
    entry = f"## {tables_version} ({today}, tool {tool_version})\n\n- {args.notes}\n\n"
    log.write_text(head + entry + body, encoding="utf-8")
    print(f"Tables {tables_version} / tool {tool_version} stamped ({len(stamp['files'])} tables).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
