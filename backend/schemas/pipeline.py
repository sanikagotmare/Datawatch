from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PipelineCreate(BaseModel):
    name:        str = Field(min_length=2, max_length=100)
    description: Optional[str] = None


class PipelineStatusUpdate(BaseModel):
    status: str


class MonitoringHistoryOut(BaseModel):
    id:                  int
    pipeline_id:         int
    execution_time:      datetime
    result:              str
    anomalies_found:     int
    schema_issues_found: int
    duration_ms:         int
    details:             Optional[str]

    class Config:
        from_attributes = True


class PipelineOut(BaseModel):
    id:              int
    name:            str
    description:     Optional[str]
    status:          str
    health_score:    int
    successful_runs: int
    failed_runs:     int
    last_run_at:     Optional[datetime]
    created_at:      datetime

    class Config:
        from_attributes = True
