from __future__ import annotations

from fastapi import APIRouter

from api import deps  # noqa: F401

from run_eval import run_evaluation
from run_intelligence_eval import run_intelligence_evaluation

router = APIRouter(tags=["evaluation"])


@router.get("/evaluation")
def get_evaluation() -> dict:
    return {**run_evaluation(), "intelligence_modules": run_intelligence_evaluation()}
