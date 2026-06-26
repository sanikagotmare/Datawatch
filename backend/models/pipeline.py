from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class Pipeline(Base):
    __tablename__ = "pipelines"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(100), nullable=False)
    description      = Column(Text)
    status           = Column(String(20), default="HEALTHY")  # HEALTHY, WARNING, FAILED
    health_score     = Column(Integer, default=100)
    successful_runs  = Column(Integer, default=0)
    failed_runs      = Column(Integer, default=0)
    last_run_at      = Column(DateTime)
    created_at       = Column(DateTime, default=datetime.utcnow)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Database / API connector fields
    connector_type   = Column(String(20))  # csv | postgresql | mysql | sqlite | api
    connection_url   = Column(Text)        # DB connection string or API URL
    query            = Column(Text)        # SQL query to run, or API endpoint path
    connector_status = Column(String(20), default="NOT_CONFIGURED")  # NOT_CONFIGURED | CONNECTED | ERROR
    last_error       = Column(Text)        # last connector error message if any

    user      = relationship("User",              back_populates="pipelines")
    history   = relationship("MonitoringHistory", back_populates="pipeline", cascade="all, delete-orphan")
    incidents = relationship("Incident",          back_populates="pipeline")


class MonitoringHistory(Base):
    __tablename__ = "monitoring_history"

    id                  = Column(Integer, primary_key=True, index=True)
    pipeline_id         = Column(Integer, ForeignKey("pipelines.id"), nullable=False)
    execution_time      = Column(DateTime, default=datetime.utcnow)
    result              = Column(String(20), nullable=False)  # SUCCESS, WARNING, FAILURE
    anomalies_found     = Column(Integer, default=0)
    schema_issues_found = Column(Integer, default=0)
    duration_ms         = Column(BigInteger, default=0)
    details             = Column(Text)
    source_type         = Column(String(20), default="csv")  # csv | database | api

    pipeline = relationship("Pipeline", back_populates="history")
