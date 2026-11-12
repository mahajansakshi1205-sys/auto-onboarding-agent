from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.module7_diagram.service import build_mermaid

router = APIRouter(prefix="/repos", tags=["diagram"])


@router.get("/{repo_id}/diagram", response_class=PlainTextResponse)
def get_diagram(repo_id: int, max_nodes: int = 15, db: Session = Depends(get_db)):
    return build_mermaid(db, repo_id, max_nodes)