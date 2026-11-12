import os
import re
import shutil
from urllib.parse import urlparse

from git import Repo as GitRepo, GitCommandError
from sqlalchemy.orm import Session

from app.config import settings
from app.modules.module1_ingestion.models import Repository, RepoFile

IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".next", ".pytest_cache", "coverage", ".idea", ".vscode", "vendor", "target",
}

TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".php",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".rs", ".md", ".json", ".yaml",
    ".yml", ".html", ".css", ".sql",
}

MAX_FILE_SIZE_BYTES = 2_000_000


def parse_owner_repo(repo_url: str) -> tuple[str, str]:
    path = urlparse(str(repo_url)).path.strip("/")
    path = re.sub(r"\.git$", "", path)
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Could not parse owner/repo from URL: {repo_url}")
    return parts[0], parts[1]


def clone_repo(repo_url: str, dest_dir: str) -> str:
    if os.path.isdir(dest_dir) and os.path.isdir(os.path.join(dest_dir, ".git")):
        return dest_dir
    if os.path.isdir(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(os.path.dirname(dest_dir), exist_ok=True)
    GitRepo.clone_from(str(repo_url), dest_dir, depth=1)
    return dest_dir


def walk_repo_files(local_path: str) -> list[dict]:
    results = []
    for root, dirs, files in os.walk(local_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                size = os.path.getsize(fpath)
            except OSError:
                continue
            if size > MAX_FILE_SIZE_BYTES:
                continue

            ext = os.path.splitext(fname)[1].lower()
            rel_path = os.path.relpath(fpath, local_path)

            line_count = 0
            if ext in TEXT_EXTENSIONS:
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        line_count = sum(1 for _ in f)
                except OSError:
                    pass

            results.append({
                "relative_path": rel_path,
                "extension": ext or None,
                "size_bytes": size,
                "line_count": line_count,
            })
    return results


def ingest_repository(db: Session, repo_url: str) -> Repository:
    owner, name = parse_owner_repo(repo_url)

    existing = db.query(Repository).filter(Repository.url == str(repo_url)).first()
    if existing:
        repo_row = existing
        repo_row.status = "cloning"
        db.commit()
    else:
        dest_dir = os.path.join(settings.repo_storage_dir, owner, name)
        repo_row = Repository(url=str(repo_url), owner=owner, name=name,
                               local_path=dest_dir, status="cloning")
        db.add(repo_row)
        db.commit()
        db.refresh(repo_row)

    try:
        local_path = clone_repo(repo_url, repo_row.local_path)
        file_records = walk_repo_files(local_path)

        db.query(RepoFile).filter(RepoFile.repository_id == repo_row.id).delete()
        for rec in file_records:
            db.add(RepoFile(repository_id=repo_row.id, **rec))

        repo_row.status = "ready"
        repo_row.error_message = None
        db.commit()
        db.refresh(repo_row)
    except (GitCommandError, ValueError, OSError) as exc:
        repo_row.status = "failed"
        repo_row.error_message = str(exc)
        db.commit()
        db.refresh(repo_row)

    return repo_row