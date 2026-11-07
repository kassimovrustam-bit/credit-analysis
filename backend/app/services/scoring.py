"""Блочная скоринг-модель: финансы группы 40% + проект 30% +
учредители 20% + риски 10%. Вердикты по порогам 70 / 50."""

from typing import Dict, Any, List

WEIGHTS = {
    "finance": 0.40,
    "project": 0.30,
    "founders": 0.20,
    "risks": 0.10,
}

VERDICTS = {
    "recommended": "Рекомендуется к финансированию",
    "conditional": "Возможно при дополнительном обеспечении / условиях",
    "rejected": "Высокий риск — финансирование не рекомендуется",
}

STATUS_SCORE = {"ok": 1.0, "warning": 0.5, "bad": 0.0, "unknown": None}

CRITICALITY_PENALTY = {"low": 2.0, "medium": 5.0, "high": 10.0, "critical": 20.0}
MITIGATION_FACTOR = 0.6  # штраф снижается на 40% при наличии мер снижения

CHECK_PENALTY = {"attention": 10.0, "negative": 30.0}
PKB_PENALTY = {"warning": 10.0, "bad": 30.0}


def _avg_status_score(statuses: List[str]) -> float:
    vals = [STATUS_SCORE[s] for s in statuses if s in STATUS_SCORE and STATUS_SCORE[s] is not None]
    if not vals:
        return 0.5
    return sum(vals) / len(vals)


def finance_block(company_ratios: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Оценка блока «Финансы группы» по рассчитанным коэффициентам компаний."""
    if not company_ratios:
        return {"score": 30.0, "note": "Нет данных отчетности — блок оценен условно низко.", "items": []}
    items: List[Dict[str, Any]] = []
    scores: List[float] = []
    for cr in company_ratios:
        statuses = [r["status"] for r in cr.get("ratios", [])]
        base = _avg_status_score(statuses)
        solvency_factor = {"ok": 1.0, "questionable": 0.6, "low": 0.25}.get(cr.get("solvency", "ok"), 1.0)
        z_factor = {"ok": 1.0, "warning": 0.7, "bad": 0.3}.get(cr.get("z_status", "ok"), 1.0)
        score = base * 0.6 + solvency_factor * 0.25 + z_factor * 0.15
        scores.append(score * 100)
        items.append({
            "company": cr.get("company_name", ""),
            "year": cr.get("year"),
            "solvency": cr.get("solvency_label", ""),
            "z_score": cr.get("z_score"),
            "score": round(score * 100, 1),
        })
    return {"score": round(sum(scores) / len(scores), 1), "items": items}


def project_block(yield_data: Dict[str, Any], dscr_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Оценка блока «Проект»: NPV, IRR, DSCR."""
    if not yield_data:
        return {"score": 30.0, "note": "Нет прогноза — блок оценен условно низко.", "items": []}
    parts: List[float] = []
    items: List[Dict[str, Any]] = []

    npv_status = yield_data.get("npv_status")
    parts.append(STATUS_SCORE.get(npv_status, 0.5) or 0.0)
    items.append({"metric": "NPV", "value": yield_data.get("npv"), "status": npv_status})

    irr_status = yield_data.get("irr_status", "unknown")
    if irr_status != "unknown":
        parts.append(STATUS_SCORE.get(irr_status, 0.5) or 0.0)
    items.append({"metric": "IRR", "value": yield_data.get("irr"), "status": irr_status})

    dscr_statuses = [d["status"] for d in dscr_data if d.get("dscr") is not None]
    if dscr_statuses:
        parts.append(_avg_status_score(dscr_statuses))
        min_dscr = min((d["dscr"] for d in dscr_data if d.get("dscr") is not None), default=None)
        items.append({"metric": "DSCR (мин.)", "value": min_dscr, "status": "ok" if (min_dscr or 0) >= 1.2 else ("warning" if (min_dscr or 0) >= 1.0 else "bad")})

    score = (sum(parts) / len(parts)) * 100 if parts else 30.0
    return {"score": round(score, 1), "items": items}


def founders_block(founders_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Оценка блока «Учредители»: проверки госбаз + качество КИ по ПКБ."""
    if not founders_data:
        return {"score": 30.0, "note": "Нет данных об учредителях — блок оценен условно низко.", "items": []}
    items: List[Dict[str, Any]] = []
    scores: List[float] = []
    for f in founders_data:
        penalty = 0.0
        problems: List[str] = []
        for c in f.get("checks", []):
            p = CHECK_PENALTY.get(c.get("status", "clean"), 0.0)
            if p:
                penalty += p
                problems.append(f"{c.get('check_type')}: {c.get('status')}")
        pkb_quality = (f.get("pkb") or {}).get("quality")
        if pkb_quality in PKB_PENALTY:
            penalty += PKB_PENALTY[pkb_quality]
            problems.append(f"КИ (ПКБ): {pkb_quality}")
        score = max(100.0 - penalty, 0.0)
        scores.append(score)
        items.append({
            "founder": f.get("full_name", ""),
            "score": round(score, 1),
            "problems": problems,
            "pkb_quality": pkb_quality,
        })
    return {"score": round(sum(scores) / len(scores), 1), "items": items}


def risks_block(risks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Оценка блока «Риски». Штраф снижается на 40% при наличии мер снижения."""
    total_penalty = 0.0
    items: List[Dict[str, Any]] = []
    for r in risks:
        penalty = CRITICALITY_PENALTY.get(r.get("criticality", "medium"), 5.0)
        if (r.get("mitigation") or "").strip():
            penalty *= MITIGATION_FACTOR
        total_penalty += penalty
        items.append({
            "title": r.get("title", ""),
            "category": r.get("category", ""),
            "criticality": r.get("criticality", ""),
            "penalty": round(penalty, 1),
            "mitigated": bool((r.get("mitigation") or "").strip()),
        })
    score = max(100.0 - total_penalty, 0.0)
    return {"score": round(score, 1), "items": items, "total_penalty": round(total_penalty, 1)}


def verdict_for(score: float) -> str:
    if score >= 70:
        return VERDICTS["recommended"]
    if score >= 50:
        return VERDICTS["conditional"]
    return VERDICTS["rejected"]


def compute_scoring(company_ratios: List[Dict[str, Any]],
                    yield_data: Dict[str, Any],
                    dscr_data: List[Dict[str, Any]],
                    founders_data: List[Dict[str, Any]],
                    risks: List[Dict[str, Any]]) -> Dict[str, Any]:
    blocks = {
        "finance": finance_block(company_ratios),
        "project": project_block(yield_data, dscr_data),
        "founders": founders_block(founders_data),
        "risks": risks_block(risks),
    }
    total = sum(blocks[k]["score"] * WEIGHTS[k] for k in WEIGHTS)
    total = round(total, 1)
    return {
        "total_score": total,
        "verdict": verdict_for(total),
        "weights": WEIGHTS,
        "blocks": blocks,
    }
