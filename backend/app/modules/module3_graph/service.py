import os
import networkx as nx

from sqlalchemy.orm import Session

from app.modules.module1_ingestion.models import RepoFile
from app.modules.module2_parser.models import ParsedSymbol
from app.modules.module3_graph.models import DependencyEdge

SOURCE_ROOTS = {"src", "lib"}  # folders that are not part of the import name


def _module_name_from_path(relative_path: str) -> str:
    """'src/flask/app.py' -> 'src.flask.app', 'src/flask/__init__.py' -> 'src.flask'"""
    no_ext = os.path.splitext(relative_path)[0]
    name = no_ext.replace(os.sep, ".").replace("/", ".")
    if name.endswith(".__init__"):
        name = name[: -len(".__init__")]
    return name


def build_dependency_graph(db: Session, repo_id: int) -> nx.DiGraph:
    files = db.query(RepoFile).filter(RepoFile.repository_id == repo_id).all()
    file_ids = [f.id for f in files]
    file_by_id = {f.id: f for f in files}

    # Map every importable module name -> file id
    module_to_file_id = {}
    for f in files:
        if f.extension != ".py":
            continue
        mod = _module_name_from_path(f.relative_path)
        module_to_file_id[mod] = f.id
        parts = mod.split(".")
        if len(parts) > 1 and parts[0] in SOURCE_ROOTS:
            module_to_file_id[".".join(parts[1:])] = f.id  # 'flask.app' also works

    imports = (
        db.query(ParsedSymbol)
        .filter(ParsedSymbol.repo_file_id.in_(file_ids), ParsedSymbol.symbol_type == "import")
        .all()
    )

    graph = nx.DiGraph()
    for f in files:
        graph.add_node(f.id, path=f.relative_path)

    edges_to_save = set()
    for imp in imports:
        parts = imp.name.split(".")
        matched_file_id = None

        # Try 1: absolute import - longest prefix that is a real module in the repo
        for i in range(len(parts), 0, -1):
            candidate = ".".join(parts[:i])
            if candidate in module_to_file_id:
                matched_file_id = module_to_file_id[candidate]
                break

        # Try 2: relative import - look only inside the importing file's own package
        if not matched_file_id:
            importer = file_by_id[imp.repo_file_id]
            folder = os.path.dirname(importer.relative_path)
            package = _module_name_from_path(folder) if folder else ""
            for i in range(len(parts), 0, -1):
                candidate = ".".join(parts[:i])
                key = f"{package}.{candidate}" if package else candidate
                if key in module_to_file_id:
                    matched_file_id = module_to_file_id[key]
                    break

        if matched_file_id and matched_file_id != imp.repo_file_id:
            graph.add_edge(imp.repo_file_id, matched_file_id, type="import")
            edges_to_save.add((imp.repo_file_id, matched_file_id))

    db.query(DependencyEdge).filter(DependencyEdge.repository_id == repo_id).delete()
    for from_id, to_id in edges_to_save:
        db.add(DependencyEdge(repository_id=repo_id, from_file_id=from_id, to_file_id=to_id))
    db.commit()

    return graph


def compute_graph_stats(graph: nx.DiGraph) -> dict:
    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "is_dag": nx.is_directed_acyclic_graph(graph),
    }