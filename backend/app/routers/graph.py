from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.module1_ingestion.models import Repository
from app.modules.module3_graph.models import DependencyEdge
from app.modules.module3_graph.service import build_dependency_graph, compute_graph_stats

router = APIRouter(prefix="/repos", tags=["graph"])


@router.post("/{repo_id}/graph/build")
def build_graph(repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    graph = build_dependency_graph(db, repo_id)
    stats = compute_graph_stats(graph)
    return {"repo_id": repo_id, **stats}


@router.get("/{repo_id}/graph/edges")
def list_edges(repo_id: int, db: Session = Depends(get_db)):
    edges = db.query(DependencyEdge).filter(DependencyEdge.repository_id == repo_id).all()
    return [{"from_file_id": e.from_file_id, "to_file_id": e.to_file_id, "type": e.edge_type} for e in edges]