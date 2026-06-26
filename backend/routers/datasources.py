"""
Routers for:
  Feature 1 — Database Connectors  (/api/datasources)
  Feature 2 — Self-Healing Engine   (/api/heal)
  Feature 3 — Clean Data Export     (/api/heal/{id}/download)
"""
import numpy as np
import io
import json
import tempfile
import os
import pandas as pd
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.datasource import DataSource, DataSourceTable, HealingHistory
from models.dataset import Dataset
from services.datasource_service import (
    build_connection_url, test_connection,
    fetch_table_data, get_table_info
)
from ml.self_healer import SelfHealer
def convert_numpy(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    raise TypeError

router_ds     = APIRouter(prefix="/api/datasources", tags=["datasources"])
router_heal   = APIRouter(prefix="/api/heal",        tags=["healing"])

healer = SelfHealer()


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 1 — DATABASE CONNECTORS
# ═══════════════════════════════════════════════════════════════════════════

@router_ds.post("/test")
def test_db_connection(body: dict, user: User = Depends(get_current_user)):
    """Test a connection without saving it."""
    try:
        url = build_connection_url(
            db_type       = body.get("dbType", ""),
            host          = body.get("host", "localhost"),
            port          = int(body.get("port", 5432)),
            database_name = body.get("databaseName", ""),
            username      = body.get("username", ""),
            password      = body.get("password", "")
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

    success, message, tables = test_connection(url)
    return {"success": success, "message": message, "tables": tables[:50]}


@router_ds.post("")
def save_connection(body: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Save a database connection. Password is stored for demo; mask in production."""
    db_type       = body.get("dbType", "")
    host          = body.get("host", "localhost")
    port          = int(body.get("port") or 5432)
    database_name = body.get("databaseName", "")
    username      = body.get("username", "")
    password      = body.get("password", "")
    name          = body.get("name", f"{db_type}-{database_name}")

    try:
        url = build_connection_url(db_type, host, port, database_name, username, password)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

    # Test before saving
    success, message, tables = test_connection(url)

    source = DataSource(
        name          = name,
        db_type       = db_type,
        host          = host,
        port          = port,
        database_name = database_name,
        username      = username,
        password_hash = password,   # demo only
        connection_url= url,
        status        = "CONNECTED" if success else "ERROR",
        last_error    = None if success else message,
        last_tested_at= datetime.utcnow(),
        user_id       = user.id
    )
    db.add(source)
    db.flush()

    # Save discovered tables
    for t in get_table_info(url):
        db.add(DataSourceTable(
            source_id       = source.id,
            table_name      = t["table_name"],
            row_count       = t["row_count"],
            column_count    = t["column_count"],
            last_scanned_at = datetime.utcnow()
        ))

    db.commit(); db.refresh(source)
    return _source_dict(source, db)


@router_ds.get("")
def list_connections(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sources = db.query(DataSource).filter(DataSource.user_id == user.id)\
                .order_by(DataSource.created_at.desc()).all()
    return [_source_dict(s, db) for s in sources]


@router_ds.get("/{source_id}")
def get_connection(source_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = _get_source(db, source_id, user.id)
    return _source_dict(s, db)


@router_ds.post("/{source_id}/test")
def retest_connection(source_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = _get_source(db, source_id, user.id)
    success, message, tables = test_connection(s.connection_url)
    s.status         = "CONNECTED" if success else "ERROR"
    s.last_error     = None if success else message
    s.last_tested_at = datetime.utcnow()

    # Refresh tables
    for existing in db.query(DataSourceTable).filter(DataSourceTable.source_id == s.id).all():
        db.delete(existing)
    for t in get_table_info(s.connection_url):
        db.add(DataSourceTable(source_id=s.id, table_name=t["table_name"],
                               row_count=t["row_count"], column_count=t["column_count"],
                               last_scanned_at=datetime.utcnow()))
    db.commit(); db.refresh(s)
    return {"success": success, "message": message, "source": _source_dict(s, db)}


@router_ds.delete("/{source_id}")
def delete_connection(source_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = _get_source(db, source_id, user.id)
    db.delete(s); db.commit()
    return {"message": "Data source deleted"}


@router_ds.get("/{source_id}/tables/{table_name}/preview")
def preview_table(source_id: int, table_name: str,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return first 10 rows of a table for preview."""
    s = _get_source(db, source_id, user.id)
    df, msg = fetch_table_data(s.connection_url, table_name, row_limit=10)
    if df is None:
        raise HTTPException(400, detail=msg)
    return {
        "table":   table_name,
        "rows":    len(df),
        "columns": list(df.columns),
        "sample":  df.fillna("").to_dict(orient="records")
    }


@router_ds.post("/{source_id}/tables/{table_name}/analyze")
def analyze_table(source_id: int, table_name: str,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Fetch data from a DB table and run the full existing analysis pipeline
    (ML anomaly detection + LLM + RAG) — same as uploading a CSV.
    """
    from services.dataset_service import analyze_dataframe
    s = _get_source(db, source_id, user.id)
    df, msg = fetch_table_data(s.connection_url, table_name, row_limit=5000)
    if df is None:
        raise HTTPException(400, detail=msg)

    result = analyze_dataframe(
        db         = db,
        df         = df,
        filename   = f"{s.name}__{table_name}",
        user_id    = user.id,
        save_to_db = True
    )
    dataset_id = result.get("dataset_id")
    return {
        "message":    f"Analysis complete for table '{table_name}'",
        "dataset_id": dataset_id,
        "rows":       len(df),
        "columns":    len(df.columns),
        "anomalies":  len(result.get("anomalies", [])),
        "severity":   result.get("ai_report", {}).get("severity", "unknown")
    }


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 2 — SELF-HEALING ENGINE
# ═══════════════════════════════════════════════════════════════════════════

@router_heal.post("/dataset/{dataset_id}")
def heal_dataset(dataset_id: int,
                 db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """
    Auto-heal an existing uploaded dataset using the REAL original file.
    File is read from disk where it was saved during upload.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id,
                                        Dataset.user_id == user.id).first()
    if not dataset:
        raise HTTPException(404, detail="Dataset not found")

    # --- Use real original file if it exists ---
    if dataset.file_path and os.path.exists(dataset.file_path):
        try:
            if dataset.filename.endswith(".csv"):
                df = pd.read_csv(dataset.file_path)
            else:
                df = pd.read_json(dataset.file_path)
        except Exception as e:
            raise HTTPException(400, detail=f"Could not read original file: {e}")
    else:
        # Fallback: reconstruct from stored stats if file not on disk
        from models.dataset import AnalysisReport
        report_row = db.query(AnalysisReport).filter(AnalysisReport.dataset_id == dataset_id).first()
        if not report_row or not report_row.raw_response:
            raise HTTPException(400, detail="Original file not found and no analysis report available.")
        raw    = json.loads(report_row.raw_response)
        profile= raw.get("profile", {})
        stats  = profile.get("stats", {})
        df     = _reconstruct_df_from_stats(stats, raw.get("rows", 100))

    cleaned_df, heal_report = healer.heal(df)
    heal_report = json.loads(
    json.dumps(heal_report, default=convert_numpy)
    )
    summary = healer.generate_summary(heal_report)

    h = HealingHistory(
        dataset_id         = dataset_id,
        original_rows      = heal_report["original_rows"],
        original_columns   = heal_report["original_columns"],
        missing_filled     = heal_report["missing_filled"],
        duplicates_removed = heal_report["duplicates_removed"],
        type_fixes         = heal_report["type_fixes"],
        outliers_flagged   = heal_report["outliers_flagged"],
        cleaned_filename   = f"healed_{dataset.filename}",
        healing_report = json.dumps(heal_report, default=convert_numpy),
        user_id            = user.id
    )
    db.add(h); db.commit(); db.refresh(h)
    _save_cleaned_csv(h.id, cleaned_df)

    return {
        "healing_id":          h.id,
        "filename":            dataset.filename,
        "summary":             summary,
        "report":              heal_report,
        "original_rows":       heal_report["original_rows"],
        "final_rows":          heal_report["final_rows"],
        "missing_filled":      heal_report["missing_filled"],
        "duplicates_removed":  heal_report["duplicates_removed"],
        "type_fixes":          heal_report["type_fixes"],
        "outliers_flagged":    heal_report["outliers_flagged"],
        "steps":               heal_report["steps"],
        "preview":             cleaned_df.head(10).fillna("").to_dict(orient="records"),
        "columns":             list(cleaned_df.columns),
        "used_real_file":      dataset.file_path is not None and os.path.exists(dataset.file_path or "")
    }


@router_heal.post("/upload")
async def heal_uploaded_file(
    file: UploadFile = File(...),
    db:   Session   = Depends(get_db),
    user: User      = Depends(get_current_user)
):
    """
    Upload a CSV directly to the self-healing engine.
    Returns healing report + healed data preview.
    Stores HealingHistory so the cleaned file can be downloaded.
    """
    if not file.filename.endswith((".csv", ".json")):
        raise HTTPException(400, detail="Only CSV and JSON supported")

    contents = await file.read()
    if file.filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(contents))
    else:
        df = pd.read_json(io.BytesIO(contents))

    cleaned_df, heal_report = healer.heal(df)
    summary = healer.generate_summary(heal_report)

    # Store cleaned CSV in a temp file keyed by healing_id
    h = HealingHistory(
        original_rows      = heal_report["original_rows"],
        original_columns   = heal_report["original_columns"],
        missing_filled     = heal_report["missing_filled"],
        duplicates_removed = heal_report["duplicates_removed"],
        type_fixes         = heal_report["type_fixes"],
        outliers_flagged   = heal_report["outliers_flagged"],
        cleaned_filename   = f"healed_{file.filename}",
        healing_report = json.dumps(heal_report, default=str),
        user_id            = user.id
    )
    db.add(h); db.commit(); db.refresh(h)

    # Save cleaned CSV to temp storage
    _save_cleaned_csv(h.id, cleaned_df)

    return {
        "healing_id":          h.id,
        "filename":            file.filename,
        "summary":             summary,
        "report":              heal_report,
        "original_rows":       heal_report["original_rows"],
        "final_rows":          heal_report["final_rows"],
        "missing_filled":      heal_report["missing_filled"],
        "duplicates_removed":  heal_report["duplicates_removed"],
        "type_fixes":          heal_report["type_fixes"],
        "outliers_flagged":    heal_report["outliers_flagged"],
        "steps":               heal_report["steps"],
        "preview":             cleaned_df.head(10).fillna("").to_dict(orient="records"),
        "columns":             list(cleaned_df.columns)
    }


@router_heal.get("/history")
def healing_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(HealingHistory).filter(HealingHistory.user_id == user.id)\
              .order_by(HealingHistory.created_at.desc()).limit(20).all()
    return [_history_dict(h) for h in rows]


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE 3 — CLEAN DATA EXPORT
# ═══════════════════════════════════════════════════════════════════════════

@router_heal.get("/{healing_id}/download")
def download_cleaned_csv(healing_id: int,
                          db:   Session = Depends(get_db),
                          user: User    = Depends(get_current_user)):
    """Download the cleaned CSV for a completed healing job."""
    h = db.query(HealingHistory).filter(HealingHistory.id == healing_id,
                                         HealingHistory.user_id == user.id).first()
    if not h:
        raise HTTPException(404, detail="Healing record not found")

    csv_path = _get_cleaned_csv_path(healing_id)
    if not os.path.exists(csv_path):
        raise HTTPException(404, detail="Cleaned file not found. Re-run healing.")

    def iter_file():
        with open(csv_path, "rb") as f:
            yield from f

    filename = h.cleaned_filename or f"healed_{healing_id}.csv"
    return StreamingResponse(
        iter_file(),
        media_type   = "text/csv",
        headers      = {"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router_heal.get("/{healing_id}/preview")
def preview_cleaned(healing_id: int,
                     db:   Session = Depends(get_db),
                     user: User    = Depends(get_current_user)):
    """Return first 20 rows of the cleaned dataset."""
    h = db.query(HealingHistory).filter(HealingHistory.id == healing_id,
                                         HealingHistory.user_id == user.id).first()
    if not h:
        raise HTTPException(404, detail="Healing record not found")

    csv_path = _get_cleaned_csv_path(healing_id)
    if not os.path.exists(csv_path):
        raise HTTPException(404, detail="Cleaned file not found")

    df = pd.read_csv(csv_path)
    return {
        "rows":    len(df),
        "columns": list(df.columns),
        "preview": df.head(20).fillna("").to_dict(orient="records"),
        "report":  json.loads(h.healing_report) if h.healing_report else {}
    }


# ── Helpers ──────────────────────────────────────────────────────────────

TEMP_DIR = os.path.join(tempfile.gettempdir(), "datawatch_healed")
os.makedirs(TEMP_DIR, exist_ok=True)


def _get_cleaned_csv_path(healing_id: int) -> str:
    return os.path.join(TEMP_DIR, f"healed_{healing_id}.csv")


def _save_cleaned_csv(healing_id: int, df: pd.DataFrame):
    df.to_csv(_get_cleaned_csv_path(healing_id), index=False)


def _get_source(db: Session, source_id: int, user_id: int) -> DataSource:
    s = db.query(DataSource).filter(DataSource.id == source_id,
                                     DataSource.user_id == user_id).first()
    if not s:
        raise HTTPException(404, detail="Data source not found")
    return s


def _source_dict(s: DataSource, db: Session) -> dict:
    tables = db.query(DataSourceTable).filter(DataSourceTable.source_id == s.id).all()
    return {
        "id":           s.id,
        "name":         s.name,
        "dbType":       s.db_type,
        "host":         s.host,
        "port":         s.port,
        "databaseName": s.database_name,
        "username":     s.username,
        # Never expose password
        "status":       s.status,
        "lastError":    s.last_error,
        "lastTestedAt": s.last_tested_at.isoformat() if s.last_tested_at else None,
        "createdAt":    s.created_at.isoformat(),
        "tables":       [{"tableName": t.table_name, "rowCount": t.row_count,
                          "columnCount": t.column_count} for t in tables]
    }


def _history_dict(h: HealingHistory) -> dict:
    return {
        "id":                h.id,
        "datasetId":         h.dataset_id,
        "filename":          h.cleaned_filename,
        "originalRows":      h.original_rows,
        "finalRows":         h.original_rows - (h.duplicates_removed or 0),
        "missingFilled":     h.missing_filled,
        "duplicatesRemoved": h.duplicates_removed,
        "typeFixes":         h.type_fixes,
        "outliersCount":   h.outliers_flagged,
        "createdAt":         h.created_at.isoformat()
    }


def _reconstruct_df_from_stats(stats: dict, n_rows: int) -> pd.DataFrame:
    """
    Reconstruct a representative DataFrame from profiler stats for healing demo.
    Used when the original file isn't stored server-side.
    """
    import numpy as np
    rng  = np.random.default_rng(42)
    data = {}
    for col, info in stats.items():
        dtype      = info.get("dtype", "object")
        null_pct   = info.get("null_pct", 0) / 100
        null_mask  = rng.random(n_rows) < null_pct

        if "float" in dtype or "int" in dtype:
            mean = info.get("mean", 0) or 0
            std  = info.get("std",  1) or 1
            vals = rng.normal(mean, std, n_rows)
            vals = vals.astype(object)
            vals[null_mask] = None
        else:
            top  = info.get("top_values", {})
            cats = list(top.keys()) if top else ["A","B","C"]
            vals = rng.choice(cats, n_rows).astype(object)
            vals[null_mask] = None

        data[col] = vals

    # Inject a few duplicates for demo realism
    df = pd.DataFrame(data)
    if len(df) > 5:
        df = pd.concat([df, df.iloc[:3]], ignore_index=True)
    return df
