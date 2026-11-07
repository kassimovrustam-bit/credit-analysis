"""Извлечение ключевых фактов из бизнес-плана (PDF/TXT):
NPV, IRR, срок окупаемости, бюджет проекта."""

import io
import re
from typing import Dict, Any


def _extract_text(data: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        import pdfplumber

        parts = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                if t:
                    parts.append(t)
        return "\n".join(parts)
    for enc in ("utf-8", "cp1251"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _num(s: str) -> float:
    s = re.sub(r"[^\d,\.\-]", "", s.replace(" ", "").replace(" ", "")).replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def extract_business_plan_facts(data: bytes, filename: str) -> Dict[str, Any]:
    text = _extract_text(data, filename)
    if not text.strip():
        return {"note": "Текст не извлечен (возможно, скан без текстового слоя)."}
    low = text.lower()

    facts: Dict[str, Any] = {}

    m = re.search(r"(?:npv|чдд|чист\w+\s+приведен\w+\s+(?:доход|стоимост\w+))[^\d\-]{0,40}(-?[\d\s]+(?:[.,]\d+)?)", low)
    if m:
        facts["npv"] = _num(m.group(1))

    m = re.search(r"(?:irr|внд|внутренн\w+\s+норм\w+\s+(?:доходност\w+|рентабельност\w+))[^\d]{0,40}([\d]+(?:[.,]\d+)?)", low)
    if m:
        facts["irr_pct"] = _num(m.group(1))

    m = re.search(r"(?:срок\s+окупаемост\w+|окупаемост\w+)[^\d]{0,40}(\d+(?:[.,]\d+)?)\s*(год|года|лет|мес)", low)
    if m:
        v = _num(m.group(1))
        unit = m.group(2)
        facts["payback_months"] = round(v * 12) if unit.startswith("г") or unit.startswith("л") else round(v)

    m = re.search(r"(?:бюджет|стоимость\s+проекта|инвестиционн\w+\s+(?:затрат\w+|расход\w+)|капитальн\w+\s+вложени\w+)[^\d]{0,40}([\d\s]+(?:[.,]\d+)?)\s*(млн|тыс|руб)?", low)
    if m:
        v = _num(m.group(1))
        unit = m.group(2) or ""
        if unit.startswith("млн"):
            v *= 1_000_000
        elif unit.startswith("тыс"):
            v *= 1_000
        facts["budget"] = v

    facts["note"] = "Факты извлечены автоматически из текста документа и требуют сверки с оригиналом."
    return facts
