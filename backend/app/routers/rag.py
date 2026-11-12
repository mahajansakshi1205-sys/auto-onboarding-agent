from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.module1_ingestion.models import Repository
from app.modules.module5_rag.service import index_repository, search_repository

router = APIRouter(prefix="/repos", tags=["rag"])


@router.post("/{repo_id}/index")
def index_repo(repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"repo_id": repo_id, **index_repository(db, repo_id)}


@router.get("/{repo_id}/search")
def search_repo(repo_id: int, q: str, top: int = 5):
    try:
        return {"query": q, "results": search_repository(repo_id, q, top)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))