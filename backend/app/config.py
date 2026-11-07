import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

DATABASE_URL = "sqlite:///" + os.path.join(BASE_DIR, "credit_analysis.db")

DOC_TYPES = {
    "business_plan": "Бизнес-план",
    "charter": "Учредительные документы",
    "personal": "Личные документы",
    "permits": "Разрешительные документы",
    "terms": "Условия кредитования",
    "other": "Прочее",
}

CHECK_TYPES = {
    "tax_debt": "Налоговая задолженность (ФНС)",
    "enforcement": "Исполнительные производства (ФССП)",
    "bankruptcy": "Банкротство (ЕФРСБ)",
    "disqualification": "Дисквалификация",
    "arbitration": "Арбитражные дела",
}
