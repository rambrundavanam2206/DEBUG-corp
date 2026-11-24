from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(StrictModel):
    path: str = Field(min_length=1, max_length=500)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=3000)


class Finding(StrictModel):
    title: str = Field(min_length=1, max_length=180)
    explanation: str = Field(min_length=1, max_length=1800)
    suggested_fix: str = Field(min_length=1, max_length=1800)
    evidence: list[Evidence] = Field(min_length=1, max_length=3)


class Diagnosis(StrictModel):
    summary: str = Field(min_length=1, max_length=2000)
    confidence: Literal["low", "medium", "high"]
    findings: list[Finding] = Field(max_length=10)
    suggested_reproduction: list[str] = Field(max_length=8)
    verification_steps: list[str] = Field(max_length=8)
    questions: list[str] = Field(max_length=5)
    limitations: list[str] = Field(max_length=8)


class AnalysisFailure(Exception):
    """A safe, user-facing analysis failure; never include raw provider errors."""

    def __init__(self, message: str, code: str = "analysis_failed"):
        super().__init__(message)
        self.code = code
