
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.services.auth_service import get_current_user, require_role
from backend.services.eval_service import eval_service

router = APIRouter(prefix="/api/eval", tags=["Evaluation & Ablation Hub"])

class RunAblationRequest(BaseModel):
    domain: str | None = "cloud_computing"
    target_lang: str | None = "hi"

@router.post("/run")
def run_ablation(
    req: RunAblationRequest,
    current_user: dict[str, Any] = Depends(require_role(["ADMIN"]))
):
    return eval_service.run_comprehensive_ablation(domain=req.domain)

@router.get("/latest")
def get_latest_results(
    current_user: dict[str, Any] = Depends(get_current_user)
):
    return eval_service.get_latest_eval_run()

@router.get("/runs")
def list_eval_runs(
    current_user: dict[str, Any] = Depends(get_current_user)
):
    return eval_service.list_eval_runs()

@router.post("/baselines")
def compare_baselines(
    req: RunAblationRequest,
    current_user: dict[str, Any] = Depends(require_role(["ADMIN"]))
):
    return eval_service.run_baselines_comparison(domain=req.domain)
