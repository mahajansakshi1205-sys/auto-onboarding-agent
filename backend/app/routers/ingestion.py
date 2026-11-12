from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.module1_ingestion.models import Repository, RepoFile
from app.modules.module1_ingestion.schemas import IngestRequest, RepositoryOut, RepoFileOut
from app.modules.module1_ingestion.service import ingest_repository

router = APIRouter(prefix="/repos", tags=["ingestion"])


@router.post("/ingest", response_model=RepositoryOut)
def ingest(req: IngestRequest, db: Session = Depends(get_db)):
    repo = ingest_repository(db, req.repo_url)
    if repo.status == "failed":
        raise HTTPException(status_code=422, detail=repo.error_message)
    out = RepositoryOut.model_validate(repo)
    out.file_count = db.query(RepoFile).filter(RepoFile.repository_id == repo.id).count()
    return out


@router.get("", response_model=list[RepositoryOut])
def list_repos(db: Session = Depends(get_db)):
    repos = db.query(Repository).all()
    out = []
    for r in repos:
        item = RepositoryOut.model_validate(r)
        item.file_count = db.query(RepoFile).filter(RepoFile.repository_id == r.id).count()
        out.append(item)
    return out


@router.get("/{repo_id}/files", response_model=list[RepoFileOut])
def list_repo_files(repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return db.query(RepoFile).filter(RepoFile.repository_id == repo_id).all()