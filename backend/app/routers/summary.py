import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..services.summary import build_summary, summary_to_docx

router = APIRouter(prefix="/api/projects", tags=["Скоринг и резюме"])


@router.get("/{project_id}/summary", summary="Резюме проекта (пересчет скоринга)")
def get_summary(project_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Project, project_id)
    if not p:
        raise HTTPException(404, "Проект не найден")
    summary = build_summary(db, p)

    # Скоринг пересчитывается при формировании резюме; детализация сохраняется
    run = models.ScoringRun(
        project_id=project_id,
        total_score=summary["scoring"]["total_score"],
        verdict=summary["scoring"]["verdict"],
        details_json=json.dumps(summary["scoring"], ensure_ascii=False),
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    db.add(run)
    db.commit()

    return summary


@router.get("/{project_id}/summary/docx", summary="Выгрузка резюме в Word (.docx)")
def get_summary_docx(project_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Project, project_id)
    if not p:
        raise HTTPException(404, "Проект не найден")
    summary = build_summary(db, p)
    content = summary_to_docx(summary)
    safe_name = f"resume_project_{project_id}.docx"
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.get("/{project_id}/scoring/history", response_model=list[schemas.ScoringOut],
            summary="История скоринга")
def scoring_history(project_id: int, db: Session = Depends(get_db)):
    runs = (db.query(models.ScoringRun).filter_by(project_id=project_id)
            .order_by(models.ScoringRun.id.desc()).limit(50).all())
    return [{
        "id": r.id, "project_id": r.project_id, "total_score": r.total_score,
        "verdict": r.verdict, "details": json.loads(r.details_json or "{}"),
        "created_at": r.created_at,
    } for r in runs]
