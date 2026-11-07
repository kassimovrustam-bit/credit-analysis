import json
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/projects", tags=["Проекты"])


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _counters(db: Session, project: models.Project) -> dict:
    return {
        "companies": len(project.companies),
        "founders": len(project.founders),
        "risks": len(project.risks),
        "documents": len(project.documents),
    }


def _to_out(db: Session, p: models.Project) -> dict:
    last_run = max(p.scoring_runs, key=lambda r: r.created_at, default=None)
    return {
        "id": p.id,
        "name": p.name,
        "borrower": p.borrower,
        "industry": p.industry,
        "purpose": p.purpose,
        "description": p.description,
        "status": p.status,
        "created_at": p.created_at or "",
        "updated_at": p.updated_at or "",
        "counters": _counters(db, p),
        "last_score": last_run.total_score if last_run else None,
        "last_verdict": last_run.verdict if last_run else None,
    }


@router.get("", response_model=List[schemas.ProjectOut], summary="Список проектов")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.id.desc()).all()
    return [_to_out(db, p) for p in projects]


@router.post("", response_model=schemas.ProjectOut, status_code=201, summary="Создать проект")
def create_project(data: schemas.ProjectIn, db: Session = Depends(get_db)):
    p = models.Project(**data.model_dump(), created_at=_now(), updated_at=_now())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _to_out(db, p)


@router.get("/{project_id}", response_model=schemas.ProjectOut, summary="Карточка проекта")
def get_project(project_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Project, project_id)
    if not p:
        raise HTTPException(404, "Проект не найден")
    return _to_out(db, p)


@router.put("/{project_id}", response_model=schemas.ProjectOut, summary="Обновить проект")
def update_project(project_id: int, data: schemas.ProjectIn, db: Session = Depends(get_db)):
    p = db.get(models.Project, project_id)
    if not p:
        raise HTTPException(404, "Проект не найден")
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    p.updated_at = _now()
    db.commit()
    db.refresh(p)
    return _to_out(db, p)


@router.delete("/{project_id}", status_code=204, summary="Удалить проект")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Project, project_id)
    if not p:
        raise HTTPException(404, "Проект не найден")
    db.delete(p)
    db.commit()
    return None
