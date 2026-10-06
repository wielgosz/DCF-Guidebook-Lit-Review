"""Figures 1-3, rendered with matplotlib from a style file.

The figure contract (unchanged from earlier protocol versions):
- bars show ``reports_referencing`` (documents mentioning the term);
- one figure per category: Figure 1 jurisdictional/landscape terms (AOI terms
  excluded), Figure 2 supply chain terms, Figure 3 farm level terms;
- a shared x-axis limit across the three figures; highest value at the top;
- canonical file names DCF_PRISMA_S_Figure_{1,2,3}_*.{svg,png}.

Look and feel come from a YAML style file (``templates/figure_style.yml`` by
default). Output is deterministic: fixed font, fixed SVG id salt, and no
creation dates or software stamps in the files, so identical data gives
byte-identical figures.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml

FIGURES = [
    ("Jurisdictional terms", "DCF_PRISMA_S_Figure_1_jurisdictional_terms", "Jurisdictional and landscape terms"),
    ("Supply chain terms", "DCF_PRISMA_S_Figure_2_supply_chain_terms", "Supply chain terms"),
    ("Farm level terms", "DCF_PRISMA_S_Figure_3_farm_level_terms", "Farm level terms"),
]
AXIS_LABEL = "Number of reports referencing term"


def load_style(path: Path) -> Dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _rc(style: Dict) -> Dict:
    font, colors = style.get("font", {}), style.get("colors", {})
    return {
        "font.family": font.get("family", "DejaVu Sans"),
        "font.size": font.get("size", 9),
        "axes.titlesize": font.get("title_size", 11),
        "axes.titleweight": font.get("title_weight", "bold"),
        "text.color": colors.get("text", "#000000"),
        "axes.labelcolor": colors.get("text", "#000000"),
        "axes.edgecolor": colors.get("axis", "#4D4D4D"),
        "xtick.color": colors.get("axis", "#4D4D4D"),
        "ytick.color": colors.get("axis", "#4D4D4D"),
        "figure.facecolor": colors.get("background", "#FFFFFF"),
        "axes.facecolor": colors.get("background", "#FFFFFF"),
        "svg.hashsalt": "supply-chain-data-review",
        "svg.fonttype": "path",  # text as outlines: identical rendering everywhere
        "pdf.fonttype": 42,
    }


def plot_category(term_summary: pd.DataFrame, category: str, title: str, xlim: float,
                  style: Dict, out_base: Path) -> List[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lay, colors, out_cfg = style.get("layout", {}), style.get("colors", {}), style.get("output", {})
    sub = term_summary[term_summary["category"].astype(str).str.lower() == category.lower()].copy()
    if sub.empty:
        return []
    sub["reports_referencing"] = pd.to_numeric(sub["reports_referencing"], errors="coerce").fillna(0)
    data = sub.sort_values(["reports_referencing", "term"], ascending=[False, True]).iloc[::-1]

    written: List[Path] = []
    with plt.rc_context(_rc(style)):
        height = max(lay.get("min_height_in", 3.2), lay.get("row_height_in", 0.32) * len(data) + lay.get("extra_height_in", 1.4))
        fig, ax = plt.subplots(figsize=(lay.get("width_in", 7.2), height))
        ax.barh(data["term"].astype(str), data["reports_referencing"], color=colors.get("bar", "#F0B310"),
                height=lay.get("bar_height", 0.55))
        ax.set_xlim(0, xlim if xlim > 0 else 1)
        ax.set_xlabel(AXIS_LABEL)
        if lay.get("title", True):
            ax.set_title(title)
        if lay.get("frame", "axes_only") == "axes_only":
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
        ax.grid(bool(lay.get("grid", False)))
        if lay.get("value_labels", True):
            for i, v in enumerate(data["reports_referencing"].tolist()):
                ax.text(float(v) + max(xlim, 1) * 0.01, i, str(int(v)), va="center",
                        fontsize=max(6, style.get("font", {}).get("size", 9) - 1), color=colors.get("value_label", "#000000"))
        fig.tight_layout()
        for fmt in out_cfg.get("formats", ["svg", "png"]):
            path = out_base.with_suffix("." + fmt)
            meta = {"Date": None, "Creator": None} if fmt == "svg" else {"Software": None} if fmt == "png" else {}
            fig.savefig(path, format=fmt, dpi=out_cfg.get("png_dpi", 200) if fmt == "png" else None, metadata=meta)
            written.append(path)
        plt.close(fig)
    return written


def render_term_figures(term_summary: pd.DataFrame, out_dir: Path, style_path: Path) -> Dict[str, str]:
    """Render Figures 1-3; return {file name: sha256} for the run manifest."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if term_summary.empty or "reports_referencing" not in term_summary.columns:
        return {}
    style = load_style(style_path)
    ratio = style.get("layout", {}).get("x_padding_ratio", 1.08)
    xlim = float(pd.to_numeric(term_summary["reports_referencing"], errors="coerce").fillna(0).max()) * ratio
    hashes: Dict[str, str] = {}
    for category, stem, title in FIGURES:
        for path in plot_category(term_summary, category, title, xlim, style, out_dir / stem):
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes
