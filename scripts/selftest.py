"""Самотест расчетных сервисов: парсер форм, коэффициенты, NPV/IRR, график, DSCR.

Запуск из корня проекта:  python scripts/selftest.py
Без обращений к БД и HTTP — только чистые функции сервисного слоя.
"""

import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from app.services import statement_parser, ratios, finance, sample_data, pkb_parser, scoring

FAILURES = []


def check(name: str, cond: bool, detail: str = "") -> None:
    mark = "OK " if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


def approx(a, b, tol=1e-6) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol


# 1. Парсер форм 1/2
values = sample_data.sample_statement_values(year=2025, seed=42)
xlsx_bytes = sample_data.statement_to_xlsx(values)
parsed = statement_parser.parse_statement(xlsx_bytes, "forma1.xlsx")
check("Парсер .xlsx: извлечены все коды", set(values.keys()) <= set(parsed.keys()))
check("Парсер: значение 2110 совпадает", approx(parsed.get("2110"), values["2110"]))
check("Парсер: расходная строка 2330 приведена к модулю", parsed.get("2330", -1) >= 0)

csv_text = "Код;Наименование;Значение\n2110;Выручка;123 456,78\n2330;Проценты к уплате;(2 500)\n1250;Денежные средства;1000\n"
parsed_csv = statement_parser.parse_statement(csv_text.encode("utf-8-sig"), "forma.csv")
check("Парсер .csv: разделитель ';', запятая в числе", approx(parsed_csv.get("2110"), 123456.78))
check("Парсер .csv: скобки -> модуль для 2330", approx(parsed_csv.get("2330"), 2500.0))

# 2. Коэффициенты
res = ratios.compute_ratios(values)
keys = {r["key"] for r in res["ratios"]}
check("Коэффициенты: рассчитаны все 13 показателей", len(keys) == 13, str(len(keys)))
check("Платежеспособность определена", res["solvency"] in ("ok", "questionable", "low"))
check("Z-score посчитан", isinstance(res["z_score"], float))
check("EBITDA = прибыль до налога + проценты", approx(res["ebitda"], values["2300"] + values["2330"]))
statuses = {r["key"]: r["status"] for r in res["ratios"]}
check("Статусы в допустимом наборе", all(s in ("ok", "warning", "bad", "unknown") for s in statuses.values()))

weak = sample_data.sample_statement_values(year=2025, seed=1, profile="weak")
weak_res = ratios.compute_ratios(weak)
check("Слабый профиль: оценка не выше нормальной",
      ["low", "questionable", "ok"].index(weak_res["solvency"]) <= ["low", "questionable", "ok"].index(res["solvency"]))

# 3. NPV / IRR / PI / окупаемость
forecast = sample_data.sample_forecast(start_year=2026, years=5, seed=7)
# Инвестиция подобрана так, чтобы NPV > 0 и IRR лежал в области локализации бисекции.
investment = 20_000.0
y = finance.project_yield(forecast, investment, 15.0)
check("NPV посчитан", isinstance(y["npv"], float))
check("NPV > 0 (приемлемо)", y["npv"] > 0 and y["npv_status"] == "ok", f"NPV={y['npv']}")
check("IRR посчитан и > ставки дисконтирования",
      y["irr"] is not None and y["irr"] > 15.0, f"IRR={y['irr']}")
check("PI посчитан и > 1", y["pi"] is not None and y["pi"] > 1, f"PI={y['pi']}")
check("Сроки окупаемости посчитаны", y["payback_simple_years"] is not None)

flows = [finance.compute_cfads(r) for r in forecast]
cfs = [-investment] + flows
check("NPV(IRR) ~= 0 (самосогласованность; допуск с учетом округления IRR до 0.01 п.п.)",
      abs(finance.npv(y["irr"] / 100.0, cfs)) < 0.05 * investment,
      f"NPV(IRR)={finance.npv(y['irr'] / 100.0, cfs):.4f}")
check("IRR некорректной формы потока -> None",
      finance.irr([100.0, 100.0, 100.0]) is None)

# 4. График платежей
sched_ann = finance.payment_schedule(120_000.0, 12.0, 24, 0, "annuity")
check("Аннуитет: 24 платежа", len(sched_ann) == 24)
check("Аннуитет: баланс погашен в ноль", approx(sched_ann[-1]["balance"], 0.0, tol=0.01))
first_pay = sched_ann[0]["payment"]
check("Аннуитет: платежи почти равные", all(abs(r["payment"] - first_pay) < 0.02 for r in sched_ann[1:]))

sched_diff = finance.payment_schedule(120_000.0, 12.0, 24, 0, "differentiated")
check("Дифференцированный: тело равными долями",
      all(approx(r["principal"], 120_000.0 / 24, tol=0.01) for r in sched_diff))
