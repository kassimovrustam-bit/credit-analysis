from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False)
    borrower = Column(String(500), default="")
    industry = Column(String(300), default="")
    purpose = Column(String(500), default="")
    description = Column(Text, default="")
    status = Column(String(30), default="draft")  # draft/review/approved/rejected
    created_at = Column(String(30), default="")
    updated_at = Column(String(30), default="")

    companies = relationship("Company", back_populates="project", cascade="all, delete-orphan")
    founders = relationship("Founder", back_populates="project", cascade="all, delete-orphan")
    risks = relationship("Risk", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    forecast_rows = relationship("ForecastRow", back_populates="project", cascade="all, delete-orphan")
    terms = relationship("CreditTerms", back_populates="project", uselist=False, cascade="all, delete-orphan")
    scoring_runs = relationship("ScoringRun", back_populates="project", cascade="all, delete-orphan")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(500), nullable=False)
    inn = Column(String(20), default="")
    okved = Column(String(20), default="")
    role = Column(String(30), default="borrower")  # borrower/guarantor/related

    project = relationship("Project", back_populates="companies")
    statements = relationship("Statement", back_populates="company", cascade="all, delete-orphan")


class Statement(Base):
    __tablename__ = "statements"
    __table_args__ = (UniqueConstraint("company_id", "year", name="uq_statement_company_year"),)

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    year = Column(Integer, nullable=False)
    values_json = Column(Text, default="{}")

    company = relationship("Company", back_populates="statements")


class ForecastRow(Base):
    __tablename__ = "forecast_rows"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    year = Column(Integer, nullable=False)
    revenue = Column(Float, default=0.0)
    ebitda = Column(Float, default=0.0)
    capex = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    cfads = Column(Float, nullable=True)

    project = relationship("Project", back_populates="forecast_rows")


class CreditTerms(Base):
    __tablename__ = "credit_terms"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, unique=True)
    amount = Column(Float, default=0.0)
    rate = Column(Float, default=0.0)          # годовая ставка, %
    term_months = Column(Integer, default=0)
    grace_months = Column(Integer, default=0)
    schedule_type = Column(String(20), default="annuity")  # annuity/differentiated
    discount_rate = Column(Float, default=15.0)  # ставка дисконтирования, %

    project = relationship("Project", back_populates="terms")


class Founder(Base):
    __tablename__ = "founders"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    full_name = Column(String(500), nullable=False)
    inn = Column(String(20), default="")
    share = Column(Float, default=0.0)
    role = Column(String(200), default="")

    project = relationship("Project", back_populates="founders")
    checks = relationship("FounderCheck", back_populates="founder", cascade="all, delete-orphan")
    pkb_reports = relationship("PkbReport", back_populates="founder", cascade="all, delete-orphan")


class FounderCheck(Base):
    __tablename__ = "founder_checks"
    __table_args__ = (UniqueConstraint("founder_id", "check_type", name="uq_check_founder_type"),)

    id = Column(Integer, primary_key=True)
    founder_id = Column(Integer, ForeignKey("founders.id"), nullable=False)
    check_type = Column(String(30), nullable=False)  # см. config.CHECK_TYPES
    status = Column(String(20), default="clean")     # clean/attention/negative
    comment = Column(Text, default="")
    checked_at = Column(String(30), default="")

    founder = relationship("Founder", back_populates="checks")


class PkbReport(Base):
    __tablename__ = "pkb_reports"

    id = Column(Integer, primary_key=True)
    founder_id = Column(Integer, ForeignKey("founders.id"), nullable=False)
    file_path = Column(String(1000), default="")
    uploaded_at = Column(String(30), default="")
    result_json = Column(Text, default="{}")

    founder = relationship("Founder", back_populates="pkb_reports")


class Risk(Base):
    __tablename__ = "risks"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(500), nullable=False)
    category = Column(String(30), default="structural")  # structural/industry/financial/other
    criticality = Column(String(20), default="medium")   # low/medium/high/critical
    description = Column(Text, default="")
    mitigation = Column(Text, default="")

    project = relationship("Project", back_populates="risks")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    doc_type = Column(String(30), default="other")  # см. config.DOC_TYPES
    filename = Column(String(500), default="")
    file_path = Column(String(1000), default="")
    uploaded_at = Column(String(30), default="")
    extracted_json = Column(Text, default="{}")

    project = relationship("Project", back_populates="documents")


class ScoringRun(Base):
    __tablename__ = "scoring_runs"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    total_score = Column(Float, default=0.0)
    verdict = Column(String(50), default="")
    details_json = Column(Text, default="{}")
    created_at = Column(String(30), default="")

    project = relationship("Project", back_populates="scoring_runs")
