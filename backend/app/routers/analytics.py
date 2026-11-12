from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.module1_ingestion.models import Repository
from app.modules.module4_analytics.service import build_metrics_dataframe, make_importance_chart

router = APIRouter(prefix="/repos", tags=["analytics"])


def _get_metrics_or_error(db: Session, repo_id: int):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    df = build_metrics_dataframe(db, repo_id)
    if df.empty:
        raise HTTPException(status_code=400, detail="No Python files found. Run /parse first.")
    return df


@router.get("/{repo_id}/analytics")
def get_analytics(repo_id: int, top: int = 10, db: Session = Depends(get_db)):
    df = _get_metrics_or_error(db, repo_id)
    top_df = df.head(top).round(4)
    return {
        "repo_id": repo_id,
        "files_analyzed": len(df),
        "total_lines": int(df["lines"].sum()),
        "top_files": top_df.to_dict(orient="records"),
    }


@router.get("/{repo_id}/analytics/chart")
def get_analytics_chart(repo_id: int, top: int = 10, db: Session = Depends(get_db)):
    df = _get_metrics_or_error(db, repo_id)
    return Response(content=make_importance_chart(df, top), media_type="image/png")