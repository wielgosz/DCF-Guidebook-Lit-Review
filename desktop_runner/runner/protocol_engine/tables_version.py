"""Version stamp for the reference tables.

The packaged reference tables carry a version tied to the tool version:
tool ``MAJOR.MINOR.PATCH`` ships tables ``MAJOR.MINOR`` followed by the patch
digit(s) - tool 2.3.0 ships tables 2.30, tool 2.3.1 ships tables 2.31. Any
change to a packaged table (for example registering new PDFs in B1) is
released as a patch bump of the tool via ``tools/release_tables.py``.

``reference_tables/TABLES_VERSION.json`` records the version, the release date
and a SHA-256 per table, so every run can state whether it used the packaged
tables unchanged ("packaged 2.31") or an edited copy ("custom, based on 2.31").
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict

from . import __version__

VERSION_FILE = "TABLES_VERSION.json"


def tables_version_for(tool_version: str = __version__) -> str:
    major, minor, patch = tool_version.split(".")[:3]
    return f"{major}.{minor}{patch}"


def table_hashes(folder: Path) -> Dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(Path(folder).glob("*.csv"))
    }


def read_version(folder: Path) -> Dict:
    path = Path(folder) / VERSION_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def describe(folder: Path) -> Dict[str, str]:
    """Return {'label', 'tables_version', 'state', 'changed_files'} for a tables folder."""
    info = read_version(folder)
    version = info.get("tables_version", "")
    if not info:
        return {"label": "custom (no TABLES_VERSION.json)", "tables_version": "", "state": "unversioned", "changed_files": ""}
    recorded = info.get("files", {})
    actual = table_hashes(folder)
    changed = sorted(f for f in set(recorded) | set(actual) if recorded.get(f) != actual.get(f))
    if changed:
        return {"label": f"custom, based on {version}", "tables_version": version, "state": "modified",
                "changed_files": "; ".join(changed)}
    return {"label": f"packaged {version} ({info.get('released', '')})", "tables_version": version,
            "state": "unchanged", "changed_files": ""}
