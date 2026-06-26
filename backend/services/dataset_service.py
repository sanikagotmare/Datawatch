import numpy as np
import math
import json
import io
import os
from typing import Optional
import pandas as pd
from sqlalchemy.orm import Session
from models.dataset import Dataset, AnalysisReport
from models.incident import Incident
from models.pipeline import Pipeline
from ml.anomaly_detector import AnomalyDetector
from ml.data_profiler import DataProfiler
from ml.schema_detector import SchemaDetector
from services.llm_service import LLMService

# Directory where uploaded files are stored permanently
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploaded_files")
os.makedirs(UPLOAD_DIR, exist_ok=True)
from services.memory_service import MemoryService


llm     = LLMService()
memory  = MemoryService()
schema_detector = SchemaDetector()
profiler        = DataProfiler()
def clean_for_json(obj):
    """
    Recursively convert NaN, Inf, numpy values
    into JSON-safe values.
    """
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [clean_for_json(v) for v in obj]

    if isinstance(obj, tuple):
        return [clean_for_json(v) for v in obj]

    if isinstance(obj, np.integer):
        return int(obj)

    if isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    return obj


def analyze_dataset(db: Session, file_bytes: bytes, filename: str,
                    user_id: int, pipeline_id: Optional[int] = None) -> Dataset:
    """
    Full analysis pipeline:
    1. Parse CSV/JSON
    2. ML anomaly detection (Isolation Forest + Z-score)
    3. Data profiling (charts + stats)
    4. Schema drift detection
    5. PII detection
    6. RAG memory retrieval
    7. LLM diagnosis + explainability
    8. Store results + auto-create incidents
    """
    # Parse file
    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_bytes))
    elif filename.endswith(".json"):
        df = pd.read_json(io.BytesIO(file_bytes))
    else:
        raise ValueError("Only CSV and JSON supported")

    # Create dataset record
    dataset = Dataset(
        filename=filename, file_size=len(file_bytes),
        upload_status="UPLOADED", analysis_status="PROCESSING",
        user_id=user_id
    )
    db.add(dataset); db.flush()

    # Save original file to disk so healing can use the real data later
    file_path = os.path.join(UPLOAD_DIR, f"{dataset.id}_{filename}")
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    dataset.file_path = file_path

    try:
        # --- Step 1: ML anomaly detection ---
        detector  = AnomalyDetector(contamination=0.1)
        anomalies = detector.detect(df)
        ml_scores = detector.get_anomaly_scores(df)

        # --- Step 2: Data profiling (charts + stats) ---
        profile = profiler.profile(df, filename)

        # --- Step 3: Schema drift ---
        prev_schema = _get_previous_schema(db, user_id)
        schema_issues = schema_detector.detect_drift(df, prev_schema)
        current_schema = schema_detector.get_schema(df)

        # --- Step 4: PII detection ---
        pii_fields = schema_detector.detect_pii(df)

        # --- Step 5: RAG retrieval ---
        issue_desc = " ".join([f"{a['type']} in {a['column']}" for a in anomalies] +
                               [f"{s['type']} on {s['column']}" for s in schema_issues]) or "general"
        past_fixes = memory.retrieve(issue_desc, top_k=5)

        # --- Step 6: LLM diagnosis ---
        ml_summary = {
            "isolation_forest_anomalies": [a for a in anomalies if a.get("detection_method") == "isolation_forest_ml"],
            "statistical_outliers":       [a for a in anomalies if a.get("detection_method") == "zscore_statistical"],
            "anomaly_score_sample":       ml_scores.get("scores", [])[:10]
        }
        llm_result = llm.diagnose(
            df_sample=df.head(5).to_dict(),
            stats={"total_rows": len(df), "total_columns": len(df.columns)},
            anomalies=anomalies,
            schema_issues=schema_issues,
            pii_fields=pii_fields,
            past_fixes=past_fixes,
            ml_results=ml_summary
        )

        # --- Step 7: Store in RAG memory ---
        if anomalies:
            affected = list(set([a["column"] for a in anomalies if a.get("column")]))
            issue_types = list(set([a["type"] for a in anomalies]))
            memory.store(
                issue_type=", ".join(issue_types),
                dataset_meta={"rows": len(df), "cols": len(df.columns), "columns_affected": ", ".join(affected[:5])},
                suggested_fixes=llm_result.get("recommended_fixes", []),
                outcome="auto_detected",
                confidence=0.85,
                dataset_id=str(dataset.id)
            )

        # --- Step 8: Update dataset record ---
        health = llm_result.get("overall_data_health_score", profile["quality"]["overall"])
        dataset.row_count       = len(df)
        dataset.column_count    = len(df.columns)
        dataset.analysis_status = "COMPLETED"
        dataset.health_score    = int(health)
        dataset.severity        = llm_result.get("severity", "unknown")
        dataset.schema_snapshot = json.dumps(current_schema)

        # --- Step 9: Save full analysis report ---
        full_result = clean_for_json({
        "filename": filename,
        "rows": len(df),
        "columns": len(df.columns),
        "profile": profile,
        "anomalies": anomalies,
        "schema_issues": schema_issues,
        "pii_fields": pii_fields,
        "ai_report": llm_result,
        "past_similar_fixes": past_fixes,
        "ml_scores": ml_scores
        })
        report = AnalysisReport(
            dataset_id= dataset.id,
            raw_response = json.dumps(full_result,
            default=lambda x: None
            ),
            summary           = llm_result.get("summary", ""),
            health_score      = int(health),
            severity          = llm_result.get("severity", "unknown"),
            anomaly_count     = len(anomalies),
            schema_issue_count= len(schema_issues),
            pii_field_count   = len(pii_fields),
            fix_count         = len(llm_result.get("recommended_fixes", []))
        )
        db.add(report)

        # --- Step 10: Auto-create incident if high/critical ---
        sev = llm_result.get("severity", "")
        if sev in ("high", "critical"):
            issues = llm_result.get("issues", [])
            if issues:
                first = issues[0]
                pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first() if pipeline_id else None
                _auto_create_incident(
                    db, user_id,
                    title=f"[Auto] {first.get('title','Data quality issue')}",
                    description=llm_result.get("summary",""),
                    severity="CRITICAL" if sev=="critical" else "HIGH",
                    root_cause=first.get("description",""),
                    business_impact=first.get("impact",""),
                    suggested_resolution=f"{len(issues)} issue(s) found. Review full report.",
                    confidence=0.9,
                    affected_column=first.get("column","multiple"),
                    pipeline=pipeline,
                    dataset=dataset
                )

        db.commit()
        db.refresh(dataset)
        return dataset

    except Exception as e:
        dataset.analysis_status = "FAILED"
        db.commit()
        raise e


