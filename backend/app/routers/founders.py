import json
import os
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..config import CHECK_TYPES, STORAGE_DIR
from ..services.pkb_parser import parse_pkb_report

router = APIRouter(prefix="/api", tags=["Учредители и проверки"])


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _founder_out(f: models.Founder) -> dict:
    checks = [{"id": c.id, "check_type": c.check_type, "status": c.status,
               "comment": c.comment, "checked_at": c.checked_at} for c in f.checks]
    pkb = None
    if f.pkb_reports:
        latest = max(f.pkb_reports, key=lambda r: r.uploaded_at or "")
        pkb = json.loads(latest.result_json or "{}")
        pkb["report_id"] = latest.id
    return {
        "id": f.id, "project_id": f.project_id, "full_name": f.full_name, "inn": f.inn,
        "share": f.share, "role": f.role, "checks": checks, "pkb": pkb,
    }


@router.post("/projects/{project_id}/founders", response_model=schemas.FounderOut, status_code=201,
             summary="Добавить учредителя")
def create_founder(project_id: int, data: schemas.FounderIn, db: Session = Depends(get_db)):
    if not db.get(models.Project, project_id):
        raise HTTPException(404, "Проект не найден")
    f = models.Founder(project_id=project_id, **data.model_dump())
    db.add(f)
    db.commit()
    db.refresh(f)
    return _founder_out(f)


@router.get("/projects/{project_id}/founders", response_model=List[schemas.FounderOut],
            summary="Учредители проекта")
def list_founders(project_id: int, db: Session = Depends(get_db)):
    founders = db.query(models.Founder).filter_by(project_id=project_id).all()
    return [_founder_out(f) for f in founders]


@router.put("/founders/{founder_id}", response_model=schemas.FounderOut, summary="Обновить учредителя")
def update_founder(founder_id: int, data: schemas.FounderIn, db: Session = Depends(get_db)):
    f = db.get(models.Founder, founder_id)
    if not f:
        raise HTTPException(404, "Учредитель не найден")
    for k, v in data.model_dump().items():
        setattr(f, k, v)
    db.commit()
    db.refresh(f)
    return _founder_out(f)


@router.delete("/founders/{founder_id}", status_code=204, summary="Удалить учредителя")
def delete_founder(founder_id: int, db: Session = Depends(get_db)):
    f = db.get(models.Founder, founder_id)
    if not f:
        raise HTTPException(404, "Учредитель не найден")
    db.delete(f)
    db.commit()
    return None


@router.get("/check-types", summary="Справочник видов проверок")
def check_types():
    return CHECK_TYPES


@router.put("/founders/{founder_id}/checks/{check_type}", response_model=schemas.CheckOut,
            summary="Внести результат проверки (статус + комментарий)")
def set_check(founder_id: int, check_type: str, data: schemas.CheckIn, db: Session = Depends(get_db)):
    f = db.get(models.Founder, founder_id)
    if not f:
        raise HTTPException(404, "Учредитель не найден")
    if check_type not in CHECK_TYPES:
        raise HTTPException(400, f"Неизвестный вид проверки. Допустимые: {', '.join(CHECK_TYPES)}")
    if data.status not in ("clean", "attention", "negative"):
        raise HTTPException(400, "Статус должен быть: clean / attention / negative")
    checked_at = data.checked_at or _now()
    c = db.query(models.FounderCheck).filter_by(founder_id=founder_id, check_type=check_type).first()
    if c:
        c.status, c.comment, c.checked_at = data.status, data.comment, checked_at
    else:
        c = models.FounderCheck(founder_id=founder_id, check_type=check_type,
                                status=data.status, comment=data.comment, checked_at=checked_at)
        db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "check_type": c.check_type, "status": c.status,
            "comment": c.comment, "checked_at": c.checked_at}


@router.post("/founders/{founder_id}/pkb", summary="Загрузить отчет ПКБ (PDF)")
async def upload_pkb(founder_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    f = db.get(models.Founder, founder_id)
    if not f:
        raise HTTPException(404, "Учредитель не найден")
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Отчет ПКБ загружается в формате PDF с текстовым слоем")
    data = await file.read()
    result = parse_pkb_report(data)

    folder = os.path.join(STORAGE_DIR, f"project_{f.project_id}", "pkb")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"founder_{founder_id}_{int(datetime.now().timestamp())}.pdf")
    with open(path, "wb") as fh:
        fh.write(data)

    report = models.PkbReport(founder_id=founder_id, file_path=path, uploaded_at=_now(),
                              result_json=json.dumps(result, ensure_ascii=False))
    db.add(report)
    db.commit()
    db.refresh(report)
    result["report_id"] = report.id
    return result


@router.get("/founders/{founder_id}/pkb/file", summary="Скачать оригинал отчета ПКБ")
def download_pkb(founder_id: int, db: Session = Depends(get_db)):
    report = (db.query(models.PkbReport).filter_by(founder_id=founder_id)
              .order_by(models.PkbReport.id.desc()).first())
    if not report or not os.path.exists(report.file_path):
        raise HTTPException(404, "Файл отчета не найден")
    return FileResponse(report.file_path, media_type="application/pdf",
                        filename=os.path.basename(report.file_path))
