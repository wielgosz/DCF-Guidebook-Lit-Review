# PyInstaller spec for the Supply Chain Data Review desktop runner.
#   python -m PyInstaller --clean --noconfirm SupplyChainDataReview.spec
# Produces dist/SupplyChainDataReview/ (onedir). Backend stage scripts run
# in-process via runpy, so their imports are listed as hidden imports.
import glob
import os
import sys

from PyInstaller.utils.hooks import collect_submodules

# SCDR_CONSOLE=1 builds a console variant (errors and selftest output visible).
CONSOLE = os.environ.get("SCDR_CONSOLE") == "1"

hidden = (
    collect_submodules("pypdf")
    + ["yaml", "uuid", "matplotlib.backends.backend_agg", "matplotlib.backends.backend_svg",
       "matplotlib.backends.backend_pdf", "openpyxl.drawing.image", "PIL.Image"]
)

# Conda / non-standard Pythons keep the native DLLs behind C extensions (ffi for
# _ctypes, bz2, lzma, ssl, sqlite, tcl/tk) in Library\bin, which PyInstaller can
# miss: the built app then dies at start-up with "DLL load failed while
# importing _ctypes". Bundle a short allowlist from the base interpreter's DLL
# directories (same approach as desktop/prisma-s.spec).
_BASE = sys.base_prefix
_DLL_DIRS = [d for d in (os.path.join(_BASE, "DLLs"), os.path.join(_BASE, "Library", "bin"), _BASE) if os.path.isdir(d)]
_CRITICAL = ("ffi*.dll", "libffi*.dll", "libbz2*.dll", "bz2*.dll", "liblzma*.dll", "lzma*.dll",
             "libcrypto*.dll", "libssl*.dll", "sqlite3*.dll", "libsqlite3*.dll", "zlib*.dll",
             "libexpat*.dll", "tcl86*.dll", "tk86*.dll")
binaries, _seen = [], set()
for _dir in _DLL_DIRS:
    for _pat in _CRITICAL:
        for _dll in glob.glob(os.path.join(_dir, _pat)):
            if os.path.basename(_dll).lower() not in _seen:
                _seen.add(os.path.basename(_dll).lower())
                binaries.append((_dll, "."))

a = Analysis(
    ["app.py"],
    pathex=["."] + _DLL_DIRS,
    binaries=binaries,
    datas=[
        ("protocol_v2_1/scripts", "protocol_v2_1/scripts"),
        ("protocol_v2_1/config", "protocol_v2_1/config"),
        ("reference_tables", "reference_tables"),
        ("templates", "templates"),
    ],
    hiddenimports=hidden,
    excludes=["fitz", "pymupdf", "PyMuPDF"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="SupplyChainDataReview",
    console=CONSOLE,
)
coll = COLLECT(exe, a.binaries, a.datas, name="SupplyChainDataReview")
