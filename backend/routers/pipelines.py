from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.pipeline import Pipeline, MonitoringHistory
from schemas.pipeline import PipelineCreate, PipelineOut, PipelineStatusUpdate
from services.pipeline_service import run_monitoring_check

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])

VALID_STATUSES = {"HEALTHY", "WARNING", "FAILED"}


@router.post("")
def create(req: PipelineCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = Pipeline(name=req.name, description=req.description, user_id=user.id)
    db.add(p); db.commit(); db.refresh(p)
    return _to_dict(p)


@router.get("")
def list_pipelines(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_to_dict(p) for p in
            db.query(Pipeline).filter(Pipeline.user_id == user.id)
              .order_by(Pipeline.created_at.desc()).all()]


@router.get("/{pipeline_id}")
def get_pipeline(pipeline_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = _get_or_404(db, pipeline_id, user.id)
    result = _to_dict(p)
    history = db.query(MonitoringHistory)\
        .filter(MonitoringHistory.pipeline_id == pipeline_id)\
        .order_by(MonitoringHistory.execution_time.desc()).limit(10).all()
    result["recentHistory"] = [_history_dict(h) for h in history]

    from models.incident import Incident
    open_incidents = db.query(Incident)\
        .filter(Incident.pipeline_id == pipeline_id, Incident.status != "RESOLVED").all()
    result["openIncidents"] = [{
        "id": i.id, "title": i.title, "severity": i.severity,
        "status": i.status, "createdAt": i.created_at.isoformat()
    } for i in open_incidents]
    return result


@router.patch("/{pipeline_id}/status")
def update_status(pipeline_id: int, req: PipelineStatusUpdate,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if req.status not in VALID_STATUSES:
        raise HTTPException(400, detail=f"Invalid status. Must be one of {VALID_STATUSES}")
    p = _get_or_404(db, pipeline_id, user.id)
    p.status = req.status; db.commit(); db.refresh(p)
    return _to_dict(p)


@router.delete("/{pipeline_id}")
def delete_pipeline(pipeline_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = _get_or_404(db, pipeline_id, user.id)
    db.delete(p); db.commit()
    return {"message": "Pipeline deleted"}


@router.post("/{pipeline_id}/run")
def trigger_run(pipeline_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = _get_or_404(db, pipeline_id, user.id)
    h = run_monitoring_check(db, p)
    return {"message": "Run triggered", "result": h.result, "anomaliesFound": h.anomalies_found}


@router.get("/{pipeline_id}/history")
def get_history(pipeline_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_or_404(db, pipeline_id, user.id)
    history = db.query(MonitoringHistory)\
        .filter(MonitoringHistory.pipeline_id == pipeline_id)\
        .order_by(MonitoringHistory.execution_time.desc()).all()
    return [_history_dict(h) for h in history]


def _get_or_404(db: Session, pipeline_id: int, user_id: int) -> Pipeline:
    p = db.query(Pipeline).filter(Pipeline.id == pipeline_id, Pipeline.user_id == user_id).first()
    if not p:
        raise HTTPException(404, detail="Pipeline not found")
    return p


def _to_dict(p: Pipeline) -> dict:
    return {
        "id": p.id, "name": p.name, "description": p.description,
        "status": p.status, "healthScore": p.health_score,
        "successfulRuns": p.successful_runs, "failedRuns": p.failed_runs,
        "lastRunAt":       p.last_run_at.isoformat() if p.last_run_at else None,
        "createdAt":       p.created_at.isoformat(),
        "connectorType":   p.connector_type,
        "connectorStatus": p.connector_status or "NOT_CONFIGURED",
        "hasConnector":    bool(p.connector_type and p.connector_type != "csv"),
        "lastError":       p.last_error,
        "query":           p.query,
    }


def _history_dict(h: MonitoringHistory) -> dict:
    return {
        "id": h.id, "pipelineId": h.pipeline_id,
        "executionTime": h.execution_time.isoformat(),
        "result": h.result, "anomaliesFound": h.anomalies_found,
        "schemaIssuesFound": h.schema_issues_found,
        "durationMs": h.duration_ms or 0,
        "details": h.details or ""
    }


# ── Connector endpoints ──────────────────────────────────────────────────────

@router.post("/{pipeline_id}/connector")
def save_connector(
    pipeline_id: int,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Save a connector config (DB connection string / API URL) to the pipeline."""
    p = _get_or_404(db, pipeline_id, user.id)

    connector_type = body.get("connectorType", "").lower()
    connection_url = body.get("connectionUrl", "").strip()
    query          = body.get("query", "").strip()

    if connector_type not in ("postgresql", "mysql", "sqlite", "api", "csv"):
        raise HTTPException(400, detail="Unsupported connector type")
    if connector_type != "csv" and not connection_url:
        raise HTTPException(400, detail="Connection URL is required")
    if connector_type in ("postgresql", "mysql", "sqlite") and not query:
        raise HTTPException(400, detail="SQL query is required for database connectors")

    p.connector_type   = connector_type
    p.connection_url   = connection_url
    p.query            = query
    p.connector_status = "NOT_CONFIGURED"
    p.last_error       = None
    db.commit(); db.refresh(p)
    return {**_to_dict(p), "message": "Connector saved. Click Test Connection to verify."}


@router.post("/{pipeline_id}/connector/test")
def test_connector(
    pipeline_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Test the connector — tries to fetch data and returns a preview."""
    from services.connector_service import fetch_data
    p = _get_or_404(db, pipeline_id, user.id)

    if not p.connector_type or p.connector_type == "csv":
        raise HTTPException(400, detail="No database/API connector configured on this pipeline.")
    if not p.connection_url or not p.query:
        raise HTTPException(400, detail="Connector is incomplete. Save connector config first.")

    df, message = fetch_data(p.connector_type, p.connection_url, p.query)

    if df is None:
        p.connector_status = "ERROR"
        p.last_error       = message
        db.commit()
        return {"success": False, "message": message, "preview": None}

    p.connector_status = "CONNECTED"
    p.last_error       = None
    db.commit()

    # Return a small preview of the data
    preview = {
        "rows":    len(df),
        "columns": list(df.columns),
        "sample":  df.head(3).fillna("").to_dict(orient="records")
    }
    return {"success": True, "message": message, "preview": preview}


@router.delete("/{pipeline_id}/connector")
def remove_connector(
    pipeline_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Remove the connector from a pipeline, reverting to CSV mode."""
    p = _get_or_404(db, pipeline_id, user.id)
    p.connector_type   = None
    p.connection_url   = None
    p.query            = None
    p.connector_status = "NOT_CONFIGURED"
    p.last_error       = None
    db.commit()
    return {"message": "Connector removed. Pipeline will use CSV uploads again."}
