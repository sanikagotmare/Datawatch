"""
Data Science Profiling Engine
Generates statistical summaries + matplotlib/seaborn visualisations.
Charts are saved as base64 PNG so the React frontend can embed them directly.
"""
import io
import base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # non-interactive backend — essential for server-side rendering
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, List

# Consistent dark-themed style across all charts
plt.style.use("dark_background")
PALETTE = ["#6366f1", "#22c55e", "#eab308", "#ef4444", "#f97316", "#06b6d4"]


def _fig_to_b64(fig) -> str:
    """Convert a matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110,
                facecolor=fig.get_facecolor(), edgecolor="none")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return b64


class DataProfiler:

    def profile(self, df: pd.DataFrame, filename: str = "") -> Dict[str, Any]:
        """Run full data science profile and return stats + chart images."""
        stats   = self._compute_stats(df)
        charts  = self._generate_charts(df)
        quality = self._data_quality_score(df)
        return {
            "filename":      filename,
            "total_rows":    len(df),
            "total_columns": len(df.columns),
            "memory_usage_kb": round(df.memory_usage(deep=True).sum() / 1024, 2),
            "stats":         stats,
            "charts":        charts,
            "quality":       quality
        }

    def _compute_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        result = {}
        for col in df.columns:
            s = df[col]
            info: Dict[str, Any] = {
                "dtype":        str(s.dtype),
                "null_count":   int(s.isnull().sum()),
                "null_pct":     round(s.isnull().mean() * 100, 2),
                "unique_count": int(s.nunique()),
            }
            if pd.api.types.is_numeric_dtype(s):
                clean = s.dropna()
                if len(clean) > 0:
                    info.update({
                        "mean":     round(float(clean.mean()), 4),
                        "median":   round(float(clean.median()), 4),
                        "std":      round(float(clean.std()), 4),
                        "min":      round(float(clean.min()), 4),
                        "max":      round(float(clean.max()), 4),
                        "q25":      round(float(clean.quantile(0.25)), 4),
                        "q75":      round(float(clean.quantile(0.75)), 4),
                        "skewness": round(float(clean.skew()), 4),
                        "kurtosis": round(float(clean.kurtosis()), 4),
                    })
            else:
                vc = s.value_counts()
                info["top_values"] = vc.head(5).to_dict()
            result[col] = info
        return result

    def _generate_charts(self, df: pd.DataFrame) -> Dict[str, str]:
        charts = {}
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols     = df.select_dtypes(include=["object"]).columns.tolist()

        # 1. Missing values heatmap
        if df.isnull().any().any():
            charts["missing_heatmap"] = self._missing_heatmap(df)

        # 2. Distribution histograms for numeric cols
        if numeric_cols:
            charts["distributions"] = self._distribution_grid(df, numeric_cols)

        # 3. Correlation heatmap
        if len(numeric_cols) >= 2:
            charts["correlation"] = self._correlation_heatmap(df, numeric_cols)

        # 4. Box plots for outlier visualisation
        if numeric_cols:
            charts["boxplots"] = self._boxplot_grid(df, numeric_cols)

        # 5. Categorical value counts
        if cat_cols:
            charts["categorical"] = self._categorical_charts(df, cat_cols)

        return charts

    def _missing_heatmap(self, df: pd.DataFrame) -> str:
        fig, ax = plt.subplots(figsize=(max(8, len(df.columns) * 0.8), 3))
        fig.patch.set_facecolor("#0d0d14")
        ax.set_facecolor("#0d0d14")
        missing = df.isnull().astype(int)
        sns.heatmap(missing.T, ax=ax, cmap=["#1f2937", "#ef4444"],
                    cbar=False, yticklabels=True, xticklabels=False, linewidths=0.1)
        ax.set_title("Missing Values (red = null)", color="#e5e7eb", fontsize=11, pad=8)
        ax.tick_params(colors="#9ca3af", labelsize=8)
        return _fig_to_b64(fig)

    def _distribution_grid(self, df: pd.DataFrame, cols: List[str]) -> str:
        n = min(len(cols), 6)
        cols = cols[:n]
        ncols = min(3, n)
        nrows = (n + ncols - 1) // ncols
        fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 3.5 * nrows))
        fig.patch.set_facecolor("#0d0d14")
        axes_flat = np.array(axes).flatten() if n > 1 else [axes]
        for i, col in enumerate(cols):
            ax = axes_flat[i]
            ax.set_facecolor("#111118")
            clean = df[col].dropna()
            ax.hist(clean, bins=20, color=PALETTE[i % len(PALETTE)], alpha=0.8, edgecolor="none")
            ax.axvline(clean.mean(),   color="#f9fafb", linestyle="--", linewidth=1, alpha=0.7, label=f"Mean={clean.mean():.1f}")
            ax.axvline(clean.median(), color="#fbbf24", linestyle=":",  linewidth=1, alpha=0.7, label=f"Median={clean.median():.1f}")
            ax.set_title(col, color="#e5e7eb", fontsize=9)
            ax.tick_params(colors="#6b7280", labelsize=7)
            ax.legend(fontsize=6, labelcolor="#9ca3af")
            for spine in ax.spines.values(): spine.set_visible(False)
        for j in range(n, len(axes_flat)):
            axes_flat[j].set_visible(False)
        fig.suptitle("Feature Distributions", color="#f3f4f6", fontsize=12, y=1.01)
        fig.tight_layout()
        return _fig_to_b64(fig)

    def _correlation_heatmap(self, df: pd.DataFrame, cols: List[str]) -> str:
        cols = cols[:8]  # cap at 8 for readability
        corr = df[cols].corr()
        fig, ax = plt.subplots(figsize=(max(5, len(cols)), max(4, len(cols) * 0.8)))
        fig.patch.set_facecolor("#0d0d14")
        ax.set_facecolor("#0d0d14")
        mask = np.triu(np.ones_like(corr, dtype=bool))
        cmap = sns.diverging_palette(220, 20, as_cmap=True)
        sns.heatmap(corr, ax=ax, mask=mask, cmap=cmap, center=0,
                    annot=True, fmt=".2f", annot_kws={"size": 8, "color": "#e5e7eb"},
                    linewidths=0.5, linecolor="#1f2937",
                    cbar_kws={"shrink": 0.7})
        ax.set_title("Correlation Matrix", color="#e5e7eb", fontsize=11, pad=8)
        ax.tick_params(colors="#9ca3af", labelsize=8)
        ax.collections[0].colorbar.ax.tick_params(colors="#9ca3af", labelsize=7)
        return _fig_to_b64(fig)

    def _boxplot_grid(self, df: pd.DataFrame, cols: List[str]) -> str:
        cols = cols[:6]
        fig, ax = plt.subplots(figsize=(max(8, len(cols) * 1.5), 4))
        fig.patch.set_facecolor("#0d0d14")
        ax.set_facecolor("#111118")
        data = [df[c].dropna().values for c in cols]
        bp = ax.boxplot(data, patch_artist=True, notch=False,
                        medianprops={"color": "#f9fafb", "linewidth": 2},
                        whiskerprops={"color": "#6b7280"},
                        capprops={"color": "#6b7280"},
                        flierprops={"marker": "o", "markerfacecolor": "#ef4444", "markersize": 4, "alpha": 0.6})
        for patch, color in zip(bp["boxes"], PALETTE):
            patch.set_facecolor(color); patch.set_alpha(0.6)
        ax.set_xticklabels(cols, rotation=30, ha="right", color="#9ca3af", fontsize=8)
        ax.set_title("Box Plots — Outlier Visualisation", color="#e5e7eb", fontsize=11, pad=8)
        ax.tick_params(axis="y", colors="#6b7280", labelsize=7)
        for spine in ax.spines.values(): spine.set_visible(False)
        return _fig_to_b64(fig)

    def _categorical_charts(self, df: pd.DataFrame, cols: List[str]) -> str:
        cols = cols[:4]
        ncols = min(2, len(cols))
        nrows = (len(cols) + 1) // 2
        fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 3.5 * nrows))
        fig.patch.set_facecolor("#0d0d14")
        axes_flat = np.array(axes).flatten() if len(cols) > 1 else [axes]
        for i, col in enumerate(cols):
            ax = axes_flat[i]
            ax.set_facecolor("#111118")
            vc = df[col].value_counts().head(8)
            bars = ax.barh(vc.index.astype(str), vc.values, color=PALETTE[i % len(PALETTE)], alpha=0.8)
            ax.set_title(col, color="#e5e7eb", fontsize=9)
            ax.tick_params(colors="#6b7280", labelsize=7)
            for spine in ax.spines.values(): spine.set_visible(False)
        for j in range(len(cols), len(axes_flat)):
            axes_flat[j].set_visible(False)
        fig.suptitle("Categorical Value Distributions", color="#f3f4f6", fontsize=12)
        fig.tight_layout()
        return _fig_to_b64(fig)

    def _data_quality_score(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute a composite data quality score 0-100."""
        completeness = (1 - df.isnull().mean().mean()) * 100
        uniqueness   = min(100.0, (1 - df.duplicated().mean()) * 100)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        validity     = 100.0
        if len(numeric_cols):
            neg_issues = sum(1 for c in numeric_cols if (df[c] < 0).any()
                             and any(k in c.lower() for k in ["price","amount","quantity","age"]))
            validity = max(0, 100 - neg_issues * 20)
        overall = round((completeness * 0.5 + uniqueness * 0.3 + validity * 0.2), 1)
        return {
            "overall":      overall,
            "completeness": round(completeness, 1),
            "uniqueness":   round(uniqueness, 1),
            "validity":     round(validity, 1),
        }
