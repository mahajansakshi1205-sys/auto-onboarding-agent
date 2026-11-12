from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.module10_insights.service import build_impact, build_map

router = APIRouter(prefix="/repos", tags=["insights"])


@router.get("/{repo_id}/map")
def get_map(repo_id: int, db: Session = Depends(get_db)):
    return build_map(db, repo_id)


@router.get("/{repo_id}/impact/{file_id}")
def get_impact(repo_id: int, file_id: int, db: Session = Depends(get_db)):
    try:
        return build_impact(db, repo_id, file_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
