"""Расчет финансовых коэффициентов по данным РСБУ и оценка приемлемости.

Пороги — по Приложению А PRD; подлежат калибровке на пилоте.
EBITDA приближенная: прибыль до налогообложения (2300) + проценты (2330),
т.к. в формах РСБУ нет амортизации.
"""

from typing import Dict, Any, List, Optional

# warning-зона — 15% от границы нормы
WARN_ZONE = 0.15

RATIO_DEFS: List[Dict[str, Any]] = [
    {"key": "current_ratio", "name": "Текущая ликвидность", "norm": "1.5 – 2.5", "kind": "range", "low": 1.5, "high": 2.5, "unit": ""},
    {"key": "quick_ratio", "name": "Быстрая ликвидность", "norm": "≥ 0.8", "kind": "min", "min": 0.8, "unit": ""},
    {"key": "cash_ratio", "name": "Абсолютная ликвидность", "norm": "≥ 0.2", "kind": "min", "min": 0.2, "unit": ""},
    {"key": "autonomy", "name": "Автономия (СК/активы)", "norm": "≥ 0.5", "kind": "min", "min": 0.5, "unit": ""},
    {"key": "debt_to_equity", "name": "Заемные/собственные", "norm": "≤ 1.5", "kind": "max", "max": 1.5, "unit": ""},
    {"key": "debt_to_assets", "name": "Заемные/активы", "norm": "≤ 0.6", "kind": "max", "max": 0.6, "unit": ""},
    {"key": "working_capital", "name": "Собственный оборотный капитал", "norm": "≥ 0", "kind": "min", "min": 0.0, "unit": "абс."},
    {"key": "ros", "name": "ROS (рентабельность продаж)", "norm": "≥ 5%", "kind": "min", "min": 0.05, "unit": "%"},
    {"key": "roa", "name": "ROA (рентабельность активов)", "norm": "≥ 5%", "kind": "min", "min": 0.05, "unit": "%"},
    {"key": "roe", "name": "ROE (рентабельность капитала)", "norm": "≥ 10%", "kind": "min", "min": 0.10, "unit": "%"},
    {"key": "net_debt_ebitda", "name": "Чистый долг/EBITDA", "norm": "≤ 4.0", "kind": "max", "max": 4.0, "unit": ""},
    {"key": "interest_coverage", "name": "Покрытие процентов", "norm": "≥ 1.5", "kind": "min", "min": 1.5, "unit": ""},
    {"key": "revenue_growth", "name": "Темп роста выручки", "norm": "≥ 0%", "kind": "min", "min": 0.0, "unit": "%"},
]

# Ключевые коэффициенты для сводной оценки платежеспособности
KEY_RATIOS = ["current_ratio", "quick_ratio", "autonomy", "net_debt_ebitda", "interest_coverage", "ros"]


def _g(values: Dict[str, float], code: str) -> float:
    return float(values.get(code, 0.0))


def _safe_div(a: float, b: float) -> Optional[float]:
    if b == 0:
        return None
    return a / b


def evaluate(value: Optional[float], spec: Dict[str, Any]) -> str:
    """ok / warning / bad / unknown. Warning-зона — 15% от границы нормы."""
    if value is None:
        return "unknown"
    kind = spec["kind"]
    if kind == "range":
        low, high = spec["low"], spec["high"]
        warn_low = low * (1 - WARN_ZONE)
        warn_high = high * (1 + WARN_ZONE)
        if low <= value <= high:
            return "ok"
        if warn_low <= value <= warn_high:
            return "warning"
        return "bad"
    if kind == "min":
        m = spec["min"]
        if value >= m:
            return "ok"
        warn_border = m * (1 - WARN_ZONE) if m > 0 else m
        return "warning" if value >= warn_border else "bad"
    if kind == "max":
        m = spec["max"]
        if value <= m:
            return "ok"
        warn_border = m * (1 + WARN_ZONE)
        return "warning" if value <= warn_border else "bad"
    return "unknown"


