import networkx as nx
from sqlalchemy import text
from sqlalchemy.orm import Session

SKIP_DIRS = {"tests", "test", "docs", "examples", "doc", "example"}
ENTRY_NAMES = {"setup.py", "conftest.py", "manage.py", "__main__.py", "wsgi.py", "asgi.py"}
MAX_NODES = 40


def _is_core(path: str) -> bool:
    parts = path.split("/")
    name = parts[-1]
    if not name.endswith(".py"):
        return False
    if any(p in SKIP_DIRS for p in parts[:-1]):
        return False
    if name.startswith("test_") or name.endswith("_test.py"):
        return False
    return True


def _load(db: Session, repo_id: int):
    """Return (graph, info). Edge A -> B means 'A imports B'."""
    rows = db.execute(
        text("SELECT id, relative_path, line_count FROM repo_files WHERE repository_id = :r"),
        {"r": repo_id},
    ).all()
    info = {}
    for fid, path, loc in rows:
        p = path.replace("\\", "/")
        if _is_core(p):
            info[fid] = {"id": fid, "path": p, "label": p.split("/")[-1], "loc": loc or 0, "symbols": 0}

    sym_rows = db.execute(
        text(
            "SELECT s.repo_file_id, COUNT(*) FROM parsed_symbols s "
            "JOIN repo_files f ON f.id = s.repo_file_id "
            "WHERE f.repository_id = :r AND s.symbol_type != 'import' "
            "GROUP BY s.repo_file_id"
        ),
        {"r": repo_id},
    ).all()
    for fid, n in sym_rows:
        if fid in info:
            info[fid]["symbols"] = n

    edge_rows = db.execute(
        text("SELECT from_file_id, to_file_id FROM dependency_edges WHERE repository_id = :r"),
        {"r": repo_id},
    ).all()
    G = nx.DiGraph()
    G.add_nodes_from(info)
    for a, b in edge_rows:
        if a in info and b in info and a != b:
            G.add_edge(a, b)

    for fid, d in info.items():
        d["fan_in"] = G.in_degree(fid)
        d["fan_out"] = G.out_degree(fid)
    return G, info


def _ref(info, fid):
    return {"id": fid, "path": info[fid]["path"]}


def build_map(db: Session, repo_id: int):
    G, info = _load(db, repo_id)
    degree = {f: info[f]["fan_in"] + info[f]["fan_out"] for f in info}

    # --- health checks ---
    in_cycle = set()
    cycles = []
    for comp in nx.strongly_connected_components(G):
        if len(comp) > 1:
            in_cycle |= comp
            cycles.append(comp)
    cycles.sort(key=len, reverse=True)

    degs = sorted(degree.values())
    p90 = degs[int(0.9 * (len(degs) - 1))] if degs else 0
    threshold = max(10, p90)
    god = [
        f for f in info
        if degree[f] >= threshold and info[f]["fan_in"] >= 3 and info[f]["fan_out"] >= 3
    ]
    god.sort(key=lambda f: degree[f], reverse=True)

    orphans = [
        f for f in info
        if degree[f] == 0
        and not info[f]["path"].endswith("__init__.py")
        and info[f]["label"] not in ENTRY_NAMES
    ]

    health = {
        "cycles": [
            {"size": len(c), "files": [_ref(info, f) for f in sorted(c, key=lambda x: info[x]["path"])]}
            for c in cycles
        ],
        "coupled": [
            {**_ref(info, f), "fan_in": info[f]["fan_in"], "fan_out": info[f]["fan_out"]}
            for f in god[:8]
        ],
        "isolated": [_ref(info, f) for f in sorted(orphans, key=lambda x: info[x]["path"])[:12]],
        "isolated_total": len(orphans),
    }

    # --- nodes/edges to draw: the most connected files ---
    connected = [f for f in info if degree[f] > 0]
    connected.sort(key=lambda f: degree[f], reverse=True)
    keep = connected[:MAX_NODES]
    keep_set = set(keep)
    nodes = [
        {**info[f], "god": f in god, "in_cycle": f in in_cycle}
        for f in keep
    ]
    edges = [{"from": a, "to": b} for a, b in G.edges if a in keep_set and b in keep_set]

    return {
        "nodes": nodes,
        "edges": edges,
        "health": health,
        "stats": {
            "files": len(info),
            "links": G.number_of_edges(),
            "cycle_groups": len(cycles),
            "shown": len(nodes),
        },
    }


def build_impact(db: Session, repo_id: int, file_id: int):
    G, info = _load(db, repo_id)
    if file_id not in G:
        raise ValueError("File not found in this repository's dependency graph")

    direct = set(G.predecessors(file_id))          # files that import this one
    everyone = nx.ancestors(G, file_id)            # files that depend on it, any depth
    indirect = everyone - direct - {file_id}
    uses = set(G.successors(file_id))              # files this one imports

    def pack(ids):
        return [_ref(info, f) for f in sorted(ids, key=lambda x: info[x]["path"])]

    return {
        "file": _ref(info, file_id),
        "direct": pack(direct),
        "indirect": pack(indirect),
        "uses": pack(uses),
        "total": len(direct | indirect),
    }
