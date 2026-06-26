from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from typing import Optional
import json
from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.dataset import Dataset, AnalysisReport
from services.dataset_service import analyze_dataset

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("/upload")
async def upload(
    file:        UploadFile = File(...),
    pipeline_id: Optional[int] = Form(None),
    db:          Session = Depends(get_db),
    user:        User    = Depends(get_current_user)
):
    if not file.filename.endswith((".csv", ".json")):
        raise HTTPException(400, detail="Only CSV and JSON files supported")
    try:
        contents = await file.read()
        dataset  = analyze_dataset(db, contents, file.filename, user.id, pipeline_id)
        return {
            "id":             dataset.id,
            "filename":       dataset.filename,
            "rows":           dataset.row_count or 0,
            "columns":        dataset.column_count or 0,
            "healthScore":    dataset.health_score or 0,
            "severity":       dataset.severity or "unknown",
            "analysisStatus": dataset.analysis_status,
            "createdAt":      dataset.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("")
def list_datasets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    datasets = db.query(Dataset)\
        .filter(Dataset.user_id == user.id)\
        .order_by(Dataset.created_at.desc()).all()
    return [{
        "id":             d.id,
        "filename":       d.filename,
        "rows":           d.row_count or 0,
        "columns":        d.column_count or 0,
        "healthScore":    d.health_score or 0,
        "severity":       d.severity or "unknown",
        "analysisStatus": d.analysis_status,
        "createdAt":      d.created_at.isoformat()
    } for d in datasets]


@router.get("/{dataset_id}/report")
def get_report(dataset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == user.id).first()
    if not dataset:
        raise HTTPException(404, detail="Dataset not found")
    report = db.query(AnalysisReport).filter(AnalysisReport.dataset_id == dataset_id).first()
    if not report or not report.raw_response:
        raise HTTPException(404, detail="Report not ready yet")
    return json.loads(report.raw_response)
