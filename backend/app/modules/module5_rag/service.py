import ast
import os

import chromadb
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.config import settings
from app.modules.module1_ingestion.models import Repository, RepoFile

MAX_CHARS = 1500
_model = None


def _get_model() -> SentenceTransformer:
    """Load the embedding model once and reuse it (loading is slow)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def _get_client():
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


def chunk_python_file(source: str, path: str) -> list[dict]:
    """Split a Python file into one chunk per function/class."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines()
    chunks = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            start = node.lineno
            end = node.end_lineno or node.lineno
            code = "\n".join(lines[start - 1:end])[:MAX_CHARS]
            chunks.append({
                "text": f"# {path}\n{code}",  # path in the text helps the search
                "path": path,
                "name": node.name,
                "kind": kind,
                "start_line": start,
                "end_line": end,
            })

    # Files with no functions/classes (config, constants): index the top of the file
    if not chunks and source.strip():
        chunks.append({
            "text": f"# {path}\n{source[:MAX_CHARS]}",
            "path": path,
            "name": os.path.basename(path),
            "kind": "module",
            "start_line": 1,
            "end_line": len(lines),
        })
    return chunks


def index_repository(db: Session, repo_id: int) -> dict:
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    files = (
        db.query(RepoFile)
        .filter(RepoFile.repository_id == repo_id, RepoFile.extension == ".py")
        .all()
    )

    all_chunks = []
    for f in files:
        full_path = os.path.join(repo.local_path, f.relative_path)
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
                source = fh.read()
        except OSError:
            continue
        all_chunks.extend(chunk_python_file(source, f.relative_path.replace("\\", "/")))

    if not all_chunks:
        return {"files": len(files), "chunks_indexed": 0}

    embeddings = _get_model().encode(
        [c["text"] for c in all_chunks],
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
    )

    client = _get_client()
    name = f"repo_{repo_id}"
    try:
        client.delete_collection(name)  # re-indexing starts fresh
    except Exception:
        pass
    collection = client.create_collection(name, metadata={"hnsw:space": "cosine"})

    for i in range(0, len(all_chunks), 500):
        batch = all_chunks[i:i + 500]
        collection.add(
            ids=[f"{repo_id}-{i + j}" for j in range(len(batch))],
            documents=[c["text"] for c in batch],
            embeddings=embeddings[i:i + 500].tolist(),
            metadatas=[
                {k: c[k] for k in ("path", "name", "kind", "start_line", "end_line")}
                for c in batch
            ],
        )

    return {"files": len(files), "chunks_indexed": len(all_chunks)}


def search_repository(repo_id: int, query: str, top: int = 5) -> list[dict]:
    client = _get_client()
    try:
        collection = client.get_collection(f"repo_{repo_id}")
    except Exception:
        raise ValueError(f"Repo {repo_id} is not indexed yet. Run POST /repos/{repo_id}/index first.")

    query_embedding = _get_model().encode([query], normalize_embeddings=True).tolist()
    res = collection.query(query_embeddings=query_embedding, n_results=top)

    results = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        results.append({**meta, "score": round(1 - dist, 4), "snippet": doc[:400]})
    return results