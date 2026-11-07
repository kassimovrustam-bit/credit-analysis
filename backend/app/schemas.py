from typing import Optional, List, Dict, Any

from pydantic import BaseModel


class ProjectIn(BaseModel):
    name: str
    borrower: str = ""
    industry: str = ""
    purpose: str = ""
    description: str = ""
    status: str = "draft"


class ProjectOut(ProjectIn):
    id: int
    created_at: str = ""
    updated_at: str = ""
    counters: Dict[str, int] = {}
    last_score: Optional[float] = None
    last_verdict: Optional[str] = None

    class Config:
        from_attributes = True


class CompanyIn(BaseModel):
    name: str
    inn: str = ""
    okved: str = ""
    role: str = "borrower"


class CompanyOut(CompanyIn):
    id: int
    project_id: int
    years: List[int] = []

    class Config:
        from_attributes = True


class StatementOut(BaseModel):
    id: int
    company_id: int
    year: int
    values: Dict[str, float]

    class Config:
        from_attributes = True


class ForecastRowIn(BaseModel):
    year: int
    revenue: float = 0.0
    ebitda: float = 0.0
    capex: float = 0.0
    tax: float = 0.0
    cfads: Optional[float] = None


class ForecastRowOut(ForecastRowIn):
    id: int

    class Config:
        from_attributes = True


class TermsIn(BaseModel):
    amount: float = 0.0
    rate: float = 0.0
    term_months: int = 0
    grace_months: int = 0
    schedule_type: str = "annuity"
    discount_rate: float = 15.0


class TermsOut(TermsIn):
    id: int
    project_id: int

    class Config:
        from_attributes = True


class FounderIn(BaseModel):
    full_name: str
    inn: str = ""
    share: float = 0.0
    role: str = ""


class CheckIn(BaseModel):
    status: str = "clean"
    comment: str = ""
    checked_at: str = ""


class CheckOut(CheckIn):
    id: int
    check_type: str

    class Config:
        from_attributes = True


class FounderOut(FounderIn):
    id: int
    project_id: int
    checks: List[CheckOut] = []
    pkb: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class RiskIn(BaseModel):
    title: str
    category: str = "structural"
    criticality: str = "medium"
    description: str = ""
    mitigation: str = ""


class RiskOut(RiskIn):
    id: int
    project_id: int

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: int
    project_id: int
    doc_type: str
    filename: str
    uploaded_at: str
    extracted: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class ScoringOut(BaseModel):
    id: int
    project_id: int
    total_score: float
    verdict: str
    details: Dict[str, Any]
    created_at: str

    class Config:
        from_attributes = True
