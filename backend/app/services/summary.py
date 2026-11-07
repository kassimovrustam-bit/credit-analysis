"""Формирование итогового резюме проекта: текст по разделам и выгрузка в .docx."""

import io
import json
from typing import Dict, Any, List

from sqlalchemy.orm import Session

from .. import models
from .context import project_payload
from ..config import CHECK_TYPES, DOC_TYPES

STATUS_LABELS = {
    "ok": "соответствует норме",
    "warning": "пограничное значение",
    "bad": "не соответствует норме",
    "unknown": "нет данных",
}

CHECK_STATUS_LABELS = {"clean": "чисто", "attention": "внимание", "negative": "негатив"}

RISK_CATEGORY_LABELS = {
    "structural": "структурные",
    "industry": "отраслевые",
    "financial": "финансовые",
    "other": "прочие",
}
RISK_CRIT_LABELS = {"low": "низкая", "medium": "средняя", "high": "высокая", "critical": "критическая"}

ROLE_LABELS = {"borrower": "заемщик", "guarantor": "поручитель", "related": "связанная компания"}

PROJECT_STATUS_LABELS = {"draft": "черновик", "review": "на рассмотрении", "approved": "одобрен", "rejected": "отклонен"}


def _fmt_money(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.2f}".replace(",", " ").replace(".", ",")
    except (TypeError, ValueError):
        return str(v)


def _fmt_num(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.3f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",")
    except (TypeError, ValueError):
        return str(v)


