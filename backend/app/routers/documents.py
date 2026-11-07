import json
import os
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..config import DOC_TYPES, STORAGE_DIR
from ..services.doc_parser import extract_business_plan_facts

router = APIRouter(prefix="/api", tags=["Документы"])


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _doc_out(d: models.Document) -> dict:
    return {
        "id": d.id, "project_id": d.project_id, "doc_type": d.doc_type,
        "filename": d.filename, "uploaded_at": d.uploaded_at,
        "extracted": json.loads(d.extracted_json or "{}"),
    }


@router.get("/doc-types", summary="Справочник типов документов")
def doc_types():
    return DOC_TYPES


@router.post("/projects/{project_id}/documents", response_model=schemas.DocumentOut, status_code=201,
             summary="Загрузить документ проекта")
async def upload_document(project_id: int, doc_type: str = Form("other"), file: UploadFile = File(...),
                          db: Session = Depends(get_db)):
    if not db.get(models.Project, project_id):
        raise HTTPException(404, "Проект не найден")
    if doc_type not in DOC_TYPES:
        raise HTTPException(400, f"Тип документа должен быть одним из: {', '.join(DOC_TYPES)}")
    data = await file.read()
    filename = file.filename or "document"

    extracted = {}
    if doc_type == "business_plan" and filename.lower().endswith((".pdf", ".txt")):
        extracted = extract_business_plan_facts(data, filename)

    folder = os.path.join(STORAGE_DIR, f"project_{project_id}", "documents")
    os.makedirs(folder, exist_ok=True)
    safe_name = f"{int(datetime.now().timestamp())}_{os.path.basename(filename)}"
    path = os.path.join(folder, safe_name)
    with open(path, "wb") as fh:
        fh.write(data)

    d = models.Document(project_id=project_id, doc_type=doc_type, filename=filename,
                        file_path=path, uploaded_at=_now(),
                        extracted_json=json.dumps(extracted, ensure_ascii=False))
    db.add(d)
    db.commit()
    db.refresh(d)
    return _doc_out(d)


@router.get("/projects/{project_id}/documents", response_model=List[schemas.DocumentOut],
            summary="Документы проекта")
def list_documents(project_id: int, db: Session = Depends(get_db)):
    docs = db.query(models.Document).filter_by(project_id=project_id).order_by(models.Document.id.desc()).all()
    return [_doc_out(d) for d in docs]


@router.get("/documents/{document_id}/download", summary="Скачать документ")
def download_document(document_id: int, db: Session = Depends(get_db)):
    d = db.get(models.Document, document_id)
    if not d or not os.path.exists(d.file_path):
        raise HTTPException(404, "Файл не найден")
    return FileResponse(d.file_path, filename=d.filename)


@router.delete("/documents/{document_id}", status_code=204, summary="Удалить документ")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    d = db.get(models.Document, document_id)
    if not d:
        raise HTTPException(404, "Документ не найден")
    if d.file_path and os.path.exists(d.file_path):
        try:
            os.remove(d.file_path)
        except OSError:
            pass
    db.delete(d)
    db.commit()
    return None
