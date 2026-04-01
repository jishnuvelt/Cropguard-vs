from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from .ai_engine import analyze_case
from .database import Base, SessionLocal, engine, get_db
from .models import Case, CaseStatus, ExpertRecommendation, FollowUp, User, UserRole
from .schemas import (
    CaseDetail,
    CaseRead,
    FollowUpRead,
    RecommendationCreate,
    RecommendationRead,
    UserCreate,
    UserRead,
    WeatherCurrentRead,
)
from .services import (
    STATIC_DIR,
    TEMPLATE_DIR,
    UPLOAD_DIR,
    ensure_runtime_dirs,
    get_next_expert_id,
    get_users_by_role,
    save_upload_file,
    seed_demo_users,
)
from .weather import fetch_current_weather_from_env, WeatherServiceError

app = FastAPI(
    title="CropGuard API",
    description="Plant disease triage and expert-assisted advisory system",
    version="1.0.0",
)
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.on_event("startup")
def on_startup() -> None:
    ensure_runtime_dirs()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_users(db)


def _get_user_or_404(db: Session, user_id: int, expected_role: Optional[UserRole] = None) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if expected_role and user.role != expected_role:
        raise HTTPException(status_code=400, detail=f"User must have role '{expected_role.value}'.")
    return user


async def _create_case(
    db: Session,
    farmer_id: int,
    crop_name: str,
    symptoms: str,
    location: str,
    image: UploadFile,
) -> Case:
    _get_user_or_404(db, farmer_id, UserRole.farmer)

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported.")

    image_path = await save_upload_file(image)
    triage = analyze_case(symptoms=symptoms, crop_name=crop_name, filename=image.filename or "")
    status_value = CaseStatus.needs_expert if triage["needs_expert"] else CaseStatus.ai_resolved
    expert_id = get_next_expert_id(db) if status_value == CaseStatus.needs_expert else None

    case = Case(
        farmer_id=farmer_id,
        expert_id=expert_id,
        crop_name=crop_name.strip(),
        symptoms=symptoms.strip(),
        location=location.strip(),
        image_path=image_path,
        predicted_disease=triage["disease"],
        ai_confidence=triage["confidence"],
        severity_score=triage["severity"],
        ai_recommendation=triage["recommendation"],
        status=status_value,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def _load_case_detail(db: Session, case_id: int) -> Case:
    case = (
        db.execute(
            select(Case)
            .options(selectinload(Case.recommendations), selectinload(Case.followups))
            .where(Case.id == case_id)
        )
        .scalars()
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/weather/current", response_model=WeatherCurrentRead)
def get_current_weather(
    city: str = Query(..., min_length=2, description="City name, e.g., Chennai"),
    units: str = Query("metric", pattern="^(standard|metric|imperial)$"),
) -> dict:
    try:
        return fetch_current_weather_from_env(city=city, units=units)
    except WeatherServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/farmers", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_farmer(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    farmer = User(
        name=payload.name.strip(),
        phone=payload.phone,
        language=payload.language,
        role=UserRole.farmer,
    )
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return farmer


@app.post("/api/experts", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_expert(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    expert = User(
        name=payload.name.strip(),
        phone=payload.phone,
        language=payload.language,
        role=UserRole.expert,
    )
    db.add(expert)
    db.commit()
    db.refresh(expert)
    return expert


@app.get("/api/farmers", response_model=list[UserRead])
def list_farmers(db: Session = Depends(get_db)) -> list[User]:
    return get_users_by_role(db, UserRole.farmer)


@app.get("/api/experts", response_model=list[UserRead])
def list_experts(db: Session = Depends(get_db)) -> list[User]:
    return get_users_by_role(db, UserRole.expert)


@app.post("/api/cases", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
async def create_case(
    farmer_id: int = Form(...),
    crop_name: str = Form(...),
    symptoms: str = Form(...),
    location: str = Form(""),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Case:
    return await _create_case(db, farmer_id, crop_name, symptoms, location, image)


@app.get("/api/cases/{case_id}", response_model=CaseDetail)
def get_case(case_id: int, db: Session = Depends(get_db)) -> Case:
    return _load_case_detail(db, case_id)


@app.get("/api/farmers/{farmer_id}/cases", response_model=list[CaseRead])
def list_farmer_cases(farmer_id: int, db: Session = Depends(get_db)) -> list[Case]:
    _get_user_or_404(db, farmer_id, UserRole.farmer)
    return list(
        db.execute(select(Case).where(Case.farmer_id == farmer_id).order_by(Case.created_at.desc())).scalars()
    )


@app.get("/api/experts/{expert_id}/queue", response_model=list[CaseRead])
def list_expert_queue(expert_id: int, db: Session = Depends(get_db)) -> list[Case]:
    _get_user_or_404(db, expert_id, UserRole.expert)
    query = select(Case).where(
        and_(
            Case.status == CaseStatus.needs_expert,
            or_(Case.expert_id.is_(None), Case.expert_id == expert_id),
        )
    )
    return list(db.execute(query.order_by(Case.created_at.asc())).scalars())


@app.post(
    "/api/cases/{case_id}/recommendations",
    response_model=RecommendationRead,
    status_code=status.HTTP_201_CREATED,
)
def add_recommendation(
    case_id: int,
    payload: RecommendationCreate,
    db: Session = Depends(get_db),
) -> ExpertRecommendation:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    _get_user_or_404(db, payload.expert_id, UserRole.expert)

    recommendation = ExpertRecommendation(
        case_id=case_id,
        expert_id=payload.expert_id,
        diagnosis=payload.diagnosis.strip(),
        treatment_plan=payload.treatment_plan.strip(),
        dosage=(payload.dosage.strip() if payload.dosage else None),
        duration_days=payload.duration_days,
        safety_notes=(payload.safety_notes.strip() if payload.safety_notes else None),
    )
    case.status = CaseStatus.expert_resolved
    case.expert_id = payload.expert_id
    case.updated_at = datetime.utcnow()
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


@app.post(
    "/api/cases/{case_id}/followups",
    response_model=FollowUpRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_followup(
    case_id: int,
    farmer_id: int = Form(...),
    notes: str = Form(""),
    outcome: str = Form(""),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
) -> FollowUp:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    _get_user_or_404(db, farmer_id, UserRole.farmer)

    image_path = None
    if image and image.filename:
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Follow-up image must be an image file.")
        image_path = await save_upload_file(image)

    followup = FollowUp(
        case_id=case_id,
        farmer_id=farmer_id,
        notes=notes.strip(),
        outcome=outcome.strip() or None,
        image_path=image_path,
    )
    case.updated_at = datetime.utcnow()
    db.add(followup)
    db.commit()
    db.refresh(followup)
    return followup


@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    farmers = get_users_by_role(db, UserRole.farmer)
    experts = get_users_by_role(db, UserRole.expert)
    recent_cases = list(db.execute(select(Case).order_by(Case.created_at.desc()).limit(10)).scalars())
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "farmers": farmers,
            "experts": experts,
            "recent_cases": recent_cases,
        },
    )


@app.get("/farmer/{farmer_id}")
def farmer_dashboard(farmer_id: int, request: Request, db: Session = Depends(get_db)):
    farmer = _get_user_or_404(db, farmer_id, UserRole.farmer)
    cases = list(
        db.execute(
            select(Case)
            .options(selectinload(Case.recommendations))
            .where(Case.farmer_id == farmer_id)
            .order_by(Case.created_at.desc())
        ).scalars()
    )
    return templates.TemplateResponse(
        "farmer_dashboard.html",
        {"request": request, "farmer": farmer, "cases": cases},
    )


@app.post("/web/cases")
async def create_case_web(
    farmer_id: int = Form(...),
    crop_name: str = Form(...),
    symptoms: str = Form(...),
    location: str = Form(""),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    await _create_case(db, farmer_id, crop_name, symptoms, location, image)
    return RedirectResponse(
        url=f"/farmer/{farmer_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get("/expert/{expert_id}")
def expert_dashboard(expert_id: int, request: Request, db: Session = Depends(get_db)):
    expert = _get_user_or_404(db, expert_id, UserRole.expert)
    queue = list(
        db.execute(
            select(Case)
            .where(
                and_(
                    Case.status == CaseStatus.needs_expert,
                    or_(Case.expert_id.is_(None), Case.expert_id == expert_id),
                )
            )
            .order_by(Case.created_at.asc())
        ).scalars()
    )
    reviewed = list(
        db.execute(
            select(ExpertRecommendation)
            .options(selectinload(ExpertRecommendation.case))
            .where(ExpertRecommendation.expert_id == expert_id)
            .order_by(ExpertRecommendation.created_at.desc())
            .limit(10)
        ).scalars()
    )
    return templates.TemplateResponse(
        "expert_dashboard.html",
        {
            "request": request,
            "expert": expert,
            "queue": queue,
            "reviewed": reviewed,
        },
    )


@app.post("/web/cases/{case_id}/recommend")
def add_recommendation_web(
    case_id: int,
    expert_id: int = Form(...),
    diagnosis: str = Form(...),
    treatment_plan: str = Form(...),
    dosage: str = Form(""),
    duration_days: Optional[int] = Form(None),
    safety_notes: str = Form(""),
    db: Session = Depends(get_db),
):
    payload = RecommendationCreate(
        expert_id=expert_id,
        diagnosis=diagnosis,
        treatment_plan=treatment_plan,
        dosage=dosage or None,
        duration_days=duration_days,
        safety_notes=safety_notes or None,
    )
    add_recommendation(case_id, payload, db)
    return RedirectResponse(
        url=f"/expert/{expert_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
