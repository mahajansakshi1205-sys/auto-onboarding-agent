from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.modules.module6_explain.service import explain

router = APIRouter(prefix="/repos", tags=["explain"])


class ExplainRequest(BaseModel):
    question: str
    top_k: int = 6


@router.post("/{repo_id}/explain")
def explain_repo(repo_id: int, body: ExplainRequest):
    try:
        return explain(repo_id, body.question, body.top_k)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explain failed: {e}")