def compute_ratios(values: Dict[str, float], prev_values: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Расчет коэффициентов по словарю {код_строки: значение}."""
    current_assets = _g(values, "1200")
    inventory = _g(values, "1210")
    receivables = _g(values, "1230")
    fin_assets = _g(values, "1240")
    cash = _g(values, "1250")
    equity = _g(values, "1300")
    lt_liab = _g(values, "1400")
    lt_loans = _g(values, "1410")
    st_liab = _g(values, "1500")
    st_loans = _g(values, "1510")
    payables = _g(values, "1520")
    total_assets = _g(values, "1600")

    revenue = _g(values, "2110")
    cogs = _g(values, "2120")
    gross_profit = _g(values, "2200")
    profit_before_tax = _g(values, "2300")
    interest_paid = _g(values, "2330")
    net_profit = _g(values, "2400")

    loans = lt_loans + st_loans
    money = cash + fin_assets
    net_debt = loans - money
    ebitda = profit_before_tax + interest_paid

    raw: Dict[str, Optional[float]] = {
        "current_ratio": _safe_div(current_assets, st_liab),
        "quick_ratio": _safe_div(current_assets - inventory, st_liab),
        "cash_ratio": _safe_div(money, st_liab),
        "autonomy": _safe_div(equity, total_assets),
        "debt_to_equity": _safe_div(loans, equity),
        "debt_to_assets": _safe_div(lt_liab + st_liab, total_assets),
        "working_capital": equity - _g(values, "1100"),
        "ros": _safe_div(gross_profit if gross_profit else profit_before_tax, revenue),
        "roa": _safe_div(net_profit, total_assets),
        "roe": _safe_div(net_profit, equity),
        "net_debt_ebitda": _safe_div(net_debt, ebitda) if ebitda > 0 else (None if net_debt <= 0 else float("inf")),
        "interest_coverage": _safe_div(ebitda, interest_paid) if interest_paid > 0 else None,
        "revenue_growth": None,
    }
    if prev_values:
        prev_rev = _g(prev_values, "2110")
        if prev_rev > 0:
            raw["revenue_growth"] = revenue / prev_rev - 1.0

    # Z-score Альтмана (5-факторная модель для непубличных компаний)
    x1 = _safe_div(current_assets - st_liab, total_assets) or 0.0
    x2 = _safe_div(net_profit, total_assets) or 0.0
    x3 = _safe_div(profit_before_tax + interest_paid, total_assets) or 0.0
    x4 = _safe_div(equity, lt_liab + st_liab) or 0.0
    x5 = _safe_div(revenue, total_assets) or 0.0
    z_score = 0.717 * x1 + 0.847 * x2 + 3.107 * x3 + 0.420 * x4 + 0.998 * x5
    if z_score > 2.9:
        z_status = "ok"
        z_zone = "низкий риск банкротства"
    elif z_score >= 1.23:
        z_status = "warning"
        z_zone = "серая зона"
    else:
        z_status = "bad"
        z_zone = "высокий риск банкротства"

    ratios: List[Dict[str, Any]] = []
    for spec in RATIO_DEFS:
        v = raw.get(spec["key"])
        status = evaluate(v, spec)
        ratios.append({
            "key": spec["key"],
            "name": spec["name"],
            "norm": spec["norm"],
            "value": None if v is None else (round(v, 3) if v != float("inf") else None),
            "status": status,
            "unit": spec["unit"],
        })

    by_key = {r["key"]: r["status"] for r in ratios}
    key_bad = sum(1 for k in KEY_RATIOS if by_key.get(k) == "bad")
    key_warn = sum(1 for k in KEY_RATIOS if by_key.get(k) == "warning")
    if key_bad >= 2:
        solvency = "low"
        solvency_label = "Низкая платежеспособность"
    elif key_bad == 1 or key_warn >= 2:
        solvency = "questionable"
        solvency_label = "Платежеспособность под вопросом"
    else:
        solvency = "ok"
        solvency_label = "Платежеспособность удовлетворительная"

    return {
        "ratios": ratios,
        "solvency": solvency,
        "solvency_label": solvency_label,
        "z_score": round(z_score, 3),
        "z_status": z_status,
        "z_zone": z_zone,
        "ebitda": round(ebitda, 2),
        "ebitda_note": "EBITDA приближенная: прибыль до налогообложения + проценты (без амортизации).",
        "derived": {
            "loans": round(loans, 2),
            "net_debt": round(net_debt, 2),
            "revenue": round(revenue, 2),
            "net_profit": round(net_profit, 2),
            "cogs": round(cogs, 2),
        },
    }
