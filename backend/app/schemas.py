from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(StrictModel):
    account: Literal["citizen-1", "citizen-2", "citizen-3", "staff-1", "staff-2", "staff-3", "staff-4", "admin-1"]


class CaseCreate(StrictModel):
    title: str = Field(min_length=5, max_length=160)
    category: Literal["Consumer", "Civil", "Commercial"] = "Civil"
    court: str = Field(default="Nyaya Demo District Forum", min_length=3, max_length=150)
    owner_id: str = "citizen-1"
    assigned_staff: str = "staff-1"


class CasePatch(StrictModel):
    status: Literal["Pending", "Closed"] | None = None
    stage: Literal["Document review", "Notice", "Evidence", "Arguments"] | None = None
    note: str | None = Field(default=None, min_length=3, max_length=1500)


class TaskCreate(StrictModel):
    title: str = Field(min_length=3, max_length=200)
    deadline: date
    assigned_staff: str = "staff-1"


class TaskPatch(StrictModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    deadline: date | None = None
    assigned_staff: str | None = None
    status: Literal["pending", "complete"] | None = None


class Query(StrictModel):
    question: str = Field(min_length=3, max_length=2000)
    source_type: str | None = None
    jurisdiction: str | None = None
    mode: Literal["keyword", "similarity"] = "similarity"


class SummaryInput(StrictModel):
    document_id: str


class FilingInput(StrictModel):
    case_id: str
    document_ids: list[str] = Field(min_length=1, max_length=10)
    applicant_name: str = Field(min_length=2, max_length=100)
    respondent_name: str = Field(min_length=2, max_length=100)
    incident_date: date
    document_types: dict[str, Literal["statement", "supporting record", "other"]]


class ScheduleInput(StrictModel):
    case_id: str
    start_date: date
    duration_minutes: Literal[30, 60] = 60
    deadline: date | None = None


class ScheduleApprove(StrictModel):
    case_id: str
    start: datetime
    duration_minutes: Literal[30, 60] = 60


class RiskInput(StrictModel):
    case_id: str


class DecisionInput(StrictModel):
    case_id: str
    summary: str = Field(min_length=10, max_length=5000)
    provisions: str = Field(default="", max_length=1500)
    claimant: str = Field(min_length=10, max_length=5000)
    opponent: str = Field(min_length=10, max_length=5000)
    evidence: str = Field(min_length=5, max_length=8000)
    questions: str = Field(min_length=5, max_length=2000)
    document_ids: list[str] = Field(default_factory=list, max_length=10)
    reviewed: bool = False


class IngestInput(StrictModel):
    document_id: str
    title: str = Field(min_length=3, max_length=200)
    jurisdiction: str = Field(default="India", max_length=80)
    source_type: Literal["statute", "judgment", "procedural rules", "local document"] = "local document"
    publication_date: date | None = None
    effective_date: date | None = None