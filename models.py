import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class UserRole(str, enum.Enum):
    farmer = "farmer"
    expert = "expert"


class CaseStatus(str, enum.Enum):
    ai_resolved = "ai_resolved"
    needs_expert = "needs_expert"
    expert_resolved = "expert_resolved"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True, unique=True)
    language = Column(String(20), nullable=False, default="en")
    role = Column(SqlEnum(UserRole), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    farmer_cases = relationship(
        "Case",
        back_populates="farmer",
        foreign_keys="Case.farmer_id",
    )
    expert_cases = relationship(
        "Case",
        back_populates="assigned_expert",
        foreign_keys="Case.expert_id",
    )
    recommendations = relationship("ExpertRecommendation", back_populates="expert")


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expert_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    crop_name = Column(String(80), nullable=False)
    symptoms = Column(Text, nullable=False)
    location = Column(String(120), nullable=True)
    image_path = Column(String(300), nullable=False)

    predicted_disease = Column(String(120), nullable=False)
    ai_confidence = Column(Float, nullable=False)
    severity_score = Column(Integer, nullable=False)
    ai_recommendation = Column(Text, nullable=False)
    status = Column(SqlEnum(CaseStatus), nullable=False, default=CaseStatus.needs_expert)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    farmer = relationship("User", back_populates="farmer_cases", foreign_keys=[farmer_id])
    assigned_expert = relationship(
        "User",
        back_populates="expert_cases",
        foreign_keys=[expert_id],
    )
    recommendations = relationship("ExpertRecommendation", back_populates="case")
    followups = relationship("FollowUp", back_populates="case")


class ExpertRecommendation(Base):
    __tablename__ = "expert_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    expert_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    diagnosis = Column(String(120), nullable=False)
    treatment_plan = Column(Text, nullable=False)
    dosage = Column(String(120), nullable=True)
    duration_days = Column(Integer, nullable=True)
    safety_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="recommendations")
    expert = relationship("User", back_populates="recommendations")


class FollowUp(Base):
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    outcome = Column(String(80), nullable=True)
    image_path = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="followups")
