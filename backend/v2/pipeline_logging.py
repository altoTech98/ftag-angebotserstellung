"""
Structured step logging helper for the v2 pipeline.

Produces INFO-level log records with extra fields for structured JSON logging.
All pipeline stages use this helper for consistent observability.
"""

import logging
from typing import Optional


logger = logging.getLogger("v2.pipeline")


def log_step(
    tender_id: str,
    stage: str,
    position_nr: str,
    pass_num: int,
    result: str,
    details: Optional[dict] = None,
) -> None:
    """Log a structured pipeline step.

    Args:
        tender_id: Unique tender/analysis identifier.
        stage: Pipeline stage name (e.g. 'matching', 'extraction').
        position_nr: Position number being processed.
        pass_num: Pass number within the stage (1, 2, 3...).
        result: Step outcome description.
        details: Optional additional details dict.
    """
    message = f"[{tender_id}] {stage} | Position {position_nr} | Pass {pass_num} | Result: {result}"
    logger.info(
        message,
        extra={
            "tender_id": tender_id,
            "stage": stage,
            "position_nr": position_nr,
            "pass_num": pass_num,
            "result": result,
            "details": details,
        },
    )
