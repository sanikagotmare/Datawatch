from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id                   = Column(Integer, primary_key=True, index=True)
    title                = Column(String(255), nullable=False)
    description          = Column(Text)
    severity             = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    status               = Column(String(20), default="OPEN")  # OPEN, INVESTIGATING, RESOLVED
    root_cause           = Column(Text)
    business_impact      = Column(Text)
    suggested_resolution = Column(Text)
    confidence_score     = Column(Float)
    affected_column      = Column(String(100))
    created_at           = Column(DateTime, default=datetime.utcnow)
    resolved_at          = Column(DateTime)
    user_id              = Column(Integer, ForeignKey("users.id"),     nullable=False)
    pipeline_id          = Column(Integer, ForeignKey("pipelines.id"), nullable=True)
    dataset_id           = Column(Integer, ForeignKey("datasets.id"),  nullable=True)

    user     = relationship("User",     back_populates="incidents")
    pipeline = relationship("Pipeline", back_populates="incidents")
    dataset  = relationship("Dataset")
