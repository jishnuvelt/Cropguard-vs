from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import CaseStatus, UserRole


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    language: str = Field(default="en", max_length=20)


class UserRead(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    language: str
    role: UserRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationCreate(BaseModel):
    expert_id: int
    diagnosis: str = Field(min_length=2, max_length=120)
    treatment_plan: str = Field(min_length=5)
    dosage: Optional[str] = Field(default=None, max_length=120)
    duration_days: Optional[int] = Field(default=None, ge=1, le=120)
    safety_notes: Optional[str] = None


class RecommendationRead(BaseModel):
    id: int
    case_id: int
    expert_id: int
    diagnosis: str
    treatment_plan: str
    dosage: Optional[str]
    duration_days: Optional[int]
    safety_notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FollowUpRead(BaseModel):
    id: int
    case_id: int
    farmer_id: int
    notes: Optional[str]
    outcome: Optional[str]
    image_path: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaseRead(BaseModel):
    id: int
    farmer_id: int
    expert_id: Optional[int]
    crop_name: str
    symptoms: str
    location: Optional[str]
    image_path: str
    predicted_disease: str
    ai_confidence: float
    severity_score: int
    ai_recommendation: str
    status: CaseStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaseDetail(CaseRead):
    recommendations: list[RecommendationRead]
    followups: list[FollowUpRead]


class WeatherCurrentRead(BaseModel):
    city: str
    country: Optional[str] = None
    observed_at_utc: Optional[str] = None
    temperature_c: Optional[float] = None
    feels_like_c: Optional[float] = None
    humidity_percent: Optional[int] = None
    condition: Optional[str] = None
    condition_detail: Optional[str] = None
