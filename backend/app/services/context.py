"""Сборка полного набора данных проекта для резюме и скоринга."""

import json
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from .. import models
from . import ratios as ratios_service
from . import finance as finance_service
from . import scoring as scoring_service


def get_latest_ratios(db: Session, project: models.Project) -> List[Dict[str, Any]]:
    """Коэффициенты по каждой компании за последний доступный год."""
    result: List[Dict[str, Any]] = []
    for company in project.companies:
        if not company.statements:
            continue
        by_year = {s.year: s for s in company.statements}
        latest_year = max(by_year.keys())
        values = json.loads(by_year[latest_year].values_json or "{}")
        prev = by_year.get(latest_year - 1)
        prev_values = json.loads(prev.values_json) if prev else None
        computed = ratios_service.compute_ratios(values, prev_values)
        computed["company_id"] = company.id
        computed["company_name"] = company.name
        computed["year"] = latest_year
        result.append(computed)
    return result


def get_ratios_history(db: Session, company: models.Company) -> List[Dict[str, Any]]:
    by_year = {s.year: s for s in company.statements}
    result: List[Dict[str, Any]] = []
    for year in sorted(by_year.keys()):
        values = json.loads(by_year[year].values_json or "{}")
        prev = by_year.get(year - 1)
        prev_values = json.loads(prev.values_json) if prev else None
        computed = ratios_service.compute_ratios(values, prev_values)
        computed["company_id"] = company.id
        computed["company_name"] = company.name
        computed["year"] = year
        result.append(computed)
    return result


def founders_payload(project: models.Project) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    for f in project.founders:
        checks = [{"check_type": c.check_type, "status": c.status, "comment": c.comment, "checked_at": c.checked_at} for c in f.checks]
        pkb = None
        if f.pkb_reports:
            latest = max(f.pkb_reports, key=lambda r: r.uploaded_at or "")
            pkb = json.loads(latest.result_json or "{}")
        data.append({
            "id": f.id,
            "full_name": f.full_name,
            "inn": f.inn,
            "share": f.share,
            "role": f.role,
            "checks": checks,
            "pkb": pkb,
        })
    return data


def project_payload(db: Session, project: models.Project) -> Dict[str, Any]:
    """Полный расчет по проекту: коэффициенты, доходность, график, DSCR, скоринг."""
    company_ratios = get_latest_ratios(db, project)

    forecast = [
        {"year": r.year, "revenue": r.revenue, "ebitda": r.ebitda, "capex": r.capex, "tax": r.tax, "cfads": r.cfads}
        for r in sorted(project.forecast_rows, key=lambda x: x.year)
    ]

    terms = project.terms
    terms_dict: Optional[Dict[str, Any]] = None
    schedule: List[Dict[str, Any]] = []
    if terms and terms.amount > 0 and terms.term_months > 0:
        terms_dict = {
            "amount": terms.amount,
            "rate": terms.rate,
            "term_months": terms.term_months,
            "grace_months": terms.grace_months,
            "schedule_type": terms.schedule_type,
            "discount_rate": terms.discount_rate,
        }
        schedule = finance_service.payment_schedule(
            terms.amount, terms.rate, terms.term_months, terms.grace_months, terms.schedule_type
        )

    discount_rate = terms.discount_rate if terms else 15.0
    investment = terms.amount if terms and terms.amount > 0 else (
        sum(r["capex"] for r in forecast) or 0.0
    )

    yield_data: Dict[str, Any] = {}
    if forecast:
        yield_data = finance_service.project_yield(forecast, investment, discount_rate)

    dscr_data: List[Dict[str, Any]] = []
    if forecast and schedule:
        dscr_data = finance_service.dscr_by_year(forecast, schedule)

    founders_data = founders_payload(project)

    risks = [
        {"id": r.id, "title": r.title, "category": r.category, "criticality": r.criticality,
         "description": r.description, "mitigation": r.mitigation}
        for r in project.risks
    ]

    scoring = scoring_service.compute_scoring(company_ratios, yield_data, dscr_data, founders_data, risks)

    return {
        "company_ratios": company_ratios,
        "forecast": forecast,
        "terms": terms_dict,
        "schedule": schedule,
        "yield": yield_data,
        "dscr": dscr_data,
        "founders": founders_data,
        "risks": risks,
        "scoring": scoring,
    }
