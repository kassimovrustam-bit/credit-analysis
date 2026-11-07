from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api", tags=["Риски"])

CATEGORIES = {"structural": "структурные", "industry": "отраслевые", "financial": "финансовые", "other": "прочие"}
CRITICALITY = {"low": "низкая", "medium": "средняя", "high": "высокая", "critical": "критическая"}


@router.get("/risk-dicts", summary="Справочники категорий и критичности рисков")
def risk_dicts():
    return {"categories": CATEGORIES, "criticality": CRITICALITY}


@router.post("/projects/{project_id}/risks", response_model=schemas.RiskOut, status_code=201,
             summary="Добавить риск")
def create_risk(project_id: int, data: schemas.RiskIn, db: Session = Depends(get_db)):
    if not db.get(models.Project, project_id):
        raise HTTPException(404, "Проект не найден")
    if data.category not in CATEGORIES:
        raise HTTPException(400, f"Категория должна быть одной из: {', '.join(CATEGORIES)}")
    if data.criticality not in CRITICALITY:
        raise HTTPException(400, f"Критичность должна быть одной из: {', '.join(CRITICALITY)}")
    r = models.Risk(project_id=project_id, **data.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.get("/projects/{project_id}/risks", response_model=List[schemas.RiskOut], summary="Риски проекта")
def list_risks(project_id: int, db: Session = Depends(get_db)):
    return db.query(models.Risk).filter_by(project_id=project_id).all()


@router.put("/risks/{risk_id}", response_model=schemas.RiskOut, summary="Обновить риск")
def update_risk(risk_id: int, data: schemas.RiskIn, db: Session = Depends(get_db)):
    r = db.get(models.Risk, risk_id)
    if not r:
        raise HTTPException(404, "Риск не найден")
    for k, v in data.model_dump().items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return r


@router.delete("/risks/{risk_id}", status_code=204, summary="Удалить риск")
def delete_risk(risk_id: int, db: Session = Depends(get_db)):
    r = db.get(models.Risk, risk_id)
    if not r:
        raise HTTPException(404, "Риск не найден")
    db.delete(r)
    db.commit()
    return None
