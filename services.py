from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import User, UserRole

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"
UPLOAD_DIR = PROJECT_ROOT / "uploads"


def ensure_runtime_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_filename(name: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9._-]", "-", name).strip("-")
    return base or "image.jpg"


async def save_upload_file(image: UploadFile) -> str:
    suffix = Path(image.filename or "").suffix.lower() or ".jpg"
    safe_name = _sanitize_filename(Path(image.filename or "image.jpg").stem)
    stored_name = f"{uuid4().hex}-{safe_name}{suffix}"
    destination = UPLOAD_DIR / stored_name

    content = await image.read()
    destination.write_bytes(content)
    return f"/uploads/{stored_name}"


def seed_demo_users(db: Session) -> None:
    defaults = [
        ("Ramesh", "9000000001", UserRole.farmer, "en"),
        ("Lakshmi", "9000000002", UserRole.farmer, "ta"),
        ("Dr. Sharma", "9000000011", UserRole.expert, "en"),
        ("Dr. Iyer", "9000000012", UserRole.expert, "en"),
    ]

    existing = {
        row[0]
        for row in db.execute(select(User.phone).where(User.phone.is_not(None))).all()
    }
    created = False

    for name, phone, role, language in defaults:
        if phone in existing:
            continue
        db.add(User(name=name, phone=phone, role=role, language=language))
        created = True

    if created:
        db.commit()


def get_users_by_role(db: Session, role: UserRole) -> list[User]:
    return list(db.execute(select(User).where(User.role == role).order_by(User.name)).scalars())


def get_next_expert_id(db: Session) -> int | None:
    expert = db.execute(select(User).where(User.role == UserRole.expert).order_by(User.id)).scalars().first()
    return expert.id if expert else None
