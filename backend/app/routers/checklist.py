from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.module8_checklist.service import build_checklist

router = APIRouter(prefix="/repos", tags=["checklist"])


@router.get("/{repo_id}/checklist")
def get_checklist(repo_id: int, top: int = 8, db: Session = Depends(get_db)):
    try:
        return build_checklist(db, repo_id, top)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checklist failed: {e}")