"""Эвристический парсер отчета Первого кредитного бюро (PDF с текстовым слоем).

ВНИМАНИЕ: результат парсинга подлежит обязательной сверке аналитиком
с оригиналом отчета. Структура отчетов ПКБ может меняться.
"""

import re
from typing import Dict, Any, List

DISCLAIMER = (
    "Результат автоматического разбора отчета ПКБ носит справочный характер "
    "и подлежит обязательной сверке аналитиком с оригиналом документа."
)

NEGATIVE_MARKERS = {
    "bankruptcy": ["банкротств", "несостоятельн"],
    "default": ["дефолт"],
    "restructuring": ["реструктуризац", "реструктурирован"],
    "writeoff": ["списани", "списан "],
    "court": ["судебн", "исков", "взыскан"],
}


def _extract_text(data: bytes) -> str:
    import pdfplumber
    import io

    parts: List[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t:
                parts.append(t)
    return "\n".join(parts)


def _to_int(s: str) -> int:
    return int(re.sub(r"[^\d]", "", s) or 0)


def _to_float(s: str) -> float:
    s = re.sub(r"[^\d,\.]", "", s).replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _find_snippets(text: str, keywords: List[str], window: int = 160, limit: int = 8) -> List[str]:
    snippets: List[str] = []
    low = text.lower()
    for kw in keywords:
        start = 0
        while len(snippets) < limit:
            i = low.find(kw, start)
            if i == -1:
                break
            a = max(0, i - window // 2)
            b = min(len(text), i + window)
            snippet = " ".join(text[a:b].split())
            if snippet not in snippets:
                snippets.append(snippet)
            start = i + len(kw)
    return snippets


def parse_pkb_report(data: bytes) -> Dict[str, Any]:
    """Возвращает структуру с показателями кредитной истории и сниппетами."""
    text = _extract_text(data)
    if not text.strip():
        return {
            "error": "Не удалось извлечь текст: PDF без текстового слоя (скан) не разбирается.",
            "disclaimer": DISCLAIMER,
        }

    low = text.lower()

    contracts_total = 0
    m = re.search(r"(?:всего|общее\s+число)\s+(?:кредитных\s+)?договоров[^\d]{0,30}(\d+)", low)
    if m:
        contracts_total = _to_int(m.group(1))
    else:
        m = re.search(r"количество\s+(?:кредитных\s+)?договоров[^\d]{0,30}(\d+)", low)
        if m:
            contracts_total = _to_int(m.group(1))

    contracts_open = 0
    m = re.search(r"(?:открытых|действующих|активных)\s+(?:договоров|счетов)?[^\d]{0,20}(\d+)", low)
    if m:
        contracts_open = _to_int(m.group(1))

    current_debt = 0.0
    m = re.search(r"(?:текущая|остаток)\s+(?:задолженность|ссудная\s+задолженность)[^\d]{0,30}([\d\s]+(?:[.,]\d+)?)", low)
    if m:
        current_debt = _to_float(m.group(1))

    max_overdue_days = 0
    m = re.search(r"(?:максимальн\w*\s+)?просрочк\w*[^\d]{0,40}(\d{1,4})\s*(?:дн|дней|дн\.)", low)
    if m:
        max_overdue_days = _to_int(m.group(1))

    markers: Dict[str, bool] = {}
    marker_snippets: List[str] = []
    for key, words in NEGATIVE_MARKERS.items():
        hit = any(w in low for w in words)
        markers[key] = hit
        if hit:
            marker_snippets.extend(_find_snippets(text, words))

    overdue_snippets = _find_snippets(text, ["просрочк"])

    if markers.get("bankruptcy") or max_overdue_days >= 90:
        quality = "bad"
    elif max_overdue_days >= 30 or any(markers.values()):
        quality = "warning"
    else:
        quality = "ok"

    return {
        "contracts_total": contracts_total,
        "contracts_open": contracts_open,
        "current_debt": current_debt,
        "max_overdue_days": max_overdue_days,
        "markers": markers,
        "quality": quality,
        "snippets": (marker_snippets + overdue_snippets)[:12],
        "disclaimer": DISCLAIMER,
    }
