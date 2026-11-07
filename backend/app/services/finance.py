"""Финансовые расчеты проекта: NPV, IRR, сроки окупаемости, PI,
график платежей (аннуитет/дифференцированный), DSCR."""

from typing import List, Dict, Any, Optional


def compute_cfads(row: Dict[str, Any]) -> float:
    """CFADS: если не задан — EBITDA − CAPEX − налог."""
    if row.get("cfads") is not None:
        return float(row["cfads"])
    return float(row.get("ebitda", 0.0)) - float(row.get("capex", 0.0)) - float(row.get("tax", 0.0))


def npv(rate: float, cashflows: List[float]) -> float:
    """NPV ряда денежных потоков; cashflows[0] — момент 0."""
    return sum(cf / (1.0 + rate) ** i for i, cf in enumerate(cashflows))


def irr(cashflows: List[float], low: float = -0.9999, high: float = 10.0, tol: float = 1e-7, max_iter: int = 200) -> Optional[float]:
    """IRR методом бисекции. Возвращает None, если корень не локализован."""
    f_low = npv(low, cashflows)
    f_high = npv(high, cashflows)
    if f_low * f_high > 0:
        return None
    for _ in range(max_iter):
        mid = (low + high) / 2.0
        f_mid = npv(mid, cashflows)
        if abs(f_mid) < tol:
            return mid
        if f_low * f_mid < 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2.0


def payback_periods(cashflows: List[float], rate: float) -> Dict[str, Optional[float]]:
    """Простой и дисконтированный срок окупаемости (в годах/шагах потока)."""

    def _pb(flows: List[float]) -> Optional[float]:
        cum = 0.0
        for i, cf in enumerate(flows):
            prev = cum
            cum += cf
            if cum >= 0:
                if cf == 0:
                    return float(i)
                return i - 1 + (-prev / cf) if i > 0 else 0.0
        return None

    simple = _pb(cashflows)
    discounted_flows = [cf / (1.0 + rate) ** i for i, cf in enumerate(cashflows)]
    discounted = _pb(discounted_flows)
    return {"payback_simple": simple, "payback_discounted": discounted}


def project_yield(forecast: List[Dict[str, Any]], investment: float, discount_rate_pct: float) -> Dict[str, Any]:
    """Доходность проекта по прогнозу и сумме инвестиций (кредита)."""
    rate = discount_rate_pct / 100.0
    flows = [compute_cfads(r) for r in forecast]
    cashflows = [-abs(investment)] + flows

    npv_value = npv(rate, cashflows)
    irr_value = irr(cashflows)
    pb = payback_periods(cashflows, rate)
    pv_inflows = sum(cf / (1.0 + rate) ** (i + 1) for i, cf in enumerate(flows))
    pi = (pv_inflows / abs(investment)) if investment else None

    return {
        "investment": investment,
        "discount_rate": discount_rate_pct,
        "npv": round(npv_value, 2),
        "npv_status": "ok" if npv_value > 0 else "bad",
        "irr": round(irr_value * 100, 2) if irr_value is not None else None,
        "irr_status": ("ok" if irr_value * 100 > discount_rate_pct else "bad") if irr_value is not None else "unknown",
        "payback_simple_years": round(pb["payback_simple"], 2) if pb["payback_simple"] is not None else None,
        "payback_discounted_years": round(pb["payback_discounted"], 2) if pb["payback_discounted"] is not None else None,
        "pi": round(pi, 3) if pi is not None else None,
    }


def payment_schedule(amount: float, annual_rate_pct: float, term_months: int,
                     grace_months: int = 0, schedule_type: str = "annuity") -> List[Dict[str, Any]]:
    """График платежей. В льготном периоде — только проценты."""
    rows: List[Dict[str, Any]] = []
    if amount <= 0 or term_months <= 0:
        return rows
    r = annual_rate_pct / 100.0 / 12.0
    balance = amount
    repay_months = max(term_months - grace_months, 1)

    if schedule_type == "annuity":
        if r > 0:
            annuity = amount * r * (1 + r) ** repay_months / ((1 + r) ** repay_months - 1)
        else:
            annuity = amount / repay_months
    else:
        annuity = None

    for month in range(1, term_months + 1):
        interest = balance * r
        if month <= grace_months:
            principal = 0.0
            payment = interest
        elif schedule_type == "annuity":
            payment = annuity
            principal = payment - interest
            if principal > balance:
                principal = balance
                payment = principal + interest
        else:  # differentiated
            principal = amount / repay_months
            if principal > balance:
                principal = balance
            payment = principal + interest
        balance = max(balance - principal, 0.0)
        rows.append({
            "month": month,
            "payment": round(payment, 2),
            "principal": round(principal, 2),
            "interest": round(interest, 2),
            "balance": round(balance, 2),
            "grace": month <= grace_months,
        })
    return rows


def yearly_debt_service(schedule: List[Dict[str, Any]], start_year: Optional[int] = None,
                        start_month: int = 1) -> Dict[int, float]:
    """Обслуживание долга (тело + проценты) по календарным годам кредита.

    Если start_year задан — годы календарные (месяц платежа 1 попадает в
    start_year при start_month=1), иначе годы считаются от начала кредита (1..n).
    """
    by_year: Dict[int, float] = {}
    for row in schedule:
        if start_year:
            year = start_year + (row["month"] + start_month - 2) // 12
        else:
            year = (row["month"] - 1) // 12 + 1
        by_year[year] = by_year.get(year, 0.0) + row["payment"]
    return {y: round(v, 2) for y, v in sorted(by_year.items())}


def dscr_by_year(forecast: List[Dict[str, Any]], schedule: List[Dict[str, Any]],
                 start_year: Optional[int] = None, start_month: int = 1) -> List[Dict[str, Any]]:
    """DSCR = CFADS / обслуживание долга по годам.
    ≥1.2 — приемлемо, 1.0–1.2 — погранично, <1.0 — неприемлемо.

    Обслуживание долга привязывается к календарным годам прогноза:
    start_year — год первого месяца кредита (по умолчанию — первый год прогноза).
    """
    cfads_by_year: Dict[int, float] = {}
    for row in forecast:
        year = int(row["year"])
        cfads_by_year[year] = cfads_by_year.get(year, 0.0) + compute_cfads(row)
    if start_year is None and cfads_by_year:
        start_year = min(cfads_by_year.keys())
    service = yearly_debt_service(schedule, start_year, start_month)

    years = sorted(set(list(service.keys()) + list(cfads_by_year.keys())))
    result: List[Dict[str, Any]] = []
    for y in years:
        svc = service.get(y, 0.0)
        cfads = cfads_by_year.get(y, 0.0)
        if svc > 0:
            dscr = cfads / svc
            status = "ok" if dscr >= 1.2 else ("warning" if dscr >= 1.0 else "bad")
        elif cfads_by_year.get(y) is not None:
            # год прогноза вне срока кредита — обслуживания нет, DSCR не считается
            dscr = None
            status = "unknown"
        else:
            dscr = None
            status = "unknown"
        result.append({
            "year": y,
            "cfads": round(cfads, 2),
            "debt_service": round(svc, 2),
            "dscr": round(dscr, 3) if dscr is not None else None,
            "status": status,
        })
    return result