def _get_previous_schema(db: Session, user_id: int):
    latest = db.query(Dataset)\
        .filter(Dataset.user_id == user_id, Dataset.schema_snapshot.isnot(None))\
        .order_by(Dataset.created_at.desc()).first()
    if latest and latest.schema_snapshot:
        try:
            return json.loads(latest.schema_snapshot)
        except Exception:
            return None
    return None


def _auto_create_incident(db: Session, user_id: int, title: str, description: str,
                           severity: str, root_cause: str, business_impact: str,
                           suggested_resolution: str, confidence: float,
                           affected_column: str, pipeline, dataset):
    existing = db.query(Incident).filter(
        Incident.user_id == user_id,
        Incident.title == title,
        Incident.status != "RESOLVED"
    ).first()
    if existing:
        return
    incident = Incident(
        title=title, description=description, severity=severity,
        root_cause=root_cause, business_impact=business_impact,
        suggested_resolution=suggested_resolution,
        confidence_score=confidence, affected_column=affected_column,
        user_id=user_id,
        pipeline_id=pipeline.id if pipeline else None,
        dataset_id=dataset.id if dataset else None
    )
    db.add(incident)


def analyze_dataframe(db: Session, df, filename: str, user_id: int,
                       pipeline_id: Optional[int] = None, save_to_db: bool = True) -> dict:
    """
    Run the full ML + LLM analysis pipeline on an already-loaded DataFrame.
    Used by the connector service when fetching live data from a DB or API.
    """
    detector  = AnomalyDetector(contamination=0.1)
    anomalies = detector.detect(df)
    ml_scores = detector.get_anomaly_scores(df)
    profile   = profiler.profile(df, filename)

    prev_schema   = _get_previous_schema(db, user_id)
    schema_issues = schema_detector.detect_drift(df, prev_schema)
    current_schema = schema_detector.get_schema(df)
    pii_fields    = schema_detector.detect_pii(df)

    issue_desc = " ".join([f"{a['type']} in {a['column']}" for a in anomalies]) or "general"
    past_fixes = memory.retrieve(issue_desc, top_k=5)

    ml_summary = {
        "isolation_forest_anomalies": [a for a in anomalies if a.get("detection_method") == "isolation_forest_ml"],
        "statistical_outliers":       [a for a in anomalies if a.get("detection_method") == "zscore_statistical"],
    }
    llm_result = llm.diagnose(
        df_sample=df.head(5).to_dict(),
        stats={"total_rows": len(df), "total_columns": len(df.columns)},
        anomalies=anomalies, schema_issues=schema_issues,
        pii_fields=pii_fields, past_fixes=past_fixes, ml_results=ml_summary
    )

    saved_dataset_id = None

    if save_to_db:
        health  = llm_result.get("overall_data_health_score", profile["quality"]["overall"])
        dataset = Dataset(
            filename=filename, file_size=0, row_count=len(df),
            column_count=len(df.columns), upload_status="CONNECTOR",
            analysis_status="COMPLETED", health_score=int(health),
            severity=llm_result.get("severity","unknown"),
            schema_snapshot=json.dumps(current_schema), user_id=user_id
        )
        db.add(dataset); db.flush()
        saved_dataset_id = dataset.id

        report_data = {
    "filename": filename,
    "rows": len(df),
    "columns": len(df.columns),
    "profile": profile,
    "anomalies": anomalies,
    "schema_issues": schema_issues,
    "pii_fields": pii_fields,
    "ai_report": llm_result,
    "past_similar_fixes": past_fixes,
    "ml_scores": ml_scores
}

        report_data = {
    "filename": filename,
    "rows": len(df),
    "columns": len(df.columns),
    "profile": profile,
    "anomalies": anomalies,
    "schema_issues": schema_issues,
    "pii_fields": pii_fields,
    "ai_report": llm_result,
    "past_similar_fixes": past_fixes,
    "ml_scores": ml_scores
}

        report = AnalysisReport(
        dataset_id=dataset.id,
        summary=llm_result.get("summary", ""),
        health_score=int(health),
        severity=llm_result.get("severity", "unknown"),
        anomaly_count=len(anomalies),
        schema_issue_count=len(schema_issues),
        pii_field_count=len(pii_fields),
        fix_count=len(llm_result.get("recommended_fixes", [])),
        raw_response=json.dumps(
          report_data,
          default=lambda x: None
            )
        )
        db.add(report); db.commit()

        # auto-create incident for high/critical severity
        sev = llm_result.get("severity", "")
        issues = llm_result.get("issues", [])
        if sev in ("high", "critical") and issues:
            first = issues[0]
            _auto_create_incident(
                db, user_id,
                title=f"[Auto] {first.get('title','Data quality issue')}",
                description=llm_result.get("summary",""),
                severity="CRITICAL" if sev == "critical" else "HIGH",
                root_cause=first.get("description",""),
                business_impact=first.get("impact",""),
                suggested_resolution=f"{len(issues)} issue(s) detected. Review report.",
                confidence=0.9,
                affected_column=first.get("column","multiple"),
                pipeline=None, dataset=dataset
            )

    return {
        "dataset_id":   saved_dataset_id,
        "anomalies":    anomalies,
        "schema_issues":schema_issues,
        "pii_fields":   pii_fields,
        "ai_report":    llm_result,
        "profile":      profile
    }
