from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class IncidentCreate(BaseModel):
    title:               str = Field(min_length=2)
    description:         Optional[str] = None
    severity:            str
    root_cause:          Optional[str] = None
    business_impact:     Optional[str] = None
    suggested_resolution:Optional[str] = None
    confidence_score:    Optional[float] = None
    affected_column:     Optional[str] = None
    pipeline_id:         Optional[int] = None
    dataset_id:          Optional[int] = None


class IncidentUpdate(BaseModel):
    status:      Optional[str] = None
    description: Optional[str] = None


class IncidentOut(BaseModel):
    id:                   int
    title:                str
    description:          Optional[str]
    severity:             str
    status:               str
    root_cause:           Optional[str]
    business_impact:      Optional[str]
    suggested_resolution: Optional[str]
    confidence_score:     Optional[float]
    affected_column:      Optional[str]
    pipeline_id:          Optional[int]
    dataset_id:           Optional[int]
    created_at:           datetime
    resolved_at:          Optional[datetime]

    class Config:
        from_attributes = True
