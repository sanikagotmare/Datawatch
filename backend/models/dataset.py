from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id              = Column(Integer, primary_key=True, index=True)
    filename        = Column(String(255), nullable=False)
    file_size       = Column(BigInteger)
    row_count       = Column(Integer)
    column_count    = Column(Integer)
    upload_status   = Column(String(20), default="UPLOADED")
    analysis_status = Column(String(20), default="PENDING")
    health_score    = Column(Integer)
    severity        = Column(String(20))
    schema_snapshot = Column(Text)
    file_path       = Column(String(500))   # path to original uploaded file on disk
    created_at      = Column(DateTime, default=datetime.utcnow)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)

    user   = relationship("User",           back_populates="datasets")
    report = relationship("AnalysisReport", back_populates="dataset", uselist=False, cascade="all, delete-orphan")


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id                = Column(Integer, primary_key=True, index=True)
    dataset_id        = Column(Integer, ForeignKey("datasets.id"), unique=True)
    raw_response      = Column(Text)
    summary           = Column(Text)
    health_score      = Column(Integer)
    severity          = Column(String(20))
    anomaly_count     = Column(Integer, default=0)
    schema_issue_count= Column(Integer, default=0)
    pii_field_count   = Column(Integer, default=0)
    fix_count         = Column(Integer, default=0)
    created_at        = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="report")
