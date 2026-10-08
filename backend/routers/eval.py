from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.services.eval_service import eval_service

router = APIRouter(prefix="/api/eval", tags=["Evaluation & Ablation Hub"])

class RunAblationRequest(BaseModel):
    domain: Optional[str] = "cloud_computing"

@router.post("/run")
def run_ablation(req: RunAblationRequest):
    return eval_service.run_comprehensive_ablation(domain=req.domain)

@router.get("/latest")
def get_latest_results():
    return eval_service.get_latest_eval_run()

@router.post("/baselines")
def compare_baselines(req: RunAblationRequest):
    return eval_service.run_baselines_comparison(domain=req.domain)
