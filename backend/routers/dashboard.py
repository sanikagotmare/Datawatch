from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.dataset import Dataset
from models.pipeline import Pipeline, MonitoringHistory
from models.incident import Incident

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def get_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    uid    = user.id
    since  = datetime.utcnow() - timedelta(days=7)

    total_pipelines   = db.query(Pipeline).filter(Pipeline.user_id == uid).count()
    healthy_pipelines = db.query(Pipeline).filter(Pipeline.user_id == uid, Pipeline.status == "HEALTHY").count()
    warning_pipelines = db.query(Pipeline).filter(Pipeline.user_id == uid, Pipeline.status == "WARNING").count()
    failed_pipelines  = db.query(Pipeline).filter(Pipeline.user_id == uid, Pipeline.status == "FAILED").count()
    open_incidents    = db.query(Incident).filter(Incident.user_id == uid, Incident.status != "RESOLVED").count()
    critical_incidents= db.query(Incident).filter(Incident.user_id == uid, Incident.severity == "CRITICAL", Incident.status != "RESOLVED").count()
    total_datasets    = db.query(Dataset).filter(Dataset.user_id == uid).count()

    avg_health = db.query(func.avg(Dataset.health_score))\
        .filter(Dataset.user_id == uid, Dataset.health_score.isnot(None)).scalar()

    # 7-day anomaly total from monitoring runs
    pipeline_ids = [p.id for p in db.query(Pipeline.id).filter(Pipeline.user_id == uid).all()]
    total_anomalies  = 0
    monitoring_runs  = 0
    if pipeline_ids:
        total_anomalies = db.query(func.sum(MonitoringHistory.anomalies_found))\
            .filter(MonitoringHistory.pipeline_id.in_(pipeline_ids),
                    MonitoringHistory.execution_time >= since).scalar() or 0
        monitoring_runs = db.query(MonitoringHistory)\
            .filter(MonitoringHistory.pipeline_id.in_(pipeline_ids),
                    MonitoringHistory.execution_time >= since).count()

    recent_history = []
    if pipeline_ids:
        rows = db.query(MonitoringHistory)\
            .filter(MonitoringHistory.pipeline_id.in_(pipeline_ids))\
            .order_by(MonitoringHistory.execution_time.desc()).limit(14).all()
        recent_history = [{
            "id": h.id, "pipelineId": h.pipeline_id,
            "pipelineName": h.pipeline.name if h.pipeline else "",
            "executionTime": h.execution_time.isoformat(),
            "result": h.result, "anomaliesFound": h.anomalies_found,
            "durationMs": h.duration_ms or 0
        } for h in rows]

    recent_datasets = [{
        "id": d.id, "filename": d.filename,
        "healthScore": d.health_score or 0,
        "severity": d.severity or "unknown",
        "createdAt": d.created_at.isoformat()
    } for d in db.query(Dataset).filter(Dataset.user_id == uid)
                   .order_by(Dataset.created_at.desc()).limit(5).all()]

    recent_incidents = [{
        "id": i.id, "title": i.title, "severity": i.severity,
        "status": i.status, "createdAt": i.created_at.isoformat()
    } for i in db.query(Incident).filter(Incident.user_id == uid)
                   .order_by(Incident.created_at.desc()).limit(5).all()]

    return {
        "totalPipelines":          total_pipelines,
        "healthyPipelines":        healthy_pipelines,
        "warningPipelines":        warning_pipelines,
        "failedPipelines":         failed_pipelines,
        "openIncidents":           open_incidents,
        "criticalIncidents":       critical_incidents,
        "totalDatasets":           total_datasets,
        "avgHealthScore":          round(float(avg_health), 1) if avg_health else 0,
        "totalAnomaliesLast7Days": int(total_anomalies),
        "monitoringRunsLast7Days": monitoring_runs,
        "recentHistory":           recent_history,
        "recentDatasets":          recent_datasets,
        "recentIncidents":         recent_incidents,
    }
