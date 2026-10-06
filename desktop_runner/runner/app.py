"""Supply Chain Data Review desktop runner (v2.3).

Tkinter front end for protocol_engine.run_protocol. Inputs:

- Reference tables folder: CSV tables (A1, B1 register, dictionary, exclusions,
  dataset registry, settings). Defaults to the packaged copy; "Make editable
  copy" writes a copy you can update and select instead.
- PDF corpus folder.
- Publication template (.xlsx): optional; defaults to the packaged generic one.
- Reference folder: optional; the reference_snapshot/ of an accepted run.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from protocol_engine import __version__
from protocol_engine.reference_tables import copy_packaged_tables, packaged_tables_dir
from protocol_engine.run_protocol import PACKAGED_TEMPLATE, RunOptions, run_desktop_protocol

PACKAGED_LABEL = "(packaged)"


class RunnerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        from protocol_engine.tables_version import tables_version_for
        self.title(f"Supply Chain Data Review {__version__} - packaged reference tables {tables_version_for()}")
        self.geometry("980x680")
        self.tables_dir = tk.StringVar(value=PACKAGED_LABEL)
        self.pdf_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.template = tk.StringVar(value=PACKAGED_LABEL)
        self.reference_dir = tk.StringVar()
        self.figure_style = tk.StringVar(value=PACKAGED_LABEL)
        self.check_links = tk.BooleanVar(value=False)
        self.last_output: Path | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(frm, text="Supply Chain Data Review", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", **pad)
        ttk.Label(frm, text="Reference tables (CSV) + PDF folder in; validated register, counts, figures and a filled publication template out.").grid(row=1, column=0, columnspan=4, sticky="w", **pad)

        self._row(frm, 2, "Reference tables", self.tables_dir, lambda: self._pick_dir(self.tables_dir),
                  extra=("Make editable copy", self.make_copy))
        self._row(frm, 3, "PDF corpus folder", self.pdf_folder, lambda: self._pick_dir(self.pdf_folder))
        self._row(frm, 4, "Output folder", self.output_folder, lambda: self._pick_dir(self.output_folder))
        self._row(frm, 5, "Publication template", self.template, self.pick_template,
                  extra=("Use packaged", lambda: self.template.set(PACKAGED_LABEL)))
        self._row(frm, 6, "Figure style (YAML)", self.figure_style, self.pick_style,
                  extra=("Use packaged", lambda: self.figure_style.set(PACKAGED_LABEL)))
        self._row(frm, 7, "Reference folder (optional)", self.reference_dir, lambda: self._pick_dir(self.reference_dir),
                  extra=("Clear", lambda: self.reference_dir.set("")))
        ttk.Checkbutton(frm, text="Check every source URL online (slower)", variable=self.check_links).grid(row=8, column=1, sticky="w", **pad)

        btns = ttk.Frame(frm)
        btns.grid(row=9, column=0, columnspan=4, sticky="w", **pad)
        ttk.Button(btns, text="Validate corpus register", command=lambda: self.run(register_only=True)).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Run full protocol", command=lambda: self.run(register_only=False)).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Open tables folder", command=self.open_tables).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Open last output", command=self.open_last_output).pack(side="left", padx=(0, 8))

        self.progress = ttk.Progressbar(frm, mode="indeterminate")
        self.progress.grid(row=10, column=0, columnspan=4, sticky="ew", **pad)
        self.log = tk.Text(frm, height=22, wrap="word")
        self.log.grid(row=11, column=0, columnspan=4, sticky="nsew", **pad)
        scroll = ttk.Scrollbar(frm, command=self.log.yview)
        scroll.grid(row=11, column=4, sticky="ns")
        self.log.configure(yscrollcommand=scroll.set)
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(11, weight=1)

    def _row(self, parent, row, label, var, browse, extra=None) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(parent, text="Browse", command=browse).grid(row=row, column=2, sticky="ew", padx=4, pady=4)
        if extra:
            ttk.Button(parent, text=extra[0], command=extra[1]).grid(row=row, column=3, sticky="ew", padx=4, pady=4)

    @staticmethod
    def _pick_dir(var: tk.StringVar) -> None:
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    def pick_template(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Excel workbooks", "*.xlsx"), ("All files", "*.*")])
        if path:
            self.template.set(path)

    def pick_style(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Figure style", "*.yml *.yaml"), ("All files", "*.*")])
        if path:
            self.figure_style.set(path)

    def _resolved(self, var: tk.StringVar, packaged: Path) -> Path:
        value = var.get().strip()
        return packaged if value in ("", PACKAGED_LABEL) else Path(value)

    def make_copy(self) -> None:
        dest = filedialog.askdirectory(title="Choose an EMPTY folder for your editable reference tables")
        if not dest:
            return
        try:
            copy_packaged_tables(Path(dest))
        except Exception as exc:
            messagebox.showerror("Copy failed", str(exc))
            return
        self.tables_dir.set(dest)
        self.append_log(f"Copied packaged reference tables to {dest}. Edit the CSV files there (Excel works), then run.")

    def append_log(self, text: str) -> None:
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def run(self, register_only: bool) -> None:
        for label, var in [("PDF corpus folder", self.pdf_folder), ("Output folder", self.output_folder)]:
            if not var.get() or not Path(var.get()).is_dir():
                messagebox.showerror("Missing input", f"Please select the {label}.")
                return
        template_value = self.template.get().strip()
        opts = RunOptions(
            pdf_folder=Path(self.pdf_folder.get()),
            output_folder=Path(self.output_folder.get()),
            tables_dir=self._resolved(self.tables_dir, packaged_tables_dir()),
            publication_template=None if template_value in ("", PACKAGED_LABEL) else Path(template_value),
            reference_dir=Path(self.reference_dir.get()) if self.reference_dir.get().strip() else None,
            check_links=self.check_links.get(),
            register_only=register_only,
            figure_style=None if self.figure_style.get().strip() in ("", PACKAGED_LABEL) else Path(self.figure_style.get().strip()),
        )
        self.progress.start(10)
        self.append_log("Validating corpus register..." if register_only else "Running full protocol...")

        def worker() -> None:
            try:
                out = run_desktop_protocol(opts, log_callback=lambda m: self.after(0, self.append_log, m))
                self.last_output = out
            except Exception as exc:
                self.after(0, self.append_log, f"ERROR: {exc}")
                self.after(0, messagebox.showerror, "Run failed", str(exc))
            finally:
                self.after(0, self.progress.stop)

        threading.Thread(target=worker, daemon=True).start()

    def open_tables(self) -> None:
        self._open(self._resolved(self.tables_dir, packaged_tables_dir()))

    def open_last_output(self) -> None:
        if self.last_output and self.last_output.exists():
            self._open(self.last_output)
        else:
            messagebox.showinfo("No output yet", "No output folder is available yet.")

    @staticmethod
    def _open(path: Path) -> None:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])


def main() -> None:
    # Command-line mode for the frozen .exe: SupplyChainDataReview.exe --cli --pdf-folder ...
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        from protocol_engine.run_protocol import main as cli_main
        raise SystemExit(cli_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        from protocol_engine.selftest import run_selftest
        raise SystemExit(run_selftest())
    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        from protocol_engine.tables_version import tables_version_for
        print(f"{__version__} (reference tables {tables_version_for()})")
        raise SystemExit(0)
    RunnerApp().mainloop()


if __name__ == "__main__":
    main()
