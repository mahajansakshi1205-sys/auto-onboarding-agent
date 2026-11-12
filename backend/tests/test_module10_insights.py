"""Unit and API tests for Module 10 (insights): dependency map, impact analysis, health."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.modules.module10_insights import service
from app.modules.module10_insights.service import _is_core, build_map, build_impact
from app.routers import insights
from app.db import get_db

SCHEMA = """
CREATE TABLE repo_files(id INTEGER PRIMARY KEY, repository_id INT, relative_path TEXT, extension TEXT, size_bytes INT, line_count INT);
CREATE TABLE parsed_symbols(id INTEGER PRIMARY KEY, repo_file_id INT, symbol_type TEXT, name TEXT, lineno INT, docstring TEXT);
CREATE TABLE dependency_edges(id INTEGER PRIMARY KEY, repository_id INT, from_file_id INT, to_file_id INT, edge_type TEXT);
"""


@pytest.fixture()
def Session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as c:
        for stmt in SCHEMA.strip().split(";"):
            if stmt.strip():
                c.execute(text(stmt))
    return sessionmaker(bind=engine)


def add_graph(Session, files, edges, symbols=None, repo=1):
    """files: {id: path}; edges: [(from, to)]; symbols: [(file_id, type)]"""
    with Session() as s:
        for fid, path in files.items():
            s.execute(text("INSERT INTO repo_files VALUES (:i,:r,:p,'.py',10,100)"), {"i": fid, "r": repo, "p": path})
        for a, b in edges:
            s.execute(text("INSERT INTO dependency_edges(repository_id,from_file_id,to_file_id,edge_type) VALUES (:r,:a,:b,'import')"),
                      {"r": repo, "a": a, "b": b})
        for fid, typ in (symbols or []):
            s.execute(text("INSERT INTO parsed_symbols(repo_file_id,symbol_type,name,lineno) VALUES (:f,:t,'x',1)"), {"f": fid, "t": typ})
        s.commit()


# ---------- _is_core: which files count as project code ----------
@pytest.mark.parametrize("path,expected", [
    ("src/flask/app.py", True),
    ("utils/llm_helper.py", True),
    ("tests/test_basic.py", False),
    ("docs/conf.py", False),
    ("examples/tutorial/app.py", False),
    ("pkg/test_utils.py", False),
    ("pkg/utils_test.py", False),
    ("README.md", False),
])
def test_is_core_rules(path, expected):
    assert _is_core(path) is expected


# ---------- build_map ----------
def test_map_counts_files_and_links(Session):
    add_graph(Session, {1: "a.py", 2: "b.py", 3: "c.py"}, [(1, 2), (2, 3)])
    with Session() as s:
        m = build_map(s, 1)
    assert m["stats"]["files"] == 3
    assert m["stats"]["links"] == 2
    assert len(m["edges"]) == 2


def test_map_excludes_test_files(Session):
    add_graph(Session, {1: "a.py", 2: "tests/test_a.py"}, [(2, 1)])
    with Session() as s:
        m = build_map(s, 1)
    assert m["stats"]["files"] == 1
    assert m["stats"]["links"] == 0


def test_map_normalises_windows_paths(Session):
    add_graph(Session, {1: "src\\flask\\app.py"}, [])
    with Session() as s:
        m = build_map(s, 1)
    assert m["health"]["isolated"][0]["path"] == "src/flask/app.py"


def test_map_detects_circular_import(Session):
    add_graph(Session, {1: "a.py", 2: "b.py", 3: "c.py"}, [(1, 2), (2, 1), (2, 3)])
    with Session() as s:
        m = build_map(s, 1)
    assert m["stats"]["cycle_groups"] == 1
    assert m["health"]["cycles"][0]["size"] == 2
    flagged = {n["path"] for n in m["nodes"] if n["in_cycle"]}
    assert flagged == {"a.py", "b.py"}


def test_map_no_cycle_in_a_chain(Session):
    add_graph(Session, {1: "a.py", 2: "b.py", 3: "c.py"}, [(1, 2), (2, 3)])
    with Session() as s:
        assert build_map(s, 1)["stats"]["cycle_groups"] == 0


def test_map_lists_isolated_but_not_entry_files(Session):
    add_graph(Session, {1: "a.py", 2: "b.py", 3: "solo.py", 4: "pkg/__init__.py", 5: "setup.py"}, [(1, 2)])
    with Session() as s:
        m = build_map(s, 1)
    assert [f["path"] for f in m["health"]["isolated"]] == ["solo.py"]
    assert m["health"]["isolated_total"] == 1


def test_map_flags_heavily_coupled_file(Session):
    # hub imports 6 files and is imported by 6 files: degree 12 >= 10, fan_in/out >= 3
    files = {i: f"f{i}.py" for i in range(1, 14)}
    hub = 1
    edges = [(hub, i) for i in range(2, 8)] + [(i, hub) for i in range(8, 14)]
    add_graph(Session, files, edges)
    with Session() as s:
        m = build_map(s, 1)
    assert [c["path"] for c in m["health"]["coupled"]] == ["f1.py"]
    assert next(n for n in m["nodes"] if n["path"] == "f1.py")["god"] is True


def test_map_hub_that_nobody_imports_is_not_flagged_as_coupled(Session):
    # imports 12 files (fan_out 12) but fan_in is 1: heavily used AND dependent is required
    files = {i: f"f{i}.py" for i in range(1, 15)}
    edges = [(1, i) for i in range(2, 14)] + [(14, 1)]
    add_graph(Session, files, edges)
    with Session() as s:
        assert build_map(s, 1)["health"]["coupled"] == []


def test_map_small_project_hub_below_threshold_is_not_flagged(Session):
    # fan_in 3 and fan_out 3 but total degree 6 < 10: not "heavily coupled"
    files = {i: f"f{i}.py" for i in range(1, 8)}
    edges = [(1, 2), (1, 3), (1, 4), (5, 1), (6, 1), (7, 1)]
    add_graph(Session, files, edges)
    with Session() as s:
        assert build_map(s, 1)["health"]["coupled"] == []


def test_map_ignores_edges_stored_for_another_repository(Session):
    add_graph(Session, {1: "a.py", 2: "b.py"}, [], repo=1)
    with Session() as s:
        s.execute(text("INSERT INTO dependency_edges(repository_id,from_file_id,to_file_id,edge_type) VALUES (2,1,2,'import')"))
        s.commit()
        assert build_map(s, 1)["stats"]["links"] == 0


def test_map_counts_only_functions_and_classes_as_symbols(Session):
    add_graph(Session, {1: "a.py", 2: "b.py"}, [(1, 2)],
              symbols=[(1, "function"), (1, "class"), (1, "function"), (1, "import"), (1, "import")])
    with Session() as s:
        m = build_map(s, 1)
    assert next(n for n in m["nodes"] if n["path"] == "a.py")["symbols"] == 3


def test_map_ignores_self_edges(Session):
    add_graph(Session, {1: "a.py", 2: "b.py"}, [(1, 1), (1, 2)])
    with Session() as s:
        assert build_map(s, 1)["stats"]["links"] == 1


def test_map_limits_nodes_drawn(Session, monkeypatch):
    monkeypatch.setattr(service, "MAX_NODES", 5)
    files = {i: f"f{i}.py" for i in range(1, 21)}
    add_graph(Session, files, [(i, i + 1) for i in range(1, 20)])
    with Session() as s:
        m = build_map(s, 1)
    assert m["stats"]["shown"] == 5
    assert all(e["from"] in {n["id"] for n in m["nodes"]} and e["to"] in {n["id"] for n in m["nodes"]} for e in m["edges"])


def test_map_is_scoped_to_one_repository(Session):
    add_graph(Session, {1: "a.py", 2: "b.py"}, [(1, 2)], repo=1)
    add_graph(Session, {3: "x.py"}, [], repo=2)
    with Session() as s:
        assert build_map(s, 2)["stats"]["files"] == 1


def test_map_empty_repository(Session):
    with Session() as s:
        m = build_map(s, 99)
    assert m["nodes"] == [] and m["stats"]["files"] == 0


# ---------- build_impact ----------
def test_impact_direct_and_indirect(Session):
    # a -> b -> c : changing c affects b directly and a indirectly
    add_graph(Session, {1: "a.py", 2: "b.py", 3: "c.py"}, [(1, 2), (2, 3)])
    with Session() as s:
        r = build_impact(s, 1, 3)
    assert [f["path"] for f in r["direct"]] == ["b.py"]
    assert [f["path"] for f in r["indirect"]] == ["a.py"]
    assert r["total"] == 2


def test_impact_uses_lists_what_the_file_imports(Session):
    add_graph(Session, {1: "a.py", 2: "b.py", 3: "c.py"}, [(1, 2), (1, 3)])
    with Session() as s:
        r = build_impact(s, 1, 1)
    assert [f["path"] for f in r["uses"]] == ["b.py", "c.py"]
    assert r["total"] == 0


def test_impact_with_cycle_does_not_count_file_itself(Session):
    add_graph(Session, {1: "a.py", 2: "b.py"}, [(1, 2), (2, 1)])
    with Session() as s:
        r = build_impact(s, 1, 1)
    assert [f["path"] for f in r["direct"]] == ["b.py"]
    assert r["indirect"] == [] and r["total"] == 1


def test_impact_unknown_file_raises(Session):
    add_graph(Session, {1: "a.py"}, [])
    with Session() as s:
        with pytest.raises(ValueError):
            build_impact(s, 1, 42)


# ---------- HTTP layer ----------
@pytest.fixture()
def client(Session):
    add_graph(Session, {1: "a.py", 2: "b.py"}, [(1, 2)])
    app = FastAPI()
    app.include_router(insights.router)

    def override():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_api_map_returns_200_and_shape(client):
    r = client.get("/repos/1/map")
    assert r.status_code == 200
    assert set(r.json()) == {"nodes", "edges", "health", "stats"}


def test_api_impact_returns_200(client):
    r = client.get("/repos/1/impact/2")
    assert r.status_code == 200
    assert r.json()["total"] == 1


def test_api_impact_unknown_file_is_404(client):
    r = client.get("/repos/1/impact/999")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()
