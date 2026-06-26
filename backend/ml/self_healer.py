"""
Self-Healing Data Engine — Feature 2
Automatically detects and fixes common data quality issues:
  1. Missing values    → fill numeric with median, categorical with mode
  2. Duplicate rows    → drop exact duplicates
  3. Data type issues  → attempt safe coercion
  4. Outliers          → FLAG only, never auto-delete

Returns a healing report and the cleaned DataFrame.
"""
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any


class SelfHealer:

    def heal(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Run all healing steps on the DataFrame.
        Returns (cleaned_df, healing_report)
        """
        report = {
            "original_rows":       len(df),
            "original_columns":    len(df.columns),
            "steps":               [],
            "missing_filled":      0,
            "duplicates_removed":  0,
            "type_fixes":          0,
            "outliers_flagged":    0,
            "final_rows":          0,
            "final_columns":       0,
        }

        cleaned = df.copy()

        # Step 1: Remove duplicates
        cleaned, report = self._remove_duplicates(cleaned, report)

        # Step 2: Fix data types
        cleaned, report = self._fix_dtypes(cleaned, report)

        # Step 3: Fill missing values
        cleaned, report = self._fill_missing(cleaned, report)

        # Step 4: Flag outliers (adds a column, never deletes rows)
        cleaned, report = self._flag_outliers(cleaned, report)

        report["final_rows"]    = len(cleaned)
        report["final_columns"] = len(cleaned.columns)

        return cleaned, report

    # ── Step 1 ──────────────────────────────────────────────────────────────
    def _remove_duplicates(self, df: pd.DataFrame, report: dict) -> Tuple[pd.DataFrame, dict]:
        before     = len(df)
        df_clean   = df.drop_duplicates()
        removed    = before - len(df_clean)
        report["duplicates_removed"] += removed
        if removed > 0:
            report["steps"].append({
                "step":    "Remove duplicates",
                "status":  "fixed",
                "detail":  f"Removed {removed} fully duplicate row(s)",
                "impact":  removed
            })
        else:
            report["steps"].append({
                "step":   "Remove duplicates",
                "status": "ok",
                "detail": "No duplicate rows found",
                "impact": 0
            })
        return df_clean, report

    # ── Step 2 ──────────────────────────────────────────────────────────────
    def _fix_dtypes(self, df: pd.DataFrame, report: dict) -> Tuple[pd.DataFrame, dict]:
        """
        Try to coerce object columns that look numeric into float.
        Example: "12,345" → 12345.0   or   " 99 " → 99.0
        """
        fixed  = 0
        detail = []
        for col in df.select_dtypes(include=["object"]).columns:
            sample = df[col].dropna().head(50)
            # Try stripping common formatting and converting to numeric
            cleaned_sample = sample.str.replace(",", "", regex=False).str.strip()
            numeric_ratio  = pd.to_numeric(cleaned_sample, errors="coerce").notna().mean()
            if numeric_ratio >= 0.8:  # 80%+ of non-null values look numeric
                before_nulls = df[col].isnull().sum()
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(",","",regex=False).str.strip(),
                    errors="coerce"
                )
                after_nulls = df[col].isnull().sum()
                coerced     = max(0, after_nulls - before_nulls)
                fixed      += 1
                detail.append(f"'{col}': object → numeric ({coerced} unparseable values set to NaN)")

        report["type_fixes"] += fixed
        report["steps"].append({
            "step":   "Fix data types",
            "status": "fixed" if fixed else "ok",
            "detail": "; ".join(detail) if detail else "All column types look correct",
            "impact": fixed
        })
        return df, report

    # ── Step 3 ──────────────────────────────────────────────────────────────
    def _fill_missing(self, df: pd.DataFrame, report: dict) -> Tuple[pd.DataFrame, dict]:
        """
        Numeric columns  → fill with median (robust to outliers)
        Categorical cols → fill with mode  (most common value)
        """
        total_filled = 0
        detail       = []

        for col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count == 0:
                continue

            if pd.api.types.is_numeric_dtype(df[col]):
                fill_val = df[col].median()
                if pd.isna(fill_val):
                    continue
                df[col] = df[col].fillna(fill_val)
                total_filled += null_count
                detail.append(f"'{col}': filled {null_count} nulls with median ({fill_val:.2f})")
            else:
                mode_vals = df[col].mode()
                if len(mode_vals) == 0:
                    continue
                fill_val = mode_vals[0]
                df[col] = df[col].fillna(fill_val)
                total_filled += null_count
                detail.append(f"'{col}': filled {null_count} nulls with mode ('{fill_val}')")

        report["missing_filled"] += total_filled
        report["steps"].append({
            "step":   "Fill missing values",
            "status": "fixed" if total_filled else "ok",
            "detail": "; ".join(detail[:5]) if detail else "No missing values found",
            "impact": total_filled
        })
        return df, report

    # ── Step 4 ──────────────────────────────────────────────────────────────
    def _flag_outliers(self, df: pd.DataFrame, report: dict) -> Tuple[pd.DataFrame, dict]:
        """
        Flag rows with extreme outliers (Z-score > 3) by adding a boolean column.
        We NEVER delete outliers automatically — they need human review.
        """
        from scipy import stats as scipy_stats

        numeric_cols  = df.select_dtypes(include=[np.number]).columns.tolist()
        flagged_total = 0
        outlier_mask  = pd.Series([False] * len(df), index=df.index)
        detail        = []

        for col in numeric_cols:
            clean = df[col].dropna()
            if len(clean) < 10:
                continue
            z       = np.abs(scipy_stats.zscore(clean))
            extreme = z > 3
            if extreme.any():
                count         = int(extreme.sum())
                flagged_total += count
                outlier_mask.loc[clean[extreme].index] = True
                detail.append(f"'{col}': {count} outlier(s) (Z>3)")

        if flagged_total > 0:
            df["_is_outlier"] = outlier_mask
            detail_str = "; ".join(detail[:5])
        else:
            detail_str = "No extreme outliers detected"

        report["outliers_flagged"] += flagged_total
        report["steps"].append({
            "step":   "Flag outliers",
            "status": "flagged" if flagged_total else "ok",
            "detail": detail_str + (" (rows kept — review before deleting)" if flagged_total else ""),
            "impact": flagged_total
        })
        return df, report

    def generate_summary(self, report: dict) -> str:
        """Plain-English healing summary."""
        lines = []
        if report["duplicates_removed"]  > 0: lines.append(f"✓ Removed {report['duplicates_removed']} duplicate row(s)")
        if report["missing_filled"]      > 0: lines.append(f"✓ Filled {report['missing_filled']} missing value(s)")
        if report["type_fixes"]          > 0: lines.append(f"✓ Fixed {report['type_fixes']} column type(s)")
        if report["outliers_flagged"]    > 0: lines.append(f"⚠ Flagged {report['outliers_flagged']} outlier(s) for review")
        if not lines:
            lines.append("✓ Dataset is already clean — no issues found")
        return "\n".join(lines)
