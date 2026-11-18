"""Run protocol backend scripts in-process.

The v2.1 backend is a set of standalone argparse scripts. Earlier runners
launched them with ``subprocess`` and ``sys.executable``, which breaks inside a
PyInstaller build (there ``sys.executable`` is the runner .exe itself). Running
each script with ``runpy`` in the current interpreter works the same from
source and from the frozen app.
"""
from __future__ import annotations

import contextlib
import io
import os
import runpy
import sys
from pathlib import Path
from typing import Callable, List, Optional


class StageFailed(RuntimeError):
    def __init__(self, stage: str, code: int):
        super().__init__(f"{stage} failed with exit code {code}")
        self.stage = stage
        self.code = code


class _LineWriter(io.TextIOBase):
    """File-like object that forwards complete lines to a callback."""

    def __init__(self, emit: Callable[[str], None]):
        self._emit = emit
        self._buf = ""

    def write(self, s: str) -> int:
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            self._emit(line)
        return len(s)

    def flush(self) -> None:
        if self._buf:
            self._emit(self._buf)
            self._buf = ""


def run_script(
    script: Path,
    args: List[str],
    cwd: Path,
    emit: Callable[[str], None],
    stage: Optional[str] = None,
) -> int:
    """Execute ``script`` as ``__main__`` with ``args``; return its exit code.

    Output is streamed line by line to ``emit``. ``SystemExit`` with a string
    message (the backend's "Refusing run: ..." style) is reported and mapped to
    exit code 1.
    """
    stage = stage or script.stem
    old_argv, old_cwd, old_path = sys.argv[:], os.getcwd(), sys.path[:]
    writer = _LineWriter(emit)
    code = 0
    try:
        sys.argv = [str(script)] + [str(a) for a in args]
        sys.path.insert(0, str(script.parent))
        os.chdir(cwd)
        with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
            try:
                result = runpy.run_path(str(script), run_name="__main__")
                del result
            except SystemExit as exc:
                if exc.code is None:
                    code = 0
                elif isinstance(exc.code, int):
                    code = exc.code
                else:
                    print(str(exc.code))
                    code = 1
    finally:
        writer.flush()
        sys.argv, sys.path = old_argv, old_path
        os.chdir(old_cwd)
    return code
