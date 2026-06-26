"""
ML Anomaly Detection Engine
Uses Isolation Forest (unsupervised ML) + Z-score statistics.
This is what makes DataWatch an actual AI/ML project, not just an LLM wrapper.
"""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Any


class AnomalyDetector:

    def __init__(self, contamination: float = 0.1):
        """
        contamination: expected fraction of anomalies in data (0.0 to 0.5)
        Default 10% — adjust based on domain.
        """
        self.contamination = contamination
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.is_fitted = False

    def detect(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Run full anomaly detection pipeline on a DataFrame."""
        issues = []
        issues.extend(self._missing_value_analysis(df))
        issues.extend(self._isolation_forest_detection(df))
        issues.extend(self._zscore_outliers(df))
        issues.extend(self._negative_value_check(df))
        issues.extend(self._duplicate_detection(df))
        issues.extend(self._cardinality_analysis(df))
        return issues

    def _missing_value_analysis(self, df: pd.DataFrame) -> List[Dict]:
        issues = []
        for col in df.columns:
            null_pct = df[col].isnull().mean() * 100
            if null_pct > 0:
                severity = "critical" if null_pct > 50 else "high" if null_pct > 30 else "medium" if null_pct > 10 else "low"
                issues.append({
                    "type": "missing_values",
                    "column": col,
                    "severity": severity,
                    "detail": f"{null_pct:.1f}% null values ({int(df[col].isnull().sum())} rows)",
                    "affected_rows": int(df[col].isnull().sum()),
                    "detection_method": "statistical"
                })
        return issues

    def _isolation_forest_detection(self, df: pd.DataFrame) -> List[Dict]:
        """
        Isolation Forest: an unsupervised ML algorithm that isolates anomalies
        by randomly selecting a feature and split value. Anomalies need fewer
        splits to isolate — hence a shorter path length in the tree.
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            return []

        X = df[numeric_cols].dropna()
        if len(X) < 10:
            return []

        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True

        predictions  = self.model.predict(X_scaled)  # -1 = anomaly, 1 = normal
        scores       = self.model.score_samples(X_scaled)  # more negative = more anomalous
        anomaly_mask = predictions == -1
        anomaly_count = int(anomaly_mask.sum())

        if anomaly_count == 0:
            return []

        # Find which columns contribute most to anomalies
        anomaly_rows     = X[anomaly_mask]
        normal_rows      = X[~anomaly_mask]
        contributing_cols = []
        for col in numeric_cols:
            if col in anomaly_rows.columns:
                a_mean = anomaly_rows[col].mean()
                n_mean = normal_rows[col].mean() if len(normal_rows) > 0 else 0
                if n_mean != 0 and abs((a_mean - n_mean) / n_mean) > 0.3:
                    contributing_cols.append(col)

        avg_anomaly_score = float(scores[anomaly_mask].mean())

        return [{
            "type": "ml_anomaly_cluster",
            "column": ", ".join(contributing_cols[:3]) if contributing_cols else "multiple",
            "severity": "high" if anomaly_count > len(X) * 0.15 else "medium",
            "detail": (
                f"Isolation Forest detected {anomaly_count} anomalous rows "
                f"(avg isolation score: {avg_anomaly_score:.3f}). "
                f"Most anomalous features: {', '.join(contributing_cols[:3]) if contributing_cols else 'multiple columns'}"
            ),
            "affected_rows": anomaly_count,
            "detection_method": "isolation_forest_ml",
            "anomaly_score": avg_anomaly_score,
            "contributing_columns": contributing_cols
        }]

    def _zscore_outliers(self, df: pd.DataFrame) -> List[Dict]:
        issues = []
        for col in df.select_dtypes(include=[np.number]).columns:
            clean = df[col].dropna()
            if len(clean) < 10:
                continue
            z_scores = np.abs(stats.zscore(clean))
            outlier_count = int((z_scores > 3).sum())
            if outlier_count > 0:
                max_z = float(z_scores.max())
                issues.append({
                    "type": "statistical_outlier",
                    "column": col,
                    "severity": "high" if max_z > 5 else "medium",
                    "detail": f"{outlier_count} outliers with Z-score > 3 (max Z={max_z:.2f})",
                    "affected_rows": outlier_count,
                    "detection_method": "zscore_statistical",
                    "max_zscore": max_z
                })
        return issues

    def _negative_value_check(self, df: pd.DataFrame) -> List[Dict]:
        issues = []
        financial_keywords = ["price","amount","revenue","quantity","age","count","salary","cost","fee","balance"]
        for col in df.select_dtypes(include=[np.number]).columns:
            if any(k in col.lower() for k in financial_keywords):
                clean = df[col].dropna()
                neg_count = int((clean < 0).sum())
                if neg_count > 0:
                    issues.append({
                        "type": "invalid_negative_values",
                        "column": col,
                        "severity": "high",
                        "detail": f"{neg_count} unexpected negative values in financial column",
                        "affected_rows": neg_count,
                        "detection_method": "domain_rule"
                    })
        return issues

    def _duplicate_detection(self, df: pd.DataFrame) -> List[Dict]:
        dup_count = int(df.duplicated().sum())
        if dup_count > 0:
            return [{
                "type": "duplicate_rows",
                "column": "all",
                "severity": "high",
                "detail": f"{dup_count} fully duplicate rows found",
                "affected_rows": dup_count,
                "detection_method": "exact_match"
            }]
        return []

    def _cardinality_analysis(self, df: pd.DataFrame) -> List[Dict]:
        issues = []
        for col in df.select_dtypes(include=["object"]).columns:
            if df[col].nunique() == 1:
                issues.append({
                    "type": "zero_variance",
                    "column": col,
                    "severity": "low",
                    "detail": f"Column has only 1 unique value across all {len(df)} rows",
                    "affected_rows": 0,
                    "detection_method": "cardinality_check"
                })
        return issues

    def get_anomaly_scores(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Return per-row anomaly scores for visualization."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2 or not self.is_fitted:
            return {"scores": [], "columns": numeric_cols}

        X = df[numeric_cols].fillna(df[numeric_cols].median())
        X_scaled = self.scaler.transform(X)
        scores = self.model.score_samples(X_scaled).tolist()
        return {"scores": scores, "columns": numeric_cols, "threshold": float(np.percentile(scores, 10))}
