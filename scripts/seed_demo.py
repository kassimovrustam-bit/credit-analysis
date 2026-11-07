"""Сидер демо-проекта: создает через API полный демо-проект со всеми разделами.

Запуск из корня проекта:  python scripts/seed_demo.py
Идемпотентен: повторный запуск удаляет прежний демо-проект и создает заново.
Использует in-process TestClient — внешний сервер не нужен; БД и файлы те же,
что у рабочего backend (backend/credit_analysis.db, backend/storage/).
"""

import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(BASE_DIR), "backend"))

from fastapi.testclient import TestClient

from app.main import app
from app.services import sample_data

client = TestClient(app)

DEMO_NAME = "ДЕМО: Строительство логистического центра (ГК «Вектор»)"


def fail(msg: str, resp=None) -> None:
    print(f"ОШИБКА: {msg}")
    if resp is not None:
        print(f"  HTTP {resp.status_code}: {resp.text[:500]}")
    sys.exit(1)


def expect(resp, ok=(200, 201), what=""):
    if resp.status_code not in ok:
        fail(what or "запрос не выполнен", resp)
    return resp.json() if resp.content else None


# --- Очистка прежнего демо-проекта (идемпотентность) ---
projects = expect(client.get("/api/projects"), what="список проектов")
for p in projects:
    if p["name"] == DEMO_NAME:
        resp = client.delete(f"/api/projects/{p['id']}")
        if resp.status_code != 204:
            fail("удаление прежнего демо-проекта", resp)
        print(f"Удален прежний демо-проект id={p['id']}")

# --- Проект ---
project = expect(client.post("/api/projects", json={
    "name": DEMO_NAME,
    "borrower": "ГК «Вектор» (ООО «Вектор-Логистика»)",
    "industry": "Складская логистика",
    "purpose": "Строительство логистического центра 20 000 м² в подмосковном кластере",
    "description": "Демонстрационный проект для проверки системы. Данные сгенерированы.",
    "status": "review",
}), what="создание проекта")
pid = project["id"]
print(f"Создан проект id={pid}")

# --- Компании группы и отчетность ---
companies_spec = [
    {"name": "ООО «Вектор-Логистика»", "inn": "7729451120", "okved": "52.10", "role": "borrower", "seed": 42},
    {"name": "ООО «Вектор-Холдинг»", "inn": "7729451121", "okved": "64.20", "role": "guarantor", "seed": 77},
]
for spec in companies_spec:
    seed = spec.pop("seed")
    c = expect(client.post(f"/api/projects/{pid}/companies", json=spec), what="создание компании")
    for year in (2024, 2025):
        values = sample_data.sample_statement_values(year=year, seed=seed)
        content = sample_data.statement_to_xlsx(values)
        resp = client.post(
            f"/api/companies/{c['id']}/statements",
            data={"year": str(year)},
            files={"file": (f"forma_{year}.xlsx", content,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        expect(resp, ok=(201,), what=f"загрузка отчетности {year}")
    print(f"  Компания «{spec['name']}»: отчетность 2024–2025 загружена")

# --- Прогноз ---
forecast = sample_data.sample_forecast(start_year=2027, years=7, seed=7)
expect(client.put(f"/api/projects/{pid}/forecast", json=forecast), what="прогноз")
print(f"  Прогноз: {len(forecast)} лет")

# --- Условия кредитования ---
# Параметры подобраны так, чтобы демо показывал осмысленную картину:
# NPV > 0, DSCR в зоне 1.2–2.5 по большинству лет.
expect(client.put(f"/api/projects/{pid}/terms", json={
    "amount": 40_000.0,
    "rate": 16.0,
    "term_months": 84,
    "grace_months": 12,
    "schedule_type": "annuity",
    "discount_rate": 15.0,
}), what="условия")
print("  Условия: 40 млн, 16%, 84 мес., льгота 12 мес., аннуитет")

# --- Учредители и проверки ---
founders_spec = [
    {"full_name": "Иванов Сергей Петрович", "inn": "771405236987", "share": 60.0, "role": "бенефициар"},
    {"full_name": "Петрова Анна Владимировна", "inn": "771405236988", "share": 40.0, "role": "бенефициар"},
]
for fs in founders_spec:
    f = expect(client.post(f"/api/projects/{pid}/founders", json=fs), what="учредитель")
    for ct in ("tax_debt", "enforcement", "bankruptcy", "disqualification", "arbitration"):
        expect(client.put(f"/api/founders/{f['id']}/checks/{ct}", json={
            "status": "clean",
            "comment": "Задолженности/производства не выявлены (выписка от 05.11.2026).",
        }), what=f"проверка {ct}")
    print(f"  Учредитель {fs['full_name']}: 5 проверок «чисто»")

# --- Риски ---
risks_spec = [
    {"title": "Рост ставки по кредиту при рефинансировании",
     "category": "financial", "criticality": "medium",
     "description": "Часть долга с плавающей ставкой.",
     "mitigation": "Фиксация ставки на весь срок в кредитном договоре."},
    {"title": "Задержка ввода объекта в эксплуатацию",
     "category": "structural", "criticality": "high",
     "description": "Зависимость от генподрядчика и согласований.",
     "mitigation": "Неустойка в договоре генподряда, резерв 3 мес. в графике."},
    {"title": "Незаполненность складов арендаторами",
     "category": "industry", "criticality": "medium",
     "description": "Конкуренция в кластере.",
     "mitigation": ""},
]
for rs in risks_spec:
    expect(client.post(f"/api/projects/{pid}/risks", json=rs), what="риск")
print(f"  Риски: {len(risks_spec)}")

# --- Документы ---
bp_text = (
    "Бизнес-план «Логистический центр Вектор».\n"
    "Бюджет проекта: 120 000 тыс. руб.\n"
    "NPV проекта: 45 000 тыс. руб. при ставке дисконтирования 18%.\n"
    "IRR: 24%. Срок окупаемости: 5,5 лет.\n"
)
doc = expect(client.post(
    f"/api/projects/{pid}/documents",
    data={"doc_type": "business_plan"},
    files={"file": ("business_plan.txt", bp_text.encode("utf-8"), "text/plain")},
), ok=(201,), what="загрузка бизнес-плана")
print(f"  Документы: бизнес-план загружен, извлечено фактов: {len(doc.get('extracted') or {})}")

# --- Резюме и скоринг ---
summary = expect(client.get(f"/api/projects/{pid}/summary"), what="резюме")
sc = summary["scoring"]
print()
print(f"Скоринг: {sc['total_score']} / 100 — {sc['verdict']}")
for k, label in (("finance", "Финансы"), ("project", "Проект"),
                 ("founders", "Учредители"), ("risks", "Риски")):
    print(f"  {label}: {sc['blocks'][k]['score']}")

resp = client.get(f"/api/projects/{pid}/summary/docx")
if resp.status_code != 200 or len(resp.content) < 1000:
    fail("выгрузка .docx", resp)
print(f"  Выгрузка .docx: {len(resp.content)} байт")

print()
print(f"Готово. Демо-проект id={pid} доступен в интерфейсе и через /api/projects/{pid}.")
