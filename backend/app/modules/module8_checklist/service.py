from groq import Groq
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

EXCLUDED = ("tests/", "docs/", "examples/")


def _rank_files(db: Session, repo_id: int, top: int):
    files = db.execute(
        text("SELECT id, relative_path FROM repo_files WHERE repository_id = :r"),
        {"r": repo_id},
    ).all()
    path = {f[0]: f[1].replace("\\", "/") for f in files}

    rows = db.execute(
        text("SELECT from_file_id, to_file_id FROM dependency_edges WHERE repository_id = :r"),
        {"r": repo_id},
    ).all()
    edges = {(a, b) for a, b in rows if a in path and b in path and a != b}

    fan_in, fan_out = {}, {}
    for a, b in edges:
        fan_out[a] = fan_out.get(a, 0) + 1
        fan_in[b] = fan_in.get(b, 0) + 1

    candidates = [
        i for i, p in path.items()
        if p.endswith(".py")
        and not p.startswith(EXCLUDED)
        and not p.endswith("__init__.py")
    ]
    # most depended-on files first = the foundation a newcomer must know
    candidates.sort(key=lambda i: (fan_in.get(i, 0), fan_out.get(i, 0)), reverse=True)

    result = []
    for i in candidates[:top]:
        syms = db.execute(
            text(
                "SELECT symbol_type, name, docstring FROM parsed_symbols "
                "WHERE repo_file_id = :f AND symbol_type != 'import' "
                "ORDER BY lineno LIMIT 10"
            ),
            {"f": i},
        ).all()
        doc = next((s[2] for s in syms if s[2]), "")
        result.append({
            "path": path[i],
            "imported_by": fan_in.get(i, 0),
            "imports": fan_out.get(i, 0),
            "symbols": [f"{s[0]} {s[1]}" for s in syms],
            "doc": (doc or "")[:200],
        })
    return result


def build_checklist(db: Session, repo_id: int, top: int = 8):
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is missing in .env")

    files = _rank_files(db, repo_id, top)
    if not files:
        return {"checklist": "No files found. Run parse and graph build first.", "files": []}

    facts = "\n\n".join(
        f"{n}. {f['path']}\n"
        f"   imported by {f['imported_by']} files, imports {f['imports']} files\n"
        f"   contains: {', '.join(f['symbols']) or 'n/a'}\n"
        f"   docstring: {f['doc'] or 'n/a'}"
        for n, f in enumerate(files, 1)
    )
    prompt = (
        "Write an onboarding checklist for a new developer, in EXACTLY the order given. "
        "For each file write: one sentence on what it is for, and one sentence on what to look for "
        "when reading it, mentioning specific functions or classes by name. "
        "Do not talk about imports. Use only the facts given, do not invent anything. "
        "Use simple language and a numbered markdown list.\n\n" + facts
    )
    llm = Groq(api_key=settings.groq_api_key)
    resp = llm.chat.completions.create(
        model=settings.groq_model,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"checklist": resp.choices[0].message.content, "files": files}