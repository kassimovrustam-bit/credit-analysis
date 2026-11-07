"""Генератор тестовых данных: формы 1/2 и прогноз проекта."""

import io
import random
from typing import Dict, List


def sample_statement_values(year: int = 2025, seed: int = 42, profile: str = "normal") -> Dict[str, float]:
    """Правдоподобный набор значений форм 1/2 (тыс. руб.)."""
    rnd = random.Random(seed + year)
    mult = 1.0 if profile == "normal" else (0.6 if profile == "weak" else 1.4)

    revenue = rnd.uniform(80_000, 150_000) * mult * (1.0 + (year - 2024) * 0.1)
    cogs = revenue * rnd.uniform(0.6, 0.75)
    gross = revenue - cogs
    profit_before_tax = gross * rnd.uniform(0.35, 0.55)
    interest = revenue * 0.02
    net_profit = profit_before_tax * 0.8

    fixed = revenue * 0.5
    inventory = revenue * 0.15
    receivables = revenue * 0.12
    fin_assets = revenue * 0.02
    cash = revenue * 0.05
    current_assets = inventory + receivables + fin_assets + cash + revenue * 0.01
    total_assets = fixed + current_assets
    equity = total_assets * (0.55 if profile == "normal" else 0.3)
    lt_loans = total_assets * 0.2
    st_loans = total_assets * 0.1
    payables = total_assets - equity - lt_loans - st_loans

    return {
        "1100": round(fixed, 0),
        "1200": round(current_assets, 0),
        "1210": round(inventory, 0),
        "1230": round(receivables, 0),
        "1240": round(fin_assets, 0),
        "1250": round(cash, 0),
        "1300": round(equity, 0),
        "1400": round(lt_loans, 0),
        "1410": round(lt_loans, 0),
        "1500": round(st_loans + payables, 0),
        "1510": round(st_loans, 0),
        "1520": round(payables, 0),
        "1600": round(total_assets, 0),
        "2110": round(revenue, 0),
        "2120": round(cogs, 0),
        "2200": round(gross, 0),
        "2300": round(profit_before_tax, 0),
        "2330": round(interest, 0),
        "2400": round(net_profit, 0),
        "2500": round(net_profit, 0),
    }


def statement_to_xlsx(values: Dict[str, float]) -> bytes:
    """Генерирует .xlsx формы с колонками: код, наименование, значение."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Форма"
    ws.append(["Код строки", "Наименование показателя", "Значение"])
    for code, value in values.items():
        ws.append([code, f"Показатель {code}", value])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def sample_forecast(start_year: int = 2026, years: int = 5, seed: int = 7) -> List[Dict]:
    rnd = random.Random(seed)
    rows = []
    base = rnd.uniform(90_000, 130_000)
    for i in range(years):
        revenue = base * (1.15 ** i)
        ebitda = revenue * 0.22
        capex = base * 0.08 if i < 2 else base * 0.03
        tax = ebitda * 0.2
        rows.append({
            "year": start_year + i,
            "revenue": round(revenue, 0),
            "ebitda": round(ebitda, 0),
            "capex": round(capex, 0),
            "tax": round(tax, 0),
            "cfads": round(ebitda - capex - tax, 0),
        })
    return rows


def forecast_to_xlsx(rows: List[Dict]) -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Прогноз"
    ws.append(["year", "revenue", "ebitda", "capex", "tax", "cfads"])
    for r in rows:
        ws.append([r["year"], r["revenue"], r["ebitda"], r["capex"], r["tax"], r.get("cfads")])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
