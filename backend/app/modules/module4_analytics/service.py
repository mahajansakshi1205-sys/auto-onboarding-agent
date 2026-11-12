import io

import matplotlib
matplotlib.use("Agg")  # draw charts without opening a window (needed on a server)
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.modules.module1_ingestion.models import RepoFile
from app.modules.module2_parser.models import ParsedSymbol
from app.modules.module3_graph.models import DependencyEdge


def _minmax(series: pd.Series) -> pd.Series:
    """Scale values to 0..1 so different metrics can be compared and combined."""
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - lo) / (hi - lo)


EXCLUDED_DIRS = {"tests", "test", "docs", "doc", "examples", "example", "scripts"}


def _is_core_file(path: str) -> bool:
    """Skip tests, docs and examples so the ranking shows the real source code."""
    parts = path.replace("\\", "/").split("/")
    name = parts[-1]
    if {p.lower() for p in parts[:-1]} & EXCLUDED_DIRS:
        return False
    return not (name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py")

def build_metrics_dataframe(db: Session, repo_id: int) -> pd.DataFrame:
    files = (
        db.query(RepoFile)
        .filter(RepoFile.repository_id == repo_id, RepoFile.extension == ".py")
        .all()
    )
    files = [f for f in files if _is_core_file(f.relative_path)]
    if not files:
        return pd.DataFrame()

    file_ids = [f.id for f in files]
    df = pd.DataFrame(
        [{"file_id": f.id, "path": f.relative_path, "lines": f.line_count} for f in files]
    )

    # Count functions / classes / imports per file (from Module 2)
    symbols = db.query(ParsedSymbol).filter(ParsedSymbol.repo_file_id.in_(file_ids)).all()
    if symbols:
        sym_df = pd.DataFrame(
            [{"file_id": s.repo_file_id, "symbol_type": s.symbol_type} for s in symbols]
        )
        counts = sym_df.groupby(["file_id", "symbol_type"]).size().unstack(fill_value=0)
        counts = counts.reindex(columns=["function", "class", "import"], fill_value=0)
        counts.columns = ["functions", "classes", "imports"]
        df = df.merge(counts, left_on="file_id", right_index=True, how="left")
    for col in ["functions", "classes", "imports"]:
        if col not in df.columns:
            df[col] = 0
    df[["functions", "classes", "imports"]] = df[["functions", "classes", "imports"]].fillna(0).astype(int)

    # Rebuild the dependency graph from Module 3's saved edges
    graph = nx.DiGraph()
    graph.add_nodes_from(file_ids)
    edges = db.query(DependencyEdge).filter(DependencyEdge.repository_id == repo_id).all()
    graph.add_edges_from(
        (e.from_file_id, e.to_file_id)
        for e in edges
        if e.from_file_id in graph and e.to_file_id in graph
    )

    pagerank = nx.pagerank(graph) if graph.number_of_edges() > 0 else {n: 0.0 for n in graph}
    df["fan_in"] = df["file_id"].map(dict(graph.in_degree()))    # how many files import this one
    df["fan_out"] = df["file_id"].map(dict(graph.out_degree()))  # how many files this one imports
    df["pagerank"] = df["file_id"].map(pagerank)

    # Importance score: weighted mix of normalized metrics
    df["importance"] = (
        0.40 * _minmax(df["pagerank"])
        + 0.25 * _minmax(df["fan_in"])
        + 0.20 * _minmax(df["functions"] + df["classes"])
        + 0.15 * _minmax(df["lines"])
    )
    return df.sort_values("importance", ascending=False).reset_index(drop=True)


def make_importance_chart(df: pd.DataFrame, top: int = 10) -> bytes:
    top_df = df.head(top).iloc[::-1]  # reverse so the best file is at the top of the chart
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(top_df["path"], top_df["importance"], color="#1F3C88")
    ax.set_xlabel("Importance score (0 to 1)")
    ax.set_title(f"Top {len(top_df)} most important files")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()