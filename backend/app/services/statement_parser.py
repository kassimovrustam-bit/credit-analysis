"""Парсер форм 1 (баланс) и 2 (отчет о финрезультатах) РСБУ из .xlsx/.csv.

Извлекает значения по 4-значным кодам строк. При нескольких числах в строке
берется первое (на отчетную дату / за отчетный период). Расходные строки
формы 2 (проценты 2330 и т.п.) приводятся к модулю.
"""

import csv
import io
import re
from typing import Dict, Optional

# Коды строк, извлекаемые парсером
BALANCE_CODES = [
    "1100", "1200", "1210", "1230", "1240", "1250",
    "1300", "1400", "1410", "1500", "1510", "1520", "1600",
]
INCOME_CODES = [
    "2110", "2120", "2200", "2210", "2220",
    "2300", "2310", "2320", "2330", "2400", "2410", "2500",
]
# Расходные строки формы 2 — приводятся к модулю
NEGATIVE_CODES = {"2120", "2210", "2220", "2330"}

_CODE_RE = re.compile(r"^\s*(\d{4})\s*$")
_NUM_RE = re.compile(r"^-?[\d\s  ]+([.,]\d+)?-?$")


def _parse_number(raw) -> Optional[float]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    if not s or s in ("-", "—", "–"):
        return None
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    s = s.replace(" ", "").replace(" ", "").replace(" ", "").replace(",", ".")
    if s.endswith("-"):
        negative = True
        s = s[:-1]
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if negative else v


def _collect_rows_from_xlsx(data: bytes):
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        ws = wb.worksheets[0]
        rows = []
        for row in ws.iter_rows(values_only=True):
            rows.append([c for c in row])
        return rows
    finally:
        wb.close()


def _collect_rows_from_csv(data: bytes):
    text = None
    for enc in ("utf-8-sig", "cp1251", "utf-8"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = data.decode("utf-8", errors="replace")
    sample = text[:2000]
    dialect = csv.Sniffer().sniff(sample, delimiters=";,\t") if sample.strip() else csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    return [list(r) for r in reader]


def parse_statement(data: bytes, filename: str) -> Dict[str, float]:
    """Разбирает файл формы 1/2 и возвращает {код_строки: значение}."""
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        rows = _collect_rows_from_xlsx(data)
    elif name.endswith(".csv"):
        rows = _collect_rows_from_csv(data)
    else:
        raise ValueError("Поддерживаются файлы .xlsx и .csv")

    values: Dict[str, float] = {}
    for row in rows:
        if not row:
            continue
        code: Optional[str] = None
        code_idx = -1
        for i, cell in enumerate(row):
            if cell is None:
                continue
            m = _CODE_RE.match(str(cell))
            if m:
                code = m.group(1)
                code_idx = i
                break
        if code is None or code not in BALANCE_CODES + INCOME_CODES:
            continue
        # берем первое число после кода (на отчетную дату / за отчетный период)
        for cell in row[code_idx + 1:]:
            v = _parse_number(cell)
            if v is not None:
                if code in NEGATIVE_CODES:
                    v = abs(v)
                values[code] = v
                break
    return values
