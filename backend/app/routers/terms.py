import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..services import finance as finance_service
from ..services import sample_data

router = APIRouter(prefix="/api", tags=["Доходность и условия"])


def forecast_start_year(forecast: List[dict]) -> Optional[int]:
    """Год первого месяца кредита = первый год прогноза (если задан)."""
    return min((r["year"] for r in forecast), default=None)


@router.get("/projects/{project_id}/forecast", response_model=List[schemas.ForecastRowOut],
            summary="Прогноз проекта")
def get_forecast(project_id: int, db: Session = Depends(get_db)):
    rows = (db.query(models.ForecastRow).filter_by(project_id=project_id)
            .order_by(models.ForecastRow.year).all())
    return rows


@router.put("/projects/{project_id}/forecast", response_model=List[schemas.ForecastRowOut],
            summary="Заменить прогноз таблицей")
def set_forecast(project_id: int, rows: List[schemas.ForecastRowIn], db: Session = Depends(get_db)):
    if not db.get(models.Project, project_id):
        raise HTTPException(404, "Проект не найден")
    db.query(models.ForecastRow).filter_by(project_id=project_id).delete()
    out = []
    for r in rows:
        cfads = r.cfads if r.cfads is not None else r.ebitda - r.capex - r.tax
        row = models.ForecastRow(project_id=project_id, year=r.year, revenue=r.revenue,
                                 ebitda=r.ebitda, capex=r.capex, tax=r.tax, cfads=cfads)
        db.add(row)
        out.append(row)
    db.commit()
    for row in out:
        db.refresh(row)
    return out


@router.post("/projects/{project_id}/forecast/upload", response_model=List[schemas.ForecastRowOut],
             status_code=201, summary="Загрузить прогноз из Excel")
async def upload_forecast(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Колонки: year, revenue, ebitda, capex, tax, cfads (пустой CFADS = EBITDA − CAPEX − налог)."""
    if not db.get(models.Project, project_id):
        raise HTTPException(404, "Проект не найден")
    import openpyxl, io

    data = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception:
        raise HTTPException(400, "Не удалось прочитать Excel-файл")
    ws = wb.worksheets[0]
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip().lower() if h else "" for h in next(rows_iter, [])]
    required = ["year", "revenue", "ebitda", "capex", "tax", "cfads"]
    try:
        idx = {h: headers.index(h) for h in required}
    except ValueError:
        wb.close()
        raise HTTPException(400, "Ожидаются колонки: " + ", ".join(required))

    parsed: List[dict] = []
    for row in rows_iter:
        if row is None or row[idx["year"]] is None:
            continue
        def num(key):
            v = row[idx[key]]
            return float(v) if v is not None and v != "" else None
        parsed.append({
            "year": int(num("year")),
            "revenue": num("revenue") or 0.0,
            "ebitda": num("ebitda") or 0.0,
            "capex": num("capex") or 0.0,
            "tax": num("tax") or 0.0,
            "cfads": num("cfads"),
        })
    wb.close()
    if not parsed:
        raise HTTPException(400, "В файле нет строк прогноза")

    db.query(models.ForecastRow).filter_by(project_id=project_id).delete()
    out = []
    for p in parsed:
        cfads = p["cfads"] if p["cfads"] is not None else p["ebitda"] - p["capex"] - p["tax"]
        row = models.ForecastRow(project_id=project_id, cfads=cfads, **{k: v for k, v in p.items() if k != "cfads"})
        db.add(row)
        out.append(row)
    db.commit()
    for row in out:
        db.refresh(row)
    return out


@router.get("/projects/{project_id}/forecast/sample", summary="Скачать шаблон прогноза (xlsx)")
def sample_forecast_file(project_id: int):
    rows = sample_data.sample_forecast()
    content = sample_data.forecast_to_xlsx(rows)
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="forecast_template.xlsx"'},
    )


@router.get("/projects/{project_id}/yield", summary="Показатели доходности (NPV/IRR/PI/окупаемость)")
def project_yield(project_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Project, project_id)
    if not p:
        raise HTTPException(404, "Проект не найден")
    forecast = [
        {"year": r.year, "revenue": r.revenue, "ebitda": r.ebitda, "capex": r.capex, "tax": r.tax, "cfads": r.cfads}
        for r in sorted(p.forecast_rows, key=lambda x: x.year)
    ]
    if not forecast:
        raise HTTPException(400, "Прогноз не задан")
    terms = p.terms
    discount = terms.discount_rate if terms else 15.0
    investment = terms.amount if terms and terms.amount > 0 else sum(r["capex"] for r in forecast)
    return finance_service.project_yield(forecast, investment, discount)


@router.get("/projects/{project_id}/terms", response_model=schemas.TermsOut, summary="Условия кредитования")
def get_terms(project_id: int, db: Session = Depends(get_db)):
    t = db.query(models.CreditTerms).filter_by(project_id=project_id).first()
    if not t:
        raise HTTPException(404, "Условия не заданы")
    return t


@router.put("/projects/{project_id}/terms", response_model=schemas.TermsOut, summary="Задать условия кредитования")
def set_terms(project_id: int, data: schemas.TermsIn, db: Session = Depends(get_db)):
    if not db.get(models.Project, project_id):
        raise HTTPException(404, "Проект не найден")
    t = db.query(models.CreditTerms).filter_by(project_id=project_id).first()
    if t:
        for k, v in data.model_dump().items():
            setattr(t, k, v)
    else:
        t = models.CreditTerms(project_id=project_id, **data.model_dump())
        db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.get("/projects/{project_id}/schedule", summary="График платежей")
def get_schedule(project_id: int, db: Session = Depends(get_db)):
    t = db.query(models.CreditTerms).filter_by(project_id=project_id).first()
    if not t:
        raise HTTPException(404, "Условия не заданы")
    schedule = finance_service.payment_schedule(t.amount, t.rate, t.term_months, t.grace_months, t.schedule_type)
    return {"terms": {"amount": t.amount, "rate": t.rate, "term_months": t.term_months,
                      "grace_months": t.grace_months, "schedule_type": t.schedule_type},
            "schedule": schedule,
            "yearly_service": finance_service.yearly_debt_service(schedule)}


@router.get("/projects/{project_id}/dscr", summary="DSCR по годам")
def get_dscr(project_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Project, project_id)
    if not p:
        raise HTTPException(404, "Проект не найден")
    t = p.terms
    if not t:
        raise HTTPException(404, "Условия не заданы")
    forecast = [
        {"year": r.year, "ebitda": r.ebitda, "capex": r.capex, "tax": r.tax, "cfads": r.cfads}
        for r in sorted(p.forecast_rows, key=lambda x: x.year)
    ]
    schedule = finance_service.payment_schedule(t.amount, t.rate, t.term_months, t.grace_months, t.schedule_type)
    return finance_service.dscr_by_year(forecast, schedule, start_year=forecast_start_year(forecast))
