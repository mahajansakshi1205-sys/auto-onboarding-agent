from sqlalchemy import text
from sqlalchemy.orm import Session

EXCLUDED = ("tests/", "docs/", "examples/")


def build_mermaid(db: Session, repo_id: int, max_nodes: int = 15) -> str:
    files = db.execute(
        text("SELECT id, relative_path FROM repo_files WHERE repository_id = :r"),
        {"r": repo_id},
    ).all()
    path = {f[0]: f[1].replace("\\", "/") for f in files}

    rows = db.execute(
        text("SELECT from_file_id, to_file_id FROM dependency_edges WHERE repository_id = :r"),
        {"r": repo_id},
    ).all()

    edges = set()
    for a, b in rows:
        if a in path and b in path and a != b:
            if not path[a].startswith(EXCLUDED) and not path[b].startswith(EXCLUDED):
                edges.add((a, b))

    degree = {}
    for a, b in edges:
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1

    top = set(sorted(degree, key=degree.get, reverse=True)[:max_nodes])
    kept = [(a, b) for a, b in edges if a in top and b in top]

    lines = ["graph LR"]
    for i in top:
        lines.append(f'    n{i}["{path[i]}"]')
    for a, b in kept:
        lines.append(f"    n{a} --> n{b}")
    return "\n".join(lines)