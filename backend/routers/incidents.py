from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.incident import Incident
from models.pipeline import Pipeline
from models.dataset import Dataset
from schemas.incident import IncidentCreate, IncidentUpdate, IncidentOut

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.post("")
def create(req: IncidentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    i = Incident(user_id=user.id, **req.model_dump())
    db.add(i); db.commit(); db.refresh(i)
    return _to_dict(i, db)


@router.get("")
def list_incidents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    incidents = db.query(Incident)\
        .filter(Incident.user_id == user.id)\
        .order_by(Incident.created_at.desc()).all()
    return [_to_dict(i, db) for i in incidents]


@router.get("/{incident_id}")
def get_incident(incident_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    i = _get_or_404(db, incident_id, user.id)
    return _to_dict(i, db)


@router.patch("/{incident_id}")
def update_incident(incident_id: int, req: IncidentUpdate,
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    i = _get_or_404(db, incident_id, user.id)
    if req.status:
        if req.status not in {"OPEN", "INVESTIGATING", "RESOLVED"}:
            raise HTTPException(400, detail="Invalid status")
        i.status = req.status
        if req.status == "RESOLVED":
            i.resolved_at = datetime.utcnow()
    if req.description:
        i.description = req.description
    db.commit(); db.refresh(i)
    return _to_dict(i, db)


def _get_or_404(db, incident_id, user_id):
    i = db.query(Incident).filter(Incident.id == incident_id, Incident.user_id == user_id).first()
    if not i:
        raise HTTPException(404, detail="Incident not found")
    return i


def _to_dict(i: Incident, db: Session) -> dict:
    pipeline_name = None
    dataset_name  = None
    if i.pipeline_id:
        p = db.query(Pipeline).filter(Pipeline.id == i.pipeline_id).first()
        pipeline_name = p.name if p else None
    if i.dataset_id:
        d = db.query(Dataset).filter(Dataset.id == i.dataset_id).first()
        dataset_name = d.filename if d else None
    return {
        "id": i.id, "title": i.title, "description": i.description,
        "severity": i.severity, "status": i.status,
        "rootCause": i.root_cause, "businessImpact": i.business_impact,
        "suggestedResolution": i.suggested_resolution,
        "confidenceScore": i.confidence_score, "affectedColumn": i.affected_column,
        "pipelineId": i.pipeline_id, "pipelineName": pipeline_name,
        "datasetId": i.dataset_id, "datasetName": dataset_name,
        "createdAt": i.created_at.isoformat(),
        "resolvedAt": i.resolved_at.isoformat() if i.resolved_at else None
    }