def build_summary(db: Session, project: models.Project) -> Dict[str, Any]:
    """Собирает резюме: данные + текст по всем разделам + скоринг."""
    payload = project_payload(db, project)
    scoring = payload["scoring"]

    sections: List[Dict[str, Any]] = []

    # 1. Общие сведения
    general_text = (
        f"Проект «{project.name}». Заемщик/группа: {project.borrower or '—'}. "
        f"Отрасль: {project.industry or '—'}. Цель финансирования: {project.purpose or '—'}. "
        f"Статус проекта: {PROJECT_STATUS_LABELS.get(project.status, project.status)}."
    )
    if project.description:
        general_text += f"\n{project.description}"
    sections.append({"key": "general", "title": "Общие сведения", "text": general_text})

    # 2. Финансовое состояние группы
    fin_lines: List[str] = []
    for cr in payload["company_ratios"]:
        fin_lines.append(
            f"{cr['company_name']} ({cr['year']} г.): {cr['solvency_label']}. "
            f"Z-score Альтмана: {cr['z_score']} ({cr['z_zone']})."
        )
        bad = [r for r in cr["ratios"] if r["status"] == "bad"]
        warn = [r for r in cr["ratios"] if r["status"] == "warning"]
        if bad:
            fin_lines.append("  Не соответствуют норме: " + "; ".join(f"{r['name']} ({_fmt_num(r['value'])} при норме {r['norm']})" for r in bad) + ".")
        if warn:
            fin_lines.append("  Пограничные значения: " + "; ".join(f"{r['name']} ({_fmt_num(r['value'])})" for r in warn) + ".")
    if not fin_lines:
        fin_lines.append("Отчетность по компаниям группы не загружена.")
    fin_text = "\n".join(fin_lines)
    if payload["company_ratios"]:
        fin_text += "\nПримечание: " + payload["company_ratios"][0]["ebitda_note"]
    sections.append({"key": "finance", "title": "Финансовое состояние группы", "text": fin_text, "company_ratios": payload["company_ratios"]})

    # 3. Доходность проекта
    y = payload["yield"]
    if y:
        yield_text = (
            f"Ставка дисконтирования: {_fmt_num(y['discount_rate'])}%. "
            f"NPV: {_fmt_money(y['npv'])} ({'приемлемо' if y['npv_status'] == 'ok' else 'неприемлемо'}). "
            f"IRR: {_fmt_num(y['irr'])}% ({'выше ставки дисконтирования — приемлемо' if y.get('irr_status') == 'ok' else 'ниже ставки дисконтирования — неприемлемо' if y.get('irr_status') == 'bad' else 'не рассчитан'}). "
            f"Индекс доходности (PI): {_fmt_num(y.get('pi'))}. "
            f"Срок окупаемости: простой — {_fmt_num(y.get('payback_simple_years'))} лет, "
            f"дисконтированный — {_fmt_num(y.get('payback_discounted_years'))} лет."
        )
    else:
        yield_text = "Прогноз денежных потоков проекта не задан."
    if payload["dscr"]:
        dscr_parts = [f"{d['year']} г.: {_fmt_num(d['dscr'])} ({STATUS_LABELS.get(d['status'], d['status'])})" for d in payload["dscr"]]
        yield_text += "\nDSCR по годам: " + "; ".join(dscr_parts) + ". Норматив DSCR ≥ 1,2."
    sections.append({"key": "project", "title": "Доходность проекта", "text": yield_text, "yield": y, "dscr": payload["dscr"]})

    # 4. Учредители и проверки
    f_lines: List[str] = []
    for f in payload["founders"]:
        line = f"{f['full_name']} (ИНН {f['inn'] or '—'}, доля {_fmt_num(f['share'])}%"
        if f.get("role"):
            line += f", {f['role']}"
        line += ")."
        f_lines.append(line)
        for c in f["checks"]:
            label = CHECK_TYPES.get(c["check_type"], c["check_type"])
            st = CHECK_STATUS_LABELS.get(c["status"], c["status"])
            extra = f" — {c['comment']}" if c.get("comment") else ""
            date_part = f" (проверено: {c['checked_at']})" if c.get("checked_at") else ""
            f_lines.append(f"  • {label}: {st}{date_part}{extra}")
        pkb = f.get("pkb")
        if pkb:
            if pkb.get("error"):
                f_lines.append(f"  • Отчет ПКБ: {pkb['error']}")
            else:
                f_lines.append(
                    "  • Отчет ПКБ: договоров всего {total}, открытых {open_}; текущая задолженность {debt}; "
                    "макс. просрочка {days} дн.; качество КИ: {q}.".format(
                        total=pkb.get("contracts_total", "—"),
                        open_=pkb.get("contracts_open", "—"),
                        debt=_fmt_money(pkb.get("current_debt")),
                        days=pkb.get("max_overdue_days", "—"),
                        q={"ok": "удовлетворительное", "warning": "требует внимания", "bad": "негативное"}.get(pkb.get("quality"), "—"),
                    )
                )
                neg = [k for k, v in (pkb.get("markers") or {}).items() if v]
                if neg:
                    f_lines.append("    Негативные маркеры: " + ", ".join(neg) + ".")
            f_lines.append("    " + (pkb.get("disclaimer") or ""))
    if not f_lines:
        f_lines.append("Сведения об учредителях не внесены.")
    sections.append({"key": "founders", "title": "Учредители и проверки", "text": "\n".join(f_lines), "founders": payload["founders"]})

    # 5. Риски
    r_lines: List[str] = []
    for r in payload["risks"]:
        cat = RISK_CATEGORY_LABELS.get(r["category"], r["category"])
        crit = RISK_CRIT_LABELS.get(r["criticality"], r["criticality"])
        line = f"• [{cat}, критичность: {crit}] {r['title']}"
        if r.get("description"):
            line += f". {r['description']}"
        if r.get("mitigation"):
            line += f" Меры снижения: {r['mitigation']}"
        r_lines.append(line + ".")
    if not r_lines:
        r_lines.append("Реестр рисков не заполнен.")
    sections.append({"key": "risks", "title": "Реестр рисков", "text": "\n".join(r_lines), "risks": payload["risks"]})

    # 6. Условия кредитования
    t = payload["terms"]
    if t:
        sched_label = "аннуитетный" if t["schedule_type"] == "annuity" else "дифференцированный"
        terms_text = (
            f"Сумма: {_fmt_money(t['amount'])}; ставка: {_fmt_num(t['rate'])}% годовых; "
            f"срок: {t['term_months']} мес."
            + (f"; льготный период: {t['grace_months']} мес. (только проценты)" if t["grace_months"] else "")
            + f"; график: {sched_label}."
        )
    else:
        terms_text = "Условия кредитования не заданы."
    sections.append({"key": "terms", "title": "Условия кредитования", "text": terms_text, "terms": t})

    # 7. Заключение
    blocks = scoring["blocks"]
    concl_lines = [
        f"Итоговый балл скоринга: {scoring['total_score']} из 100.",
        f"Вердикт: {scoring['verdict']}.",
        "",
        "Детализация по блокам:",
        f"  • Финансовое состояние группы (вес 40%): {blocks['finance']['score']} баллов.",
        f"  • Доходность проекта (вес 30%): {blocks['project']['score']} баллов.",
        f"  • Учредители (вес 20%): {blocks['founders']['score']} баллов.",
        f"  • Риски (вес 10%): {blocks['risks']['score']} баллов.",
    ]
    for key in ("finance", "project", "founders"):
        note = blocks[key].get("note")
        if note:
            concl_lines.append(f"    {note}")
    sections.append({"key": "conclusion", "title": "Заключение", "text": "\n".join(concl_lines), "scoring": scoring})

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "borrower": project.borrower,
            "industry": project.industry,
            "purpose": project.purpose,
            "status": project.status,
        },
        "sections": sections,
        "scoring": scoring,
        "payload": payload,
    }


def summary_to_docx(summary: Dict[str, Any]) -> bytes:
    """Генерирует .docx с резюме."""
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    doc.add_heading(f"Резюме по проекту «{summary['project']['name']}»", level=0)
    scoring = summary["scoring"]
    doc.add_paragraph(f"Скоринг: {scoring['total_score']} / 100. Вердикт: {scoring['verdict']}.")

    for section in summary["sections"]:
        doc.add_heading(section["title"], level=1)
        for para in section["text"].split("\n"):
            if para.strip():
                doc.add_paragraph(para)
        if section["key"] == "finance" and section.get("company_ratios"):
            for cr in section["company_ratios"]:
                doc.add_paragraph(f"Коэффициенты: {cr['company_name']}, {cr['year']} г.", style=None).runs[0].bold = True
                table = doc.add_table(rows=1, cols=4)
                table.style = "Light Grid Accent 1"
                hdr = table.rows[0].cells
                hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text = "Коэффициент", "Значение", "Норма", "Оценка"
                for r in cr["ratios"]:
                    cells = table.add_row().cells
                    cells[0].text = r["name"]
                    cells[1].text = _fmt_num(r["value"])
                    cells[2].text = r["norm"]
                    cells[3].text = STATUS_LABELS.get(r["status"], r["status"])

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
