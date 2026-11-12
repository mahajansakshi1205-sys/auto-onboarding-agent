from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.module1_ingestion.models import Repository, RepoFile
from app.modules.module2_parser.models import ParsedSymbol
from app.modules.module2_parser.service import parse_repo_files

router = APIRouter(prefix="/repos", tags=["parsing"])


@router.post("/{repo_id}/parse")
def parse_repo(repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    files = db.query(RepoFile).filter(RepoFile.repository_id == repo_id).all()
    file_records = [{"id": f.id, "relative_path": f.relative_path, "extension": f.extension} for f in files]

    parsed = parse_repo_files(repo.local_path, file_records)

    # Clear old symbols for this repo's files, then save fresh ones
    file_ids = [f.id for f in files]
    db.query(ParsedSymbol).filter(ParsedSymbol.repo_file_id.in_(file_ids)).delete(synchronize_session=False)
    total_symbols = 0
    for repo_file_id, symbols in parsed.items():
        for sym in symbols:
            db.add(ParsedSymbol(repo_file_id=repo_file_id, **sym))
            total_symbols += 1
    db.commit()

    return {"repo_id": repo_id, "files_parsed": len(parsed), "symbols_found": total_symbols}


@router.get("/{repo_id}/symbols")
def list_symbols(repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    file_ids = [f.id for f in db.query(RepoFile).filter(RepoFile.repository_id == repo_id).all()]
    symbols = db.query(ParsedSymbol).filter(ParsedSymbol.repo_file_id.in_(file_ids)).all()
    return [
        {"repo_file_id": s.repo_file_id, "symbol_type": s.symbol_type, "name": s.name, "lineno": s.lineno}
        for s in symbols
    ]