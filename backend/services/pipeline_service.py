import io
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from models.pipeline import Pipeline, MonitoringHistory
from models.dataset import Dataset
from models.incident import Incident


def recalculate_health(db: Session, pipeline: Pipeline):
    total = pipeline.successful_runs + pipeline.failed_runs
    if total == 0:
        pipeline.health_score = 100
        pipeline.status = "HEALTHY"
    else:
        score = int((pipeline.successful_runs * 100) / total)
        pipeline.health_score = score
        pipeline.status = "HEALTHY" if score >= 80 else "WARNING" if score >= 50 else "FAILED"
    db.commit()


def run_monitoring_check(db: Session, pipeline: Pipeline) -> MonitoringHistory:
    """
    Run a monitoring check on a pipeline.
    If the pipeline has a connector configured, fetch live data and run full ML+LLM analysis.
    Otherwise fall back to checking the last uploaded CSV dataset.
    """
    start = datetime.utcnow()

    # --- Route 1: Real connector (DB or API) ---
    if pipeline.connector_type and pipeline.connector_type != "csv" and pipeline.connection_url and pipeline.query:
        return _run_connector_check(db, pipeline, start)

    # --- Route 2: CSV fallback (existing behaviour) ---
    return _run_csv_check(db, pipeline, start)


def _run_connector_check(db: Session, pipeline: Pipeline, start: datetime) -> MonitoringHistory:
    """Fetch live data from the configured connector and run full analysis."""
    from services.connector_service import fetch_data
    from services.dataset_service import analyze_dataframe

    try:
        df, message = fetch_data(pipeline.connector_type, pipeline.connection_url, pipeline.query)

        if df is None:
            pipeline.connector_status = "ERROR"
            pipeline.last_error = message
            db.commit()
            return _record_run(db, pipeline, "FAILURE", 0, 0,
                               int((datetime.utcnow()-start).total_seconds()*1000),
                               f"Connector error: {message}", "database")

        # Run the full ML + LLM analysis on the live dataframe
        result_data = analyze_dataframe(
            db=db,
            df=df,
            filename=f"{pipeline.name}_live_{datetime.utcnow().strftime('%Y%m%d_%H%M')}",
            user_id=pipeline.user_id,
            pipeline_id=pipeline.id,
            save_to_db=True
        )

        anomalies   = len(result_data.get("anomalies", []))
        schema_issues = len(result_data.get("schema_issues", []))
        result      = "WARNING" if anomalies >= 3 else "SUCCESS"
        duration    = int((datetime.utcnow()-start).total_seconds()*1000)

        pipeline.connector_status = "CONNECTED"
        pipeline.last_error       = None
        db.commit()

        # Auto-create incident if needed
        if anomalies >= 3:
            _maybe_create_incident(db, pipeline, anomalies, None)

        return _record_run(db, pipeline, result, anomalies, schema_issues,
                           duration, f"Live data: {len(df)} rows fetched from {pipeline.connector_type}",
                           pipeline.connector_type)

    except Exception as e:
        pipeline.connector_status = "ERROR"
        pipeline.last_error       = str(e)
        db.commit()
        return _record_run(db, pipeline, "FAILURE", 0, 0,
                           int((datetime.utcnow()-start).total_seconds()*1000),
                           f"Connector exception: {str(e)[:200]}", "database")


def _run_csv_check(db: Session, pipeline: Pipeline, start: datetime) -> MonitoringHistory:
    """
    Check the most recent dataset for this user.
    Uses the REAL anomaly count stored in analysis_reports — not an estimate.
    """
    from models.dataset import Dataset, AnalysisReport

    datasets = db.query(Dataset)\
        .filter(Dataset.user_id == pipeline.user_id,
                Dataset.analysis_status == "COMPLETED")\
        .order_by(Dataset.created_at.desc()).all()

    if not datasets:
        return _record_run(db, pipeline, "SUCCESS", 0, 0, 5,
                           "No datasets found. Upload a CSV to start monitoring.", "csv")

    latest   = datasets[0]
    duration = int((datetime.utcnow()-start).total_seconds()*1000)

    # Read REAL anomaly count from the stored analysis report
    report = db.query(AnalysisReport)\
               .filter(AnalysisReport.dataset_id == latest.id).first()

    if report:
        anomalies    = report.anomaly_count or 0
        schema_issues= report.schema_issue_count or 0
        detail       = (
            f"Dataset: {latest.filename} | "
            f"Health: {latest.health_score}% | "
            f"Anomalies: {anomalies} | "
            f"Schema issues: {schema_issues} | "
            f"PII fields: {report.pii_field_count or 0}"
        )
    else:
        anomalies    = 0
        schema_issues= 0
        detail       = f"No analysis report found for {latest.filename}"

    result = "WARNING" if anomalies >= 3 else "SUCCESS"

    if anomalies >= 3:
        _maybe_create_incident(db, pipeline, anomalies, latest)

    return _record_run(db, pipeline, result, anomalies, schema_issues,
                       duration, detail, "csv")


def _maybe_create_incident(db: Session, pipeline: Pipeline, anomalies: int, dataset):
    sev   = "CRITICAL" if anomalies >= 5 else "HIGH"
    title = f"[Auto] {anomalies} anomalies detected in pipeline: {pipeline.name}"
    exists = db.query(Incident).filter(
        Incident.user_id   == pipeline.user_id,
        Incident.title     == title,
        Incident.status    != "RESOLVED"
    ).first()
    if exists:
        return
    db.add(Incident(
        title                = title,
        description          = f"Scheduled monitoring found {anomalies} anomalies.",
        severity             = sev,
        root_cause           = "Automated health check detected data quality issues",
        business_impact      = "Downstream reports may contain inaccurate data",
        suggested_resolution = "Review dataset analysis report and apply suggested fixes",
        confidence_score     = 0.85,
        affected_column      = "multiple",
        user_id              = pipeline.user_id,
        pipeline_id          = pipeline.id,
        dataset_id           = dataset.id if dataset else None
    ))
    db.commit()


def _record_run(db: Session, pipeline: Pipeline, result: str,
                anomalies: int, schema_issues: int,
                duration_ms: int, details: str,
                source_type: str = "csv") -> MonitoringHistory:
    h = MonitoringHistory(
        pipeline_id         = pipeline.id,
        result              = result,
        anomalies_found     = anomalies,
        schema_issues_found = schema_issues,
        duration_ms         = duration_ms,
        details             = details,
        source_type         = source_type
    )
    db.add(h)

    if result in ("SUCCESS", "WARNING"):
        pipeline.successful_runs += 1
    else:
        pipeline.failed_runs += 1

    pipeline.last_run_at = datetime.utcnow()
    recalculate_health(db, pipeline)
    return h
