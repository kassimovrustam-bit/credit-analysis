import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..services.statement_parser import parse_statement
from ..services.context import get_ratios_history
from ..services import sample_data

router = APIRouter(prefix="/api", tags=["Компании и отчетность"])


def _company_out(c: models.Company) -> dict:
    return {
        "id": c.id,
        "project_id": c.project_id,
        "name": c.name,
        "inn": c.inn,
        "okved": c.okved,
        "role": c.role,
        "years": sorted([s.year for s in c.statements]),
    }


@router.post("/projects/{project_id}/companies", response_model=schemas.CompanyOut, status_code=201,
             summary="Добавить компанию группы")
def create_company(project_id: int, data: schemas.CompanyIn, db: Session = Depends(get_db)):
    if not db.get(models.Project, project_id):
        raise HTTPException(404, "Проект не найден")
    c = models.Company(project_id=project_id, **data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _company_out(c)


@router.get("/projects/{project_id}/companies", response_model=List[schemas.CompanyOut],
            summary="Компании проекта")
def list_companies(project_id: int, db: Session = Depends(get_db)):
    companies = db.query(models.Company).filter_by(project_id=project_id).all()
    return [_company_out(c) for c in companies]


@router.put("/companies/{company_id}", response_model=schemas.CompanyOut, summary="Обновить компанию")
def update_company(company_id: int, data: schemas.CompanyIn, db: Session = Depends(get_db)):
    c = db.get(models.Company, company_id)
    if not c:
        raise HTTPException(404, "Компания не найдена")
    for k, v in data.model_dump().items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return _company_out(c)


@router.delete("/companies/{company_id}", status_code=204, summary="Удалить компанию")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    c = db.get(models.Company, company_id)
    if not c:
        raise HTTPException(404, "Компания не найдена")
    db.delete(c)
    db.commit()
    return None


@router.post("/companies/{company_id}/statements", response_model=schemas.StatementOut, status_code=201,
             summary="Загрузить форму 1/2 за год (xlsx/csv)")
async def upload_statement(company_id: int, year: int = Form(...), file: UploadFile = File(...),
                           db: Session = Depends(get_db)):
    c = db.get(models.Company, company_id)
    if not c:
        raise HTTPException(404, "Компания не найдена")
    data = await file.read()
    try:
        values = parse_statement(data, file.filename or "file.xlsx")
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not values:
        raise HTTPException(400, "В файле не найдены коды строк РСБУ (например, 1100, 1200, 1600, 2110).")

    # Повторная загрузка за тот же год перезаписывает данные
    existing = db.query(models.Statement).filter_by(company_id=company_id, year=year).first()
    if existing:
        existing.values_json = json.dumps(values, ensure_ascii=False)
        db.commit()
        db.refresh(existing)
        st = existing
    else:
        st = models.Statement(company_id=company_id, year=year,
                              values_json=json.dumps(values, ensure_ascii=False))
        db.add(st)
        db.commit()
        db.refresh(st)
    return {"id": st.id, "company_id": st.company_id, "year": st.year, "values": values}


@router.get("/companies/{company_id}/statements", response_model=List[schemas.StatementOut],
            summary="Отчетность компании по годам")
def list_statements(company_id: int, db: Session = Depends(get_db)):
    sts = db.query(models.Statement).filter_by(company_id=company_id).order_by(models.Statement.year).all()
    return [{"id": s.id, "company_id": s.company_id, "year": s.year,
             "values": json.loads(s.values_json or "{}")} for s in sts]


@router.delete("/companies/{company_id}/statements/{year}", status_code=204,
               summary="Удалить отчетность за год")
def delete_statement(company_id: int, year: int, db: Session = Depends(get_db)):
    st = db.query(models.Statement).filter_by(company_id=company_id, year=year).first()
    if not st:
        raise HTTPException(404, "Отчетность за указанный год не найдена")
    db.delete(st)
    db.commit()
    return None


@router.get("/companies/{company_id}/ratios", summary="Коэффициенты компании по годам")
def company_ratios(company_id: int, db: Session = Depends(get_db)):
    c = db.get(models.Company, company_id)
    if not c:
        raise HTTPException(404, "Компания не найдена")
    return get_ratios_history(db, c)


@router.get("/sample/statement", summary="Скачать тестовую форму 1/2 (xlsx)")
def sample_statement(year: int = 2025):
    from fastapi.responses import Response

    values = sample_data.sample_statement_values(year=year)
    content = sample_data.statement_to_xlsx(values)
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="forma_{year}.xlsx"'},
    )
