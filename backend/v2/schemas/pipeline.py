"""
Pipeline orchestration schemas.

Tracks the state of an analysis job as it flows through
all pipeline stages.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PipelineStage(str, Enum):
    """Stages of the analysis pipeline."""

    PARSING = "parsing"
    EXTRACTION = "extraction"
    MATCHING = "matching"
    VALIDATION = "validation"
    GAP_ANALYSE = "gap_analyse"
    OUTPUT = "output"


class StageStatus(str, Enum):
    """Status of a single pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageProgress(BaseModel):
    """Progress tracking for a single pipeline stage."""

    stage: PipelineStage = Field(description="Which pipeline stage")
    status: StageStatus = Field(description="Current status of the stage")
    fortschritt_prozent: float = Field(
        0.0, description="Progress percentage between 0.0 and 100.0"
    )
    aktuelle_position: Optional[str] = Field(
        None, description="Currently processing position number"
    )
    details: Optional[str] = Field(
        None, description="Additional status details"
    )


class AnalysisJob(BaseModel):
    """A complete analysis job tracking all pipeline stages."""

    job_id: str = Field(description="Unique job identifier")
    erstellt_am: datetime = Field(description="Job creation timestamp")
    dateien: list[str] = Field(
        description="List of uploaded file paths to analyze"
    )
    pipeline_status: list[StageProgress] = Field(
        default_factory=list,
        description="Status of each pipeline stage"
    )
    ergebnis_pfad: Optional[str] = Field(
        None, description="Path to output results when complete"
    )