check("Дифференцированный: первый платеж выше последнего", sched_diff[0]["payment"] > sched_diff[-1]["payment"])

sched_grace = finance.payment_schedule(120_000.0, 12.0, 24, 6, "annuity")
check("Льготный период: первые 6 платежей — только проценты",
      all(r["principal"] == 0.0 for r in sched_grace[:6]))
check("Льготный период: баланс не меняется в льготе",
      all(approx(r["balance"], 120_000.0, tol=0.01) for r in sched_grace[:6]))

# 5. DSCR
dscr = finance.dscr_by_year(forecast, sched_ann)
check("DSCR рассчитан по годам", len(dscr) > 0 and all("dscr" in d for d in dscr))
for d in dscr:
    if d["dscr"] is not None and d["debt_service"] > 0:
        check(f"DSCR {d['year']}: статус корректен",
              (d["dscr"] >= 1.2 and d["status"] == "ok") or
              (1.0 <= d["dscr"] < 1.2 and d["status"] == "warning") or
              (d["dscr"] < 1.0 and d["status"] == "bad"),
              f"DSCR={d['dscr']} status={d['status']}")
        break

# Обслуживание долга привязывается к календарным годам прогноза
dscr_cal = finance.dscr_by_year(forecast, sched_ann, start_year=2026)
svc_2026 = next(d for d in dscr_cal if d["year"] == 2026)
sched_year1 = sum(r["payment"] for r in sched_ann[:12])
check("DSCR: год 2026 содержит платежи первых 12 мес. кредита",
      approx(svc_2026["debt_service"], sched_year1, tol=0.02),
      f"{svc_2026['debt_service']} vs {sched_year1}")
check("DSCR: годы прогноза совпадают с календарными",
      [d["year"] for d in dscr_cal][:5] == [2026, 2027, 2028, 2029, 2030])

# 6. Парсер ПКБ (на синтетическом тексте через монк _extract_text)
sample_text = (
    "Кредитный отчет. Общее число кредитных договоров: 12. Открытых договоров: 3. "
    "Текущая задолженность: 1 250 000 руб. Максимальная просрочка 45 дней. "
    "Реструктуризация задолженности имела место в 2023 году."
)
_orig = pkb_parser._extract_text
pkb_parser._extract_text = lambda data: sample_text
try:
    pkb = pkb_parser.parse_pkb_report(b"fake")
finally:
    pkb_parser._extract_text = _orig
check("ПКБ: число договоров извлечено", pkb["contracts_total"] == 12, str(pkb["contracts_total"]))
check("ПКБ: открытых договоров извлечено", pkb["contracts_open"] == 3)
check("ПКБ: макс. просрочка 45 дней", pkb["max_overdue_days"] == 45, str(pkb["max_overdue_days"]))
check("ПКБ: маркер реструктуризации", pkb["markers"]["restructuring"] is True)
check("ПКБ: качество = warning (просрочка 45 дн + маркер)", pkb["quality"] == "warning")
check("ПКБ: сниппеты сформированы", len(pkb["snippets"]) > 0)
check("ПКБ: дисклеймер присутствует", "сверке аналитиком" in pkb["disclaimer"])

# 7. Скоринг
sc = scoring.compute_scoring([res], y, dscr, [], [])
check("Скоринг: итог в диапазоне 0–100", 0.0 <= sc["total_score"] <= 100.0, str(sc["total_score"]))
check("Скоринг: вердикт из списка",
      sc["verdict"] in scoring.VERDICTS.values())
blocks = sc["blocks"]
check("Скоринг: 4 блока рассчитаны", set(blocks.keys()) == {"finance", "project", "founders", "risks"})

sc_risky = scoring.compute_scoring(
    [res], y, dscr, [],
    [{"title": "Риск", "category": "financial", "criticality": "high", "mitigation": ""}])
check("Скоринг: риск без мер снижает балл", sc_risky["blocks"]["risks"]["score"] < 100.0)
sc_mitigated = scoring.compute_scoring(
    [res], y, dscr, [],
    [{"title": "Риск", "category": "financial", "criticality": "high", "mitigation": "Страхование"}])
check("Скоринг: меры снижения уменьшают штраф на 40%",
      approx(sc_mitigated["blocks"]["risks"]["total_penalty"], 10.0 * 0.6, tol=0.01),
      str(sc_mitigated["blocks"]["risks"]["total_penalty"]))

print()
if FAILURES:
    print(f"ПРОВАЛЕНО проверок: {len(FAILURES)}: {', '.join(FAILURES)}")
    sys.exit(1)
print("Все проверки пройдены.")
